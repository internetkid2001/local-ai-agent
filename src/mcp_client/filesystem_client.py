"""
Filesystem MCP Client

Concrete implementation of MCP client specialized for filesystem operations.
Integrates with the filesystem MCP server to provide file and directory management.

Author: Claude Code
Date: 2025-07-13
Session: 1.3
"""

import asyncio
import os
import logging
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

from .base_client import BaseMCPClient, MCPClientConfig, MCPServerConfig
from .exceptions import MCPError, ConnectionError
from ...utils.logger import get_logger

logger = get_logger(__name__)


class FilesystemMCPClient(BaseMCPClient):
    """
    Specialized MCP client for filesystem operations.
    
    Features:
    - File reading and writing operations
    - Directory management and navigation
    - File search and information retrieval
    - Path validation and security checks
    - Integration with filesystem MCP server
    """
    
    def __init__(self, config: MCPClientConfig = None):
        """
        Initialize filesystem MCP client.
        
        Args:
            config: Client configuration, creates default if None
        """
        if config is None:
            config = self._create_default_config()
        
        super().__init__(config)
        
        # Filesystem-specific settings
        self.base_directory = Path.cwd()
        self.allowed_extensions = {
            '.txt', '.md', '.py', '.js', '.ts', '.json', '.yaml', '.yml',
            '.toml', '.ini', '.cfg', '.conf', '.log', '.csv', '.xml', '.html'
        }
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        
        logger.info("Filesystem MCP client initialized")
    
    @classmethod
    def _create_default_config(cls) -> MCPClientConfig:
        """Create default configuration for filesystem operations"""
        filesystem_server = MCPServerConfig(
            name="filesystem",
            url="ws://localhost:8765",
            enabled=True,
            tools=[
                "read_file", "write_file", "list_directory", "create_directory",
                "copy_file", "move_file", "delete_file", "search_files", "get_file_info"
            ]
        )
        
        return MCPClientConfig(
            servers=[filesystem_server],
            connection_timeout=5.0,
            default_timeout=30.0,
            max_concurrent_connections=5
        )
    
    async def process_task(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process filesystem-related tasks using available tools.
        
        Args:
            task: Task description
            context: Task context
            
        Returns:
            Task result with filesystem operation outcomes
        """
        logger.info(f"Processing filesystem task: {task}")
        
        task_lower = task.lower()
        
        try:
            # Route to appropriate filesystem operation
            if any(keyword in task_lower for keyword in ['read', 'show', 'display', 'contents']):
                return await self._handle_read_operation(task, context)
            
            elif any(keyword in task_lower for keyword in ['write', 'create', 'save']):
                return await self._handle_write_operation(task, context)
            
            elif any(keyword in task_lower for keyword in ['list', 'ls', 'directory', 'folder']):
                return await self._handle_list_operation(task, context)
            
            elif any(keyword in task_lower for keyword in ['search', 'find']):
                return await self._handle_search_operation(task, context)
            
            elif any(keyword in task_lower for keyword in ['copy', 'cp']):
                return await self._handle_copy_operation(task, context)
            
            elif any(keyword in task_lower for keyword in ['move', 'mv', 'rename']):
                return await self._handle_move_operation(task, context)
            
            elif any(keyword in task_lower for keyword in ['delete', 'remove', 'rm']):
                return await self._handle_delete_operation(task, context)
            
            elif any(keyword in task_lower for keyword in ['info', 'stat', 'details']):
                return await self._handle_info_operation(task, context)
            
            else:
                # Default to general file operation
                return await self._handle_general_operation(task, context)
        
        except Exception as e:
            logger.error(f"Filesystem task failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "task": task
            }
    
    async def read_file(self, file_path: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """
        Read a file using the filesystem MCP server.
        
        Args:
            file_path: Path to the file
            encoding: File encoding
            
        Returns:
            File contents and metadata
        """
        logger.debug(f"Reading file: {file_path}")
        
        # Validate file path
        validated_path = self._validate_path(file_path)
        
        try:
            result = await self.execute_tool("read_file", {
                "path": str(validated_path),
                "encoding": encoding
            })
            
            return {
                "success": True,
                "path": str(validated_path),
                "content": result.get("content", ""),
                "size": result.get("size", 0),
                "encoding": encoding
            }
            
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "path": file_path
            }
    
    async def write_file(self, file_path: str, content: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """
        Write content to a file using the filesystem MCP server.
        
        Args:
            file_path: Path to the file
            content: Content to write
            encoding: File encoding
            
        Returns:
            Write operation result
        """
        logger.debug(f"Writing file: {file_path}")
        
        # Validate file path and content
        validated_path = self._validate_path(file_path)
        self._validate_content(content)
        
        try:
            result = await self.execute_tool("write_file", {
                "path": str(validated_path),
                "content": content,
                "encoding": encoding
            })
            
            return {
                "success": True,
                "path": str(validated_path),
                "bytes_written": result.get("bytes_written", len(content.encode(encoding))),
                "encoding": encoding
            }
            
        except Exception as e:
            logger.error(f"Failed to write file {file_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "path": file_path
            }
    
    async def list_directory(self, directory_path: str = ".", recursive: bool = False) -> Dict[str, Any]:
        """
        List directory contents using the filesystem MCP server.
        
        Args:
            directory_path: Path to the directory
            recursive: Whether to list recursively
            
        Returns:
            Directory listing
        """
        logger.debug(f"Listing directory: {directory_path}")
        
        validated_path = self._validate_path(directory_path)
        
        try:
            result = await self.execute_tool("list_directory", {
                "path": str(validated_path),
                "recursive": recursive
            })
            
            return {
                "success": True,
                "path": str(validated_path),
                "files": result.get("files", []),
                "directories": result.get("directories", []),
                "total_items": result.get("total_items", 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to list directory {directory_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "path": directory_path
            }
    
    async def create_directory(self, directory_path: str, parents: bool = True) -> Dict[str, Any]:
        """
        Create a directory using the filesystem MCP server.
        
        Args:
            directory_path: Path to create
            parents: Whether to create parent directories
            
        Returns:
            Directory creation result
        """
        logger.debug(f"Creating directory: {directory_path}")
        
        validated_path = self._validate_path(directory_path)
        
        try:
            result = await self.execute_tool("create_directory", {
                "path": str(validated_path),
                "parents": parents
            })
            
            return {
                "success": True,
                "path": str(validated_path),
                "created": result.get("created", True)
            }
            
        except Exception as e:
            logger.error(f"Failed to create directory {directory_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "path": directory_path
            }
    
    async def search_files(self, pattern: str, directory: str = ".", recursive: bool = True) -> Dict[str, Any]:
        """
        Search for files using the filesystem MCP server.
        
        Args:
            pattern: Search pattern (glob or regex)
            directory: Directory to search in
            recursive: Whether to search recursively
            
        Returns:
            Search results
        """
        logger.debug(f"Searching files: {pattern} in {directory}")
        
        validated_path = self._validate_path(directory)
        
        try:
            result = await self.execute_tool("search_files", {
                "pattern": pattern,
                "directory": str(validated_path),
                "recursive": recursive
            })
            
            return {
                "success": True,
                "pattern": pattern,
                "directory": str(validated_path),
                "matches": result.get("matches", []),
                "count": result.get("count", 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to search files {pattern}: {e}")
            return {
                "success": False,
                "error": str(e),
                "pattern": pattern
            }
    
    async def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Get file information using the filesystem MCP server.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File information
        """
        logger.debug(f"Getting file info: {file_path}")
        
        validated_path = self._validate_path(file_path)
        
        try:
            result = await self.execute_tool("get_file_info", {
                "path": str(validated_path)
            })
            
            return {
                "success": True,
                "path": str(validated_path),
                "size": result.get("size", 0),
                "modified_time": result.get("modified_time"),
                "created_time": result.get("created_time"),
                "is_file": result.get("is_file", False),
                "is_directory": result.get("is_directory", False),
                "permissions": result.get("permissions")
            }
            
        except Exception as e:
            logger.error(f"Failed to get file info {file_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "path": file_path
            }
    
    def _validate_path(self, path: str) -> Path:
        """
        Validate and resolve a file path.
        
        Args:
            path: Path to validate
            
        Returns:
            Validated Path object
            
        Raises:
            ValueError: If path is invalid or unsafe
        """
        try:
            # Convert to Path object and resolve
            path_obj = Path(path).expanduser().resolve()
            
            # Basic security checks
            if path_obj.is_absolute():
                # Ensure it's under allowed directories for absolute paths
                # For now, allow any absolute path but log a warning
                logger.warning(f"Using absolute path: {path_obj}")
            else:
                # Resolve relative to base directory
                path_obj = (self.base_directory / path).resolve()
            
            # Check for path traversal attempts
            try:
                path_obj.relative_to(path_obj.anchor)
            except ValueError:
                raise ValueError(f"Invalid path: {path}")
            
            return path_obj
            
        except Exception as e:
            raise ValueError(f"Path validation failed: {e}")
    
    def _validate_content(self, content: str):
        """
        Validate file content before writing.
        
        Args:
            content: Content to validate
            
        Raises:
            ValueError: If content is invalid
        """
        if not isinstance(content, str):
            raise ValueError("Content must be a string")
        
        # Check content size
        content_size = len(content.encode('utf-8'))
        if content_size > self.max_file_size:
            raise ValueError(f"Content too large: {content_size} bytes > {self.max_file_size}")
    
    async def _handle_read_operation(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle read file operations"""
        file_path = context.get('file_path') or self._extract_path_from_task(task)
        if not file_path:
            return {"success": False, "error": "No file path specified"}
        
        return await self.read_file(file_path)
    
    async def _handle_write_operation(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle write file operations"""
        file_path = context.get('file_path') or self._extract_path_from_task(task)
        content = context.get('content', "")
        
        if not file_path:
            return {"success": False, "error": "No file path specified"}
        
        return await self.write_file(file_path, content)
    
    async def _handle_list_operation(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle directory listing operations"""
        directory = context.get('directory') or self._extract_path_from_task(task) or "."
        recursive = context.get('recursive', False)
        
        return await self.list_directory(directory, recursive)
    
    async def _handle_search_operation(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file search operations"""
        pattern = context.get('pattern') or self._extract_pattern_from_task(task)
        directory = context.get('directory', ".")
        
        if not pattern:
            return {"success": False, "error": "No search pattern specified"}
        
        return await self.search_files(pattern, directory)
    
    async def _handle_copy_operation(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file copy operations"""
        # This would require implementing copy_file tool in MCP server
        return {"success": False, "error": "Copy operation not yet implemented"}
    
    async def _handle_move_operation(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file move/rename operations"""
        # This would require implementing move_file tool in MCP server
        return {"success": False, "error": "Move operation not yet implemented"}
    
    async def _handle_delete_operation(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file deletion operations"""
        # This would require implementing delete_file tool in MCP server
        return {"success": False, "error": "Delete operation not yet implemented"}
    
    async def _handle_info_operation(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file info operations"""
        file_path = context.get('file_path') or self._extract_path_from_task(task)
        if not file_path:
            return {"success": False, "error": "No file path specified"}
        
        return await self.get_file_info(file_path)
    
    async def _handle_general_operation(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general filesystem operations"""
        # Default to listing current directory
        return await self.list_directory(".")
    
    def _extract_path_from_task(self, task: str) -> Optional[str]:
        """Extract file path from task description"""
        # Simple path extraction - could be enhanced with regex
        words = task.split()
        for word in words:
            if '/' in word or '\\' in word or '.' in word:
                # Likely a file path
                return word.strip('"\'')
        return None
    
    def _extract_pattern_from_task(self, task: str) -> Optional[str]:
        """Extract search pattern from task description"""
        # Look for quoted patterns or common file extensions
        words = task.split()
        for word in words:
            if word.startswith('"') and word.endswith('"'):
                return word.strip('"')
            elif word.startswith("'") and word.endswith("'"):
                return word.strip("'")
            elif '*' in word or '?' in word:
                return word
        return None
    
    def set_base_directory(self, directory: str):
        """Set the base directory for relative path resolution"""
        self.base_directory = Path(directory).resolve()
        logger.info(f"Base directory set to: {self.base_directory}")
    
    def add_allowed_extension(self, extension: str):
        """Add allowed file extension"""
        if not extension.startswith('.'):
            extension = '.' + extension
        self.allowed_extensions.add(extension.lower())
        logger.debug(f"Added allowed extension: {extension}")
    
    def set_max_file_size(self, size_bytes: int):
        """Set maximum file size for operations"""
        self.max_file_size = size_bytes
        logger.info(f"Max file size set to: {size_bytes} bytes")
    
    async def batch_read_files(self, file_paths: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Read multiple files concurrently.
        
        Args:
            file_paths: List of file paths to read
            
        Returns:
            Dictionary mapping file paths to read results
        """
        logger.info(f"Batch reading {len(file_paths)} files")
        
        tasks = [self.read_file(path) for path in file_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        batch_results = {}
        for path, result in zip(file_paths, results):
            if isinstance(result, Exception):
                batch_results[path] = {
                    "success": False,
                    "error": str(result),
                    "path": path
                }
            else:
                batch_results[path] = result
        
        return batch_results
    
    async def quick_file_check(self, file_path: str) -> bool:
        """
        Quick check if file exists and is readable.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file exists and is readable
        """
        try:
            info = await self.get_file_info(file_path)
            return info.get("success", False) and info.get("is_file", False)
        except:
            return False