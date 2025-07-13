"""
MCP Client Implementation

Real Model Context Protocol client for connecting to MCP servers.

Author: Claude Code
Date: 2025-07-13
Session: 4.4
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass
import websockets
import subprocess

from .protocol import (
    MCPMessage, MCPMessageType, MCPCapability, MCPClientInfo, MCPCapabilities,
    MCPTool, MCPResource, MCPPrompt, MCPErrorCode,
    create_initialize_message, create_initialized_message, create_list_tools_message,
    create_call_tool_message, create_list_resources_message, create_read_resource_message,
    create_list_prompts_message, create_get_prompt_message, create_ping_message,
    create_error_response, create_success_response,
    validate_message, is_request, is_response, is_notification
)

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server"""
    name: str
    command: List[str]
    args: List[str] = None
    env: Dict[str, str] = None
    timeout: float = 30.0
    transport: str = "stdio"  # stdio, websocket, sse
    uri: Optional[str] = None  # for websocket/sse transport


class MCPClient:
    """
    Model Context Protocol client implementation.
    
    Supports multiple transport methods:
    - stdio (subprocess communication)
    - websocket
    - SSE (server-sent events)
    """
    
    def __init__(self, client_info: MCPClientInfo, capabilities: MCPCapabilities):
        self.client_info = client_info
        self.capabilities = capabilities
        
        # Connection state
        self.connected_servers: Dict[str, Dict[str, Any]] = {}
        self.pending_requests: Dict[str, asyncio.Future] = {}
        
        # Available tools, resources, prompts from all servers
        self.available_tools: Dict[str, MCPTool] = {}
        self.available_resources: Dict[str, MCPResource] = {}
        self.available_prompts: Dict[str, MCPPrompt] = {}
        
        # Event handlers
        self.message_handlers: Dict[str, Callable] = {}
        self.notification_handlers: Dict[str, Callable] = {}
        
        # Default message handlers
        self._setup_default_handlers()
        
        logger.info(f"MCP Client {client_info.name} v{client_info.version} created")
    
    def _setup_default_handlers(self):
        """Setup default message handlers"""
        self.message_handlers[MCPMessageType.PING.value] = self._handle_ping
        self.notification_handlers["progress"] = self._handle_progress_notification
    
    async def connect_server(self, server_name: str, config: MCPServerConfig) -> bool:
        """Connect to an MCP server"""
        try:
            if config.transport == "stdio":
                return await self._connect_stdio_server(server_name, config)
            elif config.transport == "websocket":
                return await self._connect_websocket_server(server_name, config)
            else:
                logger.error(f"Unsupported transport: {config.transport}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to server {server_name}: {e}")
            return False
    
    async def _connect_stdio_server(self, server_name: str, config: MCPServerConfig) -> bool:
        """Connect to server via stdio"""
        try:
            # Start subprocess
            cmd = config.command + (config.args or [])
            env = config.env or {}
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            # Store connection info
            self.connected_servers[server_name] = {
                "config": config,
                "transport": "stdio",
                "process": process,
                "reader_task": None,
                "initialized": False,
                "server_info": None,
                "server_capabilities": None
            }
            
            # Start reading messages
            reader_task = asyncio.create_task(
                self._stdio_message_reader(server_name, process.stdout)
            )
            self.connected_servers[server_name]["reader_task"] = reader_task
            
            # Send initialize message
            await self._initialize_server(server_name)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect stdio server {server_name}: {e}")
            return False
    
    async def _connect_websocket_server(self, server_name: str, config: MCPServerConfig) -> bool:
        """Connect to server via websocket"""
        try:
            if not config.uri:
                raise ValueError("WebSocket URI required for websocket transport")
            
            websocket = await websockets.connect(config.uri)
            
            # Store connection info
            self.connected_servers[server_name] = {
                "config": config,
                "transport": "websocket",
                "websocket": websocket,
                "reader_task": None,
                "initialized": False,
                "server_info": None,
                "server_capabilities": None
            }
            
            # Start reading messages
            reader_task = asyncio.create_task(
                self._websocket_message_reader(server_name, websocket)
            )
            self.connected_servers[server_name]["reader_task"] = reader_task
            
            # Send initialize message
            await self._initialize_server(server_name)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect websocket server {server_name}: {e}")
            return False
    
    async def _initialize_server(self, server_name: str) -> bool:
        """Initialize connection with server"""
        try:
            # Send initialize message
            init_msg = create_initialize_message(self.client_info, self.capabilities)
            response = await self._send_request(server_name, init_msg)
            
            if response.error:
                logger.error(f"Server {server_name} initialization failed: {response.error}")
                return False
            
            # Store server info
            result = response.result or {}
            server_info = result.get("serverInfo", {})
            server_capabilities = result.get("capabilities", {})
            
            self.connected_servers[server_name].update({
                "initialized": True,
                "server_info": server_info,
                "server_capabilities": server_capabilities
            })
            
            # Send initialized notification
            initialized_msg = create_initialized_message(init_msg.id)
            await self._send_message(server_name, initialized_msg)
            
            # Discover available capabilities
            await self._discover_server_capabilities(server_name)
            
            logger.info(f"Successfully initialized server {server_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize server {server_name}: {e}")
            return False
    
    async def _discover_server_capabilities(self, server_name: str):
        """Discover tools, resources, and prompts from server"""
        server_info = self.connected_servers[server_name]
        capabilities = server_info.get("server_capabilities", {})
        
        # Discover tools
        if "tools" in capabilities:
            try:
                tools_msg = create_list_tools_message()
                response = await self._send_request(server_name, tools_msg)
                
                if response.result and "tools" in response.result:
                    for tool_data in response.result["tools"]:
                        tool = MCPTool(
                            name=tool_data["name"],
                            description=tool_data["description"],
                            inputSchema=tool_data["inputSchema"]
                        )
                        tool_key = f"{server_name}:{tool.name}"
                        self.available_tools[tool_key] = tool
                        
                    logger.info(f"Discovered {len(response.result['tools'])} tools from {server_name}")
                    
            except Exception as e:
                logger.error(f"Failed to discover tools from {server_name}: {e}")
        
        # Discover resources
        if "resources" in capabilities:
            try:
                resources_msg = create_list_resources_message()
                response = await self._send_request(server_name, resources_msg)
                
                if response.result and "resources" in response.result:
                    for resource_data in response.result["resources"]:
                        resource = MCPResource(
                            uri=resource_data["uri"],
                            name=resource_data["name"],
                            description=resource_data.get("description"),
                            mimeType=resource_data.get("mimeType")
                        )
                        resource_key = f"{server_name}:{resource.uri}"
                        self.available_resources[resource_key] = resource
                        
                    logger.info(f"Discovered {len(response.result['resources'])} resources from {server_name}")
                    
            except Exception as e:
                logger.error(f"Failed to discover resources from {server_name}: {e}")
        
        # Discover prompts
        if "prompts" in capabilities:
            try:
                prompts_msg = create_list_prompts_message()
                response = await self._send_request(server_name, prompts_msg)
                
                if response.result and "prompts" in response.result:
                    for prompt_data in response.result["prompts"]:
                        prompt = MCPPrompt(
                            name=prompt_data["name"],
                            description=prompt_data["description"],
                            arguments=prompt_data.get("arguments", [])
                        )
                        prompt_key = f"{server_name}:{prompt.name}"
                        self.available_prompts[prompt_key] = prompt
                        
                    logger.info(f"Discovered {len(response.result['prompts'])} prompts from {server_name}")
                    
            except Exception as e:
                logger.error(f"Failed to discover prompts from {server_name}: {e}")
    
    async def _stdio_message_reader(self, server_name: str, stdout):
        """Read messages from stdio transport"""
        try:
            while True:
                line = await stdout.readline()
                if not line:
                    break
                
                try:
                    message = MCPMessage.from_json(line.decode().strip())
                    await self._handle_message(server_name, message)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse message from {server_name}: {e}")
                except Exception as e:
                    logger.error(f"Error handling message from {server_name}: {e}")
                    
        except Exception as e:
            logger.error(f"stdio reader error for {server_name}: {e}")
        finally:
            logger.info(f"stdio reader ended for {server_name}")
    
    async def _websocket_message_reader(self, server_name: str, websocket):
        """Read messages from websocket transport"""
        try:
            async for message in websocket:
                try:
                    msg = MCPMessage.from_json(message)
                    await self._handle_message(server_name, msg)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse message from {server_name}: {e}")
                except Exception as e:
                    logger.error(f"Error handling message from {server_name}: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"WebSocket connection closed for {server_name}")
        except Exception as e:
            logger.error(f"WebSocket reader error for {server_name}: {e}")
    
    async def _handle_message(self, server_name: str, message: MCPMessage):
        """Handle incoming message from server"""
        # Validate message
        error = validate_message(message)
        if error:
            logger.error(f"Invalid message from {server_name}: {error}")
            return
        
        if is_response(message):
            # Handle response to our request
            if message.id in self.pending_requests:
                future = self.pending_requests.pop(message.id)
                future.set_result(message)
            else:
                logger.warning(f"Received response for unknown request {message.id} from {server_name}")
        
        elif is_notification(message):
            # Handle notification
            method = message.method
            if method in self.notification_handlers:
                try:
                    await self.notification_handlers[method](server_name, message)
                except Exception as e:
                    logger.error(f"Error in notification handler for {method}: {e}")
        
        elif is_request(message):
            # Handle request from server
            method = message.method
            if method in self.message_handlers:
                try:
                    response = await self.message_handlers[method](server_name, message)
                    if response and message.id:
                        await self._send_message(server_name, response)
                except Exception as e:
                    logger.error(f"Error in message handler for {method}: {e}")
                    # Send error response
                    if message.id:
                        error_response = create_error_response(
                            message.id, MCPErrorCode.INTERNAL_ERROR, str(e)
                        )
                        await self._send_message(server_name, error_response)
            else:
                logger.warning(f"No handler for method {method} from {server_name}")
                if message.id:
                    error_response = create_error_response(
                        message.id, MCPErrorCode.METHOD_NOT_FOUND, f"Method {method} not found"
                    )
                    await self._send_message(server_name, error_response)
    
    async def _send_message(self, server_name: str, message: MCPMessage):
        """Send message to server"""
        if server_name not in self.connected_servers:
            raise ValueError(f"Server {server_name} not connected")
        
        server_info = self.connected_servers[server_name]
        transport = server_info["transport"]
        
        message_json = message.to_json() + "\n"
        
        if transport == "stdio":
            process = server_info["process"]
            process.stdin.write(message_json.encode())
            await process.stdin.drain()
        
        elif transport == "websocket":
            websocket = server_info["websocket"]
            await websocket.send(message_json.rstrip())
        
        else:
            raise ValueError(f"Unsupported transport: {transport}")
    
    async def _send_request(self, server_name: str, message: MCPMessage, timeout: float = 30.0) -> MCPMessage:
        """Send request and wait for response"""
        if not message.id:
            message.id = str(uuid.uuid4())
        
        # Create future for response
        future = asyncio.Future()
        self.pending_requests[message.id] = future
        
        try:
            # Send message
            await self._send_message(server_name, message)
            
            # Wait for response
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
            
        except asyncio.TimeoutError:
            # Clean up pending request
            self.pending_requests.pop(message.id, None)
            raise
        except Exception as e:
            # Clean up pending request
            self.pending_requests.pop(message.id, None)
            raise
    
    # API Methods
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on any connected server"""
        # Find server that has this tool
        server_name = None
        for key, tool in self.available_tools.items():
            if key.endswith(f":{tool_name}"):
                server_name = key.split(":")[0]
                break
        
        if not server_name:
            raise ValueError(f"Tool {tool_name} not found")
        
        # Send call tool request
        call_msg = create_call_tool_message(tool_name, arguments)
        response = await self._send_request(server_name, call_msg)
        
        if response.error:
            raise Exception(f"Tool call failed: {response.error}")
        
        return response.result
    
    async def read_resource(self, uri: str) -> Any:
        """Read a resource from any connected server"""
        # Find server that has this resource
        server_name = None
        for key, resource in self.available_resources.items():
            if key.endswith(f":{uri}"):
                server_name = key.split(":")[0]
                break
        
        if not server_name:
            raise ValueError(f"Resource {uri} not found")
        
        # Send read resource request
        read_msg = create_read_resource_message(uri)
        response = await self._send_request(server_name, read_msg)
        
        if response.error:
            raise Exception(f"Resource read failed: {response.error}")
        
        return response.result
    
    async def get_prompt(self, prompt_name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """Get a prompt from any connected server"""
        # Find server that has this prompt
        server_name = None
        for key, prompt in self.available_prompts.items():
            if key.endswith(f":{prompt_name}"):
                server_name = key.split(":")[0]
                break
        
        if not server_name:
            raise ValueError(f"Prompt {prompt_name} not found")
        
        # Send get prompt request
        prompt_msg = create_get_prompt_message(prompt_name, arguments)
        response = await self._send_request(server_name, prompt_msg)
        
        if response.error:
            raise Exception(f"Prompt get failed: {response.error}")
        
        return response.result
    
    # Event handlers
    async def _handle_ping(self, server_name: str, message: MCPMessage) -> MCPMessage:
        """Handle ping request"""
        return create_success_response(message.id, {})
    
    async def _handle_progress_notification(self, server_name: str, message: MCPMessage):
        """Handle progress notification"""
        params = message.params or {}
        logger.debug(f"Progress from {server_name}: {params}")
    
    # Management methods
    def get_connected_servers(self) -> List[str]:
        """Get list of connected server names"""
        return [name for name, info in self.connected_servers.items() if info.get("initialized")]
    
    def get_available_tools(self) -> List[MCPTool]:
        """Get all available tools"""
        return list(self.available_tools.values())
    
    def get_available_resources(self) -> List[MCPResource]:
        """Get all available resources"""
        return list(self.available_resources.values())
    
    def get_available_prompts(self) -> List[MCPPrompt]:
        """Get all available prompts"""
        return list(self.available_prompts.values())
    
    async def disconnect_server(self, server_name: str):
        """Disconnect from a server"""
        if server_name not in self.connected_servers:
            return
        
        server_info = self.connected_servers[server_name]
        
        # Cancel reader task
        if server_info["reader_task"]:
            server_info["reader_task"].cancel()
            try:
                await server_info["reader_task"]
            except asyncio.CancelledError:
                pass
        
        # Close connection
        if server_info["transport"] == "stdio":
            process = server_info["process"]
            process.terminate()
            await process.wait()
        elif server_info["transport"] == "websocket":
            websocket = server_info["websocket"]
            await websocket.close()
        
        # Remove from available capabilities
        tools_to_remove = [k for k in self.available_tools.keys() if k.startswith(f"{server_name}:")]
        for key in tools_to_remove:
            del self.available_tools[key]
        
        resources_to_remove = [k for k in self.available_resources.keys() if k.startswith(f"{server_name}:")]
        for key in resources_to_remove:
            del self.available_resources[key]
        
        prompts_to_remove = [k for k in self.available_prompts.keys() if k.startswith(f"{server_name}:")]
        for key in prompts_to_remove:
            del self.available_prompts[key]
        
        # Remove from connected servers
        del self.connected_servers[server_name]
        
        logger.info(f"Disconnected from server {server_name}")
    
    async def shutdown(self):
        """Shutdown client and disconnect all servers"""
        server_names = list(self.connected_servers.keys())
        
        for server_name in server_names:
            await self.disconnect_server(server_name)
        
        # Cancel any pending requests
        for future in self.pending_requests.values():
            future.cancel()
        
        self.pending_requests.clear()
        
        logger.info("MCP Client shutdown complete")