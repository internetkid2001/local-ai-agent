#!/usr/bin/env python3
"""
Visual UI Automation

Advanced visual automation capabilities including screenshot analysis,
image recognition, and AI-powered UI interaction.

Author: Claude Code
Date: 2025-07-14
Phase: 4.6
"""

import asyncio
import cv2
import numpy as np
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from pathlib import Path
import base64
import json
import time
from PIL import Image, ImageDraw, ImageFont
import tempfile

logger = logging.getLogger(__name__)


@dataclass
class VisualElement:
    """Represents a visual element found in screenshot"""
    x: int
    y: int
    width: int
    height: int
    confidence: float
    label: str
    element_type: str  # button, text, input, etc.
    text: Optional[str] = None
    attributes: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {}
    
    @property
    def center(self) -> Tuple[int, int]:
        """Get center coordinates of element"""
        return (self.x + self.width // 2, self.y + self.height // 2)
    
    @property
    def bounding_box(self) -> Tuple[int, int, int, int]:
        """Get bounding box (x, y, x2, y2)"""
        return (self.x, self.y, self.x + self.width, self.y + self.height)


@dataclass
class ScreenAnalysis:
    """Results of screen analysis"""
    timestamp: float
    resolution: Tuple[int, int]
    elements: List[VisualElement]
    screenshot_path: str
    analysis_metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.analysis_metadata is None:
            self.analysis_metadata = {}


class VisualAutomationEngine:
    """Visual automation engine for UI interaction"""
    
    def __init__(self):
        self.template_cache: Dict[str, np.ndarray] = {}
        self.analysis_history: List[ScreenAnalysis] = []
        self.confidence_threshold = 0.7
        
    async def take_screenshot(self, output_path: str) -> str:
        """Take screenshot and save to file"""
        try:
            # Use system screenshot tool
            import subprocess
            subprocess.run([
                "gnome-screenshot", "--file", output_path
            ], check=True)
            
            logger.info(f"Screenshot saved to: {output_path}")
            return output_path
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Screenshot failed: {e}")
            raise
        except FileNotFoundError:
            # Fallback to other screenshot methods
            logger.warning("gnome-screenshot not found, trying alternative methods")
            return await self._fallback_screenshot(output_path)
    
    async def _fallback_screenshot(self, output_path: str) -> str:
        """Fallback screenshot method using Python"""
        try:
            import pyautogui
            screenshot = pyautogui.screenshot()
            screenshot.save(output_path)
            return output_path
        except ImportError:
            logger.error("pyautogui not available for screenshot")
            raise RuntimeError("No screenshot method available")
    
    async def analyze_screen(self, screenshot_path: str) -> ScreenAnalysis:
        """Analyze screenshot for UI elements"""
        try:
            # Load screenshot
            image = cv2.imread(screenshot_path)
            if image is None:
                raise ValueError(f"Could not load screenshot: {screenshot_path}")
            
            height, width = image.shape[:2]
            
            # Perform different types of analysis
            elements = []
            
            # 1. Text detection
            text_elements = await self._detect_text(image)
            elements.extend(text_elements)
            
            # 2. Button detection
            button_elements = await self._detect_buttons(image)
            elements.extend(button_elements)
            
            # 3. Input field detection
            input_elements = await self._detect_input_fields(image)
            elements.extend(input_elements)
            
            # 4. Icon detection
            icon_elements = await self._detect_icons(image)
            elements.extend(icon_elements)
            
            # Create analysis result
            analysis = ScreenAnalysis(
                timestamp=time.time(),
                resolution=(width, height),
                elements=elements,
                screenshot_path=screenshot_path,
                analysis_metadata={
                    "total_elements": len(elements),
                    "text_elements": len(text_elements),
                    "button_elements": len(button_elements),
                    "input_elements": len(input_elements),
                    "icon_elements": len(icon_elements)
                }
            )
            
            # Store in history
            self.analysis_history.append(analysis)
            
            # Keep only last 10 analyses
            if len(self.analysis_history) > 10:
                self.analysis_history = self.analysis_history[-10:]
            
            logger.info(f"Screen analysis complete: {len(elements)} elements found")
            return analysis
            
        except Exception as e:
            logger.error(f"Screen analysis failed: {e}")
            raise
    
    async def _detect_text(self, image: np.ndarray) -> List[VisualElement]:
        """Detect text elements in image"""
        try:
            # Use OCR for text detection
            import pytesseract
            
            # Get text data with bounding boxes
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            
            elements = []
            for i, text in enumerate(data['text']):
                if text.strip():  # Skip empty text
                    confidence = float(data['conf'][i]) / 100.0
                    if confidence > self.confidence_threshold:
                        elements.append(VisualElement(
                            x=data['left'][i],
                            y=data['top'][i],
                            width=data['width'][i],
                            height=data['height'][i],
                            confidence=confidence,
                            label=text.strip(),
                            element_type="text",
                            text=text.strip()
                        ))
            
            return elements
            
        except ImportError:
            logger.warning("pytesseract not available for text detection")
            return []
        except Exception as e:
            logger.error(f"Text detection failed: {e}")
            return []
    
    async def _detect_buttons(self, image: np.ndarray) -> List[VisualElement]:
        """Detect button elements using template matching"""
        try:
            # Convert to grayscale for template matching
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Simple button detection using edge detection
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            elements = []
            for contour in contours:
                # Filter contours that might be buttons
                x, y, w, h = cv2.boundingRect(contour)
                area = cv2.contourArea(contour)
                
                # Basic button heuristics
                if (50 < w < 200 and 20 < h < 60 and area > 1000):
                    elements.append(VisualElement(
                        x=x,
                        y=y,
                        width=w,
                        height=h,
                        confidence=0.6,  # Lower confidence for heuristic detection
                        label=f"button_{len(elements)}",
                        element_type="button"
                    ))
            
            return elements
            
        except Exception as e:
            logger.error(f"Button detection failed: {e}")
            return []
    
    async def _detect_input_fields(self, image: np.ndarray) -> List[VisualElement]:
        """Detect input field elements"""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Detect rectangular regions that might be input fields
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            elements = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                area = cv2.contourArea(contour)
                
                # Input field heuristics (typically rectangular, longer than tall)
                if (w > 100 and h > 20 and h < 50 and w > 2 * h and area > 2000):
                    elements.append(VisualElement(
                        x=x,
                        y=y,
                        width=w,
                        height=h,
                        confidence=0.5,
                        label=f"input_{len(elements)}",
                        element_type="input"
                    ))
            
            return elements
            
        except Exception as e:
            logger.error(f"Input field detection failed: {e}")
            return []
    
    async def _detect_icons(self, image: np.ndarray) -> List[VisualElement]:
        """Detect icon elements"""
        try:
            # Simple icon detection using small square regions
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            elements = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                area = cv2.contourArea(contour)
                
                # Icon heuristics (typically small and square-ish)
                if (10 < w < 64 and 10 < h < 64 and abs(w - h) < 10 and area > 100):
                    elements.append(VisualElement(
                        x=x,
                        y=y,
                        width=w,
                        height=h,
                        confidence=0.4,
                        label=f"icon_{len(elements)}",
                        element_type="icon"
                    ))
            
            return elements
            
        except Exception as e:
            logger.error(f"Icon detection failed: {e}")
            return []
    
    async def find_element_by_text(self, text: str, screenshot_path: str) -> Optional[VisualElement]:
        """Find element by text content"""
        analysis = await self.analyze_screen(screenshot_path)
        
        for element in analysis.elements:
            if element.text and text.lower() in element.text.lower():
                return element
        
        return None
    
    async def find_element_by_type(self, element_type: str, screenshot_path: str) -> List[VisualElement]:
        """Find elements by type"""
        analysis = await self.analyze_screen(screenshot_path)
        
        return [elem for elem in analysis.elements if elem.element_type == element_type]
    
    async def create_annotated_screenshot(self, analysis: ScreenAnalysis, output_path: str) -> str:
        """Create annotated screenshot with detected elements"""
        try:
            # Load original screenshot
            image = Image.open(analysis.screenshot_path)
            draw = ImageDraw.Draw(image)
            
            # Try to use a font (fallback to default if not available)
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
            except:
                font = ImageFont.load_default()
            
            # Draw bounding boxes and labels for each element
            colors = {
                "text": "red",
                "button": "blue", 
                "input": "green",
                "icon": "orange"
            }
            
            for element in analysis.elements:
                color = colors.get(element.element_type, "purple")
                
                # Draw bounding box
                x, y, x2, y2 = element.bounding_box
                draw.rectangle([x, y, x2, y2], outline=color, width=2)
                
                # Draw label
                label = f"{element.element_type}:{element.label}" if element.label else element.element_type
                text_bbox = draw.textbbox((0, 0), label, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                
                # Background for text
                draw.rectangle([x, y-text_height-2, x+text_width+4, y], fill=color)
                draw.text((x+2, y-text_height-1), label, fill="white", font=font)
            
            # Save annotated image
            image.save(output_path)
            logger.info(f"Annotated screenshot saved to: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to create annotated screenshot: {e}")
            raise
    
    async def generate_automation_script(self, analysis: ScreenAnalysis, task_description: str) -> str:
        """Generate automation script based on screen analysis"""
        script_lines = [
            "# Generated UI Automation Script",
            f"# Task: {task_description}",
            f"# Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"# Screen resolution: {analysis.resolution}",
            f"# Elements found: {len(analysis.elements)}",
            "",
            "import time",
            "import pyautogui",
            "",
            "# Automation steps:",
        ]
        
        # Group elements by type
        buttons = [e for e in analysis.elements if e.element_type == "button"]
        inputs = [e for e in analysis.elements if e.element_type == "input"]
        
        # Generate basic interaction patterns
        if "click" in task_description.lower() and buttons:
            button = buttons[0]  # Use first button found
            script_lines.extend([
                f"# Click button at {button.center}",
                f"pyautogui.click({button.center[0]}, {button.center[1]})",
                "time.sleep(0.5)",
            ])
        
        if "type" in task_description.lower() and inputs:
            input_field = inputs[0]  # Use first input found
            script_lines.extend([
                f"# Click input field at {input_field.center}",
                f"pyautogui.click({input_field.center[0]}, {input_field.center[1]})",
                "time.sleep(0.2)",
                "# Type text (replace with actual text)",
                "pyautogui.typewrite('your text here')",
                "time.sleep(0.5)",
            ])
        
        script_lines.extend([
            "",
            "print('Automation script completed')"
        ])
        
        return "\n".join(script_lines)
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get summary of analysis history"""
        if not self.analysis_history:
            return {"total_analyses": 0}
        
        total_elements = sum(len(analysis.elements) for analysis in self.analysis_history)
        element_types = {}
        
        for analysis in self.analysis_history:
            for element in analysis.elements:
                element_types[element.element_type] = element_types.get(element.element_type, 0) + 1
        
        return {
            "total_analyses": len(self.analysis_history),
            "total_elements_found": total_elements,
            "average_elements_per_screen": total_elements / len(self.analysis_history),
            "element_types_distribution": element_types,
            "latest_analysis": {
                "timestamp": self.analysis_history[-1].timestamp,
                "resolution": self.analysis_history[-1].resolution,
                "elements_count": len(self.analysis_history[-1].elements)
            } if self.analysis_history else None
        }


# Global instance
visual_automation_engine = VisualAutomationEngine()