"""
Filesystem MCP Server

A secure MCP server implementation for file system operations with sandboxing,
search functionality, and comprehensive error handling.

Author: Claude Code
Date: 2025-07-13
Session: 1.2
"""

import asyncio
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
import logging
import mimetypes
import hashlib
from datetime import datetime

# MCP protocol imports
try:
    import websockets
    from websockets.server import WebSocketServerProtocol
except ImportError:
    print("websockets library required. Install with: pip install websockets")
    raise

logger = logging.getLogger(__name__)


@dataclass
class FileSystemConfig:
    """Configuration for filesystem MCP server"""
    allowed_paths: List[str]
    sandbox_root: str
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    max_search_results: int = 1000
    allowed_extensions: List[str] = None
    denied_extensions: List[str] = None
    read_only: bool = False
    
    def __post_init__(self):
        if self.allowed_extensions is None:
            self.allowed_extensions = []
        if self.denied_extensions is None:
            self.denied_extensions = ['.exe', '.bat', '.cmd', '.scr', '.com']


class SecurityError(Exception):
    """Raised when security constraints are violated"""
    pass


class FileSystemValidator:
    """Validates file system operations for security"""
    
    def __init__(self, config: FileSystemConfig):
        self.config = config
        self.sandbox_root = Path(config.sandbox_root).resolve()
        self.allowed_paths = [Path(p).resolve() for p in config.allowed_paths]
    
    def validate_path(self, path: Union[str, Path]) -> Path:
        """
        Validate and resolve a path for security.
        
        Args:
            path: Path to validate
            
        Returns:
            Resolved secure path
            
        Raises:
            SecurityError: If path is not allowed
        """
        path = Path(path).resolve()
        
        # Check if path is within sandbox
        try:
            path.relative_to(self.sandbox_root)
        except ValueError:
            raise SecurityError(f"Path outside sandbox: {path}")
        
        # Check if path is within allowed paths
        if self.allowed_paths:
            allowed = False
            for allowed_path in self.allowed_paths:
                try:
                    path.relative_to(allowed_path)
                    allowed = True
                    break
                except ValueError:
                    continue
            
            if not allowed:
                raise SecurityError(f"Path not in allowed directories: {path}")
        
        return path
    
    def validate_file_extension(self, path: Path):
        """Validate file extension against allowed/denied lists"""
        extension = path.suffix.lower()
        
        if self.config.denied_extensions and extension in self.config.denied_extensions:
            raise SecurityError(f"File extension not allowed: {extension}")
        
        if self.config.allowed_extensions and extension not in self.config.allowed_extensions:
            raise SecurityError(f"File extension not in allowed list: {extension}")
    
    def validate_file_size(self, size: int):
        """Validate file size against limits"""
        if size > self.config.max_file_size:
            raise SecurityError(f"File size exceeds limit: {size} > {self.config.max_file_size}")
    
    def validate_write_operation(self):
        """Check if write operations are allowed"""
        if self.config.read_only:
            raise SecurityError("Server is in read-only mode")


