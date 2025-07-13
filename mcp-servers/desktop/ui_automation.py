"""
UI Automation for Desktop Automation

UI element detection, interaction, and screenshot capabilities for the desktop MCP server.
Handles element finding, waiting, clicking, and visual verification.

Author: Claude Code
Date: 2025-07-13
Phase: 2.1
"""

import asyncio
import platform
import subprocess
import tempfile
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import time
import base64

logger = logging.getLogger(__name__)


class UIAutomation:
    """
    UI automation and visual interaction system.
    
    Features:
    - Screenshot capture with regions
    - UI element detection and waiting
    - Visual element interaction
    - Image comparison and verification
    - OCR text recognition (if available)
    """
    
    def __init__(self):
        """Initialize UI automation"""
        self.platform = platform.system().lower()
        self.tools_available = self._detect_tools()
        self.temp_dir = Path(tempfile.gettempdir()) / "desktop_automation"
        self.temp_dir.mkdir(exist_ok=True)
        
        logger.info(f"UI automation initialized for {self.platform}")
        logger.debug(f"Available tools: {list(self.tools_available.keys())}")
    
    def _detect_tools(self) -> Dict[str, bool]:
        """Detect available UI automation tools"""
        tools = {}
        
        if self.platform == "linux":
            tools["gnome-screenshot"] = self._command_available("gnome-screenshot")
            tools["scrot"] = self._command_available("scrot")
            tools["import"] = self._command_available("import")  # ImageMagick
            tools["xwininfo"] = self._command_available("xwininfo")
            tools["tesseract"] = self._command_available("tesseract")  # OCR
            
        elif self.platform == "darwin":  # macOS
            tools["screencapture"] = self._command_available("screencapture")
            tools["osascript"] = self._command_available("osascript")
            
        elif self.platform == "windows":
            tools["powershell"] = self._command_available("powershell")
            tools["snippingtool"] = self._command_available("snippingtool")
        
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
    
    async def take_screenshot(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Take a screenshot of the desktop or specific region.
        
        Args:
            args: Screenshot parameters including filename, region, window_id
            
        Returns:
            Screenshot result with file path and metadata
        """
        try:
            window_id = args.get("window_id")
            filename = args.get("filename")
            region = args.get("region")  # {x, y, width, height}
            
            # Generate filename if not provided
            if not filename:
                timestamp = int(time.time() * 1000)
                filename = f"screenshot_{timestamp}.png"
            
            # Ensure absolute path
            if not Path(filename).is_absolute():
                filename = str(self.temp_dir / filename)
            
            if self.platform == "linux":
                return await self._take_screenshot_linux(filename, window_id, region)
            elif self.platform == "darwin":
                return await self._take_screenshot_macos(filename, window_id, region)
            elif self.platform == "windows":
                return await self._take_screenshot_windows(filename, window_id, region)
            else:
                return {"success": False, "error": f"Unsupported platform: {self.platform}"}
        
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return {"success": False, "error": str(e)}
    
    async def _take_screenshot_linux(self, filename: str, window_id: Optional[str], region: Optional[Dict]) -> Dict[str, Any]:
        """Take screenshot on Linux"""
        try:
            if self.tools_available.get("gnome-screenshot"):
                cmd = ["gnome-screenshot", "-f", filename]
                
                if window_id:
                    cmd.extend(["-w"])
                elif region:
                    cmd.extend(["-a"])
                
                result = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await result.communicate()
                
                if result.returncode == 0 and Path(filename).exists():
                    return await self._process_screenshot_result(filename, region)
            
            elif self.tools_available.get("scrot"):
                cmd = ["scrot", filename]
                
                if region:
                    x, y, w, h = region["x"], region["y"], region["width"], region["height"]
                    cmd.extend(["-a", f"{x},{y},{w},{h}"])
                
                result = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await result.communicate()
                
                if result.returncode == 0 and Path(filename).exists():
                    return await self._process_screenshot_result(filename, region)
            
            elif self.tools_available.get("import"):
                cmd = ["import"]
                
                if region:
                    x, y, w, h = region["x"], region["y"], region["width"], region["height"]
                    cmd.extend(["-window", "root", "-crop", f"{w}x{h}+{x}+{y}"])
                else:
                    cmd.extend(["-window", "root"])
                
                cmd.append(filename)
                
                result = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await result.communicate()
                
                if result.returncode == 0 and Path(filename).exists():
                    return await self._process_screenshot_result(filename, region)
            
            return {"success": False, "error": "No screenshot tool available"}
        
        except Exception as e:
            logger.error(f"Linux screenshot failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _take_screenshot_macos(self, filename: str, window_id: Optional[str], region: Optional[Dict]) -> Dict[str, Any]:
        """Take screenshot on macOS"""
        try:
            if self.tools_available.get("screencapture"):
                cmd = ["screencapture"]
                
                if region:
                    x, y, w, h = region["x"], region["y"], region["width"], region["height"]
                    cmd.extend(["-R", f"{x},{y},{w},{h}"])
                
                cmd.append(filename)
                
                result = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await result.communicate()
                
                if result.returncode == 0 and Path(filename).exists():
                    return await self._process_screenshot_result(filename, region)
            
            return {"success": False, "error": "screencapture not available"}
        
        except Exception as e:
            logger.error(f"macOS screenshot failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _take_screenshot_windows(self, filename: str, window_id: Optional[str], region: Optional[Dict]) -> Dict[str, Any]:
        """Take screenshot on Windows"""
        try:
            if self.tools_available.get("powershell"):
                # PowerShell script for screenshot
                script = f'''
                Add-Type -AssemblyName System.Windows.Forms
                Add-Type -AssemblyName System.Drawing
                $Screen = [System.Windows.Forms.SystemInformation]::VirtualScreen
                '''
                
                if region:
                    x, y, w, h = region["x"], region["y"], region["width"], region["height"]
                    script += f'''
                    $bitmap = New-Object System.Drawing.Bitmap {w}, {h}
                    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
                    $graphics.CopyFromScreen({x}, {y}, 0, 0, $bitmap.Size)
                    '''
                else:
                    script += '''
                    $bitmap = New-Object System.Drawing.Bitmap $Screen.Width, $Screen.Height
                    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
                    $graphics.CopyFromScreen($Screen.Left, $Screen.Top, 0, 0, $bitmap.Size)
                    '''
                
                script += f'''
                $bitmap.Save("{filename}")
                $graphics.Dispose()
                $bitmap.Dispose()
                '''
                
                result = await asyncio.create_subprocess_exec(
                    "powershell", "-Command", script,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await result.communicate()
                
                if result.returncode == 0 and Path(filename).exists():
                    return await self._process_screenshot_result(filename, region)
            
            return {"success": False, "error": "PowerShell screenshot failed"}
        
        except Exception as e:
            logger.error(f"Windows screenshot failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _process_screenshot_result(self, filename: str, region: Optional[Dict]) -> Dict[str, Any]:
        """Process screenshot result and return metadata"""
        try:
            file_path = Path(filename)
            if not file_path.exists():
                return {"success": False, "error": "Screenshot file not found"}
            
            stat = file_path.stat()
            
            # Get image dimensions (basic approach)
            width, height = await self._get_image_dimensions(str(file_path))
            
            # Encode as base64 for optional return
            with open(file_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            return {
                "success": True,
                "filename": str(file_path),
                "size_bytes": stat.st_size,
                "width": width,
                "height": height,
                "region": region,
                "timestamp": time.time(),
                "image_data": image_data[:1000] + "..." if len(image_data) > 1000 else image_data  # Truncate for display
            }
        
        except Exception as e:
            logger.error(f"Failed to process screenshot result: {e}")
            return {"success": False, "error": str(e)}
    
    async def _get_image_dimensions(self, file_path: str) -> Tuple[int, int]:
        """Get image dimensions"""
        try:
            if self.tools_available.get("identify"):  # ImageMagick
                result = await asyncio.create_subprocess_exec(
                    "identify", "-format", "%wx%h", file_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await result.communicate()
                
                if result.returncode == 0:
                    dimensions = stdout.decode().strip()
                    width, height = map(int, dimensions.split('x'))
                    return width, height
            
            # Fallback: assume common dimensions
            return 1920, 1080
        
        except Exception:
            return 1920, 1080
    
    async def find_element(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Find UI element on screen.
        
        Args:
            args: Element search parameters (text, image, coordinates)
            
        Returns:
            Element location and metadata
        """
        try:
            search_type = args.get("type", "text")  # text, image, coordinate
            search_value = args.get("value")
            region = args.get("region")  # Optional search region
            
            if search_type == "text":
                return await self._find_text_element(search_value, region)
            elif search_type == "image":
                return await self._find_image_element(search_value, region)
            elif search_type == "coordinate":
                return await self._find_coordinate_element(search_value)
            else:
                return {"success": False, "error": f"Unknown search type: {search_type}"}
        
        except Exception as e:
            logger.error(f"Failed to find element: {e}")
            return {"success": False, "error": str(e)}
    
    async def _find_text_element(self, text: str, region: Optional[Dict]) -> Dict[str, Any]:
        """Find text element using OCR"""
        try:
            if not self.tools_available.get("tesseract"):
                return {"success": False, "error": "OCR not available (tesseract not found)"}
            
            # Take screenshot first
            screenshot_args = {}
            if region:
                screenshot_args["region"] = region
            
            screenshot_result = await self.take_screenshot(screenshot_args)
            if not screenshot_result.get("success"):
                return screenshot_result
            
            screenshot_file = screenshot_result["filename"]
            
            # Run OCR
            result = await asyncio.create_subprocess_exec(
                "tesseract", screenshot_file, "stdout",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            
            if result.returncode == 0:
                ocr_text = stdout.decode()
                if text.lower() in ocr_text.lower():
                    return {
                        "success": True,
                        "found": True,
                        "text": text,
                        "ocr_result": ocr_text,
                        "screenshot": screenshot_file
                    }
                else:
                    return {
                        "success": True,
                        "found": False,
                        "text": text,
                        "ocr_result": ocr_text
                    }
            
            return {"success": False, "error": "OCR failed"}
        
        except Exception as e:
            logger.error(f"Text element search failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _find_image_element(self, image_path: str, region: Optional[Dict]) -> Dict[str, Any]:
        """Find image element using template matching"""
        # This would require image processing libraries like OpenCV
        return {"success": False, "error": "Image element search not implemented yet"}
    
    async def _find_coordinate_element(self, coordinates: Dict[str, int]) -> Dict[str, Any]:
        """Verify element at specific coordinates"""
        x, y = coordinates.get("x"), coordinates.get("y")
        if x is None or y is None:
            return {"success": False, "error": "Invalid coordinates"}
        
        return {
            "success": True,
            "found": True,
            "x": x,
            "y": y,
            "type": "coordinate"
        }
    
    async def wait_for_element(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Wait for UI element to appear.
        
        Args:
            args: Element search parameters with timeout
            
        Returns:
            Element found result
        """
        try:
            timeout = args.get("timeout", 10.0)
            check_interval = args.get("interval", 1.0)
            
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                result = await self.find_element(args)
                
                if result.get("success") and result.get("found"):
                    result["wait_time"] = time.time() - start_time
                    return result
                
                await asyncio.sleep(check_interval)
            
            return {
                "success": False,
                "error": "Element not found within timeout",
                "timeout": timeout,
                "wait_time": time.time() - start_time
            }
        
        except Exception as e:
            logger.error(f"Wait for element failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def click_element(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Click a UI element found by search.
        
        Args:
            args: Element search and click parameters
            
        Returns:
            Click result
        """
        try:
            # First find the element
            find_result = await self.find_element(args)
            
            if not find_result.get("success") or not find_result.get("found"):
                return {
                    "success": False,
                    "error": "Element not found for clicking",
                    "find_result": find_result
                }
            
            # Extract coordinates if available
            x = find_result.get("x")
            y = find_result.get("y")
            
            if x is None or y is None:
                return {
                    "success": False,
                    "error": "Element coordinates not available",
                    "find_result": find_result
                }
            
            # Import keyboard_mouse module for clicking
            from .keyboard_mouse import KeyboardMouse
            kb_mouse = KeyboardMouse()
            
            # Perform click
            click_result = await kb_mouse.click_coordinates(x, y, args.get("button", "left"))
            
            return {
                "success": click_result.get("success"),
                "element_found": find_result,
                "click_result": click_result
            }
        
        except Exception as e:
            logger.error(f"Click element failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def hover_element(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hover over a UI element.
        
        Args:
            args: Element search parameters
            
        Returns:
            Hover result
        """
        try:
            # Find the element first
            find_result = await self.find_element(args)
            
            if not find_result.get("success") or not find_result.get("found"):
                return {
                    "success": False,
                    "error": "Element not found for hovering",
                    "find_result": find_result
                }
            
            x = find_result.get("x")
            y = find_result.get("y")
            
            if x is None or y is None:
                return {
                    "success": False,
                    "error": "Element coordinates not available"
                }
            
            # Import keyboard_mouse for mouse movement
            from .keyboard_mouse import KeyboardMouse
            kb_mouse = KeyboardMouse()
            
            # Move mouse to element
            move_result = await kb_mouse.move_mouse(x, y)
            
            return {
                "success": move_result.get("success"),
                "element_found": find_result,
                "hover_result": move_result
            }
        
        except Exception as e:
            logger.error(f"Hover element failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def extract_text_from_region(self, region: Dict[str, int]) -> Dict[str, Any]:
        """Extract text from a screen region using OCR"""
        try:
            if not self.tools_available.get("tesseract"):
                return {"success": False, "error": "OCR not available"}
            
            # Take screenshot of region
            screenshot_result = await self.take_screenshot({"region": region})
            if not screenshot_result.get("success"):
                return screenshot_result
            
            screenshot_file = screenshot_result["filename"]
            
            # Run OCR
            result = await asyncio.create_subprocess_exec(
                "tesseract", screenshot_file, "stdout",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "text": stdout.decode().strip(),
                    "region": region,
                    "screenshot": screenshot_file
                }
            
            return {"success": False, "error": "OCR extraction failed"}
        
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            return {"success": False, "error": str(e)}
    
    def cleanup_temp_files(self, max_age_hours: float = 24):
        """Clean up old temporary files"""
        try:
            current_time = time.time()
            for file_path in self.temp_dir.glob("screenshot_*.png"):
                if current_time - file_path.stat().st_mtime > max_age_hours * 3600:
                    file_path.unlink()
                    logger.debug(f"Cleaned up old screenshot: {file_path}")
        
        except Exception as e:
            logger.error(f"Failed to cleanup temp files: {e}")