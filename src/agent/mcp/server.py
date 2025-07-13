"""
MCP Server Implementation

Basic Model Context Protocol server implementation.

Author: Claude Code
Date: 2025-07-13
Session: 4.4
"""

import asyncio
import json
import sys
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass

from .protocol import (
    MCPMessage, MCPMessageType, MCPServerInfo, MCPCapabilities,
    MCPTool, MCPResource, MCPPrompt, MCPErrorCode,
    create_success_response, create_error_response,
    validate_message, is_request, is_response
)
from .tools import ToolRegistry, get_default_tools

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """MCP Server configuration"""
    name: str
    version: str
    capabilities: MCPCapabilities
    tool_registry: Optional[ToolRegistry] = None


class MCPServer:
    """
    Model Context Protocol server implementation.
    
    Supports stdio transport for communication.
    """
    
    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.server_info = MCPServerInfo(
            name=config.name,
            version=config.version
        )
        
        # Use provided tool registry or default
        self.tool_registry = config.tool_registry or get_default_tools()
        
        # Server state
        self.initialized = False
        self.client_info = None
        self.client_capabilities = None
        
        # Message handlers
        self.handlers = {
            MCPMessageType.INITIALIZE.value: self._handle_initialize,
            MCPMessageType.INITIALIZED.value: self._handle_initialized,
            MCPMessageType.LIST_TOOLS.value: self._handle_list_tools,
            MCPMessageType.CALL_TOOL.value: self._handle_call_tool,
            MCPMessageType.LIST_RESOURCES.value: self._handle_list_resources,
            MCPMessageType.READ_RESOURCE.value: self._handle_read_resource,
            MCPMessageType.LIST_PROMPTS.value: self._handle_list_prompts,
            MCPMessageType.GET_PROMPT.value: self._handle_get_prompt,
            MCPMessageType.PING.value: self._handle_ping,
        }
        
        # Resources and prompts (can be extended)
        self.resources: List[MCPResource] = []
        self.prompts: List[MCPPrompt] = []
        
        logger.info(f"MCP Server {config.name} v{config.version} created")
    
    async def start_stdio(self):
        """Start server with stdio transport"""
        logger.info("Starting MCP Server with stdio transport")
        
        try:
            # Read from stdin, write to stdout
            while True:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )
                
                if not line:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                try:
                    message = MCPMessage.from_json(line)
                    response = await self._handle_message(message)
                    
                    if response:
                        response_json = response.to_json()
                        print(response_json, flush=True)
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse message: {e}")
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    
        except KeyboardInterrupt:
            logger.info("Server interrupted")
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            logger.info("MCP Server stopped")
    
    async def _handle_message(self, message: MCPMessage) -> Optional[MCPMessage]:
        """Handle incoming message"""
        # Validate message
        error = validate_message(message)
        if error:
            logger.error(f"Invalid message: {error}")
            if message.id:
                return create_error_response(
                    message.id, MCPErrorCode.INVALID_REQUEST, error
                )
            return None
        
        # Only handle requests
        if not is_request(message):
            logger.warning("Received non-request message")
            return None
        
        # Get handler
        handler = self.handlers.get(message.method)
        if not handler:
            logger.warning(f"No handler for method: {message.method}")
            if message.id:
                return create_error_response(
                    message.id, MCPErrorCode.METHOD_NOT_FOUND, 
                    f"Method {message.method} not found"
                )
            return None
        
        # Call handler
        try:
            return await handler(message)
        except Exception as e:
            logger.error(f"Handler error for {message.method}: {e}")
            if message.id:
                return create_error_response(
                    message.id, MCPErrorCode.INTERNAL_ERROR, str(e)
                )
            return None
    
    async def _handle_initialize(self, message: MCPMessage) -> MCPMessage:
        """Handle initialize request"""
        params = message.params or {}
        
        # Store client info
        self.client_info = params.get("clientInfo", {})
        self.client_capabilities = params.get("capabilities", {})
        
        # Return server info and capabilities
        result = {
            "protocolVersion": "2024-11-05",
            "serverInfo": {
                "name": self.server_info.name,
                "version": self.server_info.version
            },
            "capabilities": {}
        }
        
        # Add capabilities
        if self.config.capabilities.tools:
            result["capabilities"]["tools"] = self.config.capabilities.tools
        if self.config.capabilities.resources:
            result["capabilities"]["resources"] = self.config.capabilities.resources
        if self.config.capabilities.prompts:
            result["capabilities"]["prompts"] = self.config.capabilities.prompts
        if self.config.capabilities.logging:
            result["capabilities"]["logging"] = self.config.capabilities.logging
        
        logger.info(f"Initialized for client: {self.client_info.get('name', 'unknown')}")
        
        return create_success_response(message.id, result)
    
    async def _handle_initialized(self, message: MCPMessage) -> Optional[MCPMessage]:
        """Handle initialized notification"""
        self.initialized = True
        logger.info("Client initialization complete")
        return None  # No response for notifications
    
    async def _handle_list_tools(self, message: MCPMessage) -> MCPMessage:
        """Handle list tools request"""
        if not self.initialized:
            return create_error_response(
                message.id, MCPErrorCode.INVALID_REQUEST, "Not initialized"
            )
        
        tools = self.tool_registry.get_tool_list()
        
        result = {
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema
                }
                for tool in tools
            ]
        }
        
        return create_success_response(message.id, result)
    
    async def _handle_call_tool(self, message: MCPMessage) -> MCPMessage:
        """Handle call tool request"""
        if not self.initialized:
            return create_error_response(
                message.id, MCPErrorCode.INVALID_REQUEST, "Not initialized"
            )
        
        params = message.params or {}
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if not tool_name:
            return create_error_response(
                message.id, MCPErrorCode.INVALID_PARAMS, "Tool name required"
            )
        
        try:
            result = await self.tool_registry.call_tool(tool_name, arguments)
            
            return create_success_response(message.id, {
                "content": [
                    {
                        "type": "text",
                        "text": str(result)
                    }
                ]
            })
            
        except ValueError as e:
            return create_error_response(
                message.id, MCPErrorCode.TOOL_NOT_FOUND, str(e)
            )
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return create_error_response(
                message.id, MCPErrorCode.INTERNAL_ERROR, str(e)
            )
    
    async def _handle_list_resources(self, message: MCPMessage) -> MCPMessage:
        """Handle list resources request"""
        if not self.initialized:
            return create_error_response(
                message.id, MCPErrorCode.INVALID_REQUEST, "Not initialized"
            )
        
        result = {
            "resources": [
                {
                    "uri": resource.uri,
                    "name": resource.name,
                    "description": resource.description,
                    "mimeType": resource.mimeType
                }
                for resource in self.resources
            ]
        }
        
        return create_success_response(message.id, result)
    
    async def _handle_read_resource(self, message: MCPMessage) -> MCPMessage:
        """Handle read resource request"""
        if not self.initialized:
            return create_error_response(
                message.id, MCPErrorCode.INVALID_REQUEST, "Not initialized"
            )
        
        params = message.params or {}
        uri = params.get("uri")
        
        if not uri:
            return create_error_response(
                message.id, MCPErrorCode.INVALID_PARAMS, "Resource URI required"
            )
        
        # Find resource
        resource = None
        for r in self.resources:
            if r.uri == uri:
                resource = r
                break
        
        if not resource:
            return create_error_response(
                message.id, MCPErrorCode.RESOURCE_NOT_FOUND, f"Resource {uri} not found"
            )
        
        # For now, just return placeholder content
        result = {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": resource.mimeType or "text/plain",
                    "text": f"Content of {resource.name}"
                }
            ]
        }
        
        return create_success_response(message.id, result)
    
    async def _handle_list_prompts(self, message: MCPMessage) -> MCPMessage:
        """Handle list prompts request"""
        if not self.initialized:
            return create_error_response(
                message.id, MCPErrorCode.INVALID_REQUEST, "Not initialized"
            )
        
        result = {
            "prompts": [
                {
                    "name": prompt.name,
                    "description": prompt.description,
                    "arguments": prompt.arguments
                }
                for prompt in self.prompts
            ]
        }
        
        return create_success_response(message.id, result)
    
    async def _handle_get_prompt(self, message: MCPMessage) -> MCPMessage:
        """Handle get prompt request"""
        if not self.initialized:
            return create_error_response(
                message.id, MCPErrorCode.INVALID_REQUEST, "Not initialized"
            )
        
        params = message.params or {}
        prompt_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if not prompt_name:
            return create_error_response(
                message.id, MCPErrorCode.INVALID_PARAMS, "Prompt name required"
            )
        
        # Find prompt
        prompt = None
        for p in self.prompts:
            if p.name == prompt_name:
                prompt = p
                break
        
        if not prompt:
            return create_error_response(
                message.id, MCPErrorCode.PROMPT_NOT_FOUND, f"Prompt {prompt_name} not found"
            )
        
        # For now, return basic prompt content
        result = {
            "description": prompt.description,
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": f"This is the {prompt_name} prompt with arguments: {arguments}"
                    }
                }
            ]
        }
        
        return create_success_response(message.id, result)
    
    async def _handle_ping(self, message: MCPMessage) -> MCPMessage:
        """Handle ping request"""
        return create_success_response(message.id, {})
    
    def add_resource(self, resource: MCPResource):
        """Add a resource to the server"""
        self.resources.append(resource)
        logger.info(f"Added resource: {resource.name}")
    
    def add_prompt(self, prompt: MCPPrompt):
        """Add a prompt to the server"""
        self.prompts.append(prompt)
        logger.info(f"Added prompt: {prompt.name}")


