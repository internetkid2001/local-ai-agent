"""
MCP Tools Registry

Registry for MCP tools and utilities.

Author: Claude Code
Date: 2025-07-13
Session: 4.4
"""

import asyncio
import inspect
import json
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass
import logging

from .protocol import MCPTool

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """Tool definition with handler"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable
    is_async: bool = True


class ToolRegistry:
    """Registry for MCP tools"""
    
    def __init__(self):
        self.tools: Dict[str, ToolDefinition] = {}
        
    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        handler: Callable
    ):
        """Register a tool"""
        is_async = inspect.iscoroutinefunction(handler)
        
        tool_def = ToolDefinition(
            name=name,
            description=description,
            input_schema=input_schema,
            handler=handler,
            is_async=is_async
        )
        
        self.tools[name] = tool_def
        logger.info(f"Registered tool: {name}")
    
    def tool(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any]
    ):
        """Decorator for registering tools"""
        def decorator(func):
            self.register_tool(name, description, input_schema, func)
            return func
        return decorator
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool"""
        if name not in self.tools:
            raise ValueError(f"Tool {name} not found")
        
        tool_def = self.tools[name]
        
        try:
            if tool_def.is_async:
                result = await tool_def.handler(**arguments)
            else:
                result = tool_def.handler(**arguments)
            
            return result
            
        except Exception as e:
            logger.error(f"Tool {name} execution failed: {e}")
            raise
    
    def get_tool_list(self) -> List[MCPTool]:
        """Get list of available tools"""
        return [
            MCPTool(
                name=tool_def.name,
                description=tool_def.description,
                inputSchema=tool_def.input_schema
            )
            for tool_def in self.tools.values()
        ]
    
    def get_tool_definition(self, name: str) -> Optional[ToolDefinition]:
        """Get tool definition"""
        return self.tools.get(name)


# Global tool registry
default_registry = ToolRegistry()


# Common tool schemas
def create_string_parameter(description: str, required: bool = True) -> Dict[str, Any]:
    """Create a string parameter schema"""
    return {
        "type": "string",
        "description": description
    }


def create_number_parameter(description: str, minimum: Optional[float] = None, maximum: Optional[float] = None) -> Dict[str, Any]:
    """Create a number parameter schema"""
    schema = {
        "type": "number",
        "description": description
    }
    if minimum is not None:
        schema["minimum"] = minimum
    if maximum is not None:
        schema["maximum"] = maximum
    return schema


def create_boolean_parameter(description: str) -> Dict[str, Any]:
    """Create a boolean parameter schema"""
    return {
        "type": "boolean",
        "description": description
    }


def create_object_parameter(description: str, properties: Dict[str, Any], required: Optional[List[str]] = None) -> Dict[str, Any]:
    """Create an object parameter schema"""
    schema = {
        "type": "object",
        "description": description,
        "properties": properties
    }
    if required:
        schema["required"] = required
    return schema


def create_array_parameter(description: str, items: Dict[str, Any]) -> Dict[str, Any]:
    """Create an array parameter schema"""
    return {
        "type": "array",
        "description": description,
        "items": items
    }


