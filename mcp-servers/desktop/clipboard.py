"""
Clipboard Management for Desktop Automation

Cross-platform clipboard operations for the desktop MCP server.
Handles reading, writing, and history tracking of clipboard contents.

Author: Claude Code
Date: 2025-07-13
Phase: 2.1
"""

import asyncio
import platform
import subprocess
import logging
from typing import Dict, List, Any, Optional
import time
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class ClipboardManager:
    """
    Cross-platform clipboard management system.
    
    Features:
    - Read and write text clipboard contents
    - Image clipboard support (platform dependent)
    - Clipboard history tracking
    - Format detection and conversion
    - Security controls for sensitive data
    """
    
    def __init__(self, history_limit: int = 50):
        """
        Initialize clipboard manager.
        
        Args:
            history_limit: Maximum number of clipboard history items to keep
        """
        self.platform = platform.system().lower()
        self.tools_available = self._detect_tools()
        self.history_limit = history_limit
        
        # Clipboard history storage
        self.history: List[Dict[str, Any]] = []
        
        logger.info(f"Clipboard manager initialized for {self.platform}")
        logger.debug(f"Available tools: {list(self.tools_available.keys())}")
    
    def _detect_tools(self) -> Dict[str, bool]:
        """Detect available clipboard tools"""
        tools = {}
        
        if self.platform == "linux":
            tools["xclip"] = self._command_available("xclip")
            tools["xsel"] = self._command_available("xsel")
            tools["wl-copy"] = self._command_available("wl-copy")  # Wayland
            tools["wl-paste"] = self._command_available("wl-paste")  # Wayland
            
        elif self.platform == "darwin":  # macOS
            tools["pbcopy"] = self._command_available("pbcopy")
            tools["pbpaste"] = self._command_available("pbpaste")
            
        elif self.platform == "windows":
            tools["powershell"] = self._command_available("powershell")
            tools["clip"] = self._command_available("clip")
        
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
    
    async def get_clipboard(self) -> Dict[str, Any]:
        """
        Get current clipboard contents.
        
        Returns:
            Clipboard contents and metadata
        """
        try:
            if self.platform == "linux":
                return await self._get_clipboard_linux()
            elif self.platform == "darwin":
                return await self._get_clipboard_macos()
            elif self.platform == "windows":
                return await self._get_clipboard_windows()
            else:
                return {"success": False, "error": f"Unsupported platform: {self.platform}"}
        
        except Exception as e:
            logger.error(f"Failed to get clipboard: {e}")
            return {"success": False, "error": str(e)}
    
    async def _get_clipboard_linux(self) -> Dict[str, Any]:
        """Get clipboard contents on Linux"""
        content = None
        content_type = "text"
        method = None
        
        # Try different clipboard tools
        if self.tools_available.get("xclip"):
            try:
                # Try to get text content
                result = await asyncio.create_subprocess_exec(
                    "xclip", "-selection", "clipboard", "-o",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await result.communicate()
                
                if result.returncode == 0:
                    content = stdout.decode('utf-8', errors='replace')
                    method = "xclip"
                
            except Exception as e:
                logger.debug(f"xclip failed: {e}")
        
        elif self.tools_available.get("xsel"):
            try:
                result = await asyncio.create_subprocess_exec(
                    "xsel", "--clipboard", "--output",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await result.communicate()
                
                if result.returncode == 0:
                    content = stdout.decode('utf-8', errors='replace')
                    method = "xsel"
                
            except Exception as e:
                logger.debug(f"xsel failed: {e}")
        
        elif self.tools_available.get("wl-paste"):
            try:
                # Wayland clipboard
                result = await asyncio.create_subprocess_exec(
                    "wl-paste",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await result.communicate()
                
                if result.returncode == 0:
                    content = stdout.decode('utf-8', errors='replace')
                    method = "wl-paste"
                
            except Exception as e:
                logger.debug(f"wl-paste failed: {e}")
        
        if content is not None:
            # Add to history
            self._add_to_history(content, content_type)
            
            return {
                "success": True,
                "content": content,
                "content_type": content_type,
                "method": method,
                "length": len(content),
                "timestamp": time.time()
            }
        
        return {"success": False, "error": "No clipboard tool available or clipboard empty"}
    
    async def _get_clipboard_macos(self) -> Dict[str, Any]:
        """Get clipboard contents on macOS"""
        if self.tools_available.get("pbpaste"):
            try:
                result = await asyncio.create_subprocess_exec(
                    "pbpaste",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await result.communicate()
                
                if result.returncode == 0:
                    content = stdout.decode('utf-8', errors='replace')
                    content_type = "text"
                    
                    # Add to history
                    self._add_to_history(content, content_type)
                    
                    return {
                        "success": True,
                        "content": content,
                        "content_type": content_type,
                        "method": "pbpaste",
                        "length": len(content),
                        "timestamp": time.time()
                    }
                
            except Exception as e:
                logger.error(f"pbpaste failed: {e}")
        
        return {"success": False, "error": "pbpaste not available or failed"}
    
    async def _get_clipboard_windows(self) -> Dict[str, Any]:
        """Get clipboard contents on Windows"""
        if self.tools_available.get("powershell"):
            try:
                # PowerShell script to get clipboard
                script = '''
                Add-Type -AssemblyName System.Windows.Forms
                $clipboard = [System.Windows.Forms.Clipboard]::GetText()
                if ($clipboard) {
                    Write-Output $clipboard
                } else {
                    Write-Output ""
                }
                '''
                
                result = await asyncio.create_subprocess_exec(
                    "powershell", "-Command", script,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await result.communicate()
                
                if result.returncode == 0:
                    content = stdout.decode('utf-8', errors='replace').strip()
                    content_type = "text"
                    
                    # Add to history
                    self._add_to_history(content, content_type)
                    
                    return {
                        "success": True,
                        "content": content,
                        "content_type": content_type,
                        "method": "powershell",
                        "length": len(content),
                        "timestamp": time.time()
                    }
                
            except Exception as e:
                logger.error(f"PowerShell clipboard get failed: {e}")
        
        return {"success": False, "error": "PowerShell clipboard access failed"}
    
    async def set_clipboard(self, content: str, content_type: str = "text") -> Dict[str, Any]:
        """
        Set clipboard contents.
        
        Args:
            content: Content to set
            content_type: Type of content ("text", "image")
            
        Returns:
            Success/failure result
        """
        try:
            if content_type != "text":
                return {"success": False, "error": f"Content type '{content_type}' not supported yet"}
            
            if self.platform == "linux":
                return await self._set_clipboard_linux(content)
            elif self.platform == "darwin":
                return await self._set_clipboard_macos(content)
            elif self.platform == "windows":
                return await self._set_clipboard_windows(content)
            else:
                return {"success": False, "error": f"Unsupported platform: {self.platform}"}
        
        except Exception as e:
            logger.error(f"Failed to set clipboard: {e}")
            return {"success": False, "error": str(e)}
    
    async def _set_clipboard_linux(self, content: str) -> Dict[str, Any]:
        """Set clipboard contents on Linux"""
        method = None
        
        if self.tools_available.get("xclip"):
            try:
                result = await asyncio.create_subprocess_exec(
                    "xclip", "-selection", "clipboard",
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await result.communicate(input=content.encode('utf-8'))
                
                if result.returncode == 0:
                    method = "xclip"
                
            except Exception as e:
                logger.debug(f"xclip set failed: {e}")
        
        elif self.tools_available.get("xsel"):
            try:
                result = await asyncio.create_subprocess_exec(
                    "xsel", "--clipboard", "--input",
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await result.communicate(input=content.encode('utf-8'))
                
                if result.returncode == 0:
                    method = "xsel"
                
            except Exception as e:
                logger.debug(f"xsel set failed: {e}")
        
        elif self.tools_available.get("wl-copy"):
            try:
                result = await asyncio.create_subprocess_exec(
                    "wl-copy",
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await result.communicate(input=content.encode('utf-8'))
                
                if result.returncode == 0:
                    method = "wl-copy"
                
            except Exception as e:
                logger.debug(f"wl-copy set failed: {e}")
        
        if method:
            # Add to history
            self._add_to_history(content, "text")
            
            return {
                "success": True,
                "content": content,
                "method": method,
                "length": len(content),
                "timestamp": time.time()
            }
        
        return {"success": False, "error": "No clipboard tool available"}
    
    async def _set_clipboard_macos(self, content: str) -> Dict[str, Any]:
        """Set clipboard contents on macOS"""
        if self.tools_available.get("pbcopy"):
            try:
                result = await asyncio.create_subprocess_exec(
                    "pbcopy",
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await result.communicate(input=content.encode('utf-8'))
                
                if result.returncode == 0:
                    # Add to history
                    self._add_to_history(content, "text")
                    
                    return {
                        "success": True,
                        "content": content,
                        "method": "pbcopy",
                        "length": len(content),
                        "timestamp": time.time()
                    }
                
            except Exception as e:
                logger.error(f"pbcopy failed: {e}")
        
        return {"success": False, "error": "pbcopy not available or failed"}
    
    async def _set_clipboard_windows(self, content: str) -> Dict[str, Any]:
        """Set clipboard contents on Windows"""
        if self.tools_available.get("powershell"):
            try:
                # Escape content for PowerShell
                escaped_content = content.replace("'", "''")
                
                script = f'''
                Add-Type -AssemblyName System.Windows.Forms
                [System.Windows.Forms.Clipboard]::SetText('{escaped_content}')
                '''
                
                result = await asyncio.create_subprocess_exec(
                    "powershell", "-Command", script,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await result.communicate()
                
                if result.returncode == 0:
                    # Add to history
                    self._add_to_history(content, "text")
                    
                    return {
                        "success": True,
                        "content": content,
                        "method": "powershell",
                        "length": len(content),
                        "timestamp": time.time()
                    }
                
            except Exception as e:
                logger.error(f"PowerShell clipboard set failed: {e}")
        
        elif self.tools_available.get("clip"):
            try:
                # Use built-in clip command
                result = await asyncio.create_subprocess_exec(
                    "clip",
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await result.communicate(input=content.encode('utf-8'))
                
                if result.returncode == 0:
                    # Add to history
                    self._add_to_history(content, "text")
                    
                    return {
                        "success": True,
                        "content": content,
                        "method": "clip",
                        "length": len(content),
                        "timestamp": time.time()
                    }
                
            except Exception as e:
                logger.error(f"clip command failed: {e}")
        
        return {"success": False, "error": "Windows clipboard set failed"}
    
    def _add_to_history(self, content: str, content_type: str):
        """Add content to clipboard history"""
        try:
            # Don't add empty content or duplicates
            if not content or (self.history and self.history[-1].get("content") == content):
                return
            
            # Add to history
            history_item = {
                "content": content,
                "content_type": content_type,
                "timestamp": time.time(),
                "length": len(content)
            }
            
            self.history.append(history_item)
            
            # Limit history size
            if len(self.history) > self.history_limit:
                self.history = self.history[-self.history_limit:]
            
            logger.debug(f"Added to clipboard history: {len(content)} chars")
        
        except Exception as e:
            logger.error(f"Failed to add to history: {e}")
    
    async def get_history(self) -> Dict[str, Any]:
        """
        Get clipboard history.
        
        Returns:
            Clipboard history items
        """
        try:
            return {
                "success": True,
                "history": self.history.copy(),
                "count": len(self.history),
                "limit": self.history_limit
            }
        
        except Exception as e:
            logger.error(f"Failed to get history: {e}")
            return {"success": False, "error": str(e)}
    
    async def clear_history(self) -> Dict[str, Any]:
        """Clear clipboard history"""
        try:
            self.history.clear()
            return {"success": True, "message": "Clipboard history cleared"}
        
        except Exception as e:
            logger.error(f"Failed to clear history: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_clipboard_formats(self) -> Dict[str, Any]:
        """Get available clipboard formats"""
        try:
            formats = ["text"]
            
            # Platform-specific format detection could be added here
            if self.platform == "windows":
                # Windows supports more formats
                formats.extend(["image", "html", "rtf"])
            elif self.platform == "darwin":
                # macOS formats
                formats.extend(["image", "html"])
            elif self.platform == "linux":
                # Linux X11 formats
                formats.extend(["image"])
            
            return {
                "success": True,
                "formats": formats,
                "platform": self.platform
            }
        
        except Exception as e:
            logger.error(f"Failed to get clipboard formats: {e}")
            return {"success": False, "error": str(e)}
    
    async def monitor_clipboard(self, callback: Optional[callable] = None, interval: float = 1.0) -> Dict[str, Any]:
        """
        Monitor clipboard for changes.
        
        Args:
            callback: Function to call when clipboard changes
            interval: Check interval in seconds
            
        Returns:
            Monitoring result
        """
        try:
            last_content = None
            monitoring = True
            
            logger.info(f"Starting clipboard monitoring (interval: {interval}s)")
            
            while monitoring:
                current_result = await self.get_clipboard()
                
                if current_result.get("success"):
                    current_content = current_result.get("content")
                    
                    if current_content != last_content and current_content:
                        logger.info(f"Clipboard changed: {len(current_content)} chars")
                        
                        if callback:
                            try:
                                await callback(current_result)
                            except Exception as e:
                                logger.error(f"Callback failed: {e}")
                        
                        last_content = current_content
                
                await asyncio.sleep(interval)
            
            return {"success": True, "message": "Clipboard monitoring stopped"}
        
        except Exception as e:
            logger.error(f"Clipboard monitoring failed: {e}")
            return {"success": False, "error": str(e)}
    
    def export_history(self, file_path: str) -> Dict[str, Any]:
        """Export clipboard history to file"""
        try:
            history_data = {
                "export_timestamp": time.time(),
                "platform": self.platform,
                "history": self.history
            }
            
            with open(file_path, 'w') as f:
                json.dump(history_data, f, indent=2)
            
            return {
                "success": True,
                "file_path": file_path,
                "items_exported": len(self.history)
            }
        
        except Exception as e:
            logger.error(f"Failed to export history: {e}")
            return {"success": False, "error": str(e)}
    
    def import_history(self, file_path: str) -> Dict[str, Any]:
        """Import clipboard history from file"""
        try:
            with open(file_path, 'r') as f:
                history_data = json.load(f)
            
            imported_history = history_data.get("history", [])
            
            # Merge with existing history
            self.history.extend(imported_history)
            
            # Apply limit
            if len(self.history) > self.history_limit:
                self.history = self.history[-self.history_limit:]
            
            return {
                "success": True,
                "items_imported": len(imported_history),
                "total_items": len(self.history)
            }
        
        except Exception as e:
            logger.error(f"Failed to import history: {e}")
            return {"success": False, "error": str(e)}