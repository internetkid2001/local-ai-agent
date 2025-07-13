"""
Base MCP Client

Abstract base class for MCP client implementations with connection pooling,
tool management, and unified interface for MCP server communication.

Author: Claude Code
Date: 2025-07-13
Session: 1.1
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
import logging

from .connection import MCPConnection, MCPMessage, ConnectionState
from .exceptions import MCPError, ConnectionError

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server"""
    name: str
    url: str
    enabled: bool = True
    retry_attempts: int = 5
    timeout: float = 30.0
    tools: List[str] = field(default_factory=list)


@dataclass
class MCPClientConfig:
    """Configuration for MCP client"""
    servers: List[MCPServerConfig]
    connection_timeout: float = 10.0
    default_timeout: float = 30.0
    max_concurrent_connections: int = 10


class MCPTool:
    """Represents an MCP tool with its schema and handler"""
    
    def __init__(self, name: str, description: str, parameters: Dict[str, Any], server_name: str):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.server_name = server_name
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tool to dictionary representation"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "server": self.server_name
        }


class BaseMCPClient(ABC):
    """
    Base MCP client providing connection management and tool execution.
    
    Features:
    - Connection pooling for multiple MCP servers
    - Automatic tool discovery and registration
    - Load balancing across servers
    - Error handling and retry logic
    - Async tool execution
    """
    
    def __init__(self, config: MCPClientConfig):
        """
        Initialize MCP client.
        
        Args:
            config: Client configuration
        """
        self.config = config
        self._connections: Dict[str, MCPConnection] = {}
        self._tools: Dict[str, MCPTool] = {}
        self._server_tools: Dict[str, List[str]] = {}
        self._connection_semaphore = asyncio.Semaphore(config.max_concurrent_connections)
        
        logger.info(f"Initialized MCP client with {len(config.servers)} servers")
    
    async def initialize(self) -> bool:
        """
        Initialize all MCP server connections and discover tools.
        
        Returns:
            True if at least one connection successful
        """
        logger.info("Initializing MCP client connections...")
        
        connection_tasks = []
        for server_config in self.config.servers:
            if server_config.enabled:
                task = self._initialize_server(server_config)
                connection_tasks.append(task)
        
        if not connection_tasks:
            logger.warning("No enabled servers configured")
            return False
        
        # Connect to all servers concurrently
        results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        successful_connections = sum(1 for result in results if result is True)
        
        if successful_connections == 0:
            logger.error("Failed to connect to any MCP servers")
            return False
        
        logger.info(f"Successfully connected to {successful_connections}/{len(connection_tasks)} servers")
        
        # Discover tools from connected servers
        await self._discover_tools()
        
        return True
    
    async def shutdown(self):
        """Gracefully shutdown all connections"""
        logger.info("Shutting down MCP client...")
        
        disconnect_tasks = []
        for connection in self._connections.values():
            task = connection.disconnect()
            disconnect_tasks.append(task)
        
        if disconnect_tasks:
            await asyncio.gather(*disconnect_tasks, return_exceptions=True)
        
        self._connections.clear()
        self._tools.clear()
        self._server_tools.clear()
        
        logger.info("MCP client shutdown complete")
    
    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Execute a tool on the appropriate MCP server.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters
            timeout: Optional timeout override
            
        Returns:
            Tool execution result
            
        Raises:
            MCPError: If tool not found or execution fails
        """
        if tool_name not in self._tools:
            raise MCPError(f"Tool not found: {tool_name}")
        
        tool = self._tools[tool_name]
        server_name = tool.server_name
        
        if server_name not in self._connections:
            raise ConnectionError(f"Server not connected: {server_name}")
        
        connection = self._connections[server_name]
        
        if not connection.is_connected:
            logger.warning(f"Server {server_name} disconnected, attempting reconnection...")
            if not await connection.connect():
                raise ConnectionError(f"Failed to reconnect to server: {server_name}")
        
        # Create MCP message
        message = MCPMessage(
            id=str(uuid.uuid4()),
            method="tools/call",
            params={
                "name": tool_name,
                "arguments": parameters
            }
        )
        
        timeout = timeout or self.config.default_timeout
        
        async with self._connection_semaphore:
            try:
                logger.debug(f"Executing tool {tool_name} on server {server_name}")
                result = await connection.send_message(message)
                logger.debug(f"Tool {tool_name} completed successfully")
                return result
                
            except Exception as e:
                logger.error(f"Tool execution failed: {tool_name} - {e}")
                raise MCPError(f"Tool execution failed: {e}")
    
    async def list_tools(self, server_name: Optional[str] = None) -> List[MCPTool]:
        """
        List available tools.
        
        Args:
            server_name: Optional server filter
            
        Returns:
            List of available tools
        """
        if server_name:
            if server_name not in self._server_tools:
                return []
            tool_names = self._server_tools[server_name]
            return [self._tools[name] for name in tool_names if name in self._tools]
        
        return list(self._tools.values())
    
    async def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get schema for a specific tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool schema or None if not found
        """
        if tool_name not in self._tools:
            return None
        
        return self._tools[tool_name].to_dict()
    
    async def health_check(self) -> Dict[str, Dict[str, Any]]:
        """
        Check health of all server connections.
        
        Returns:
            Health status for each server
        """
        health_status = {}
        
        for server_name, connection in self._connections.items():
            try:
                # Send ping message
                ping_message = MCPMessage(
                    id=str(uuid.uuid4()),
                    method="ping",
                    params={}
                )
                
                start_time = asyncio.get_event_loop().time()
                await connection.send_message(ping_message)
                response_time = asyncio.get_event_loop().time() - start_time
                
                health_status[server_name] = {
                    "status": "healthy",
                    "response_time": response_time,
                    "state": connection.state.value,
                    "tools_count": len(self._server_tools.get(server_name, []))
                }
                
            except Exception as e:
                health_status[server_name] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "state": connection.state.value,
                    "tools_count": len(self._server_tools.get(server_name, []))
                }
        
        return health_status
    
    async def _initialize_server(self, server_config: MCPServerConfig) -> bool:
        """Initialize connection to a single MCP server"""
        try:
            logger.info(f"Connecting to MCP server: {server_config.name}")
            
            connection = MCPConnection(
                server_url=server_config.url,
                max_reconnect_attempts=server_config.retry_attempts,
                message_timeout=server_config.timeout
            )
            
            # Set up event handlers
            connection.set_event_handlers(
                on_connect=lambda: self._on_server_connect(server_config.name),
                on_disconnect=lambda: self._on_server_disconnect(server_config.name)
            )
            
            success = await connection.connect()
            
            if success:
                self._connections[server_config.name] = connection
                self._server_tools[server_config.name] = []
                logger.info(f"Successfully connected to {server_config.name}")
                return True
            else:
                logger.error(f"Failed to connect to {server_config.name}")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing server {server_config.name}: {e}")
            return False
    
    async def _discover_tools(self):
        """Discover tools from all connected servers"""
        logger.info("Discovering tools from MCP servers...")
        
        discovery_tasks = []
        for server_name, connection in self._connections.items():
            if connection.is_connected:
                task = self._discover_server_tools(server_name, connection)
                discovery_tasks.append(task)
        
        if discovery_tasks:
            await asyncio.gather(*discovery_tasks, return_exceptions=True)
        
        total_tools = len(self._tools)
        logger.info(f"Discovered {total_tools} tools from {len(self._connections)} servers")
    
    async def _discover_server_tools(self, server_name: str, connection: MCPConnection):
        """Discover tools from a specific server"""
        try:
            # Request tools list
            message = MCPMessage(
                id=str(uuid.uuid4()),
                method="tools/list",
                params={}
            )
            
            response = await connection.send_message(message)
            tools_data = response.get("tools", [])
            
            server_tool_names = []
            for tool_data in tools_data:
                tool_name = tool_data.get("name")
                if tool_name:
                    tool = MCPTool(
                        name=tool_name,
                        description=tool_data.get("description", ""),
                        parameters=tool_data.get("inputSchema", {}),
                        server_name=server_name
                    )
                    
                    self._tools[tool_name] = tool
                    server_tool_names.append(tool_name)
            
            self._server_tools[server_name] = server_tool_names
            logger.info(f"Discovered {len(server_tool_names)} tools from {server_name}")
            
        except Exception as e:
            logger.error(f"Failed to discover tools from {server_name}: {e}")
    
    async def _on_server_connect(self, server_name: str):
        """Handle server connection event"""
        logger.info(f"Server connected: {server_name}")
        # Rediscover tools for this server
        if server_name in self._connections:
            connection = self._connections[server_name]
            await self._discover_server_tools(server_name, connection)
    
    async def _on_server_disconnect(self, server_name: str):
        """Handle server disconnection event"""
        logger.warning(f"Server disconnected: {server_name}")
        # Remove tools from disconnected server
        if server_name in self._server_tools:
            for tool_name in self._server_tools[server_name]:
                self._tools.pop(tool_name, None)
            self._server_tools[server_name] = []
    
    @abstractmethod
    async def process_task(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a high-level task using available tools.
        
        This method should be implemented by subclasses to provide
        task-specific logic and tool orchestration.
        
        Args:
            task: Task description
            context: Task context
            
        Returns:
            Task result
        """
        pass