def create_tool_schema(
    description: str,
    parameters: Dict[str, Dict[str, Any]],
    required: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Create a complete tool input schema"""
    return {
        "type": "object",
        "description": description,
        "properties": parameters,
        "required": required or []
    }


# Built-in tools
@default_registry.tool(
    name="echo",
    description="Echo back the input text",
    input_schema=create_tool_schema(
        "Echo tool for testing",
        {
            "text": create_string_parameter("Text to echo back")
        },
        required=["text"]
    )
)
async def echo_tool(text: str) -> str:
    """Echo tool for testing"""
    return f"Echo: {text}"


@default_registry.tool(
    name="calculate",
    description="Perform basic mathematical calculations",
    input_schema=create_tool_schema(
        "Basic calculator",
        {
            "expression": create_string_parameter("Mathematical expression to evaluate (e.g., '2 + 2', '10 * 5')")
        },
        required=["expression"]
    )
)
async def calculate_tool(expression: str) -> Union[float, str]:
    """Basic calculator tool"""
    try:
        # Simple evaluation (in real usage, would want more security)
        allowed_chars = set("0123456789+-*/.() ")
        if not all(c in allowed_chars for c in expression):
            return "Error: Invalid characters in expression"
        
        result = eval(expression)
        return result
        
    except Exception as e:
        return f"Error: {str(e)}"


@default_registry.tool(
    name="get_time",
    description="Get current time and date",
    input_schema=create_tool_schema(
        "Get current time",
        {
            "format": create_string_parameter("Time format (iso, timestamp, human)", required=False)
        }
    )
)
async def get_time_tool(format: str = "human") -> str:
    """Get current time"""
    import datetime
    
    now = datetime.datetime.now()
    
    if format == "iso":
        return now.isoformat()
    elif format == "timestamp":
        return str(now.timestamp())
    else:  # human
        return now.strftime("%Y-%m-%d %H:%M:%S")


@default_registry.tool(
    name="file_read",
    description="Read contents of a file",
    input_schema=create_tool_schema(
        "Read file contents",
        {
            "path": create_string_parameter("File path to read"),
            "encoding": create_string_parameter("File encoding", required=False)
        },
        required=["path"]
    )
)
async def file_read_tool(path: str, encoding: str = "utf-8") -> str:
    """Read file contents"""
    try:
        with open(path, "r", encoding=encoding) as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"


@default_registry.tool(
    name="file_write",
    description="Write contents to a file",
    input_schema=create_tool_schema(
        "Write file contents",
        {
            "path": create_string_parameter("File path to write"),
            "content": create_string_parameter("Content to write"),
            "encoding": create_string_parameter("File encoding", required=False),
            "append": create_boolean_parameter("Append to file instead of overwriting")
        },
        required=["path", "content"]
    )
)
async def file_write_tool(path: str, content: str, encoding: str = "utf-8", append: bool = False) -> str:
    """Write file contents"""
    try:
        mode = "a" if append else "w"
        with open(path, mode, encoding=encoding) as f:
            f.write(content)
        return f"Successfully {'appended to' if append else 'wrote'} file: {path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"


@default_registry.tool(
    name="list_files",
    description="List files in a directory",
    input_schema=create_tool_schema(
        "List directory contents",
        {
            "path": create_string_parameter("Directory path to list"),
            "pattern": create_string_parameter("File pattern to match (glob)", required=False),
            "recursive": create_boolean_parameter("List files recursively")
        },
        required=["path"]
    )
)
async def list_files_tool(path: str, pattern: str = "*", recursive: bool = False) -> List[str]:
    """List files in directory"""
    import os
    import glob
    
    try:
        if recursive:
            search_path = os.path.join(path, "**", pattern)
            files = glob.glob(search_path, recursive=True)
        else:
            search_path = os.path.join(path, pattern)
            files = glob.glob(search_path)
        
        return sorted(files)
        
    except Exception as e:
        return [f"Error listing files: {str(e)}"]


@default_registry.tool(
    name="execute_command",
    description="Execute a system command",
    input_schema=create_tool_schema(
        "Execute system command",
        {
            "command": create_string_parameter("Command to execute"),
            "cwd": create_string_parameter("Working directory", required=False),
            "timeout": create_number_parameter("Timeout in seconds", minimum=1, maximum=300)
        },
        required=["command"]
    )
)
async def execute_command_tool(command: str, cwd: Optional[str] = None, timeout: float = 30.0) -> Dict[str, Any]:
    """Execute system command"""
    import subprocess
    
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd
        )
        
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        
        return {
            "returncode": process.returncode,
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
            "success": process.returncode == 0
        }
        
    except asyncio.TimeoutError:
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": "Command timed out",
            "success": False
        }
    except Exception as e:
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
            "success": False
        }


# Utility function to get default tools
def get_default_tools() -> ToolRegistry:
    """Get the default tool registry"""
    return default_registry