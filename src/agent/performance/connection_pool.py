#!/usr/bin/env python3
"""
MCP Connection Pool

High-performance connection pooling for MCP clients to reduce connection overhead
and improve response times.

Author: Claude Code
Date: 2025-07-14
Phase: 4.6 - Performance Optimization
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from enum import Enum
import weakref
from pathlib import Path
import json

# Add parent directory to path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from ..context.context_manager import ContextManager
from ...mcp_client.client_manager import MCPClientManager, ClientType
from ...mcp_client.base_client import BaseMCPClient

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Connection state enumeration"""
    IDLE = "idle"
    ACTIVE = "active"
    RECONNECTING = "reconnecting"
    CLOSED = "closed"
    ERROR = "error"


@dataclass
class ConnectionInfo:
    """Information about a pooled connection"""
    client: BaseMCPClient
    client_type: ClientType
    state: ConnectionState
    created_at: float
    last_used: float
    use_count: int
    error_count: int
    connection_id: str
    
    def __post_init__(self):
        if self.created_at == 0:
            self.created_at = time.time()
        if self.last_used == 0:
            self.last_used = time.time()


@dataclass
class PoolConfig:
    """Connection pool configuration"""
    max_connections_per_type: int = 5
    min_connections_per_type: int = 1
    connection_timeout: float = 30.0
    idle_timeout: float = 300.0  # 5 minutes
    max_retries: int = 3
    retry_delay: float = 1.0
    health_check_interval: float = 60.0  # 1 minute
    enable_prewarming: bool = True
    cleanup_interval: float = 30.0  # 30 seconds


