"""
Keyboard and Mouse Control for Desktop Automation

Cross-platform keyboard and mouse input simulation for the desktop MCP server.
Handles typing, key presses, mouse clicks, and movement.

Author: Claude Code
Date: 2025-07-13
Phase: 2.1
"""

import asyncio
import platform
import subprocess
import logging
from typing import Dict, List, Any, Optional, Tuple
import time

logger = logging.getLogger(__name__)


class KeyboardMouse:
    """
    Cross-platform keyboard and mouse control system.
    
    Features:
    - Text typing with configurable delays
    - Key press simulation (single keys and combinations)
    - Mouse clicking, movement, and dragging
    - Scroll wheel control
    - Current mouse position tracking
    """
    
    def __init__(self):
        """Initialize keyboard and mouse controller"""
        self.platform = platform.system().lower()
        self.tools_available = self._detect_tools()
        
        # Key mapping for cross-platform compatibility
        self.key_mapping = self._init_key_mapping()
        
        logger.info(f"Keyboard/Mouse controller initialized for {self.platform}")
        logger.debug(f"Available tools: {list(self.tools_available.keys())}")
    
    def _detect_tools(self) -> Dict[str, bool]:
        """Detect available input tools"""
        tools = {}
        
        if self.platform == "linux":
            tools["xdotool"] = self._command_available("xdotool")
            tools["xte"] = self._command_available("xte")
            tools["xinput"] = self._command_available("xinput")
            
        elif self.platform == "darwin":  # macOS
            tools["osascript"] = self._command_available("osascript")
            tools["cliclick"] = self._command_available("cliclick")
            
        elif self.platform == "windows":
            tools["powershell"] = self._command_available("powershell")
            tools["nircmd"] = self._command_available("nircmd")
        
        return tools
    
    def _command_available(self, command: str) -> bool:
        """Check if a command is available"""
        try:
            subprocess.run(
                ["which", command] if self.platform != "windows" else ["where", command],
                capture_output=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _init_key_mapping(self) -> Dict[str, str]:
        """Initialize cross-platform key mapping"""
        # Common key mappings across platforms
        mapping = {
            # Special keys
            "enter": "Return" if self.platform == "darwin" else "Return",
            "return": "Return",
            "escape": "Escape",
            "esc": "Escape",
            "tab": "Tab",
            "space": "space",
            "backspace": "BackSpace",
            "delete": "Delete",
            "home": "Home",
            "end": "End",
            "pageup": "Page_Up",
            "pagedown": "Page_Down",
            "up": "Up",
            "down": "Down",
            "left": "Left",
            "right": "Right",
            
            # Function keys
            **{f"f{i}": f"F{i}" for i in range(1, 13)},
            
            # Modifier keys
            "ctrl": "ctrl" if self.platform == "linux" else "cmd" if self.platform == "darwin" else "ctrl",
            "alt": "alt",
            "shift": "shift",
            "cmd": "cmd" if self.platform == "darwin" else "super",
            "super": "super",
            "meta": "meta"
        }
        
        return mapping
    
    async def type_text(self, text: str, delay: float = 0.05) -> Dict[str, Any]:
        """
        Type text at the current cursor position.
        
        Args:
            text: Text to type
            delay: Delay between characters in seconds
            
        Returns:
            Success/failure result
        """
        try:
            if self.platform == "linux":
                return await self._type_text_linux(text, delay)
            elif self.platform == "darwin":
                return await self._type_text_macos(text, delay)
            elif self.platform == "windows":
                return await self._type_text_windows(text, delay)
            else:
                return {"success": False, "error": f"Unsupported platform: {self.platform}"}
        
        except Exception as e:
            logger.error(f"Failed to type text: {e}")
            return {"success": False, "error": str(e)}
    
    async def _type_text_linux(self, text: str, delay: float) -> Dict[str, Any]:
        """Type text on Linux using xdotool"""
        if self.tools_available.get("xdotool"):
            try:
                # Use xdotool to type text
                delay_ms = int(delay * 1000)
                result = await asyncio.create_subprocess_exec(
                    "xdotool", "type", "--delay", str(delay_ms), text,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await result.communicate()
                
                if result.returncode == 0:
                    return {
                        "success": True,
                        "text": text,
                        "delay": delay,
                        "method": "xdotool"
                    }
                
            except Exception as e:
                logger.error(f"xdotool type failed: {e}")
        
        # Fallback to character-by-character typing
        if self.tools_available.get("xte"):
            try:
                for char in text:
                    if char == ' ':
                        await asyncio.create_subprocess_exec("xte", "key space")
                    elif char == '\n':
                        await asyncio.create_subprocess_exec("xte", "key Return")
                    else:
                        await asyncio.create_subprocess_exec("xte", f"str {char}")
                    
                    if delay > 0:
                        await asyncio.sleep(delay)
                
                return {
                    "success": True,
                    "text": text,
                    "delay": delay,
                    "method": "xte"
                }
                
            except Exception as e:
                logger.error(f"xte type failed: {e}")
        
        return {"success": False, "error": "No suitable typing tool available"}
    
    async def _type_text_macos(self, text: str, delay: float) -> Dict[str, Any]:
        """Type text on macOS using AppleScript"""
        if self.tools_available.get("osascript"):
            try:
                # Escape special characters for AppleScript
                escaped_text = text.replace('"', '\\"').replace('\\', '\\\\')
                
                script = f'''
                tell application "System Events"
                    keystroke "{escaped_text}"
                end tell
                '''
                
                result = await asyncio.create_subprocess_exec(
                    "osascript", "-e", script,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await result.communicate()
                
                if result.returncode == 0:
                    return {
                        "success": True,
                        "text": text,
                        "delay": delay,
                        "method": "osascript"
                    }
                
            except Exception as e:
                logger.error(f"AppleScript type failed: {e}")
        
        return {"success": False, "error": "AppleScript typing failed"}
    
    async def _type_text_windows(self, text: str, delay: float) -> Dict[str, Any]:
        """Type text on Windows using PowerShell"""
        if self.tools_available.get("powershell"):
            try:
                # PowerShell script to send keystrokes
                script = f'''
                Add-Type -AssemblyName System.Windows.Forms
                [System.Windows.Forms.SendKeys]::SendWait("{text}")
                '''
                
                result = await asyncio.create_subprocess_exec(
                    "powershell", "-Command", script,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await result.communicate()
                
                if result.returncode == 0:
                    return {
                        "success": True,
                        "text": text,
                        "delay": delay,
                        "method": "powershell"
                    }
                
            except Exception as e:
                logger.error(f"PowerShell type failed: {e}")
        
        return {"success": False, "error": "PowerShell typing failed"}
    
    async def press_key(self, key: str, modifiers: List[str] = None) -> Dict[str, Any]:
        """
        Press a key or key combination.
        
        Args:
            key: Key to press
            modifiers: List of modifier keys (ctrl, alt, shift, etc.)
            
        Returns:
            Success/failure result
        """
        try:
            if modifiers is None:
                modifiers = []
            
            # Map key to platform-specific format
            mapped_key = self.key_mapping.get(key.lower(), key)
            mapped_modifiers = [self.key_mapping.get(mod.lower(), mod) for mod in modifiers]
            
            if self.platform == "linux":
                return await self._press_key_linux(mapped_key, mapped_modifiers)
            elif self.platform == "darwin":
                return await self._press_key_macos(mapped_key, mapped_modifiers)
            elif self.platform == "windows":
                return await self._press_key_windows(mapped_key, mapped_modifiers)
            else:
                return {"success": False, "error": f"Unsupported platform: {self.platform}"}
        
        except Exception as e:
            logger.error(f"Failed to press key: {e}")
            return {"success": False, "error": str(e)}
    
    async def _press_key_linux(self, key: str, modifiers: List[str]) -> Dict[str, Any]:
        """Press key on Linux"""
        if self.tools_available.get("xdotool"):
            try:
                if modifiers:
                    # Build key combination
                    key_combo = "+".join(modifiers + [key])
                    result = await asyncio.create_subprocess_exec(
                        "xdotool", "key", key_combo,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                else:
                    result = await asyncio.create_subprocess_exec(
                        "xdotool", "key", key,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                
                await result.communicate()
                
                if result.returncode == 0:
                    return {
                        "success": True,
                        "key": key,
                        "modifiers": modifiers,
                        "method": "xdotool"
                    }
                
            except Exception as e:
                logger.error(f"xdotool key press failed: {e}")
        
        return {"success": False, "error": "Key press failed"}
    
    async def _press_key_macos(self, key: str, modifiers: List[str]) -> Dict[str, Any]:
        """Press key on macOS"""
        if self.tools_available.get("osascript"):
            try:
                # Build AppleScript key command
                if modifiers:
                    modifier_str = " using {" + ", ".join(f"{mod} down" for mod in modifiers) + "}"
                    script = f'tell application "System Events" to key code {key}{modifier_str}'
                else:
                    script = f'tell application "System Events" to keystroke "{key}"'
                
                result = await asyncio.create_subprocess_exec(
                    "osascript", "-e", script,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await result.communicate()
                
                if result.returncode == 0:
                    return {
                        "success": True,
                        "key": key,
                        "modifiers": modifiers,
                        "method": "osascript"
                    }
                
            except Exception as e:
                logger.error(f"AppleScript key press failed: {e}")
        
        return {"success": False, "error": "Key press failed"}
    
    async def _press_key_windows(self, key: str, modifiers: List[str]) -> Dict[str, Any]:
        """Press key on Windows"""
        # Implementation for Windows key press
        return {"success": False, "error": "Windows key press not implemented yet"}
    
    async def key_combination(self, combination: str) -> Dict[str, Any]:
        """
        Press a key combination specified as a string (e.g., 'ctrl+c').
        
        Args:
            combination: Key combination string
            
        Returns:
            Success/failure result
        """
        try:
            parts = combination.lower().split('+')
            if len(parts) == 1:
                return await self.press_key(parts[0])
            else:
                modifiers = parts[:-1]
                key = parts[-1]
                return await self.press_key(key, modifiers)
        
        except Exception as e:
            logger.error(f"Failed to execute key combination: {e}")
            return {"success": False, "error": str(e)}
    
    async def click_coordinates(self, x: int, y: int, button: str = "left") -> Dict[str, Any]:
        """
        Click at specific screen coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            button: Mouse button ("left", "right", "middle")
            
        Returns:
            Success/failure result
        """
        try:
            if self.platform == "linux":
                return await self._click_coordinates_linux(x, y, button)
            elif self.platform == "darwin":
                return await self._click_coordinates_macos(x, y, button)
            elif self.platform == "windows":
                return await self._click_coordinates_windows(x, y, button)
            else:
                return {"success": False, "error": f"Unsupported platform: {self.platform}"}
        
        except Exception as e:
            logger.error(f"Failed to click coordinates: {e}")
            return {"success": False, "error": str(e)}
    
    async def _click_coordinates_linux(self, x: int, y: int, button: str) -> Dict[str, Any]:
        """Click coordinates on Linux"""
        if self.tools_available.get("xdotool"):
            try:
                # Map button names
                button_map = {"left": "1", "middle": "2", "right": "3"}
                button_num = button_map.get(button, "1")
                
                result = await asyncio.create_subprocess_exec(
                    "xdotool", "mousemove", str(x), str(y), "click", button_num,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await result.communicate()
                
                if result.returncode == 0:
                    return {
                        "success": True,
                        "x": x,
                        "y": y,
                        "button": button,
                        "method": "xdotool"
                    }
                
            except Exception as e:
                logger.error(f"xdotool click failed: {e}")
        
        return {"success": False, "error": "Click failed"}
    
    async def _click_coordinates_macos(self, x: int, y: int, button: str) -> Dict[str, Any]:
        """Click coordinates on macOS"""
        if self.tools_available.get("cliclick"):
            try:
                # cliclick syntax: c:x,y for click
                click_type = "c" if button == "left" else "rc" if button == "right" else "c"
                
                result = await asyncio.create_subprocess_exec(
                    "cliclick", f"{click_type}:{x},{y}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await result.communicate()
                
                if result.returncode == 0:
                    return {
                        "success": True,
                        "x": x,
                        "y": y,
                        "button": button,
                        "method": "cliclick"
                    }
                
            except Exception as e:
                logger.error(f"cliclick failed: {e}")
        
        elif self.tools_available.get("osascript"):
            try:
                # Fallback to AppleScript
                script = f'''
                tell application "System Events"
                    click at {{{x}, {y}}}
                end tell
                '''
                
                result = await asyncio.create_subprocess_exec(
                    "osascript", "-e", script,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await result.communicate()
                
                if result.returncode == 0:
                    return {
                        "success": True,
                        "x": x,
                        "y": y,
                        "button": button,
                        "method": "osascript"
                    }
                
            except Exception as e:
                logger.error(f"AppleScript click failed: {e}")
        
        return {"success": False, "error": "Click failed"}
    
    async def _click_coordinates_windows(self, x: int, y: int, button: str) -> Dict[str, Any]:
        """Click coordinates on Windows"""
        # Implementation for Windows would go here
        return {"success": False, "error": "Windows click not implemented yet"}
    
    async def double_click(self, x: Optional[int] = None, y: Optional[int] = None) -> Dict[str, Any]:
        """Double click at coordinates or current position"""
        try:
            if x is not None and y is not None:
                # Move to coordinates first
                await self.move_mouse(x, y)
            
            if self.platform == "linux" and self.tools_available.get("xdotool"):
                if x is not None and y is not None:
                    result = await asyncio.create_subprocess_exec(
                        "xdotool", "mousemove", str(x), str(y), "click", "--repeat", "2", "1",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                else:
                    result = await asyncio.create_subprocess_exec(
                        "xdotool", "click", "--repeat", "2", "1",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                
                await result.communicate()
                
                if result.returncode == 0:
                    return {"success": True, "action": "double_click", "x": x, "y": y}
            
            return {"success": False, "error": "Double click not supported"}
        
        except Exception as e:
            logger.error(f"Failed to double click: {e}")
            return {"success": False, "error": str(e)}
    
    async def right_click(self, x: Optional[int] = None, y: Optional[int] = None) -> Dict[str, Any]:
        """Right click at coordinates or current position"""
        if x is not None and y is not None:
            return await self.click_coordinates(x, y, "right")
        
        try:
            if self.platform == "linux" and self.tools_available.get("xdotool"):
                result = await asyncio.create_subprocess_exec(
                    "xdotool", "click", "3",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await result.communicate()
                
                if result.returncode == 0:
                    return {"success": True, "action": "right_click"}
            
            return {"success": False, "error": "Right click not supported"}
        
        except Exception as e:
            logger.error(f"Failed to right click: {e}")
            return {"success": False, "error": str(e)}
    
    async def move_mouse(self, x: int, y: int) -> Dict[str, Any]:
        """Move mouse to coordinates"""
        try:
            if self.platform == "linux" and self.tools_available.get("xdotool"):
                result = await asyncio.create_subprocess_exec(
                    "xdotool", "mousemove", str(x), str(y),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await result.communicate()
                
                if result.returncode == 0:
                    return {"success": True, "x": x, "y": y, "action": "move"}
            
            return {"success": False, "error": "Mouse move not supported"}
        
        except Exception as e:
            logger.error(f"Failed to move mouse: {e}")
            return {"success": False, "error": str(e)}
    
    async def scroll(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Scroll wheel operation"""
        try:
            direction = args.get("direction", "down")
            clicks = args.get("clicks", 3)
            x = args.get("x")
            y = args.get("y")
            
            if self.platform == "linux" and self.tools_available.get("xdotool"):
                # Button 4 = scroll up, Button 5 = scroll down
                button = "4" if direction == "up" else "5"
                
                cmd = ["xdotool"]
                if x is not None and y is not None:
                    cmd.extend(["mousemove", str(x), str(y)])
                
                for _ in range(clicks):
                    cmd.extend(["click", button])
                
                result = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await result.communicate()
                
                if result.returncode == 0:
                    return {
                        "success": True,
                        "direction": direction,
                        "clicks": clicks,
                        "x": x,
                        "y": y
                    }
            
            return {"success": False, "error": "Scroll not supported"}
        
        except Exception as e:
            logger.error(f"Failed to scroll: {e}")
            return {"success": False, "error": str(e)}
    
    async def drag_drop(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Drag and drop operation"""
        try:
            start_x = args["start_x"]
            start_y = args["start_y"]
            end_x = args["end_x"]
            end_y = args["end_y"]
            
            if self.platform == "linux" and self.tools_available.get("xdotool"):
                result = await asyncio.create_subprocess_exec(
                    "xdotool", 
                    "mousemove", str(start_x), str(start_y),
                    "mousedown", "1",
                    "mousemove", str(end_x), str(end_y),
                    "mouseup", "1",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await result.communicate()
                
                if result.returncode == 0:
                    return {
                        "success": True,
                        "start_x": start_x,
                        "start_y": start_y,
                        "end_x": end_x,
                        "end_y": end_y
                    }
            
            return {"success": False, "error": "Drag and drop not supported"}
        
        except Exception as e:
            logger.error(f"Failed to drag and drop: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_mouse_position(self) -> Dict[str, Any]:
        """Get current mouse position"""
        try:
            if self.platform == "linux" and self.tools_available.get("xdotool"):
                result = await asyncio.create_subprocess_exec(
                    "xdotool", "getmouselocation", "--shell",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await result.communicate()
                
                if result.returncode == 0:
                    # Parse shell output
                    output = stdout.decode()
                    x, y = None, None
                    for line in output.split('\n'):
                        if line.startswith('X='):
                            x = int(line.split('=')[1])
                        elif line.startswith('Y='):
                            y = int(line.split('=')[1])
                    
                    if x is not None and y is not None:
                        return {"success": True, "x": x, "y": y}
            
            return {"success": False, "error": "Get mouse position not supported"}
        
        except Exception as e:
            logger.error(f"Failed to get mouse position: {e}")
            return {"success": False, "error": str(e)}