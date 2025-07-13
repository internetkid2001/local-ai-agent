"""
MCP Protocol Definitions

Core protocol definitions for the Model Context Protocol (MCP).
Based on the Anthropic MCP specification.

Author: Claude Code
Date: 2025-07-13
Session: 4.4
"""

import json
import uuid
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class MCPMessageType(Enum):
    """MCP message types"""
    # Initialization
    INITIALIZE = "initialize"
    INITIALIZED = "initialized"
    
    # Tools
    LIST_TOOLS = "tools/list"
    CALL_TOOL = "tools/call"
    
    # Resources
    LIST_RESOURCES = "resources/list"
    READ_RESOURCE = "resources/read"
    
    # Prompts
    LIST_PROMPTS = "prompts/list"
    GET_PROMPT = "prompts/get"
    
    # Logging
    LOG = "logging/setLevel"
    
    # Notifications
    NOTIFICATION = "notification"
    
    # Progress
    PROGRESS = "progress"
    
    # Completion
    COMPLETE = "completion/complete"
    
    # Ping/Pong
    PING = "ping"
    PONG = "pong"


class MCPCapability(Enum):
    """MCP capabilities"""
    TOOLS = "tools"
    RESOURCES = "resources"
    PROMPTS = "prompts"
    LOGGING = "logging"
    SAMPLING = "sampling"


class MCPRole(Enum):
    """MCP roles"""
    CLIENT = "client"
    SERVER = "server"


@dataclass
class MCPClientInfo:
    """MCP client information"""
    name: str
    version: str


@dataclass
class MCPServerInfo:
    """MCP server information"""
    name: str
    version: str


@dataclass
class MCPCapabilities:
    """MCP capabilities"""
    tools: Optional[Dict[str, Any]] = None
    resources: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, Any]] = None
    logging: Optional[Dict[str, Any]] = None
    sampling: Optional[Dict[str, Any]] = None


@dataclass
class MCPMessage:
    """Base MCP message"""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.id is None and (self.method or self.result is not None or self.error is not None):
            self.id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {"jsonrpc": self.jsonrpc}
        
        if self.id is not None:
            result["id"] = self.id
        if self.method is not None:
            result["method"] = self.method
        if self.params is not None:
            result["params"] = self.params
        if self.result is not None:
            result["result"] = self.result
        if self.error is not None:
            result["error"] = self.error
            
        return result
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPMessage':
        """Create from dictionary"""
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            id=data.get("id"),
            method=data.get("method"),
            params=data.get("params"),
            result=data.get("result"),
            error=data.get("error")
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'MCPMessage':
        """Create from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class MCPTool:
    """MCP tool definition"""
    name: str
    description: str
    inputSchema: Dict[str, Any]


@dataclass
class MCPResource:
    """MCP resource definition"""
    uri: str
    name: str
    description: Optional[str] = None
    mimeType: Optional[str] = None


@dataclass
class MCPPrompt:
    """MCP prompt definition"""
    name: str
    description: str
    arguments: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class MCPError:
    """MCP error"""
    code: int
    message: str
    data: Optional[Any] = None


class MCPErrorCode(Enum):
    """Standard MCP error codes"""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    
    # MCP-specific errors
    TOOL_NOT_FOUND = -32000
    RESOURCE_NOT_FOUND = -32001
    PROMPT_NOT_FOUND = -32002
    CAPABILITY_NOT_SUPPORTED = -32003


# Message builders
def create_initialize_message(
    client_info: MCPClientInfo,
    capabilities: MCPCapabilities,
    protocol_version: str = "2024-11-05"
) -> MCPMessage:
    """Create initialize message"""
    return MCPMessage(
        method=MCPMessageType.INITIALIZE.value,
        params={
            "protocolVersion": protocol_version,
            "clientInfo": {
                "name": client_info.name,
                "version": client_info.version
            },
            "capabilities": {
                k: v for k, v in {
                    "tools": capabilities.tools,
                    "resources": capabilities.resources,
                    "prompts": capabilities.prompts,
                    "logging": capabilities.logging,
                    "sampling": capabilities.sampling
                }.items() if v is not None
            }
        }
    )


def create_initialized_message(request_id: Union[str, int]) -> MCPMessage:
    """Create initialized response message"""
    return MCPMessage(
        id=request_id,
        result={}
    )


def create_list_tools_message() -> MCPMessage:
    """Create list tools message"""
    return MCPMessage(
        method=MCPMessageType.LIST_TOOLS.value,
        params={}
    )


def create_call_tool_message(tool_name: str, arguments: Dict[str, Any]) -> MCPMessage:
    """Create call tool message"""
    return MCPMessage(
        method=MCPMessageType.CALL_TOOL.value,
        params={
            "name": tool_name,
            "arguments": arguments
        }
    )


def create_list_resources_message() -> MCPMessage:
    """Create list resources message"""
    return MCPMessage(
        method=MCPMessageType.LIST_RESOURCES.value,
        params={}
    )


def create_read_resource_message(uri: str) -> MCPMessage:
    """Create read resource message"""
    return MCPMessage(
        method=MCPMessageType.READ_RESOURCE.value,
        params={
            "uri": uri
        }
    )


def create_list_prompts_message() -> MCPMessage:
    """Create list prompts message"""
    return MCPMessage(
        method=MCPMessageType.LIST_PROMPTS.value,
        params={}
    )


def create_get_prompt_message(prompt_name: str, arguments: Optional[Dict[str, Any]] = None) -> MCPMessage:
    """Create get prompt message"""
    params = {"name": prompt_name}
    if arguments:
        params["arguments"] = arguments
    
    return MCPMessage(
        method=MCPMessageType.GET_PROMPT.value,
        params=params
    )


def create_error_response(request_id: Union[str, int], error_code: MCPErrorCode, message: str, data: Any = None) -> MCPMessage:
    """Create error response message"""
    return MCPMessage(
        id=request_id,
        error={
            "code": error_code.value,
            "message": message,
            "data": data
        }
    )


def create_success_response(request_id: Union[str, int], result: Any) -> MCPMessage:
    """Create success response message"""
    return MCPMessage(
        id=request_id,
        result=result
    )


def create_notification(method: str, params: Optional[Dict[str, Any]] = None) -> MCPMessage:
    """Create notification message (no response expected)"""
    return MCPMessage(
        method=method,
        params=params or {}
    )


def create_ping_message() -> MCPMessage:
    """Create ping message"""
    return MCPMessage(
        method=MCPMessageType.PING.value,
        params={}
    )


def create_pong_message(request_id: Union[str, int]) -> MCPMessage:
    """Create pong response"""
    return MCPMessage(
        id=request_id,
        result={}
    )


# Validation helpers
def validate_message(message: MCPMessage) -> Optional[str]:
    """Validate MCP message format"""
    if message.jsonrpc != "2.0":
        return "Invalid JSON-RPC version"
    
    # Request validation
    if message.method is not None:
        if message.result is not None or message.error is not None:
            return "Request cannot have result or error"
    
    # Response validation
    elif message.result is not None or message.error is not None:
        if message.id is None:
            return "Response must have id"
        if message.result is not None and message.error is not None:
            return "Response cannot have both result and error"
    
    else:
        return "Message must be either request or response"
    
    return None


def is_request(message: MCPMessage) -> bool:
    """Check if message is a request"""
    return message.method is not None


def is_response(message: MCPMessage) -> bool:
    """Check if message is a response"""
    return message.result is not None or message.error is not None


def is_notification(message: MCPMessage) -> bool:
    """Check if message is a notification (request without id)"""
    return message.method is not None and message.id is None