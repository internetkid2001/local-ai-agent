# Model Context Protocol (MCP) Reference

## Overview

The Model Context Protocol (MCP) is an open standard for connecting AI assistants to external data sources and tools. It enables secure, controlled access to local and remote resources.

## Core Concepts

### 1. MCP Server
A server that exposes capabilities (tools, resources, prompts) to MCP clients. In our case, these will be:
- **Filesystem Server**: File operations and management
- **System Server**: System control and monitoring
- **Desktop Server**: GUI automation and screen interaction

### 2. MCP Client
The client that connects to MCP servers to access their capabilities. Our AI agent will be the client.

### 3. Transport Layer
How client and server communicate:
- **Local**: stdio (stdin/stdout)
- **Network**: HTTP/WebSocket
- **SSE**: Server-Sent Events

## MCP Server Implementation

### Basic Server Structure
```python
from mcp import MCPServer, Resource, Tool
from mcp.types import TextContent

class FilesystemServer(MCPServer):
    def __init__(self):
        super().__init__("filesystem")
        
    async def list_tools(self):
        return [
            Tool(
                name="read_file",
                description="Read contents of a file",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"}
                    }
                }
            ),
            Tool(
                name="write_file", 
                description="Write content to a file",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"}
                    }
                }
            )
        ]
    
    async def call_tool(self, name: str, arguments: dict):
        if name == "read_file":
            return await self._read_file(arguments["path"])
        elif name == "write_file":
            return await self._write_file(arguments["path"], arguments["content"])
            
    async def _read_file(self, path: str):
        try:
            with open(path, 'r') as f:
                content = f.read()
            return [TextContent(type="text", text=content)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {e}")]
```

### MCP Client Integration
```python
import asyncio
from mcp import ClientSession, StdioServerParameters

class MCPClient:
    def __init__(self):
        self.sessions = {}
    
    async def connect_server(self, name: str, command: list):
        """Connect to an MCP server"""
        server_params = StdioServerParameters(command=command)
        session = ClientSession(server_params)
        await session.initialize()
        self.sessions[name] = session
        return session
    
    async def call_tool(self, server: str, tool: str, args: dict):
        """Call a tool on a specific server"""
        if server not in self.sessions:
            raise ValueError(f"Server {server} not connected")
        
        session = self.sessions[server]
        result = await session.call_tool(tool, args)
        return result
```

## Available MCP Servers

### 1. Filesystem Server
**Capabilities:**
- Read/write files
- List directories
- Search files by name/content
- Copy/move/delete operations
- File metadata access

**Tools:**
- `read_file(path)`
- `write_file(path, content)`
- `list_directory(path)`
- `search_files(pattern, directory)`
- `copy_file(source, destination)`
- `delete_file(path)`

### 2. System Server
**Capabilities:**
- Execute shell commands
- Process management
- System monitoring
- Service control

**Tools:**
- `run_command(command, args)`
- `get_processes()`
- `kill_process(pid)`
- `get_system_info()`
- `monitor_resources()`

### 3. Desktop Server
**Capabilities:**
- Screen capture
- Mouse/keyboard automation
- Window management
- OCR text extraction

**Tools:**
- `take_screenshot(region)`
- `click_at(x, y)`
- `type_text(text)`
- `get_windows()`
- `extract_text_from_image()`

## Security Considerations

### Server-Side Security
- Input validation and sanitization
- Path traversal protection
- Command injection prevention
- Resource limits and timeouts

### Client-Side Security
- Server capability verification
- Permission-based access control
- Audit logging
- Safe mode operation

### Example Security Implementation
```python
import os
from pathlib import Path

class SecureFilesystemServer:
    def __init__(self, allowed_paths: list):
        self.allowed_paths = [Path(p).resolve() for p in allowed_paths]
    
    def _validate_path(self, path: str) -> bool:
        """Ensure path is within allowed directories"""
        resolved_path = Path(path).resolve()
        return any(
            str(resolved_path).startswith(str(allowed))
            for allowed in self.allowed_paths
        )
    
    async def read_file(self, path: str):
        if not self._validate_path(path):
            raise PermissionError("Path not allowed")
        # ... rest of implementation
```

## Integration with Ollama

### Function Calling Setup
```python
import requests
import json

class OllamaAgent:
    def __init__(self, model="llama3.1:8b"):
        self.model = model
        self.base_url = "http://localhost:11434"
        
    async def chat_with_tools(self, message: str, tools: list):
        """Chat with function calling capabilities"""
        
        # Format tools for Ollama
        formatted_tools = []
        for tool in tools:
            formatted_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                }
            })
        
        response = requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": message}],
                "tools": formatted_tools,
                "stream": False
            }
        )
        
        return response.json()
```

## Configuration

### MCP Server Configuration
```json
{
  "servers": {
    "filesystem": {
      "command": ["python", "mcp-servers/filesystem/server.py"],
      "env": {
        "ALLOWED_PATHS": "/home/vic/Documents,/home/vic/Downloads"
      }
    },
    "system": {
      "command": ["python", "mcp-servers/system/server.py"],
      "env": {
        "SAFE_MODE": "true"
      }
    },
    "desktop": {
      "command": ["python", "mcp-servers/desktop/server.py"],
      "env": {
        "SCREENSHOT_DIR": "/tmp/screenshots"
      }
    }
  }
}
```

## Best Practices

1. **Always validate inputs** before processing
2. **Use explicit permissions** for sensitive operations
3. **Log all actions** for debugging and security
4. **Implement timeouts** to prevent hanging operations
5. **Use structured error handling** with clear messages
6. **Test in safe mode** before enabling full capabilities

## Debugging

### Enable MCP Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("mcp")
```

### Common Issues
- **Connection refused**: Check if server is running
- **Permission denied**: Verify path permissions and security settings
- **Tool not found**: Ensure tool is properly registered
- **Timeout errors**: Check for long-running operations

## Resources

- [Official MCP Specification](https://github.com/modelcontextprotocol/spec)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Example Servers](https://github.com/modelcontextprotocol/servers)