class FileSystemMCPServer:
    """
    Filesystem MCP Server implementation.
    
    Provides secure file system operations including:
    - Reading and writing files
    - Directory operations
    - File search and filtering
    - Metadata retrieval
    - Content type detection
    """
    
    def __init__(self, config: FileSystemConfig):
        """
        Initialize filesystem MCP server.
        
        Args:
            config: Server configuration
        """
        self.config = config
        self.validator = FileSystemValidator(config)
        self.tools = self._define_tools()
        
        # Create sandbox directory if it doesn't exist
        sandbox_path = Path(config.sandbox_root)
        sandbox_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Filesystem MCP server initialized")
        logger.info(f"Sandbox root: {config.sandbox_root}")
        logger.info(f"Allowed paths: {config.allowed_paths}")
    
    def _define_tools(self) -> Dict[str, Dict[str, Any]]:
        """Define available MCP tools"""
        return {
            "read_file": {
                "description": "Read contents of a file",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the file to read"
                        },
                        "encoding": {
                            "type": "string",
                            "description": "File encoding (default: utf-8)",
                            "default": "utf-8"
                        }
                    },
                    "required": ["path"]
                }
            },
            "write_file": {
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
                        },
                        "encoding": {
                            "type": "string",
                            "description": "File encoding (default: utf-8)",
                            "default": "utf-8"
                        },
                        "create_dirs": {
                            "type": "boolean",
                            "description": "Create parent directories if they don't exist",
                            "default": False
                        }
                    },
                    "required": ["path", "content"]
                }
            },
            "list_directory": {
                "description": "List contents of a directory",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the directory"
                        },
                        "recursive": {
                            "type": "boolean",
                            "description": "Include subdirectories recursively",
                            "default": False
                        },
                        "include_hidden": {
                            "type": "boolean",
                            "description": "Include hidden files and directories",
                            "default": False
                        }
                    },
                    "required": ["path"]
                }
            },
            "create_directory": {
                "description": "Create a directory",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the directory to create"
                        },
                        "parents": {
                            "type": "boolean",
                            "description": "Create parent directories if they don't exist",
                            "default": False
                        }
                    },
                    "required": ["path"]
                }
            },
            "delete_file": {
                "description": "Delete a file or directory",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the file or directory to delete"
                        },
                        "recursive": {
                            "type": "boolean",
                            "description": "Delete directories recursively",
                            "default": False
                        }
                    },
                    "required": ["path"]
                }
            },
            "copy_file": {
                "description": "Copy a file or directory",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "source": {
                            "type": "string",
                            "description": "Source path"
                        },
                        "destination": {
                            "type": "string",
                            "description": "Destination path"
                        },
                        "overwrite": {
                            "type": "boolean",
                            "description": "Overwrite destination if it exists",
                            "default": False
                        }
                    },
                    "required": ["source", "destination"]
                }
            },
            "move_file": {
                "description": "Move/rename a file or directory",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "source": {
                            "type": "string",
                            "description": "Source path"
                        },
                        "destination": {
                            "type": "string",
                            "description": "Destination path"
                        },
                        "overwrite": {
                            "type": "boolean",
                            "description": "Overwrite destination if it exists",
                            "default": False
                        }
                    },
                    "required": ["source", "destination"]
                }
            },
            "get_file_info": {
                "description": "Get file or directory metadata",
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
            "search_files": {
                "description": "Search for files and directories",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to search in"
                        },
                        "pattern": {
                            "type": "string",
                            "description": "Search pattern (glob or regex)"
                        },
                        "content_search": {
                            "type": "string",
                            "description": "Search within file contents"
                        },
                        "case_sensitive": {
                            "type": "boolean",
                            "description": "Case sensitive search",
                            "default": False
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 100
                        }
                    },
                    "required": ["path"]
                }
            }
        }
    
    async def handle_mcp_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle MCP protocol request.
        
        Args:
            request: MCP request message
            
        Returns:
            MCP response message
        """
        try:
            method = request.get("method")
            params = request.get("params", {})
            request_id = request.get("id")
            
            if method == "tools/list":
                response = await self._handle_tools_list()
            elif method == "tools/call":
                response = await self._handle_tool_call(params)
            else:
                response = {
                    "error": {
                        "code": -32601,
                        "message": f"Unknown method: {method}"
                    }
                }
            
            if request_id:
                response["id"] = request_id
            
            return response
            
        except Exception as e:
            logger.error(f"Error handling MCP request: {e}")
            return {
                "id": request.get("id"),
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def _handle_tools_list(self) -> Dict[str, Any]:
        """Handle tools/list request"""
        tools_list = []
        for tool_name, tool_def in self.tools.items():
            tools_list.append({
                "name": tool_name,
                "description": tool_def["description"],
                "inputSchema": tool_def["inputSchema"]
            })
        
        return {
            "tools": tools_list
        }
    
    async def _handle_tool_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name not in self.tools:
            return {
                "error": {
                    "code": -32602,
                    "message": f"Unknown tool: {tool_name}"
                }
            }
        
        try:
            # Route to appropriate handler
            handler_name = f"_handle_{tool_name}"
            handler = getattr(self, handler_name, None)
            
            if not handler:
                return {
                    "error": {
                        "code": -32603,
                        "message": f"No handler for tool: {tool_name}"
                    }
                }
            
            result = await handler(arguments)
            return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
            
        except SecurityError as e:
            return {
                "error": {
                    "code": -32602,
                    "message": f"Security error: {str(e)}"
                }
            }
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return {
                "error": {
                    "code": -32603,
                    "message": f"Tool execution failed: {str(e)}"
                }
            }
    
    async def _handle_read_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle read_file tool"""
        path = self.validator.validate_path(args["path"])
        encoding = args.get("encoding", "utf-8")
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        if not path.is_file():
            raise ValueError(f"Path is not a file: {path}")
        
        self.validator.validate_file_extension(path)
        
        try:
            content = path.read_text(encoding=encoding)
            return {
                "success": True,
                "content": content,
                "path": str(path),
                "encoding": encoding,
                "size": len(content.encode(encoding))
            }
        except UnicodeDecodeError:
            # Try binary read for non-text files
            content = path.read_bytes()
            return {
                "success": True,
                "content": content.hex(),
                "path": str(path),
                "encoding": "binary",
                "size": len(content)
            }
    
    async def _handle_write_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle write_file tool"""
        self.validator.validate_write_operation()
        
        path = self.validator.validate_path(args["path"])
        content = args["content"]
        encoding = args.get("encoding", "utf-8")
        create_dirs = args.get("create_dirs", False)
        
        self.validator.validate_file_extension(path)
        self.validator.validate_file_size(len(content.encode(encoding)))
        
        if create_dirs:
            path.parent.mkdir(parents=True, exist_ok=True)
        
        path.write_text(content, encoding=encoding)
        
        return {
            "success": True,
            "path": str(path),
            "size": path.stat().st_size,
            "encoding": encoding
        }
    
    async def _handle_list_directory(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle list_directory tool"""
        path = self.validator.validate_path(args["path"])
        recursive = args.get("recursive", False)
        include_hidden = args.get("include_hidden", False)
        
        if not path.exists():
            raise FileNotFoundError(f"Directory not found: {path}")
        
        if not path.is_dir():
            raise ValueError(f"Path is not a directory: {path}")
        
        items = []
        
        if recursive:
            pattern = "**/*" if include_hidden else "**/[!.]*"
            for item in path.glob(pattern):
                items.append(self._get_item_info(item))
        else:
            for item in path.iterdir():
                if not include_hidden and item.name.startswith('.'):
                    continue
                items.append(self._get_item_info(item))
        
        return {
            "success": True,
            "path": str(path),
            "items": sorted(items, key=lambda x: (x["type"], x["name"]))
        }
    
    async def _handle_create_directory(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle create_directory tool"""
        self.validator.validate_write_operation()
        
        path = self.validator.validate_path(args["path"])
        parents = args.get("parents", False)
        
        path.mkdir(parents=parents, exist_ok=True)
        
        return {
            "success": True,
            "path": str(path),
            "created": True
        }
    
    async def _handle_delete_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle delete_file tool"""
        self.validator.validate_write_operation()
        
        path = self.validator.validate_path(args["path"])
        recursive = args.get("recursive", False)
        
        if not path.exists():
            raise FileNotFoundError(f"Path not found: {path}")
        
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            if recursive:
                shutil.rmtree(path)
            else:
                path.rmdir()  # Will fail if directory is not empty
        
        return {
            "success": True,
            "path": str(path),
            "deleted": True
        }
    
    async def _handle_copy_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle copy_file tool"""
        self.validator.validate_write_operation()
        
        source = self.validator.validate_path(args["source"])
        destination = self.validator.validate_path(args["destination"])
        overwrite = args.get("overwrite", False)
        
        if not source.exists():
            raise FileNotFoundError(f"Source not found: {source}")
        
        if destination.exists() and not overwrite:
            raise FileExistsError(f"Destination exists: {destination}")
        
        if source.is_file():
            shutil.copy2(source, destination)
        elif source.is_dir():
            shutil.copytree(source, destination, dirs_exist_ok=overwrite)
        
        return {
            "success": True,
            "source": str(source),
            "destination": str(destination),
            "copied": True
        }
    
    async def _handle_move_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle move_file tool"""
        self.validator.validate_write_operation()
        
        source = self.validator.validate_path(args["source"])
        destination = self.validator.validate_path(args["destination"])
        overwrite = args.get("overwrite", False)
        
        if not source.exists():
            raise FileNotFoundError(f"Source not found: {source}")
        
        if destination.exists() and not overwrite:
            raise FileExistsError(f"Destination exists: {destination}")
        
        shutil.move(str(source), str(destination))
        
        return {
            "success": True,
            "source": str(source),
            "destination": str(destination),
            "moved": True
        }
    
    async def _handle_get_file_info(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_file_info tool"""
        path = self.validator.validate_path(args["path"])
        
        if not path.exists():
            raise FileNotFoundError(f"Path not found: {path}")
        
        info = self._get_item_info(path)
        
        # Add additional metadata for files
        if path.is_file():
            # Content type detection
            content_type, _ = mimetypes.guess_type(str(path))
            info["content_type"] = content_type
            
            # File hash for integrity
            with open(path, "rb") as f:
                content = f.read()
                info["md5_hash"] = hashlib.md5(content).hexdigest()
                info["sha256_hash"] = hashlib.sha256(content).hexdigest()
        
        return info
    
    async def _handle_search_files(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle search_files tool"""
        path = self.validator.validate_path(args["path"])
        pattern = args.get("pattern", "*")
        content_search = args.get("content_search")
        case_sensitive = args.get("case_sensitive", False)
        max_results = min(args.get("max_results", 100), self.config.max_search_results)
        
        if not path.exists():
            raise FileNotFoundError(f"Search path not found: {path}")
        
        if not path.is_dir():
            raise ValueError(f"Search path is not a directory: {path}")
        
        results = []
        
        # File name pattern search
        for item in path.glob(f"**/{pattern}"):
            if len(results) >= max_results:
                break
                
            item_info = self._get_item_info(item)
            
            # Content search if specified
            if content_search and item.is_file():
                try:
                    content = item.read_text(encoding='utf-8', errors='ignore')
                    search_text = content_search if case_sensitive else content_search.lower()
                    file_content = content if case_sensitive else content.lower()
                    
                    if search_text in file_content:
                        # Find matching lines
                        lines = content.split('\n')
                        matching_lines = []
                        for i, line in enumerate(lines, 1):
                            check_line = line if case_sensitive else line.lower()
                            if search_text in check_line:
                                matching_lines.append({"line": i, "content": line.strip()})
                        
                        item_info["content_matches"] = matching_lines[:10]  # Limit to 10 matches
                        results.append(item_info)
                except:
                    # Skip files that can't be read as text
                    continue
            else:
                results.append(item_info)
        
        return {
            "success": True,
            "search_path": str(path),
            "pattern": pattern,
            "content_search": content_search,
            "results": results,
            "total_found": len(results),
            "truncated": len(results) >= max_results
        }
    
    def _get_item_info(self, path: Path) -> Dict[str, Any]:
        """Get basic information about a file or directory"""
        stat = path.stat()
        
        return {
            "name": path.name,
            "path": str(path),
            "type": "directory" if path.is_dir() else "file",
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "permissions": oct(stat.st_mode)[-3:],
            "is_hidden": path.name.startswith('.'),
            "extension": path.suffix if path.is_file() else None
        }


# WebSocket server implementation
class MCPWebSocketServer:
    """WebSocket server for MCP protocol communication"""
    
    def __init__(self, fs_server: FileSystemMCPServer, host: str = "localhost", port: int = 8765):
        self.fs_server = fs_server
        self.host = host
        self.port = port
        self.clients = set()
    
    async def handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Handle WebSocket client connection"""
        self.clients.add(websocket)
        logger.info(f"Client connected: {websocket.remote_address}")
        
        try:
            async for message in websocket:
                try:
                    request = json.loads(message)
                    response = await self.fs_server.handle_mcp_request(request)
                    await websocket.send(json.dumps(response))
                except json.JSONDecodeError:
                    error_response = {
                        "error": {
                            "code": -32700,
                            "message": "Parse error: Invalid JSON"
                        }
                    }
                    await websocket.send(json.dumps(error_response))
                except Exception as e:
                    logger.error(f"Error handling client message: {e}")
                    error_response = {
                        "error": {
                            "code": -32603,
                            "message": f"Internal error: {str(e)}"
                        }
                    }
                    await websocket.send(json.dumps(error_response))
        
        finally:
            self.clients.remove(websocket)
            logger.info(f"Client disconnected: {websocket.remote_address}")
    
    async def start_server(self):
        """Start the WebSocket server"""
        logger.info(f"Starting MCP WebSocket server on {self.host}:{self.port}")
        
        server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port
        )
        
        logger.info(f"MCP WebSocket server running on ws://{self.host}:{self.port}")
        await server.wait_closed()


# CLI entry point
async def main():
    """Main entry point for the filesystem MCP server"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Filesystem MCP Server")
    parser.add_argument("--host", default="localhost", help="WebSocket host")
    parser.add_argument("--port", type=int, default=8765, help="WebSocket port")
    parser.add_argument("--sandbox", required=True, help="Sandbox root directory")
    parser.add_argument("--allowed-paths", nargs="+", help="Allowed paths for operations")
    parser.add_argument("--read-only", action="store_true", help="Read-only mode")
    parser.add_argument("--max-file-size", type=int, default=50*1024*1024, help="Max file size in bytes")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create configuration
    config = FileSystemConfig(
        allowed_paths=args.allowed_paths or [args.sandbox],
        sandbox_root=args.sandbox,
        max_file_size=args.max_file_size,
        read_only=args.read_only
    )
    
    # Create and start server
    fs_server = FileSystemMCPServer(config)
    ws_server = MCPWebSocketServer(fs_server, args.host, args.port)
    
    try:
        await ws_server.start_server()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")


if __name__ == "__main__":
    asyncio.run(main())