# Utility function to create a basic server
def create_basic_server(
    name: str = "BasicMCPServer",
    version: str = "1.0.0",
    enable_tools: bool = True,
    enable_resources: bool = False,
    enable_prompts: bool = False,
    tool_registry: Optional[ToolRegistry] = None
) -> MCPServer:
    """Create a basic MCP server"""
    capabilities = MCPCapabilities()
    
    if enable_tools:
        capabilities.tools = {}
    if enable_resources:
        capabilities.resources = {}
    if enable_prompts:
        capabilities.prompts = {}
    
    config = MCPServerConfig(
        name=name,
        version=version,
        capabilities=capabilities,
        tool_registry=tool_registry
    )
    
    return MCPServer(config)


# CLI entry point for standalone server
async def main():
    """Main entry point for standalone MCP server"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP Server")
    parser.add_argument("--name", default="BasicMCPServer", help="Server name")
    parser.add_argument("--version", default="1.0.0", help="Server version")
    parser.add_argument("--no-tools", action="store_true", help="Disable tools")
    parser.add_argument("--resources", action="store_true", help="Enable resources")
    parser.add_argument("--prompts", action="store_true", help="Enable prompts")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)]  # Log to stderr to avoid interfering with stdio
    )
    
    # Create and start server
    server = create_basic_server(
        name=args.name,
        version=args.version,
        enable_tools=not args.no_tools,
        enable_resources=args.resources,
        enable_prompts=args.prompts
    )
    
    await server.start_stdio()


if __name__ == "__main__":
    asyncio.run(main())