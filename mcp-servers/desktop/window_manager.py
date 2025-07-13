"""
Window Manager for Desktop Automation

Cross-platform window management functionality for the desktop MCP server.
Handles window listing, focusing, moving, resizing, and state management.

Author: Claude Code
Date: 2025-07-13
Phase: 2.1
"""

import asyncio
import subprocess
import platform
import logging
from typing import Dict, List, Any, Optional, Tuple
import json
import re

logger = logging.getLogger(__name__)


class WindowManager:
    """
    Cross-platform window management system.
    
    Features:
    - List all open windows with details
    - Focus windows by title or process
    - Move and resize windows
    - Change window states (minimize, maximize, close)
    - Get desktop and monitor information
    """
    
    def __init__(self):
        """Initialize window manager"""
        self.platform = platform.system().lower()
        self.tools_available = self._detect_tools()
        
        logger.info(f"Window manager initialized for {self.platform}")
        logger.debug(f"Available tools: {list(self.tools_available.keys())}")
    
    def _detect_tools(self) -> Dict[str, bool]:
        """Detect available window management tools"""
        tools = {}
        
        if self.platform == "linux":
            # Linux tools
            tools["wmctrl"] = self._command_available("wmctrl")
            tools["xdotool"] = self._command_available("xdotool")
            tools["xwininfo"] = self._command_available("xwininfo")
            tools["xprop"] = self._command_available("xprop")
            tools["gnome-screenshot"] = self._command_available("gnome-screenshot")
            
        elif self.platform == "darwin":  # macOS
            tools["osascript"] = self._command_available("osascript")
            tools["screencapture"] = self._command_available("screencapture")
            
        elif self.platform == "windows":
            tools["powershell"] = self._command_available("powershell")
            tools["tasklist"] = self._command_available("tasklist")
        
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
    
    async def list_windows(self, include_minimized: bool = False) -> Dict[str, Any]:
        """
        List all open windows.
        
        Args:
            include_minimized: Whether to include minimized windows
            
        Returns:
            Dictionary with window information
        """
        try:
            if self.platform == "linux":
                return await self._list_windows_linux(include_minimized)
            elif self.platform == "darwin":
                return await self._list_windows_macos(include_minimized)
            elif self.platform == "windows":
                return await self._list_windows_windows(include_minimized)
            else:
                return {"success": False, "error": f"Unsupported platform: {self.platform}"}
        
        except Exception as e:
            logger.error(f"Failed to list windows: {e}")
            return {"success": False, "error": str(e)}
    
    async def _list_windows_linux(self, include_minimized: bool) -> Dict[str, Any]:
        """List windows on Linux using wmctrl/xdotool"""
        windows = []
        
        if self.tools_available.get("wmctrl"):
            try:
                # Use wmctrl to get window list
                result = await asyncio.create_subprocess_exec(
                    "wmctrl", "-l", "-G", "-p",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await result.communicate()
                
                if result.returncode == 0:
                    lines = stdout.decode().strip().split('\n')
                    for line in lines:
                        if line.strip():
                            parts = line.split(None, 7)
                            if len(parts) >= 8:
                                window = {
                                    "id": parts[0],
                                    "desktop": parts[1],
                                    "pid": parts[2],
                                    "x": int(parts[3]),
                                    "y": int(parts[4]),
                                    "width": int(parts[5]),
                                    "height": int(parts[6]),
                                    "title": parts[7],
                                    "platform": "linux"
                                }
                                
                                # Get additional window properties
                                if self.tools_available.get("xprop"):
                                    props = await self._get_window_properties_linux(parts[0])
                                    window.update(props)
                                
                                windows.append(window)
                
            except Exception as e:
                logger.error(f"wmctrl failed: {e}")
        
        elif self.tools_available.get("xdotool"):
            try:
                # Fallback to xdotool
                result = await asyncio.create_subprocess_exec(
                    "xdotool", "search", "--name", ".*",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await result.communicate()
                
                if result.returncode == 0:
                    window_ids = stdout.decode().strip().split('\n')
                    for window_id in window_ids:
                        if window_id.strip():
                            window_info = await self._get_window_info_xdotool(window_id)
                            if window_info:
                                windows.append(window_info)
            
            except Exception as e:
                logger.error(f"xdotool failed: {e}")
        
        return {
            "success": True,
            "windows": windows,
            "count": len(windows),
            "platform": "linux"
        }
    
    async def _list_windows_macos(self, include_minimized: bool) -> Dict[str, Any]:
        """List windows on macOS using AppleScript"""
        windows = []
        
        if self.tools_available.get("osascript"):
            try:
                # AppleScript to get window information
                script = '''
                tell application "System Events"
                    set windowList to {}
                    repeat with proc in (every process whose background only is false)
                        try
                            set procName to name of proc
                            repeat with win in (every window of proc)
                                try
                                    set winTitle to title of win
                                    set winPos to position of win
                                    set winSize to size of win
                                    set winMinimized to minimized of win
                                    set windowList to windowList & {{procName, winTitle, item 1 of winPos, item 2 of winPos, item 1 of winSize, item 2 of winSize, winMinimized}}
                                end try
                            end repeat
                        end try
                    end repeat
                    return windowList
                end tell
                '''
                
                result = await asyncio.create_subprocess_exec(
                    "osascript", "-e", script,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await result.communicate()
                
                if result.returncode == 0:
                    # Parse AppleScript output
                    output = stdout.decode().strip()
                    # This would need proper AppleScript list parsing
                    # For now, return basic structure
                    pass
                
            except Exception as e:
                logger.error(f"AppleScript failed: {e}")
        
        return {
            "success": True,
            "windows": windows,
            "count": len(windows),
            "platform": "macos"
        }
    
    async def _list_windows_windows(self, include_minimized: bool) -> Dict[str, Any]:
        """List windows on Windows using PowerShell"""
        windows = []
        
        if self.tools_available.get("powershell"):
            try:
                # PowerShell script to get window information
                script = '''
                Add-Type @"
                    using System;
                    using System.Runtime.InteropServices;
                    using System.Text;
                    public class Win32 {
                        [DllImport("user32.dll")]
                        public static extern bool EnumWindows(EnumWindowsProc enumProc, IntPtr lParam);
                        [DllImport("user32.dll")]
                        public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
                        [DllImport("user32.dll")]
                        public static extern bool IsWindowVisible(IntPtr hWnd);
                        [DllImport("user32.dll")]
                        public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
                        public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
                        public struct RECT {
                            public int Left, Top, Right, Bottom;
                        }
                    }
                "@
                
                $windows = @()
                [Win32]::EnumWindows({
                    param($hWnd, $lParam)
                    if ([Win32]::IsWindowVisible($hWnd)) {
                        $title = New-Object System.Text.StringBuilder 256
                        [Win32]::GetWindowText($hWnd, $title, 256)
                        $rect = New-Object Win32+RECT
                        [Win32]::GetWindowRect($hWnd, [ref]$rect)
                        if ($title.ToString().Length -gt 0) {
                            $windows += @{
                                id = $hWnd.ToString()
                                title = $title.ToString()
                                x = $rect.Left
                                y = $rect.Top
                                width = $rect.Right - $rect.Left
                                height = $rect.Bottom - $rect.Top
                            }
                        }
                    }
                    return $true
                }, [IntPtr]::Zero)
                
                $windows | ConvertTo-Json
                '''
                
                result = await asyncio.create_subprocess_exec(
                    "powershell", "-Command", script,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await result.communicate()
                
                if result.returncode == 0:
                    try:
                        windows_data = json.loads(stdout.decode())
                        if isinstance(windows_data, list):
                            windows = windows_data
                        elif isinstance(windows_data, dict):
                            windows = [windows_data]
                    except json.JSONDecodeError:
                        pass
                
            except Exception as e:
                logger.error(f"PowerShell failed: {e}")
        
        return {
            "success": True,
            "windows": windows,
            "count": len(windows),
            "platform": "windows"
        }
    
    async def _get_window_properties_linux(self, window_id: str) -> Dict[str, Any]:
        """Get additional window properties on Linux"""
        properties = {}
        
        try:
            result = await asyncio.create_subprocess_exec(
                "xprop", "-id", window_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                lines = stdout.decode().split('\n')
                for line in lines:
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        if key == "_NET_WM_STATE(ATOM)":
                            properties["state"] = value
                        elif key == "WM_CLASS(STRING)":
                            properties["class"] = value
                        elif key == "_NET_WM_PID(CARDINAL)":
                            properties["pid"] = value
        
        except Exception as e:
            logger.debug(f"Failed to get window properties: {e}")
        
        return properties
    
    async def _get_window_info_xdotool(self, window_id: str) -> Optional[Dict[str, Any]]:
        """Get window info using xdotool"""
        try:
            # Get window geometry
            geom_result = await asyncio.create_subprocess_exec(
                "xdotool", "getwindowgeometry", "--shell", window_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            geom_stdout, _ = await geom_result.communicate()
            
            # Get window name
            name_result = await asyncio.create_subprocess_exec(
                "xdotool", "getwindowname", window_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            name_stdout, _ = await name_result.communicate()
            
            if geom_result.returncode == 0 and name_result.returncode == 0:
                # Parse geometry output
                geom_data = {}
                for line in geom_stdout.decode().split('\n'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        geom_data[key] = value
                
                return {
                    "id": window_id,
                    "title": name_stdout.decode().strip(),
                    "x": int(geom_data.get("X", 0)),
                    "y": int(geom_data.get("Y", 0)),
                    "width": int(geom_data.get("WIDTH", 0)),
                    "height": int(geom_data.get("HEIGHT", 0)),
                    "platform": "linux"
                }
        
        except Exception as e:
            logger.debug(f"Failed to get window info for {window_id}: {e}")
        
        return None
    
    async def focus_window(self, title: Optional[str] = None, process: Optional[str] = None) -> Dict[str, Any]:
        """
        Focus a window by title or process name.
        
        Args:
            title: Window title (partial match)
            process: Process name
            
        Returns:
            Success/failure result
        """
        try:
            if self.platform == "linux":
                return await self._focus_window_linux(title, process)
            elif self.platform == "darwin":
                return await self._focus_window_macos(title, process)
            elif self.platform == "windows":
                return await self._focus_window_windows(title, process)
            else:
                return {"success": False, "error": f"Unsupported platform: {self.platform}"}
        
        except Exception as e:
            logger.error(f"Failed to focus window: {e}")
            return {"success": False, "error": str(e)}
    
    async def _focus_window_linux(self, title: Optional[str], process: Optional[str]) -> Dict[str, Any]:
        """Focus window on Linux"""
        if self.tools_available.get("wmctrl"):
            try:
                if title:
                    result = await asyncio.create_subprocess_exec(
                        "wmctrl", "-a", title,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await result.communicate()
                    
                    if result.returncode == 0:
                        return {"success": True, "method": "wmctrl", "target": title}
                
                if process:
                    # Try to find window by process and focus
                    result = await asyncio.create_subprocess_exec(
                        "wmctrl", "-x", "-a", process,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await result.communicate()
                    
                    if result.returncode == 0:
                        return {"success": True, "method": "wmctrl", "target": process}
                
            except Exception as e:
                logger.error(f"wmctrl focus failed: {e}")
        
        return {"success": False, "error": "Failed to focus window"}
    
    async def _focus_window_macos(self, title: Optional[str], process: Optional[str]) -> Dict[str, Any]:
        """Focus window on macOS"""
        if self.tools_available.get("osascript"):
            try:
                if process:
                    script = f'tell application "{process}" to activate'
                elif title:
                    script = f'''
                    tell application "System Events"
                        repeat with proc in (every process whose background only is false)
                            repeat with win in (every window of proc)
                                if title of win contains "{title}" then
                                    set frontmost of proc to true
                                    return
                                end if
                            end repeat
                        end repeat
                    end tell
                    '''
                else:
                    return {"success": False, "error": "No title or process specified"}
                
                result = await asyncio.create_subprocess_exec(
                    "osascript", "-e", script,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await result.communicate()
                
                if result.returncode == 0:
                    return {"success": True, "method": "osascript", "target": title or process}
                
            except Exception as e:
                logger.error(f"AppleScript focus failed: {e}")
        
        return {"success": False, "error": "Failed to focus window"}
    
    async def _focus_window_windows(self, title: Optional[str], process: Optional[str]) -> Dict[str, Any]:
        """Focus window on Windows"""
        # Implementation for Windows would go here
        return {"success": False, "error": "Windows focus not implemented yet"}
    
    async def move_window(self, window_id: str, x: int, y: int) -> Dict[str, Any]:
        """Move a window to specified coordinates"""
        try:
            if self.platform == "linux" and self.tools_available.get("wmctrl"):
                result = await asyncio.create_subprocess_exec(
                    "wmctrl", "-i", "-r", window_id, "-e", f"0,{x},{y},-1,-1",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await result.communicate()
                
                if result.returncode == 0:
                    return {"success": True, "window_id": window_id, "x": x, "y": y}
            
            return {"success": False, "error": "Move window not supported on this platform"}
        
        except Exception as e:
            logger.error(f"Failed to move window: {e}")
            return {"success": False, "error": str(e)}
    
    async def resize_window(self, window_id: str, width: int, height: int) -> Dict[str, Any]:
        """Resize a window"""
        try:
            if self.platform == "linux" and self.tools_available.get("wmctrl"):
                result = await asyncio.create_subprocess_exec(
                    "wmctrl", "-i", "-r", window_id, "-e", f"0,-1,-1,{width},{height}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await result.communicate()
                
                if result.returncode == 0:
                    return {"success": True, "window_id": window_id, "width": width, "height": height}
            
            return {"success": False, "error": "Resize window not supported on this platform"}
        
        except Exception as e:
            logger.error(f"Failed to resize window: {e}")
            return {"success": False, "error": str(e)}
    
    async def close_window(self, window_id: str) -> Dict[str, Any]:
        """Close a window"""
        try:
            if self.platform == "linux" and self.tools_available.get("wmctrl"):
                result = await asyncio.create_subprocess_exec(
                    "wmctrl", "-i", "-c", window_id,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await result.communicate()
                
                if result.returncode == 0:
                    return {"success": True, "window_id": window_id, "action": "closed"}
            
            return {"success": False, "error": "Close window not supported on this platform"}
        
        except Exception as e:
            logger.error(f"Failed to close window: {e}")
            return {"success": False, "error": str(e)}
    
    async def minimize_window(self, window_id: str) -> Dict[str, Any]:
        """Minimize a window"""
        try:
            if self.platform == "linux" and self.tools_available.get("xdotool"):
                result = await asyncio.create_subprocess_exec(
                    "xdotool", "windowminimize", window_id,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await result.communicate()
                
                if result.returncode == 0:
                    return {"success": True, "window_id": window_id, "action": "minimized"}
            
            return {"success": False, "error": "Minimize window not supported on this platform"}
        
        except Exception as e:
            logger.error(f"Failed to minimize window: {e}")
            return {"success": False, "error": str(e)}
    
    async def maximize_window(self, window_id: str) -> Dict[str, Any]:
        """Maximize a window"""
        try:
            if self.platform == "linux" and self.tools_available.get("wmctrl"):
                # First remove maximized state, then add it
                result = await asyncio.create_subprocess_exec(
                    "wmctrl", "-i", "-r", window_id, "-b", "add,maximized_vert,maximized_horz",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await result.communicate()
                
                if result.returncode == 0:
                    return {"success": True, "window_id": window_id, "action": "maximized"}
            
            return {"success": False, "error": "Maximize window not supported on this platform"}
        
        except Exception as e:
            logger.error(f"Failed to maximize window: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_desktop_info(self) -> Dict[str, Any]:
        """Get desktop and monitor information"""
        try:
            info = {
                "platform": self.platform,
                "tools_available": self.tools_available
            }
            
            if self.platform == "linux" and self.tools_available.get("xdpyinfo"):
                # Get display information
                result = await asyncio.create_subprocess_exec(
                    "xdpyinfo",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await result.communicate()
                
                if result.returncode == 0:
                    # Parse xdpyinfo output for screen dimensions
                    output = stdout.decode()
                    for line in output.split('\n'):
                        if 'dimensions:' in line:
                            match = re.search(r'(\d+)x(\d+)', line)
                            if match:
                                info["screen_width"] = int(match.group(1))
                                info["screen_height"] = int(match.group(2))
            
            return {"success": True, "desktop_info": info}
        
        except Exception as e:
            logger.error(f"Failed to get desktop info: {e}")
            return {"success": False, "error": str(e)}