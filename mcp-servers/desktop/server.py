#!/usr/bin/env python3
"""
Desktop Automation MCP Server

Provides desktop automation capabilities including window management,
UI interaction, input simulation, and screenshot capture.

Author: Claude Code
Date: 2025-07-13
Phase: 2.1
"""

import asyncio
import logging
import sys
import json
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
except ImportError:
    print("websockets library required. Install with: pip install websockets")
    sys.exit(1)

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.mcp_client.connection import MCPConnection, MCPMessage
from src.security import get_permission_manager, OperationType
from window_manager import WindowManager
from ui_automation import UIAutomation
from keyboard_mouse import KeyboardMouse
from clipboard import ClipboardManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('desktop_mcp.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class DesktopMCPServer:
    """
    Desktop automation MCP server providing comprehensive desktop interaction capabilities.
    
    Features:
    - Window management and control
    - UI element interaction
    - Keyboard and mouse simulation
    - Clipboard operations
    - Screenshot capture
    - Cross-platform support (Linux, macOS, Windows)
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize desktop MCP server.
        
        Args:
            config_path: Path to configuration file
        """
        self.config = self._load_config(config_path)
        
        # Initialize security
        self.permission_manager = get_permission_manager()
        
        # Initialize automation components
        self.window_manager = WindowManager()
        self.ui_automation = UIAutomation()
        self.keyboard_mouse = KeyboardMouse()
        self.clipboard = ClipboardManager()
        
        # Server state
        self.connections: Dict[str, MCPConnection] = {}
        self.running = False
        
        # Tool registry
        self.tools = {
            # Window management
            "list_windows": self._list_windows,
            "focus_window": self._focus_window,
            "move_window": self._move_window,
            "resize_window": self._resize_window,
            "close_window": self._close_window,
            "minimize_window": self._minimize_window,
            "maximize_window": self._maximize_window,
            
            # UI interaction
            "click_element": self._click_element,
            "click_coordinates": self._click_coordinates,
            "double_click": self._double_click,
            "right_click": self._right_click,
            "hover_element": self._hover_element,
            "scroll": self._scroll,
            
            # Keyboard input
            "type_text": self._type_text,
            "press_key": self._press_key,
            "key_combination": self._key_combination,
            
            # Mouse operations
            "move_mouse": self._move_mouse,
            "drag_drop": self._drag_drop,
            
            # Clipboard operations
            "get_clipboard": self._get_clipboard,
            "set_clipboard": self._set_clipboard,
            "clipboard_history": self._clipboard_history,
            
            # Screenshot and visual
            "take_screenshot": self._take_screenshot,
            "find_element": self._find_element,
            "wait_for_element": self._wait_for_element,
            
            # Visual automation
            "analyze_screen": self._analyze_screen,
            "find_element_by_text": self._find_element_by_text,
            "generate_automation_script": self._generate_automation_script,
            "click_visual_element": self._click_element,
            
            # System info
            "get_desktop_info": self._get_desktop_info,
            "get_mouse_position": self._get_mouse_position
        }
        
        logger.info("Desktop MCP server initialized")
    
    def _check_permission(self, operation: OperationType, context: Dict[str, Any] = None) -> bool:
        """Check if operation is permitted by security manager"""
        try:
            return self.permission_manager.check_permission(operation, context or {})
        except Exception as e:
            logger.error(f"Permission check failed: {e}")
            return False
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load server configuration"""
        default_config = {
            "server": {
                "host": "localhost",
                "port": 8766,
                "name": "desktop-automation"
            },
            "security": {
                "require_confirmation": True,
                "allowed_applications": [],
                "blocked_applications": ["sudo", "rm", "del"],
                "max_screenshot_size": "1920x1080"
            },
            "automation": {
                "click_delay": 0.1,
                "type_delay": 0.05,
                "screenshot_quality": 80,
                "element_timeout": 10.0
            }
        }
        
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    # Merge with defaults
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                        elif isinstance(value, dict):
                            for subkey, subvalue in value.items():
                                if subkey not in config[key]:
                                    config[key][subkey] = subvalue
                    return config
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
        
        return default_config
    
    async def start_server(self):
        """Start the WebSocket MCP server"""
        self.running = True
        host = self.config["server"]["host"]
        port = self.config["server"]["port"]
        
        logger.info(f"Starting desktop MCP server on {host}:{port}")
        
        try:
            server = await websockets.serve(
                self._handle_websocket_client,
                host,
                port
            )
            
            logger.info(f"Desktop MCP server running on {host}:{port}")
            
            await server.wait_closed()
                
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            raise
    
    async def _handle_websocket_client(self, websocket: WebSocketServerProtocol):
        """Handle WebSocket client connections"""
        client_addr = websocket.remote_address
        client_id = f"{client_addr[0]}:{client_addr[1]}"
        
        logger.info(f"Client connected: {client_id}")
        
        try:
            async for message_data in websocket:
                try:
                    if isinstance(message_data, str):
                        message = json.loads(message_data)
                    else:
                        message = json.loads(message_data.decode())
                    
                    response = await self._process_message(message)
                    await websocket.send(json.dumps(response))
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Error processing message: {e}")
                    error_response = {
                        "error": {"code": -32700, "message": "Parse error"}
                    }
                    await websocket.send(json.dumps(error_response))
                except Exception as e:
                    logger.error(f"Client handler error: {e}")
                    error_response = {
                        "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
                    }
                    await websocket.send(json.dumps(error_response))
                
        except Exception as e:
            logger.error(f"WebSocket handler error: {e}")
        finally:
            logger.info(f"Client disconnected: {client_id}")
    
    async def _process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming MCP message"""
        method = message.get("method")
        params = message.get("params", {})
        message_id = message.get("id")
        
        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": message_id,
                "result": {
                    "tools": self._get_tool_schemas()
                }
            }
        
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if tool_name in self.tools:
                try:
                    result = await self.tools[tool_name](arguments)
                    return {
                        "jsonrpc": "2.0",
                        "id": message_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps(result, indent=2)
                                }
                            ]
                        }
                    }
                except Exception as e:
                    logger.error(f"Tool execution error: {e}")
                    return {
                        "jsonrpc": "2.0",
                        "id": message_id,
                        "error": {
                            "code": -32603,
                            "message": f"Tool execution failed: {str(e)}"
                        }
                    }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "error": {
                        "code": -32601,
                        "message": f"Tool not found: {tool_name}"
                    }
                }
        
        else:
            return {
                "jsonrpc": "2.0",
                "id": message_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
    
    def _get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get tool schemas for all available tools"""
        return [
            {
                "name": "list_windows",
                "description": "List all open windows on the desktop",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "include_minimized": {"type": "boolean", "default": False}
                    }
                }
            },
            {
                "name": "focus_window",
                "description": "Focus a specific window by title or process name",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Window title (partial match)"},
                        "process": {"type": "string", "description": "Process name"}
                    }
                }
            },
            {
                "name": "move_window",
                "description": "Move a window to specified coordinates",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "window_id": {"type": "string"},
                        "x": {"type": "integer"},
                        "y": {"type": "integer"}
                    },
                    "required": ["window_id", "x", "y"]
                }
            },
            {
                "name": "click_coordinates",
                "description": "Click at specific screen coordinates",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer"},
                        "y": {"type": "integer"},
                        "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"}
                    },
                    "required": ["x", "y"]
                }
            },
            {
                "name": "type_text",
                "description": "Type text at the current cursor position",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "delay": {"type": "number", "default": 0.05}
                    },
                    "required": ["text"]
                }
            },
            {
                "name": "press_key",
                "description": "Press a specific key or key combination",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "Key to press (e.g., 'enter', 'ctrl+c')"},
                        "modifiers": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["key"]
                }
            },
            {
                "name": "take_screenshot",
                "description": "Take a screenshot of the desktop or specific window",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "window_id": {"type": "string", "description": "Optional window ID to capture"},
                        "filename": {"type": "string", "description": "Optional filename to save to"},
                        "region": {
                            "type": "object",
                            "properties": {
                                "x": {"type": "integer"},
                                "y": {"type": "integer"},
                                "width": {"type": "integer"},
                                "height": {"type": "integer"}
                            }
                        }
                    }
                }
            },
            {
                "name": "get_clipboard",
                "description": "Get current clipboard contents",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "set_clipboard",
                "description": "Set clipboard contents",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string"},
                        "content_type": {"type": "string", "enum": ["text", "image"], "default": "text"}
                    },
                    "required": ["content"]
                }
            },
            {
                "name": "analyze_screen",
                "description": "Analyze screenshot for UI elements using visual automation",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "screenshot_path": {"type": "string", "description": "Path to screenshot file"},
                        "create_annotated": {"type": "boolean", "default": True, "description": "Create annotated screenshot"}
                    },
                    "required": ["screenshot_path"]
                }
            },
            {
                "name": "find_element_by_text",
                "description": "Find UI element by text content",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Text to search for"},
                        "screenshot_path": {"type": "string", "description": "Path to screenshot file"}
                    },
                    "required": ["text", "screenshot_path"]
                }
            },
            {
                "name": "generate_automation_script",
                "description": "Generate automation script based on screen analysis",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "screenshot_path": {"type": "string", "description": "Path to screenshot file"},
                        "task_description": {"type": "string", "description": "Description of automation task"}
                    },
                    "required": ["screenshot_path", "task_description"]
                }
            },
            {
                "name": "click_visual_element",
                "description": "Click on UI element found by visual automation",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "element_text": {"type": "string", "description": "Text of element to click"},
                        "screenshot_path": {"type": "string", "description": "Path to screenshot file"},
                        "click_type": {"type": "string", "enum": ["left", "right", "double"], "default": "left"}
                    },
                    "required": ["element_text", "screenshot_path"]
                }
            }
        ]
    
    # Tool implementations
    async def _list_windows(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List all open windows"""
        include_minimized = args.get("include_minimized", False)
        return await self.window_manager.list_windows(include_minimized)
    
    async def _focus_window(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Focus a specific window"""
        title = args.get("title")
        process = args.get("process")
        return await self.window_manager.focus_window(title, process)
    
    async def _move_window(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Move a window to specified coordinates"""
        window_id = args["window_id"]
        x = args["x"]
        y = args["y"]
        return await self.window_manager.move_window(window_id, x, y)
    
    async def _resize_window(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Resize a window"""
        window_id = args["window_id"]
        width = args["width"]
        height = args["height"]
        return await self.window_manager.resize_window(window_id, width, height)
    
    async def _close_window(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Close a window"""
        window_id = args["window_id"]
        return await self.window_manager.close_window(window_id)
    
    async def _minimize_window(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Minimize a window"""
        window_id = args["window_id"]
        return await self.window_manager.minimize_window(window_id)
    
    async def _maximize_window(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Maximize a window"""
        window_id = args["window_id"]
        return await self.window_manager.maximize_window(window_id)
    
    async def _click_element(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Click a UI element"""
        return await self.ui_automation.click_element(args)
    
    async def _click_coordinates(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Click at specific coordinates"""
        if not self._check_permission(OperationType.DESKTOP_INTERACT, {"action": "click"}):
            return {
                "success": False,
                "error": "Permission denied: desktop interaction not allowed"
            }
        x = args["x"]
        y = args["y"]
        button = args.get("button", "left")
        return await self.keyboard_mouse.click_coordinates(x, y, button)
    
    async def _double_click(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Double click"""
        x = args.get("x")
        y = args.get("y")
        return await self.keyboard_mouse.double_click(x, y)
    
    async def _right_click(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Right click"""
        x = args.get("x")
        y = args.get("y")
        return await self.keyboard_mouse.right_click(x, y)
    
    async def _hover_element(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Hover over an element"""
        return await self.ui_automation.hover_element(args)
    
    async def _scroll(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Scroll the page or element"""
        return await self.keyboard_mouse.scroll(args)
    
    async def _type_text(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Type text"""
        if not self._check_permission(OperationType.DESKTOP_INTERACT, {"action": "type"}):
            return {
                "success": False,
                "error": "Permission denied: desktop interaction not allowed"
            }
        text = args["text"]
        delay = args.get("delay", self.config["automation"]["type_delay"])
        return await self.keyboard_mouse.type_text(text, delay)
    
    async def _press_key(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Press a key or key combination"""
        key = args["key"]
        modifiers = args.get("modifiers", [])
        return await self.keyboard_mouse.press_key(key, modifiers)
    
    async def _key_combination(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Press a key combination"""
        combination = args["combination"]
        return await self.keyboard_mouse.key_combination(combination)
    
    async def _move_mouse(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Move mouse to coordinates"""
        x = args["x"]
        y = args["y"]
        return await self.keyboard_mouse.move_mouse(x, y)
    
    async def _drag_drop(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Drag and drop operation"""
        return await self.keyboard_mouse.drag_drop(args)
    
    async def _get_clipboard(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get clipboard contents"""
        if not self._check_permission(OperationType.CLIPBOARD_ACCESS):
            return {
                "success": False,
                "error": "Permission denied: clipboard access not allowed"
            }
        return await self.clipboard.get_clipboard()
    
    async def _set_clipboard(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Set clipboard contents"""
        if not self._check_permission(OperationType.CLIPBOARD_ACCESS):
            return {
                "success": False,
                "error": "Permission denied: clipboard access not allowed"
            }
        content = args["content"]
        content_type = args.get("content_type", "text")
        return await self.clipboard.set_clipboard(content, content_type)
    
    async def _clipboard_history(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get clipboard history"""
        return await self.clipboard.get_history()
    
    async def _analyze_screen(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze screenshot for UI elements using visual automation"""
        try:
            # Import visual automation engine
            import sys
            from pathlib import Path
            sys.path.append(str(Path(__file__).parent.parent.parent))
            from src.agent.automation.visual_automation import visual_automation_engine
            
            screenshot_path = args["screenshot_path"]
            create_annotated = args.get("create_annotated", True)
            
            # Analyze the screen
            analysis = await visual_automation_engine.analyze_screen(screenshot_path)
            
            # Create annotated screenshot if requested
            annotated_path = None
            if create_annotated:
                annotated_path = screenshot_path.replace(".png", "_annotated.png")
                await visual_automation_engine.create_annotated_screenshot(analysis, annotated_path)
            
            return {
                "success": True,
                "analysis": {
                    "timestamp": analysis.timestamp,
                    "resolution": analysis.resolution,
                    "elements_found": len(analysis.elements),
                    "elements": [
                        {
                            "x": elem.x,
                            "y": elem.y,
                            "width": elem.width,
                            "height": elem.height,
                            "confidence": elem.confidence,
                            "label": elem.label,
                            "type": elem.element_type,
                            "text": elem.text,
                            "center": elem.center
                        }
                        for elem in analysis.elements
                    ],
                    "metadata": analysis.analysis_metadata
                },
                "annotated_screenshot": annotated_path
            }
            
        except Exception as e:
            logger.error(f"Screen analysis failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _find_element_by_text(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Find UI element by text content"""
        try:
            # Import visual automation engine
            import sys
            from pathlib import Path
            sys.path.append(str(Path(__file__).parent.parent.parent))
            from src.agent.automation.visual_automation import visual_automation_engine
            
            text = args["text"]
            screenshot_path = args["screenshot_path"]
            
            # Find element
            element = await visual_automation_engine.find_element_by_text(text, screenshot_path)
            
            if element:
                return {
                    "success": True,
                    "element": {
                        "x": element.x,
                        "y": element.y,
                        "width": element.width,
                        "height": element.height,
                        "confidence": element.confidence,
                        "label": element.label,
                        "type": element.element_type,
                        "text": element.text,
                        "center": element.center
                    }
                }
            else:
                return {
                    "success": False,
                    "error": f"Element with text '{text}' not found"
                }
                
        except Exception as e:
            logger.error(f"Find element by text failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _generate_automation_script(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Generate automation script based on screen analysis"""
        try:
            # Import visual automation engine
            import sys
            from pathlib import Path
            sys.path.append(str(Path(__file__).parent.parent.parent))
            from src.agent.automation.visual_automation import visual_automation_engine
            
            screenshot_path = args["screenshot_path"]
            task_description = args["task_description"]
            
            # Analyze screen first
            analysis = await visual_automation_engine.analyze_screen(screenshot_path)
            
            # Generate script
            script = await visual_automation_engine.generate_automation_script(analysis, task_description)
            
            return {
                "success": True,
                "script": script,
                "analysis_summary": {
                    "elements_found": len(analysis.elements),
                    "resolution": analysis.resolution,
                    "timestamp": analysis.timestamp
                }
            }
            
        except Exception as e:
            logger.error(f"Generate automation script failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _click_element(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Click on UI element found by visual automation"""
        try:
            # Import visual automation engine
            import sys
            from pathlib import Path
            sys.path.append(str(Path(__file__).parent.parent.parent))
            from src.agent.automation.visual_automation import visual_automation_engine
            
            element_text = args["element_text"]
            screenshot_path = args["screenshot_path"]
            click_type = args.get("click_type", "left")
            
            # Find element by text
            element = await visual_automation_engine.find_element_by_text(element_text, screenshot_path)
            
            if not element:
                return {
                    "success": False,
                    "error": f"Element with text '{element_text}' not found"
                }
            
            # Click the element
            x, y = element.center
            if click_type == "left":
                result = await self.keyboard_mouse.click_coordinates(x, y)
            elif click_type == "right":
                result = await self.keyboard_mouse.click_coordinates(x, y, button="right")
            elif click_type == "double":
                result = await self.keyboard_mouse.click_coordinates(x, y)
                # Double click - wait a bit then click again
                await asyncio.sleep(0.1)
                result = await self.keyboard_mouse.click_coordinates(x, y)
            
            return {
                "success": True,
                "element": {
                    "text": element_text,
                    "center": element.center,
                    "type": element.element_type
                },
                "click_type": click_type,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Click element failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _take_screenshot(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Take a screenshot"""
        if not self._check_permission(OperationType.SCREENSHOT):
            return {
                "success": False,
                "error": "Permission denied: screenshot not allowed"
            }
        return await self.ui_automation.take_screenshot(args)
    
    async def _find_element(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Find UI element"""
        return await self.ui_automation.find_element(args)
    
    async def _wait_for_element(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Wait for UI element to appear"""
        return await self.ui_automation.wait_for_element(args)
    
    async def _get_desktop_info(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get desktop information"""
        return await self.window_manager.get_desktop_info()
    
    async def _get_mouse_position(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get current mouse position"""
        return await self.keyboard_mouse.get_mouse_position()
    
    async def stop_server(self):
        """Stop the MCP server"""
        self.running = False
        logger.info("Desktop MCP server stopped")


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Desktop Automation MCP Server")
    parser.add_argument("--config", "-c", type=str, help="Configuration file path")
    parser.add_argument("--host", type=str, default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=8766, help="Server port")
    
    args = parser.parse_args()
    
    # Create server
    server = DesktopMCPServer(config_path=args.config)
    
    # Override config with command line args
    if args.host:
        server.config["server"]["host"] = args.host
    if args.port:
        server.config["server"]["port"] = args.port
    
    try:
        await server.start_server()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())