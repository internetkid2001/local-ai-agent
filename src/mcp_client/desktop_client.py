"""
Desktop MCP Client

Client adapter for the desktop automation MCP server.

Author: Claude Code
Date: 2025-07-13
Phase: 2.1
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from .base_client import BaseMCPClient, MCPClientConfig, MCPServerConfig
from ..utils.logger import get_logger

logger = get_logger(__name__)


class DesktopMCPClient(BaseMCPClient):
    """
    Desktop automation MCP client.
    
    Features:
    - Window management operations
    - UI interaction and automation
    - Screenshot capture and analysis
    - Keyboard and mouse input simulation
    - Clipboard operations
    """
    
    def __init__(self, config: MCPClientConfig = None):
        """
        Initialize desktop MCP client.
        
        Args:
            config: Client configuration, creates default if None
        """
        if config is None:
            config = self._create_default_config()
        
        super().__init__(config)
        logger.info("Desktop MCP client initialized")
    
    @classmethod
    def _create_default_config(cls) -> MCPClientConfig:
        """Create default configuration for desktop automation"""
        desktop_server = MCPServerConfig(
            name="desktop",
            url="ws://localhost:8766",
            enabled=True,
            tools=[
                "list_windows", "focus_window", "move_window", "resize_window",
                "click_coordinates", "type_text", "press_key", "take_screenshot",
                "get_clipboard", "set_clipboard"
            ]
        )
        
        return MCPClientConfig(
            servers=[desktop_server],
            connection_timeout=5.0,
            default_timeout=30.0,
            max_concurrent_connections=3
        )
    
    async def process_task(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process desktop automation tasks.
        
        Args:
            task: Task description
            context: Task context
            
        Returns:
            Task result
        """
        logger.info(f"Processing desktop task: {task}")
        
        task_lower = task.lower()
        
        try:
            # Route to appropriate desktop operation
            if any(keyword in task_lower for keyword in ['window', 'focus', 'switch']):
                return await self._handle_window_operation(task, context)
            
            elif any(keyword in task_lower for keyword in ['click', 'mouse']):
                return await self._handle_mouse_operation(task, context)
            
            elif any(keyword in task_lower for keyword in ['type', 'keyboard', 'key']):
                return await self._handle_keyboard_operation(task, context)
            
            elif any(keyword in task_lower for keyword in ['screenshot', 'capture', 'screen']):
                return await self._handle_screenshot_operation(task, context)
            
            elif any(keyword in task_lower for keyword in ['clipboard', 'copy', 'paste']):
                return await self._handle_clipboard_operation(task, context)
            
            else:
                # Default to general desktop operation
                return await self._handle_general_operation(task, context)
        
        except Exception as e:
            logger.error(f"Desktop task failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "task": task
            }
    
    async def _handle_window_operation(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle window management operations"""
        task_lower = task.lower()
        
        if 'list' in task_lower:
            return await self.execute_tool("list_windows", {
                "include_minimized": context.get("include_minimized", False)
            })
        
        elif 'focus' in task_lower or 'switch' in task_lower:
            window_title = context.get("window_title")
            process_name = context.get("process_name")
            
            if not window_title and not process_name:
                # Try to extract from task description
                words = task.split()
                for i, word in enumerate(words):
                    if word.lower() in ['focus', 'switch'] and i + 1 < len(words):
                        window_title = words[i + 1]
                        break
            
            return await self.execute_tool("focus_window", {
                "title": window_title,
                "process": process_name
            })
        
        elif 'move' in task_lower:
            return await self.execute_tool("move_window", {
                "window_id": context.get("window_id"),
                "x": context.get("x", 100),
                "y": context.get("y", 100)
            })
        
        elif 'resize' in task_lower:
            return await self.execute_tool("resize_window", {
                "window_id": context.get("window_id"),
                "width": context.get("width", 800),
                "height": context.get("height", 600)
            })
        
        else:
            return await self.execute_tool("list_windows", {})
    
    async def _handle_mouse_operation(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle mouse operations"""
        x = context.get("x")
        y = context.get("y")
        button = context.get("button", "left")
        
        if x is None or y is None:
            return {
                "success": False,
                "error": "Mouse coordinates (x, y) required for click operation"
            }
        
        return await self.execute_tool("click_coordinates", {
            "x": x,
            "y": y,
            "button": button
        })
    
    async def _handle_keyboard_operation(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle keyboard operations"""
        task_lower = task.lower()
        
        if 'type' in task_lower:
            text = context.get("text")
            if not text:
                # Try to extract text from task description
                words = task.split()
                for i, word in enumerate(words):
                    if word.lower() == 'type' and i + 1 < len(words):
                        text = " ".join(words[i + 1:])
                        break
            
            if not text:
                return {
                    "success": False,
                    "error": "Text to type is required"
                }
            
            return await self.execute_tool("type_text", {
                "text": text,
                "delay": context.get("delay", 0.05)
            })
        
        elif 'press' in task_lower or 'key' in task_lower:
            key = context.get("key")
            modifiers = context.get("modifiers", [])
            
            if not key:
                # Try to extract key from task description
                words = task.split()
                for i, word in enumerate(words):
                    if word.lower() in ['press', 'key'] and i + 1 < len(words):
                        key = words[i + 1]
                        break
            
            if not key:
                return {
                    "success": False,
                    "error": "Key to press is required"
                }
            
            return await self.execute_tool("press_key", {
                "key": key,
                "modifiers": modifiers
            })
        
        else:
            return {
                "success": False,
                "error": "Unknown keyboard operation"
            }
    
    async def _handle_screenshot_operation(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle screenshot operations"""
        return await self.execute_tool("take_screenshot", {
            "window_id": context.get("window_id"),
            "filename": context.get("filename"),
            "region": context.get("region")
        })
    
    async def _handle_clipboard_operation(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle clipboard operations"""
        task_lower = task.lower()
        
        if any(keyword in task_lower for keyword in ['get', 'read', 'paste']):
            return await self.execute_tool("get_clipboard", {})
        
        elif any(keyword in task_lower for keyword in ['set', 'copy']):
            content = context.get("content")
            if not content:
                return {
                    "success": False,
                    "error": "Content to set in clipboard is required"
                }
            
            return await self.execute_tool("set_clipboard", {
                "content": content,
                "content_type": context.get("content_type", "text")
            })
        
        else:
            # Default to getting clipboard
            return await self.execute_tool("get_clipboard", {})
    
    async def _handle_general_operation(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general desktop operations"""
        # Default to taking a screenshot for general desktop tasks
        return await self.execute_tool("take_screenshot", {})
    
    # Convenience methods for common operations
    async def list_windows(self, include_minimized: bool = False) -> Dict[str, Any]:
        """List all open windows"""
        return await self.execute_tool("list_windows", {
            "include_minimized": include_minimized
        })
    
    async def focus_window(self, title: Optional[str] = None, 
                          process: Optional[str] = None) -> Dict[str, Any]:
        """Focus a window by title or process"""
        return await self.execute_tool("focus_window", {
            "title": title,
            "process": process
        })
    
    async def click_at(self, x: int, y: int, button: str = "left") -> Dict[str, Any]:
        """Click at specific coordinates"""
        return await self.execute_tool("click_coordinates", {
            "x": x,
            "y": y,
            "button": button
        })
    
    async def type_text(self, text: str, delay: float = 0.05) -> Dict[str, Any]:
        """Type text"""
        return await self.execute_tool("type_text", {
            "text": text,
            "delay": delay
        })
    
    async def press_key(self, key: str, modifiers: List[str] = None) -> Dict[str, Any]:
        """Press a key or key combination"""
        return await self.execute_tool("press_key", {
            "key": key,
            "modifiers": modifiers or []
        })
    
    async def take_screenshot(self, filename: Optional[str] = None,
                            region: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
        """Take a screenshot"""
        return await self.execute_tool("take_screenshot", {
            "filename": filename,
            "region": region
        })
    
    async def get_clipboard(self) -> Dict[str, Any]:
        """Get clipboard contents"""
        return await self.execute_tool("get_clipboard", {})
    
    async def set_clipboard(self, content: str, content_type: str = "text") -> Dict[str, Any]:
        """Set clipboard contents"""
        return await self.execute_tool("set_clipboard", {
            "content": content,
            "content_type": content_type
        })