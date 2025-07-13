"""
Screenshot Context System

Provides screenshot capture and analysis capabilities for visual context
in agent operations.

Author: Claude Code
Date: 2025-07-13
Session: 1.3
"""

import asyncio
import os
import time
import subprocess
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import tempfile
import logging

from ...utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ScreenshotMetadata:
    """Metadata for captured screenshots"""
    timestamp: float
    file_path: str
    width: int
    height: int
    format: str
    size_bytes: int
    capture_method: str
    display_info: Dict[str, Any] = None


class ScreenshotCapture:
    """
    Cross-platform screenshot capture system.
    
    Features:
    - Multi-platform screenshot capture (Linux, macOS, Windows)
    - Multiple display support
    - Region-specific capture
    - Automatic cleanup of temporary files
    - Metadata tracking
    """
    
    def __init__(self, temp_dir: Optional[str] = None):
        """
        Initialize screenshot capture system.
        
        Args:
            temp_dir: Directory for temporary screenshot files
        """
        self.temp_dir = Path(temp_dir) if temp_dir else Path(tempfile.gettempdir()) / "agent_screenshots"
        self.temp_dir.mkdir(exist_ok=True)
        
        # Platform detection
        self.platform = self._detect_platform()
        self.capture_tools = self._detect_capture_tools()
        
        # Settings
        self.default_format = "png"
        self.max_screenshots = 50
        self.auto_cleanup = True
        
        # Storage
        self.captured_screenshots: List[ScreenshotMetadata] = []
        
        logger.info(f"Screenshot capture initialized for {self.platform}")
        logger.debug(f"Available tools: {list(self.capture_tools.keys())}")
    
    def _detect_platform(self) -> str:
        """Detect the current platform"""
        import platform
        system = platform.system().lower()
        
        if system == "linux":
            return "linux"
        elif system == "darwin":
            return "macos"
        elif system == "windows":
            return "windows"
        else:
            return "unknown"
    
    def _detect_capture_tools(self) -> Dict[str, str]:
        """Detect available screenshot tools for the platform"""
        tools = {}
        
        if self.platform == "linux":
            # Linux screenshot tools
            for tool in ["gnome-screenshot", "scrot", "import", "xwd"]:
                if self._command_available(tool):
                    tools[tool] = tool
        
        elif self.platform == "macos":
            # macOS screenshot tools
            if self._command_available("screencapture"):
                tools["screencapture"] = "screencapture"
        
        elif self.platform == "windows":
            # Windows screenshot tools (could add PowerShell commands)
            tools["powershell"] = "powershell"
        
        return tools
    
    def _command_available(self, command: str) -> bool:
        """Check if a command is available in the system"""
        try:
            subprocess.run(
                ["which", command] if self.platform != "windows" else ["where", command],
                capture_output=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    async def capture_screenshot(
        self,
        region: Optional[Tuple[int, int, int, int]] = None,
        display: Optional[int] = None,
        delay: float = 0.0
    ) -> Optional[ScreenshotMetadata]:
        """
        Capture a screenshot.
        
        Args:
            region: Optional region (x, y, width, height) to capture
            display: Optional display number for multi-monitor setups
            delay: Delay before capture in seconds
            
        Returns:
            Screenshot metadata or None if capture failed
        """
        if delay > 0:
            await asyncio.sleep(delay)
        
        logger.debug(f"Capturing screenshot (region={region}, display={display})")
        
        # Generate unique filename
        timestamp = time.time()
        filename = f"screenshot_{int(timestamp * 1000)}.{self.default_format}"
        file_path = self.temp_dir / filename
        
        # Attempt capture with available tools
        success = False
        capture_method = "unknown"
        
        for tool_name, tool_command in self.capture_tools.items():
            try:
                success = await self._capture_with_tool(
                    tool_name, tool_command, str(file_path), region, display
                )
                if success:
                    capture_method = tool_name
                    break
            except Exception as e:
                logger.debug(f"Failed to capture with {tool_name}: {e}")
                continue
        
        if not success or not file_path.exists():
            logger.error("Screenshot capture failed with all available tools")
            return None
        
        # Get file info
        stat = file_path.stat()
        width, height = await self._get_image_dimensions(str(file_path))
        
        metadata = ScreenshotMetadata(
            timestamp=timestamp,
            file_path=str(file_path),
            width=width,
            height=height,
            format=self.default_format,
            size_bytes=stat.st_size,
            capture_method=capture_method
        )
        
        # Store metadata
        self.captured_screenshots.append(metadata)
        
        # Cleanup old screenshots if needed
        if self.auto_cleanup and len(self.captured_screenshots) > self.max_screenshots:
            await self._cleanup_old_screenshots()
        
        logger.info(f"Screenshot captured: {filename} ({width}x{height})")
        return metadata
    
    async def _capture_with_tool(
        self,
        tool_name: str,
        tool_command: str,
        file_path: str,
        region: Optional[Tuple[int, int, int, int]] = None,
        display: Optional[int] = None
    ) -> bool:
        """Capture screenshot with a specific tool"""
        
        try:
            if tool_name == "gnome-screenshot":
                cmd = ["gnome-screenshot", "-f", file_path]
                if region:
                    x, y, w, h = region
                    cmd.extend(["-a", "-x", str(x), "-y", str(y), "-w", str(w), "-h", str(h)])
            
            elif tool_name == "scrot":
                cmd = ["scrot", file_path]
                if region:
                    x, y, w, h = region
                    cmd.extend(["-a", f"{x},{y},{w},{h}"])
            
            elif tool_name == "import":  # ImageMagick
                cmd = ["import"]
                if region:
                    x, y, w, h = region
                    cmd.extend(["-window", "root", "-crop", f"{w}x{h}+{x}+{y}"])
                else:
                    cmd.extend(["-window", "root"])
                cmd.append(file_path)
            
            elif tool_name == "screencapture":  # macOS
                cmd = ["screencapture"]
                if region:
                    x, y, w, h = region
                    cmd.extend(["-R", f"{x},{y},{w},{h}"])
                cmd.append(file_path)
            
            elif tool_name == "powershell":  # Windows
                # PowerShell screenshot command
                ps_script = f"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$Screen = [System.Windows.Forms.SystemInformation]::VirtualScreen
$bitmap = New-Object System.Drawing.Bitmap $Screen.Width, $Screen.Height
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($Screen.Left, $Screen.Top, 0, 0, $bitmap.Size)
$bitmap.Save('{file_path}')
"""
                cmd = ["powershell", "-Command", ps_script]
            
            else:
                return False
            
            # Execute command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return True
            else:
                logger.debug(f"Tool {tool_name} failed: {stderr.decode()}")
                return False
        
        except Exception as e:
            logger.debug(f"Exception with tool {tool_name}: {e}")
            return False
    
    async def _get_image_dimensions(self, file_path: str) -> Tuple[int, int]:
        """Get image dimensions from file"""
        try:
            # Try using ImageMagick identify command
            if self._command_available("identify"):
                process = await asyncio.create_subprocess_exec(
                    "identify", "-format", "%wx%h", file_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await process.communicate()
                
                if process.returncode == 0:
                    dimensions = stdout.decode().strip()
                    width, height = map(int, dimensions.split('x'))
                    return width, height
            
            # Fallback: try to read basic file info
            # This is a simplified approach
            return 1920, 1080  # Default assumption
        
        except Exception:
            return 1920, 1080  # Default fallback
    
    async def _cleanup_old_screenshots(self):
        """Remove old screenshot files"""
        if len(self.captured_screenshots) <= self.max_screenshots:
            return
        
        # Sort by timestamp and remove oldest
        self.captured_screenshots.sort(key=lambda x: x.timestamp)
        to_remove = self.captured_screenshots[:-self.max_screenshots]
        
        for metadata in to_remove:
            try:
                file_path = Path(metadata.file_path)
                if file_path.exists():
                    file_path.unlink()
                    logger.debug(f"Cleaned up screenshot: {file_path.name}")
            except Exception as e:
                logger.warning(f"Failed to cleanup screenshot {metadata.file_path}: {e}")
        
        # Update list
        self.captured_screenshots = self.captured_screenshots[-self.max_screenshots:]
    
    async def capture_window(self, window_id: Optional[str] = None) -> Optional[ScreenshotMetadata]:
        """
        Capture a specific window.
        
        Args:
            window_id: Window identifier (platform-specific)
            
        Returns:
            Screenshot metadata or None if capture failed
        """
        # This would require platform-specific window detection
        # For now, fallback to full screen capture
        logger.info("Window capture not fully implemented, using full screen")
        return await self.capture_screenshot()
    
    def get_latest_screenshot(self) -> Optional[ScreenshotMetadata]:
        """Get metadata for the most recent screenshot"""
        if self.captured_screenshots:
            return max(self.captured_screenshots, key=lambda x: x.timestamp)
        return None
    
    def get_screenshots_since(self, timestamp: float) -> List[ScreenshotMetadata]:
        """Get all screenshots captured since a given timestamp"""
        return [s for s in self.captured_screenshots if s.timestamp >= timestamp]
    
    def cleanup_all_screenshots(self):
        """Remove all captured screenshot files"""
        for metadata in self.captured_screenshots:
            try:
                file_path = Path(metadata.file_path)
                if file_path.exists():
                    file_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to cleanup screenshot {metadata.file_path}: {e}")
        
        self.captured_screenshots.clear()
        logger.info("All screenshots cleaned up")


class ScreenshotAnalyzer:
    """
    Analyzes screenshots to extract useful context information.
    
    Features:
    - Basic image analysis
    - Text extraction (OCR) - would require additional dependencies
    - Window detection
    - Change detection between screenshots
    """
    
    def __init__(self):
        """Initialize screenshot analyzer"""
        self.previous_screenshot: Optional[ScreenshotMetadata] = None
        logger.info("Screenshot analyzer initialized")
    
    async def analyze_screenshot(self, metadata: ScreenshotMetadata) -> Dict[str, Any]:
        """
        Analyze a screenshot and extract useful information.
        
        Args:
            metadata: Screenshot metadata
            
        Returns:
            Analysis results
        """
        logger.debug(f"Analyzing screenshot: {metadata.file_path}")
        
        analysis = {
            "timestamp": metadata.timestamp,
            "file_path": metadata.file_path,
            "dimensions": (metadata.width, metadata.height),
            "file_size": metadata.size_bytes,
            "capture_method": metadata.capture_method
        }
        
        # Basic file analysis
        file_path = Path(metadata.file_path)
        if file_path.exists():
            analysis["file_exists"] = True
            analysis["file_accessible"] = os.access(str(file_path), os.R_OK)
        else:
            analysis["file_exists"] = False
            analysis["file_accessible"] = False
        
        # TODO: Add more sophisticated analysis
        # - OCR text extraction
        # - UI element detection
        # - Change detection
        # - Application identification
        
        return analysis
    
    async def detect_changes(
        self,
        current_metadata: ScreenshotMetadata,
        previous_metadata: Optional[ScreenshotMetadata] = None
    ) -> Dict[str, Any]:
        """
        Detect changes between screenshots.
        
        Args:
            current_metadata: Current screenshot
            previous_metadata: Previous screenshot to compare against
            
        Returns:
            Change detection results
        """
        if previous_metadata is None:
            previous_metadata = self.previous_screenshot
        
        if previous_metadata is None:
            return {"changes_detected": False, "reason": "No previous screenshot"}
        
        # Basic change detection based on file properties
        changes = {
            "changes_detected": False,
            "timestamp_diff": current_metadata.timestamp - previous_metadata.timestamp,
            "size_diff": current_metadata.size_bytes - previous_metadata.size_bytes,
            "dimension_change": (
                current_metadata.width != previous_metadata.width or
                current_metadata.height != previous_metadata.height
            )
        }
        
        # Detect if changes likely occurred
        if abs(changes["size_diff"]) > 1024:  # Size difference > 1KB
            changes["changes_detected"] = True
            changes["change_type"] = "content_change"
        
        if changes["dimension_change"]:
            changes["changes_detected"] = True
            changes["change_type"] = "resolution_change"
        
        return changes


class ScreenshotContext:
    """
    High-level screenshot context management for agent operations.
    
    Combines capture and analysis to provide contextual information
    for agent decision making.
    """
    
    def __init__(self, temp_dir: Optional[str] = None):
        """
        Initialize screenshot context system.
        
        Args:
            temp_dir: Directory for temporary files
        """
        self.capture = ScreenshotCapture(temp_dir)
        self.analyzer = ScreenshotAnalyzer()
        
        # Context settings
        self.auto_capture_interval = 30.0  # seconds
        self.auto_capture_enabled = False
        self._auto_capture_task: Optional[asyncio.Task] = None
        
        logger.info("Screenshot context system initialized")
    
    async def get_current_context(self, force_new: bool = False) -> Dict[str, Any]:
        """
        Get current visual context from screenshot.
        
        Args:
            force_new: Force capture of new screenshot
            
        Returns:
            Current visual context information
        """
        # Get latest screenshot or capture new one
        latest = self.capture.get_latest_screenshot()
        
        if force_new or latest is None or (time.time() - latest.timestamp) > 10.0:
            logger.debug("Capturing new screenshot for context")
            latest = await self.capture.capture_screenshot()
        
        if latest is None:
            return {"error": "Failed to capture screenshot", "context_available": False}
        
        # Analyze screenshot
        analysis = await self.analyzer.analyze_screenshot(latest)
        
        # Detect changes
        changes = await self.analyzer.detect_changes(latest)
        
        context = {
            "context_available": True,
            "screenshot": analysis,
            "changes": changes,
            "timestamp": latest.timestamp,
            "capture_method": latest.capture_method
        }
        
        return context
    
    async def start_auto_capture(self, interval: Optional[float] = None):
        """
        Start automatic screenshot capture at regular intervals.
        
        Args:
            interval: Capture interval in seconds
        """
        if self.auto_capture_enabled:
            logger.warning("Auto capture already enabled")
            return
        
        if interval:
            self.auto_capture_interval = interval
        
        self.auto_capture_enabled = True
        self._auto_capture_task = asyncio.create_task(self._auto_capture_loop())
        
        logger.info(f"Auto capture started (interval: {self.auto_capture_interval}s)")
    
    async def stop_auto_capture(self):
        """Stop automatic screenshot capture"""
        self.auto_capture_enabled = False
        
        if self._auto_capture_task:
            self._auto_capture_task.cancel()
            try:
                await self._auto_capture_task
            except asyncio.CancelledError:
                pass
            self._auto_capture_task = None
        
        logger.info("Auto capture stopped")
    
    async def _auto_capture_loop(self):
        """Background loop for automatic screenshot capture"""
        try:
            while self.auto_capture_enabled:
                await self.capture.capture_screenshot()
                await asyncio.sleep(self.auto_capture_interval)
        except asyncio.CancelledError:
            logger.debug("Auto capture loop cancelled")
        except Exception as e:
            logger.error(f"Error in auto capture loop: {e}")
    
    async def capture_task_context(self, task_description: str) -> Dict[str, Any]:
        """
        Capture screenshot context for a specific task.
        
        Args:
            task_description: Description of the task
            
        Returns:
            Task-specific visual context
        """
        logger.info(f"Capturing context for task: {task_description}")
        
        # Capture screenshot
        screenshot = await self.capture.capture_screenshot()
        
        if screenshot is None:
            return {
                "task": task_description,
                "context_available": False,
                "error": "Screenshot capture failed"
            }
        
        # Analyze
        analysis = await self.analyzer.analyze_screenshot(screenshot)
        
        return {
            "task": task_description,
            "context_available": True,
            "screenshot": analysis,
            "timestamp": screenshot.timestamp
        }
    
    def cleanup(self):
        """Cleanup all screenshot resources"""
        asyncio.create_task(self.stop_auto_capture())
        self.capture.cleanup_all_screenshots()
        logger.info("Screenshot context cleanup complete")