class MCPConnectionPool:
    """
    High-performance connection pool for MCP clients.
    
    Features:
    - Connection reuse and pooling
    - Automatic connection health monitoring
    - Graceful connection recovery
    - Load balancing across connections
    - Connection prewarming
    - Automatic cleanup of stale connections
    """
    
    def __init__(self, config: PoolConfig = None):
        self.config = config or PoolConfig()
        self.pools: Dict[ClientType, List[ConnectionInfo]] = {}
        self.active_connections: Dict[str, ConnectionInfo] = {}
        self.connection_counter = 0
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "pool_hits": 0,
            "pool_misses": 0,
            "reconnections": 0,
            "errors": 0
        }
        
        # Initialize pools for each client type
        for client_type in ClientType:
            self.pools[client_type] = []
        
        # Background tasks
        self._cleanup_task = None
        self._health_check_task = None
        self._running = False
        
    async def initialize(self, client_manager: MCPClientManager):
        """Initialize connection pool"""
        logger.info("Initializing MCP connection pool...")
        
        self.client_manager = client_manager
        self._running = True
        
        # Start background tasks
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        # Prewarm connections if enabled
        if self.config.enable_prewarming:
            await self._prewarm_connections()
        
        logger.info(f"Connection pool initialized with {sum(len(pool) for pool in self.pools.values())} connections")
    
    async def get_connection(self, client_type: ClientType) -> Optional[ConnectionInfo]:
        """Get a connection from the pool"""
        try:
            # Try to get an idle connection from pool
            pool = self.pools.get(client_type, [])
            
            for conn_info in pool:
                if conn_info.state == ConnectionState.IDLE:
                    # Mark as active
                    conn_info.state = ConnectionState.ACTIVE
                    conn_info.last_used = time.time()
                    conn_info.use_count += 1
                    
                    self.active_connections[conn_info.connection_id] = conn_info
                    self.stats["pool_hits"] += 1
                    
                    logger.debug(f"Reusing connection {conn_info.connection_id} for {client_type.value}")
                    return conn_info
            
            # No idle connection available, create new one if under limit
            if len(pool) < self.config.max_connections_per_type:
                conn_info = await self._create_connection(client_type)
                if conn_info:
                    self.stats["pool_misses"] += 1
                    return conn_info
            
            # Pool is full, wait for connection to become available
            logger.warning(f"Connection pool full for {client_type.value}, waiting...")
            return await self._wait_for_connection(client_type)
            
        except Exception as e:
            logger.error(f"Error getting connection for {client_type.value}: {e}")
            self.stats["errors"] += 1
            return None
    
    async def return_connection(self, connection_id: str):
        """Return a connection to the pool"""
        try:
            conn_info = self.active_connections.pop(connection_id, None)
            if not conn_info:
                logger.warning(f"Connection {connection_id} not found in active connections")
                return
            
            # Mark as idle
            conn_info.state = ConnectionState.IDLE
            conn_info.last_used = time.time()
            
            logger.debug(f"Returned connection {connection_id} to pool")
            
        except Exception as e:
            logger.error(f"Error returning connection {connection_id}: {e}")
    
    async def execute_with_pool(self, client_type: ClientType, 
                              tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool using a pooled connection"""
        conn_info = await self.get_connection(client_type)
        
        if not conn_info:
            return {
                "success": False,
                "error": f"No connection available for {client_type.value}"
            }
        
        try:
            # Execute tool using the connection
            result = await conn_info.client.call_tool(tool_name, parameters)
            
            # Return connection to pool
            await self.return_connection(conn_info.connection_id)
            
            return {
                "success": True,
                "result": result,
                "connection_id": conn_info.connection_id,
                "use_count": conn_info.use_count
            }
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name} on {client_type.value}: {e}")
            
            # Handle connection error
            await self._handle_connection_error(conn_info, e)
            
            return {
                "success": False,
                "error": str(e),
                "connection_id": conn_info.connection_id
            }
    
    async def _create_connection(self, client_type: ClientType) -> Optional[ConnectionInfo]:
        """Create a new connection"""
        try:
            # Get client info from manager
            client_info = self.client_manager.available_clients.get(client_type)
            if not client_info:
                logger.error(f"No client info available for {client_type.value}")
                return None
            
            # Create new client instance
            client = client_info.client_class()
            
            # Initialize client
            if await client.initialize():
                self.connection_counter += 1
                connection_id = f"{client_type.value}_{self.connection_counter}"
                
                conn_info = ConnectionInfo(
                    client=client,
                    client_type=client_type,
                    state=ConnectionState.ACTIVE,
                    created_at=time.time(),
                    last_used=time.time(),
                    use_count=1,
                    error_count=0,
                    connection_id=connection_id
                )
                
                # Add to pool
                self.pools[client_type].append(conn_info)
                self.active_connections[connection_id] = conn_info
                
                self.stats["total_connections"] += 1
                self.stats["active_connections"] += 1
                
                logger.debug(f"Created new connection {connection_id} for {client_type.value}")
                return conn_info
            
            else:
                logger.error(f"Failed to initialize connection for {client_type.value}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating connection for {client_type.value}: {e}")
            return None
    
    async def _wait_for_connection(self, client_type: ClientType) -> Optional[ConnectionInfo]:
        """Wait for a connection to become available"""
        start_time = time.time()
        
        while time.time() - start_time < self.config.connection_timeout:
            # Check if any connections became idle
            pool = self.pools.get(client_type, [])
            for conn_info in pool:
                if conn_info.state == ConnectionState.IDLE:
                    return await self.get_connection(client_type)
            
            # Wait a bit before checking again
            await asyncio.sleep(0.1)
        
        logger.error(f"Timeout waiting for connection to {client_type.value}")
        return None
    
    async def _handle_connection_error(self, conn_info: ConnectionInfo, error: Exception):
        """Handle connection error"""
        conn_info.error_count += 1
        conn_info.state = ConnectionState.ERROR
        
        # Remove from active connections
        self.active_connections.pop(conn_info.connection_id, None)
        
        logger.error(f"Connection {conn_info.connection_id} error: {error}")
        
        # Try to reconnect if under retry limit
        if conn_info.error_count <= self.config.max_retries:
            asyncio.create_task(self._reconnect_connection(conn_info))
        else:
            # Remove from pool
            await self._remove_connection(conn_info)
    
    async def _reconnect_connection(self, conn_info: ConnectionInfo):
        """Reconnect a failed connection"""
        try:
            conn_info.state = ConnectionState.RECONNECTING
            
            # Wait before reconnecting
            await asyncio.sleep(self.config.retry_delay * conn_info.error_count)
            
            # Try to reconnect
            if await conn_info.client.initialize():
                conn_info.state = ConnectionState.IDLE
                conn_info.error_count = 0
                conn_info.last_used = time.time()
                
                self.stats["reconnections"] += 1
                logger.info(f"Reconnected connection {conn_info.connection_id}")
            else:
                await self._remove_connection(conn_info)
                
        except Exception as e:
            logger.error(f"Failed to reconnect {conn_info.connection_id}: {e}")
            await self._remove_connection(conn_info)
    
    async def _remove_connection(self, conn_info: ConnectionInfo):
        """Remove a connection from the pool"""
        try:
            # Remove from pool
            pool = self.pools.get(conn_info.client_type, [])
            if conn_info in pool:
                pool.remove(conn_info)
            
            # Remove from active connections
            self.active_connections.pop(conn_info.connection_id, None)
            
            # Shutdown client
            try:
                await conn_info.client.shutdown()
            except:
                pass
            
            conn_info.state = ConnectionState.CLOSED
            
            self.stats["total_connections"] -= 1
            if conn_info.connection_id in self.active_connections:
                self.stats["active_connections"] -= 1
            
            logger.debug(f"Removed connection {conn_info.connection_id}")
            
        except Exception as e:
            logger.error(f"Error removing connection {conn_info.connection_id}: {e}")
    
    async def _prewarm_connections(self):
        """Prewarm connections for each client type"""
        logger.info("Prewarming connection pools...")
        
        for client_type in ClientType:
            for _ in range(self.config.min_connections_per_type):
                conn_info = await self._create_connection(client_type)
                if conn_info:
                    # Mark as idle immediately
                    conn_info.state = ConnectionState.IDLE
                    self.active_connections.pop(conn_info.connection_id, None)
                    self.stats["active_connections"] -= 1
        
        logger.info(f"Prewarmed {sum(len(pool) for pool in self.pools.values())} connections")
    
    async def _cleanup_loop(self):
        """Background task to clean up stale connections"""
        while self._running:
            try:
                await asyncio.sleep(self.config.cleanup_interval)
                await self._cleanup_stale_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    async def _cleanup_stale_connections(self):
        """Clean up stale connections"""
        current_time = time.time()
        
        for client_type, pool in self.pools.items():
            connections_to_remove = []
            
            for conn_info in pool:
                # Check if connection is stale
                if (conn_info.state == ConnectionState.IDLE and 
                    current_time - conn_info.last_used > self.config.idle_timeout):
                    connections_to_remove.append(conn_info)
            
            # Remove stale connections
            for conn_info in connections_to_remove:
                if len(pool) > self.config.min_connections_per_type:
                    await self._remove_connection(conn_info)
    
    async def _health_check_loop(self):
        """Background task to perform health checks"""
        while self._running:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                await self._health_check_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
    
    async def _health_check_connections(self):
        """Perform health checks on all connections"""
        for client_type, pool in self.pools.items():
            for conn_info in pool:
                if conn_info.state == ConnectionState.IDLE:
                    try:
                        # Simple health check - try to get tools
                        if hasattr(conn_info.client, 'get_available_tools'):
                            await asyncio.wait_for(
                                conn_info.client.get_available_tools(),
                                timeout=5.0
                            )
                    except Exception as e:
                        logger.warning(f"Health check failed for {conn_info.connection_id}: {e}")
                        await self._handle_connection_error(conn_info, e)
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        pool_stats = {}
        
        for client_type, pool in self.pools.items():
            pool_stats[client_type.value] = {
                "total_connections": len(pool),
                "idle_connections": len([c for c in pool if c.state == ConnectionState.IDLE]),
                "active_connections": len([c for c in pool if c.state == ConnectionState.ACTIVE]),
                "error_connections": len([c for c in pool if c.state == ConnectionState.ERROR]),
                "reconnecting_connections": len([c for c in pool if c.state == ConnectionState.RECONNECTING])
            }
        
        return {
            "global_stats": self.stats,
            "pool_stats": pool_stats,
            "config": {
                "max_connections_per_type": self.config.max_connections_per_type,
                "min_connections_per_type": self.config.min_connections_per_type,
                "connection_timeout": self.config.connection_timeout,
                "idle_timeout": self.config.idle_timeout
            }
        }
    
    async def shutdown(self):
        """Shutdown connection pool"""
        logger.info("Shutting down connection pool...")
        
        self._running = False
        
        # Cancel background tasks
        if self._cleanup_task:
            self._cleanup_task.cancel()
        if self._health_check_task:
            self._health_check_task.cancel()
        
        # Close all connections
        for client_type, pool in self.pools.items():
            for conn_info in pool:
                try:
                    await conn_info.client.shutdown()
                except:
                    pass
        
        # Clear pools
        self.pools.clear()
        self.active_connections.clear()
        
        logger.info("Connection pool shutdown complete")