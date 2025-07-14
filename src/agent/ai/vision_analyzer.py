#!/usr/bin/env python3
"""
AI-Powered Vision Analysis

Advanced screenshot analysis using LLM vision capabilities to understand
and describe screen content, identify patterns, and provide intelligent insights.

Author: Claude Code
Date: 2025-07-14
Phase: 4.6
"""

import asyncio
import base64
import json
import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from pathlib import Path
import time
from PIL import Image
import io

logger = logging.getLogger(__name__)


@dataclass
class ScreenContent:
    """Represents analyzed screen content"""
    description: str
    elements: List[Dict[str, Any]]
    context: str
    applications: List[str]
    actions_suggested: List[str]
    accessibility_info: Dict[str, Any]
    sentiment: str
    complexity_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "description": self.description,
            "elements": self.elements,
            "context": self.context,
            "applications": self.applications,
            "actions_suggested": self.actions_suggested,
            "accessibility_info": self.accessibility_info,
            "sentiment": self.sentiment,
            "complexity_score": self.complexity_score
        }


@dataclass
class VisionAnalysisResult:
    """Result of AI vision analysis"""
    timestamp: float
    image_path: str
    content: ScreenContent
    processing_time: float
    model_used: str
    confidence: float
    raw_response: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "timestamp": self.timestamp,
            "image_path": self.image_path,
            "content": self.content.to_dict(),
            "processing_time": self.processing_time,
            "model_used": self.model_used,
            "confidence": self.confidence,
            "raw_response": self.raw_response
        }


