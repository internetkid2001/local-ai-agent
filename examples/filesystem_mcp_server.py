#!/usr/bin/env python3
"""
Filesystem MCP Server
Provides file system operations through MCP protocol
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import mimetypes
import hashlib
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FilesystemMCPServer:
    """MCP Server for filesystem operations"""
    
    def __init__(self, allowed_paths: List[str] = None, max_file_size: int = 10 * 1024 * 1024):
        self.allowed_paths = [Path(p).resolve() for p in (allowed_paths or [])]
        self.max_file_size = max_file_size
        self.operations_count = 0
        self.start_time = time.time()
        
    def _validate_path(self, path: str) -> tuple[bool, str]:
        """Validate if path is allowed"""
        try:
            resolved_path = Path(path).resolve()
            
            if not self.allowed_paths:
                return True, str(resolved_path)
            
            for allowed in self.allowed_paths:
                if str(resolved_path).startswith(str(allowed)):
                    return True, str(resolved_path)
            
            return False, f"Path '{path}' is not in allowed directories"
            
        except Exception as e:
            return False, f"Invalid path: {e}"
    
    def _get_file_info(self, path: Path) -> Dict[str, Any]:
        """Get detailed file information"""
        try:
            stat = path.stat()
            
            file_info = {
                "name": path.name,
                "path": str(path),
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "created": stat.st_ctime,
                "is_file": path.is_file(),
                "is_dir": path.is_dir(),
                "permissions": oct(stat.st_mode)[-3:],
            }
            
            if path.is_file():
                file_info["mime_type"] = mimetypes.guess_type(str(path))[0]
                
                # Calculate file hash for small files
                if stat.st_size < 1024 * 1024:  # 1MB
                    try:
                        with open(path, 'rb') as f:
                            file_hash = hashlib.md5(f.read()).hexdigest()
                        file_info["md5_hash"] = file_hash
                    except:
                        pass
            
            return file_info
            
        except Exception as e:
            return {"error": str(e)}
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP requests"""
        try:
            method = request.get("method")
            params = request.get("params", {})
            request_id = request.get("id")
            
            self.operations_count += 1
            
            if method == "tools/list":
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "tools": [
                            {
                                "name": "read_file",
                                "description": "Read the contents of a file",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "path": {
                                            "type": "string",
                                            "description": "Path to the file to read"
                                        }
                                    },
                                    "required": ["path"]
                                }
                            },
                            {
                                "name": "write_file",
                                "description": "Write content to a file",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "path": {
                                            "type": "string",
                                            "description": "Path to the file to write"
                                        },
                                        "content": {
                                            "type": "string",
                                            "description": "Content to write to the file"
                                        }
                                    },
                                    "required": ["path", "content"]
                                }
                            },
                            {
                                "name": "list_directory",
                                "description": "List contents of a directory",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "path": {
                                            "type": "string",
                                            "description": "Directory path to list"
                                        },
                                        "detailed": {
                                            "type": "boolean",
                                            "description": "Include detailed file information",
                                            "default": False
                                        }
                                    },
                                    "required": ["path"]
                                }
                            },
                            {
                                "name": "search_files",
                                "description": "Search for files by name pattern",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "directory": {
                                            "type": "string",
                                            "description": "Directory to search in"
                                        },
                                        "pattern": {
                                            "type": "string",
                                            "description": "File name pattern to search for"
                                        },
                                        "recursive": {
                                            "type": "boolean",
                                            "description": "Search recursively in subdirectories",
                                            "default": True
                                        }
                                    },
                                    "required": ["directory", "pattern"]
                                }
                            },
                            {
                                "name": "get_file_info",
                                "description": "Get detailed information about a file or directory",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "path": {
                                            "type": "string",
                                            "description": "Path to the file or directory"
                                        }
                                    },
                                    "required": ["path"]
                                }
                            },
                            {
                                "name": "delete_file",
                                "description": "Delete a file or empty directory",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "path": {
                                            "type": "string",
                                            "description": "Path to the file or directory to delete"
                                        }
                                    },
                                    "required": ["path"]
                                }
                            },
                            {
                                "name": "copy_file",
                                "description": "Copy a file to a new location",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "source": {
                                            "type": "string",
                                            "description": "Source file path"
                                        },
                                        "destination": {
                                            "type": "string",
                                            "description": "Destination file path"
                                        }
                                    },
                                    "required": ["source", "destination"]
                                }
                            },
                            {
                                "name": "server_stats",
                                "description": "Get server statistics and status",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {}
                                }
                            }
                        ]
                    }
                }
            
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if tool_name == "read_file":
                    result = await self._read_file(arguments.get("path"))
                elif tool_name == "write_file":
                    result = await self._write_file(
                        arguments.get("path"),
                        arguments.get("content")
                    )
                elif tool_name == "list_directory":
                    result = await self._list_directory(
                        arguments.get("path"),
                        arguments.get("detailed", False)
                    )
                elif tool_name == "search_files":
                    result = await self._search_files(
                        arguments.get("directory"),
                        arguments.get("pattern"),
                        arguments.get("recursive", True)
                    )
                elif tool_name == "get_file_info":
                    result = await self._get_file_info_tool(arguments.get("path"))
                elif tool_name == "delete_file":
                    result = await self._delete_file(arguments.get("path"))
                elif tool_name == "copy_file":
                    result = await self._copy_file(
                        arguments.get("source"),
                        arguments.get("destination")
                    )
                elif tool_name == "server_stats":
                    result = await self._server_stats()
                else:
                    result = {
                        "content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}],
                        "isError": True
                    }
                
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result
                }
            
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
                
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {e}"
                }
            }
    
    async def _read_file(self, path: str) -> Dict[str, Any]:
        """Read file contents"""
        try:
            is_valid, resolved_path = self._validate_path(path)
            if not is_valid:
                return {
                    "content": [{"type": "text", "text": resolved_path}],
                    "isError": True
                }
            
            path_obj = Path(resolved_path)
            if not path_obj.exists():
                return {
                    "content": [{"type": "text", "text": f"File not found: {path}"}],
                    "isError": True
                }
            
            if not path_obj.is_file():
                return {
                    "content": [{"type": "text", "text": f"Not a file: {path}"}],
                    "isError": True
                }
            
            if path_obj.stat().st_size > self.max_file_size:
                return {
                    "content": [{"type": "text", "text": f"File too large: {path}"}],
                    "isError": True
                }
            
            with open(path_obj, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "content": [{"type": "text", "text": content}]
            }
            
        except UnicodeDecodeError:
            return {
                "content": [{"type": "text", "text": f"Cannot read binary file: {path}"}],
                "isError": True
            }
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"Error reading file: {e}"}],
                "isError": True
            }
    
    async def _write_file(self, path: str, content: str) -> Dict[str, Any]:
        """Write content to file"""
        try:
            is_valid, resolved_path = self._validate_path(path)
            if not is_valid:
                return {
                    "content": [{"type": "text", "text": resolved_path}],
                    "isError": True
                }
            
            if len(content.encode('utf-8')) > self.max_file_size:
                return {
                    "content": [{"type": "text", "text": "Content too large"}],
                    "isError": True
                }
            
            path_obj = Path(resolved_path)
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path_obj, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                "content": [{"type": "text", "text": f"Successfully wrote to {path}"}]
            }
            
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"Error writing file: {e}"}],
                "isError": True
            }
    
    async def _list_directory(self, path: str, detailed: bool = False) -> Dict[str, Any]:
        """List directory contents"""
        try:
            is_valid, resolved_path = self._validate_path(path)
            if not is_valid:
                return {
                    "content": [{"type": "text", "text": resolved_path}],
                    "isError": True
                }
            
            path_obj = Path(resolved_path)
            if not path_obj.exists():
                return {
                    "content": [{"type": "text", "text": f"Directory not found: {path}"}],
                    "isError": True
                }
            
            if not path_obj.is_dir():
                return {
                    "content": [{"type": "text", "text": f"Not a directory: {path}"}],
                    "isError": True
                }
            
            items = []
            for item in sorted(path_obj.iterdir()):
                if detailed:
                    info = self._get_file_info(item)
                    items.append(info)
                else:
                    item_type = "DIR" if item.is_dir() else "FILE"
                    size = item.stat().st_size if item.is_file() else 0
                    items.append(f"{item_type:4} {size:>8} {item.name}")
            
            if detailed:
                content = json.dumps(items, indent=2)
            else:
                content = f"Contents of {path}:\n" + "\n".join(items)
            
            return {
                "content": [{"type": "text", "text": content}]
            }
            
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"Error listing directory: {e}"}],
                "isError": True
            }
    
    async def _search_files(self, directory: str, pattern: str, recursive: bool = True) -> Dict[str, Any]:
        """Search for files matching pattern"""
        try:
            import fnmatch
            
            is_valid, resolved_path = self._validate_path(directory)
            if not is_valid:
                return {
                    "content": [{"type": "text", "text": resolved_path}],
                    "isError": True
                }
            
            path_obj = Path(resolved_path)
            if not path_obj.exists() or not path_obj.is_dir():
                return {
                    "content": [{"type": "text", "text": f"Directory not found: {directory}"}],
                    "isError": True
                }
            
            matches = []
            
            if recursive:
                for item in path_obj.rglob("*"):
                    if fnmatch.fnmatch(item.name, pattern):
                        matches.append(str(item))
            else:
                for item in path_obj.iterdir():
                    if fnmatch.fnmatch(item.name, pattern):
                        matches.append(str(item))
            
            result = f"Found {len(matches)} files matching '{pattern}' in {directory}:\n"
            result += "\n".join(matches)
            
            return {
                "content": [{"type": "text", "text": result}]
            }
            
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"Error searching files: {e}"}],
                "isError": True
            }
    
    async def _get_file_info_tool(self, path: str) -> Dict[str, Any]:
        """Get file information"""
        try:
            is_valid, resolved_path = self._validate_path(path)
            if not is_valid:
                return {
                    "content": [{"type": "text", "text": resolved_path}],
                    "isError": True
                }
            
            path_obj = Path(resolved_path)
            if not path_obj.exists():
                return {
                    "content": [{"type": "text", "text": f"Path not found: {path}"}],
                    "isError": True
                }
            
            info = self._get_file_info(path_obj)
            content = json.dumps(info, indent=2)
            
            return {
                "content": [{"type": "text", "text": content}]
            }
            
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"Error getting file info: {e}"}],
                "isError": True
            }
    
    async def _delete_file(self, path: str) -> Dict[str, Any]:
        """Delete file or directory"""
        try:
            is_valid, resolved_path =