"""
MCP Client Manager

Manages multiple MCP clients and provides unified interface for task routing.

Author: Claude Code
Date: 2025-07-13
Phase: 2.1
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Type
from dataclasses import dataclass
from enum import Enum

from .base_client import BaseMCPClient, MCPClientConfig
from .filesystem_client import FilesystemMCPClient
from .desktop_client import DesktopMCPClient
from .system_client import SystemMCPClient
from ..agent.core.task_router import TaskRouter, TaskCategory, RoutingDecision
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ClientType(Enum):
    """Available MCP client types"""
    FILESYSTEM = "filesystem"
    DESKTOP = "desktop"
    SYSTEM = "system"


@dataclass
class ClientInfo:
    """Information about a registered MCP client"""
    client_type: ClientType
    client_class: Type[BaseMCPClient]
    categories: List[TaskCategory]
    priority: int = 1  # Higher number = higher priority


class MCPClientManager:
    """
    Manager for multiple MCP clients with intelligent task routing.
    
    Features:
    - Multiple MCP client management
    - Intelligent task routing based on categories
    - Load balancing and failover
    - Health monitoring
    - Configuration management
    """
    
    def __init__(self):
        """Initialize MCP client manager"""
        self.clients: Dict[ClientType, BaseMCPClient] = {}
        self.client_configs: Dict[ClientType, MCPClientConfig] = {}
        self.task_router = TaskRouter()
        
        # Register available client types
        self.available_clients: Dict[ClientType, ClientInfo] = {
            ClientType.FILESYSTEM: ClientInfo(
                client_type=ClientType.FILESYSTEM,
                client_class=FilesystemMCPClient,
                categories=[TaskCategory.FILE_OPERATIONS, TaskCategory.DATA_ANALYSIS],
                priority=3
            ),
            ClientType.DESKTOP: ClientInfo(
                client_type=ClientType.DESKTOP,
                client_class=DesktopMCPClient,
                categories=[TaskCategory.DESKTOP_AUTOMATION],
                priority=2
            ),
            ClientType.SYSTEM: ClientInfo(
                client_type=ClientType.SYSTEM,
                client_class=SystemMCPClient,
                categories=[TaskCategory.SYSTEM_MONITORING, TaskCategory.SYSTEM_INTERACTION],
                priority=2
            )
        }
        
        logger.info("MCP client manager initialized")
    
    async def initialize(self, client_configs: Dict[str, MCPClientConfig] = None) -> bool:
        """
        Initialize all configured MCP clients.
        
        Args:
            client_configs: Optional configurations for clients
            
        Returns:
            True if at least one client initialized successfully
        """
        logger.info("Initializing MCP clients...")
        
        success_count = 0
        
        for client_type, client_info in self.available_clients.items():
            try:
                # Get configuration
                config = None
                if client_configs and client_type.value in client_configs:
                    config = client_configs[client_type.value]
                
                # Create and initialize client
                client = client_info.client_class(config)
                if await client.initialize():
                    self.clients[client_type] = client
                    success_count += 1
                    logger.info(f"Initialized {client_type.value} MCP client")
                else:
                    logger.warning(f"Failed to initialize {client_type.value} MCP client")
                    
            except Exception as e:
                logger.error(f"Error initializing {client_type.value} client: {e}")
        
        logger.info(f"Initialized {success_count}/{len(self.available_clients)} MCP clients")
        return success_count > 0
    
    async def shutdown(self):
        """Shutdown all MCP clients"""
        logger.info("Shutting down MCP clients...")
        
        for client_type, client in self.clients.items():
            try:
                await client.shutdown()
                logger.info(f"Shutdown {client_type.value} MCP client")
            except Exception as e:
                logger.error(f"Error shutting down {client_type.value} client: {e}")
        
        self.clients.clear()
        logger.info("MCP client shutdown complete")
    
    async def route_and_execute_task(self, description: str, 
                                   context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Route a task to the appropriate MCP client and execute it.
        
        Args:
            description: Task description
            context: Task context
            
        Returns:
            Task execution result
        """
        logger.info(f"Routing task: {description[:100]}...")
        
        context = context or {}
        
        try:
            # Route task to determine best execution strategy
            routing_decision = await self.task_router.route_task(description, context)
            logger.debug(f"Task routed to category: {routing_decision.category.value}")
            
            # Find appropriate client
            client = self._find_client_for_category(routing_decision.category)
            
            if not client:
                return {
                    "success": False,
                    "error": f"No available client for category: {routing_decision.category.value}",
                    "routing_decision": routing_decision
                }
            
            # Execute task using selected client
            result = await client.process_task(description, context)
            
            # Add routing information to result
            if isinstance(result, dict):
                result["routing_decision"] = {
                    "category": routing_decision.category.value,
                    "strategy": routing_decision.strategy.value,
                    "confidence": routing_decision.confidence,
                    "client_used": type(client).__name__
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Task routing and execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "task": description
            }
    
    def _find_client_for_category(self, category: TaskCategory) -> Optional[BaseMCPClient]:
        """Find the best client for a given task category"""
        
        # Find clients that can handle this category
        candidate_clients = []
        
        for client_type, client_info in self.available_clients.items():
            if category in client_info.categories and client_type in self.clients:
                candidate_clients.append((client_type, client_info.priority))
        
        if not candidate_clients:
            # Fallback: try filesystem client for general tasks
            if category in [TaskCategory.GENERAL, TaskCategory.HYBRID]:
                return self.clients.get(ClientType.FILESYSTEM)
            return None
        
        # Sort by priority (highest first)
        candidate_clients.sort(key=lambda x: x[1], reverse=True)
        
        # Return highest priority client
        best_client_type = candidate_clients[0][0]
        return self.clients.get(best_client_type)
    
    async def execute_tool_directly(self, client_type: str, tool_name: str, 
                                  parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool directly on a specific client.
        
        Args:
            client_type: Type of client to use
            tool_name: Name of tool to execute
            parameters: Tool parameters
            
        Returns:
            Tool execution result
        """
        try:
            client_enum = ClientType(client_type)
            client = self.clients.get(client_enum)
            
            if not client:
                return {
                    "success": False,
                    "error": f"Client not available: {client_type}"
                }
            
            return await client.execute_tool(tool_name, parameters)
            
        except ValueError:
            return {
                "success": False,
                "error": f"Invalid client type: {client_type}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Tool execution failed: {e}"
            }
    
    def get_available_tools(self) -> Dict[str, List[str]]:
        """Get list of available tools for each client"""
        tools = {}
        
        for client_type, client in self.clients.items():
            if hasattr(client, 'get_available_tools'):
                tools[client_type.value] = client.get_available_tools()
            else:
                # Get tools from client configuration
                if hasattr(client, 'config') and client.config.servers:
                    all_tools = []
                    for server in client.config.servers:
                        all_tools.extend(server.tools)
                    tools[client_type.value] = all_tools
                else:
                    tools[client_type.value] = []
        
        return tools
    
    def get_client_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all clients"""
        status = {}
        
        for client_type, client_info in self.available_clients.items():
            client = self.clients.get(client_type)
            
            if client:
                status[client_type.value] = {
                    "status": "connected",
                    "categories": [cat.value for cat in client_info.categories],
                    "priority": client_info.priority
                }
            else:
                status[client_type.value] = {
                    "status": "not_available",
                    "categories": [cat.value for cat in client_info.categories],
                    "priority": client_info.priority
                }
        
        return status
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all clients"""
        health_status = {
            "overall": "healthy",
            "clients": {},
            "timestamp": asyncio.get_event_loop().time()
        }
        
        unhealthy_count = 0
        
        for client_type, client in self.clients.items():
            try:
                # Perform basic connectivity test
                if hasattr(client, 'health_check'):
                    client_health = await client.health_check()
                else:
                    # Basic test - try to get available tools
                    if hasattr(client, 'get_available_tools'):
                        client.get_available_tools()
                    client_health = {"status": "healthy"}
                
                health_status["clients"][client_type.value] = client_health
                
                if client_health.get("status") != "healthy":
                    unhealthy_count += 1
                    
            except Exception as e:
                health_status["clients"][client_type.value] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                unhealthy_count += 1
        
        # Determine overall health
        total_clients = len(self.clients)
        if unhealthy_count == 0:
            health_status["overall"] = "healthy"
        elif unhealthy_count < total_clients:
            health_status["overall"] = "degraded"
        else:
            health_status["overall"] = "unhealthy"
        
        return health_status
    
    def get_routing_explanation(self, routing_decision: RoutingDecision) -> str:
        """Get explanation for a routing decision"""
        return self.task_router.get_routing_explanation(routing_decision)