class VisionAnalyzer:
    """AI-powered vision analysis for screenshots"""
    
    def __init__(self, llm_manager=None):
        self.llm_manager = llm_manager
        self.analysis_history: List[VisionAnalysisResult] = []
        self.supported_formats = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff'}
        
    async def analyze_screenshot(self, image_path: str, prompt: Optional[str] = None) -> VisionAnalysisResult:
        """Analyze screenshot using AI vision capabilities"""
        start_time = time.time()
        
        try:
            # Load and validate image
            if not Path(image_path).exists():
                raise FileNotFoundError(f"Image not found: {image_path}")
            
            if not self._is_supported_format(image_path):
                raise ValueError(f"Unsupported image format: {image_path}")
            
            # Encode image to base64
            image_b64 = self._encode_image(image_path)
            
            # Create analysis prompt
            analysis_prompt = prompt or self._create_default_prompt()
            
            # Get AI analysis
            raw_response = await self._get_ai_analysis(image_b64, analysis_prompt)
            
            # Parse response into structured format
            content = self._parse_ai_response(raw_response)
            
            # Create result
            result = VisionAnalysisResult(
                timestamp=time.time(),
                image_path=image_path,
                content=content,
                processing_time=time.time() - start_time,
                model_used=self._get_model_name(),
                confidence=self._calculate_confidence(raw_response),
                raw_response=raw_response
            )
            
            # Store in history
            self.analysis_history.append(result)
            
            # Keep only last 20 analyses
            if len(self.analysis_history) > 20:
                self.analysis_history = self.analysis_history[-20:]
            
            logger.info(f"Vision analysis completed in {result.processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Vision analysis failed: {e}")
            raise
    
    def _is_supported_format(self, image_path: str) -> bool:
        """Check if image format is supported"""
        return Path(image_path).suffix.lower() in self.supported_formats
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64"""
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if too large (for API limits)
                if img.width > 1920 or img.height > 1080:
                    img.thumbnail((1920, 1080), Image.Resampling.LANCZOS)
                
                # Convert to base64
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                buffer.seek(0)
                
                return base64.b64encode(buffer.read()).decode('utf-8')
                
        except Exception as e:
            logger.error(f"Failed to encode image: {e}")
            raise
    
    def _create_default_prompt(self) -> str:
        """Create default analysis prompt"""
        return """
        Analyze this screenshot and provide a comprehensive analysis in the following JSON format:
        
        {
          "description": "A detailed description of what's shown in the screenshot",
          "elements": [
            {
              "type": "element_type",
              "description": "element description",
              "location": "approximate location",
              "importance": "high/medium/low"
            }
          ],
          "context": "The context or purpose of this screen/application",
          "applications": ["list", "of", "applications", "visible"],
          "actions_suggested": ["list", "of", "suggested", "actions"],
          "accessibility_info": {
            "screen_reader_friendly": true/false,
            "color_contrast": "good/poor",
            "text_size": "readable/small/large"
          },
          "sentiment": "positive/negative/neutral",
          "complexity_score": 0.0-1.0
        }
        
        Please provide a thorough analysis focusing on:
        1. What the user is seeing
        2. What applications/interfaces are visible
        3. What actions the user might want to take
        4. Any accessibility considerations
        5. Overall complexity and usability
        """
    
    async def _get_ai_analysis(self, image_b64: str, prompt: str) -> str:
        """Get AI analysis from LLM with vision capabilities"""
        try:
            if not self.llm_manager:
                # Fallback to simple analysis if no LLM available
                return self._create_fallback_analysis()
            
            # Create message with image
            message = {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_b64}"
                        }
                    }
                ]
            }
            
            # Get response from LLM
            response = await self.llm_manager.generate_response(
                messages=[message],
                model="gpt-4-vision-preview",  # Use vision-capable model
                max_tokens=2000,
                temperature=0.3
            )
            
            return response.content if response else self._create_fallback_analysis()
            
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return self._create_fallback_analysis()
    
    def _create_fallback_analysis(self) -> str:
        """Create fallback analysis when AI is not available"""
        return json.dumps({
            "description": "Screenshot analysis (AI vision not available)",
            "elements": [
                {
                    "type": "screen",
                    "description": "Desktop or application screenshot",
                    "location": "full screen",
                    "importance": "medium"
                }
            ],
            "context": "General desktop or application view",
            "applications": ["Unknown"],
            "actions_suggested": ["Take screenshot for analysis"],
            "accessibility_info": {
                "screen_reader_friendly": "unknown",
                "color_contrast": "unknown",
                "text_size": "unknown"
            },
            "sentiment": "neutral",
            "complexity_score": 0.5
        })
    
    def _parse_ai_response(self, response: str) -> ScreenContent:
        """Parse AI response into structured format"""
        try:
            # Try to extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)
            else:
                # Fallback parsing
                data = json.loads(response)
            
            return ScreenContent(
                description=data.get("description", "No description available"),
                elements=data.get("elements", []),
                context=data.get("context", "Unknown context"),
                applications=data.get("applications", []),
                actions_suggested=data.get("actions_suggested", []),
                accessibility_info=data.get("accessibility_info", {}),
                sentiment=data.get("sentiment", "neutral"),
                complexity_score=float(data.get("complexity_score", 0.5))
            )
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse AI response: {e}")
            
            # Create fallback content
            return ScreenContent(
                description=response[:200] + "..." if len(response) > 200 else response,
                elements=[],
                context="Unknown",
                applications=[],
                actions_suggested=[],
                accessibility_info={},
                sentiment="neutral",
                complexity_score=0.5
            )
    
    def _get_model_name(self) -> str:
        """Get the name of the model used"""
        if self.llm_manager:
            return getattr(self.llm_manager, 'current_model', 'unknown')
        return "fallback"
    
    def _calculate_confidence(self, response: str) -> float:
        """Calculate confidence score based on response quality"""
        if not response:
            return 0.0
        
        # Simple heuristic based on response length and JSON validity
        try:
            json.loads(response)
            json_valid = True
        except:
            json_valid = False
        
        base_score = 0.6 if json_valid else 0.3
        length_bonus = min(len(response) / 1000, 0.3)  # Up to 0.3 bonus for longer responses
        
        return min(base_score + length_bonus, 1.0)
    
    async def compare_screenshots(self, image1_path: str, image2_path: str) -> Dict[str, Any]:
        """Compare two screenshots to identify differences"""
        try:
            # Analyze both images
            result1 = await self.analyze_screenshot(image1_path)
            result2 = await self.analyze_screenshot(image2_path)
            
            # Create comparison prompt
            comparison_prompt = f"""
            Compare these two screenshots and identify:
            1. What changed between them
            2. What stayed the same
            3. What actions might have caused the changes
            4. Which screenshot shows a better user experience
            
            Screenshot 1 Analysis: {result1.content.description}
            Screenshot 2 Analysis: {result2.content.description}
            
            Provide a detailed comparison in JSON format.
            """
            
            # Get comparison from AI
            image1_b64 = self._encode_image(image1_path)
            image2_b64 = self._encode_image(image2_path)
            
            comparison_response = await self._get_comparison_analysis(
                image1_b64, image2_b64, comparison_prompt
            )
            
            return {
                "comparison": comparison_response,
                "image1_analysis": result1.to_dict(),
                "image2_analysis": result2.to_dict(),
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Screenshot comparison failed: {e}")
            return {
                "error": str(e),
                "timestamp": time.time()
            }
    
    async def _get_comparison_analysis(self, image1_b64: str, image2_b64: str, prompt: str) -> str:
        """Get AI comparison analysis"""
        try:
            if not self.llm_manager:
                return "Comparison analysis not available (AI vision not available)"
            
            # Create message with both images
            message = {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image1_b64}"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image2_b64}"}}
                ]
            }
            
            response = await self.llm_manager.generate_response(
                messages=[message],
                model="gpt-4-vision-preview",
                max_tokens=1500,
                temperature=0.3
            )
            
            return response.content if response else "Comparison analysis failed"
            
        except Exception as e:
            logger.error(f"Comparison analysis failed: {e}")
            return f"Comparison analysis failed: {str(e)}"
    
    async def generate_automation_suggestions(self, image_path: str, goal: str) -> Dict[str, Any]:
        """Generate automation suggestions based on screenshot and goal"""
        try:
            # Analyze screenshot
            result = await self.analyze_screenshot(image_path)
            
            # Create automation prompt
            automation_prompt = f"""
            Based on this screenshot and the user's goal: "{goal}"
            
            Provide automation suggestions in JSON format:
            {{
              "steps": [
                {{
                  "action": "click|type|key|wait",
                  "target": "description of element to interact with",
                  "value": "text to type or key to press",
                  "coordinates": [x, y],
                  "confidence": 0.0-1.0
                }}
              ],
              "script": "Python automation script using pyautogui",
              "warnings": ["list of potential issues"],
              "success_probability": 0.0-1.0
            }}
            
            Screenshot analysis: {result.content.description}
            """
            
            # Get automation suggestions
            image_b64 = self._encode_image(image_path)
            automation_response = await self._get_ai_analysis(image_b64, automation_prompt)
            
            return {
                "suggestions": automation_response,
                "screenshot_analysis": result.to_dict(),
                "goal": goal,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Automation suggestion generation failed: {e}")
            return {
                "error": str(e),
                "timestamp": time.time()
            }
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get summary of analysis history"""
        if not self.analysis_history:
            return {"total_analyses": 0}
        
        return {
            "total_analyses": len(self.analysis_history),
            "average_processing_time": sum(r.processing_time for r in self.analysis_history) / len(self.analysis_history),
            "average_confidence": sum(r.confidence for r in self.analysis_history) / len(self.analysis_history),
            "models_used": list(set(r.model_used for r in self.analysis_history)),
            "sentiment_distribution": self._get_sentiment_distribution(),
            "complexity_stats": self._get_complexity_stats(),
            "latest_analysis": self.analysis_history[-1].to_dict() if self.analysis_history else None
        }
    
    def _get_sentiment_distribution(self) -> Dict[str, int]:
        """Get distribution of sentiment scores"""
        sentiments = {}
        for result in self.analysis_history:
            sentiment = result.content.sentiment
            sentiments[sentiment] = sentiments.get(sentiment, 0) + 1
        return sentiments
    
    def _get_complexity_stats(self) -> Dict[str, float]:
        """Get complexity statistics"""
        if not self.analysis_history:
            return {}
        
        complexity_scores = [r.content.complexity_score for r in self.analysis_history]
        return {
            "average": sum(complexity_scores) / len(complexity_scores),
            "min": min(complexity_scores),
            "max": max(complexity_scores),
            "std": self._calculate_std(complexity_scores)
        }
    
    def _calculate_std(self, values: List[float]) -> float:
        """Calculate standard deviation"""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5
    
    async def batch_analyze(self, image_paths: List[str]) -> List[VisionAnalysisResult]:
        """Analyze multiple screenshots in batch"""
        results = []
        
        for image_path in image_paths:
            try:
                result = await self.analyze_screenshot(image_path)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to analyze {image_path}: {e}")
                # Continue with other images
        
        return results
    
    async def create_analysis_report(self, results: List[VisionAnalysisResult]) -> str:
        """Create comprehensive analysis report"""
        if not results:
            return "No analysis results to report"
        
        report_lines = [
            "# Vision Analysis Report",
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Screenshots Analyzed: {len(results)}",
            "",
            "## Summary",
        ]
        
        # Add summary statistics
        avg_confidence = sum(r.confidence for r in results) / len(results)
        avg_complexity = sum(r.content.complexity_score for r in results) / len(results)
        
        report_lines.extend([
            f"- Average Confidence: {avg_confidence:.2f}",
            f"- Average Complexity: {avg_complexity:.2f}",
            f"- Processing Time: {sum(r.processing_time for r in results):.2f}s total",
            "",
            "## Individual Analyses",
        ])
        
        # Add individual results
        for i, result in enumerate(results, 1):
            report_lines.extend([
                f"### Analysis {i}",
                f"- Image: {result.image_path}",
                f"- Description: {result.content.description}",
                f"- Context: {result.content.context}",
                f"- Confidence: {result.confidence:.2f}",
                f"- Applications: {', '.join(result.content.applications)}",
                ""
            ])
        
        return "\n".join(report_lines)


# Global instance
vision_analyzer = VisionAnalyzer()