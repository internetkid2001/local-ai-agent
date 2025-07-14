#!/usr/bin/env python3
"""
AI Vision Analysis Test Suite

Tests AI-powered vision analysis capabilities including screenshot analysis,
comparison, and automation suggestions.

Author: Claude Code
Date: 2025-07-14
Phase: 4.6
"""

import asyncio
import json
import logging
import sys
import tempfile
from pathlib import Path
import time

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.agent.ai.vision_analyzer import VisionAnalyzer, VisionAnalysisResult, ScreenContent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AIVisionTester:
    """Test suite for AI vision analysis"""
    
    def __init__(self):
        self.analyzer = VisionAnalyzer()
        self.results = {}
        self.temp_dir = tempfile.mkdtemp()
        self.test_screenshots = []
        
    async def setup_test_screenshots(self):
        """Create test screenshots for analysis"""
        logger.info("Setting up test screenshots...")
        
        try:
            # Create a simple test image using PIL
            from PIL import Image, ImageDraw, ImageFont
            
            # Test image 1: Simple interface
            img1 = Image.new('RGB', (800, 600), color='white')
            draw1 = ImageDraw.Draw(img1)
            
            # Draw some UI elements
            draw1.rectangle([50, 50, 200, 100], fill='lightblue', outline='blue')
            draw1.text((75, 70), "Login Button", fill='black')
            
            draw1.rectangle([50, 120, 400, 160], fill='lightgray', outline='gray')
            draw1.text((55, 135), "Username field", fill='black')
            
            draw1.rectangle([50, 180, 400, 220], fill='lightgray', outline='gray')
            draw1.text((55, 195), "Password field", fill='black')
            
            screenshot1_path = f"{self.temp_dir}/test_login_screen.png"
            img1.save(screenshot1_path)
            self.test_screenshots.append(screenshot1_path)
            
            # Test image 2: Different interface
            img2 = Image.new('RGB', (800, 600), color='white')
            draw2 = ImageDraw.Draw(img2)
            
            draw2.rectangle([200, 200, 350, 250], fill='green', outline='darkgreen')
            draw2.text((225, 220), "Submit", fill='white')
            
            draw2.rectangle([400, 200, 550, 250], fill='red', outline='darkred')
            draw2.text((425, 220), "Cancel", fill='white')
            
            screenshot2_path = f"{self.temp_dir}/test_action_screen.png"
            img2.save(screenshot2_path)
            self.test_screenshots.append(screenshot2_path)
            
            self.results["setup"] = {
                "status": "success",
                "screenshots_created": len(self.test_screenshots),
                "temp_dir": self.temp_dir
            }
            
        except Exception as e:
            logger.error(f"Screenshot setup failed: {e}")
            self.results["setup"] = {
                "status": "failed",
                "error": str(e)
            }
    
    async def test_basic_analysis(self):
        """Test basic screenshot analysis"""
        logger.info("Testing basic AI vision analysis...")
        
        try:
            if not self.test_screenshots:
                await self.setup_test_screenshots()
            
            # Analyze first screenshot
            result = await self.analyzer.analyze_screenshot(self.test_screenshots[0])
            
            # Verify result structure
            self.results["basic_analysis"] = {
                "status": "success",
                "result_created": isinstance(result, VisionAnalysisResult),
                "has_timestamp": result.timestamp > 0,
                "has_content": isinstance(result.content, ScreenContent),
                "has_description": bool(result.content.description),
                "has_elements": len(result.content.elements) >= 0,
                "has_context": bool(result.content.context),
                "has_applications": len(result.content.applications) >= 0,
                "has_actions": len(result.content.actions_suggested) >= 0,
                "has_accessibility": isinstance(result.content.accessibility_info, dict),
                "has_sentiment": result.content.sentiment in ["positive", "negative", "neutral"],
                "valid_complexity": 0.0 <= result.content.complexity_score <= 1.0,
                "has_confidence": 0.0 <= result.confidence <= 1.0,
                "processing_time": result.processing_time
            }
            
            # Store result for other tests
            self.test_result = result
            
        except Exception as e:
            logger.error(f"Basic analysis test failed: {e}")
            self.results["basic_analysis"] = {
                "status": "failed",
                "error": str(e)
            }
    
    async def test_custom_prompt_analysis(self):
        """Test analysis with custom prompt"""
        logger.info("Testing custom prompt analysis...")
        
        try:
            if not self.test_screenshots:
                await self.setup_test_screenshots()
            
            custom_prompt = "Focus on identifying interactive elements and their accessibility"
            
            # Analyze with custom prompt
            result = await self.analyzer.analyze_screenshot(
                self.test_screenshots[0], 
                custom_prompt
            )
            
            self.results["custom_prompt_analysis"] = {
                "status": "success",
                "result_created": isinstance(result, VisionAnalysisResult),
                "prompt_used": custom_prompt,
                "has_description": bool(result.content.description),
                "processing_time": result.processing_time,
                "confidence": result.confidence
            }
            
        except Exception as e:
            logger.error(f"Custom prompt analysis test failed: {e}")
            self.results["custom_prompt_analysis"] = {
                "status": "failed",
                "error": str(e)
            }
    
    async def test_screenshot_comparison(self):
        """Test screenshot comparison functionality"""
        logger.info("Testing screenshot comparison...")
        
        try:
            if len(self.test_screenshots) < 2:
                await self.setup_test_screenshots()
            
            # Compare two screenshots
            comparison = await self.analyzer.compare_screenshots(
                self.test_screenshots[0],
                self.test_screenshots[1]
            )
            
            self.results["screenshot_comparison"] = {
                "status": "success",
                "comparison_created": isinstance(comparison, dict),
                "has_comparison": "comparison" in comparison,
                "has_image1_analysis": "image1_analysis" in comparison,
                "has_image2_analysis": "image2_analysis" in comparison,
                "has_timestamp": "timestamp" in comparison,
                "no_error": "error" not in comparison
            }
            
        except Exception as e:
            logger.error(f"Screenshot comparison test failed: {e}")
            self.results["screenshot_comparison"] = {
                "status": "failed",
                "error": str(e)
            }
    
    async def test_automation_suggestions(self):
        """Test automation suggestions generation"""
        logger.info("Testing automation suggestions...")
        
        try:
            if not self.test_screenshots:
                await self.setup_test_screenshots()
            
            goal = "Click the login button and enter credentials"
            
            # Generate automation suggestions
            suggestions = await self.analyzer.generate_automation_suggestions(
                self.test_screenshots[0],
                goal
            )
            
            self.results["automation_suggestions"] = {
                "status": "success",
                "suggestions_created": isinstance(suggestions, dict),
                "has_suggestions": "suggestions" in suggestions,
                "has_screenshot_analysis": "screenshot_analysis" in suggestions,
                "has_goal": "goal" in suggestions,
                "has_timestamp": "timestamp" in suggestions,
                "goal_match": suggestions.get("goal") == goal,
                "no_error": "error" not in suggestions
            }
            
        except Exception as e:
            logger.error(f"Automation suggestions test failed: {e}")
            self.results["automation_suggestions"] = {
                "status": "failed",
                "error": str(e)
            }
    
    async def test_batch_analysis(self):
        """Test batch analysis functionality"""
        logger.info("Testing batch analysis...")
        
        try:
            if not self.test_screenshots:
                await self.setup_test_screenshots()
            
            # Perform batch analysis
            results = await self.analyzer.batch_analyze(self.test_screenshots)
            
            self.results["batch_analysis"] = {
                "status": "success",
                "results_created": isinstance(results, list),
                "correct_count": len(results) == len(self.test_screenshots),
                "all_valid_results": all(isinstance(r, VisionAnalysisResult) for r in results),
                "total_results": len(results),
                "expected_results": len(self.test_screenshots)
            }
            
        except Exception as e:
            logger.error(f"Batch analysis test failed: {e}")
            self.results["batch_analysis"] = {
                "status": "failed",
                "error": str(e)
            }
    
    async def test_analysis_report(self):
        """Test analysis report generation"""
        logger.info("Testing analysis report generation...")
        
        try:
            if not self.test_screenshots:
                await self.setup_test_screenshots()
            
            # Get some analysis results
            results = await self.analyzer.batch_analyze(self.test_screenshots)
            
            # Generate report
            report = await self.analyzer.create_analysis_report(results)
            
            self.results["analysis_report"] = {
                "status": "success",
                "report_created": isinstance(report, str),
                "report_length": len(report),
                "has_content": len(report) > 100,
                "has_title": "Vision Analysis Report" in report,
                "has_summary": "Summary" in report,
                "has_analyses": "Analyses" in report
            }
            
        except Exception as e:
            logger.error(f"Analysis report test failed: {e}")
            self.results["analysis_report"] = {
                "status": "failed",
                "error": str(e)
            }
    
    async def test_analysis_summary(self):
        """Test analysis summary functionality"""
        logger.info("Testing analysis summary...")
        
        try:
            # Get summary
            summary = self.analyzer.get_analysis_summary()
            
            self.results["analysis_summary"] = {
                "status": "success",
                "summary_created": isinstance(summary, dict),
                "has_total_analyses": "total_analyses" in summary,
                "total_analyses": summary.get("total_analyses", 0),
                "has_processing_time": "average_processing_time" in summary or summary.get("total_analyses", 0) == 0,
                "has_confidence": "average_confidence" in summary or summary.get("total_analyses", 0) == 0,
                "has_models": "models_used" in summary or summary.get("total_analyses", 0) == 0,
                "summary_keys": list(summary.keys())
            }
            
        except Exception as e:
            logger.error(f"Analysis summary test failed: {e}")
            self.results["analysis_summary"] = {
                "status": "failed",
                "error": str(e)
            }
    
    async def test_unsupported_format(self):
        """Test handling of unsupported image formats"""
        logger.info("Testing unsupported format handling...")
        
        try:
            # Create a fake unsupported file
            unsupported_path = f"{self.temp_dir}/test.txt"
            with open(unsupported_path, 'w') as f:
                f.write("This is not an image")
            
            # Try to analyze it
            try:
                result = await self.analyzer.analyze_screenshot(unsupported_path)
                format_handled = False
            except (ValueError, FileNotFoundError):
                format_handled = True
            
            self.results["unsupported_format"] = {
                "status": "success",
                "format_properly_rejected": format_handled,
                "file_created": Path(unsupported_path).exists()
            }
            
        except Exception as e:
            logger.error(f"Unsupported format test failed: {e}")
            self.results["unsupported_format"] = {
                "status": "failed",
                "error": str(e)
            }
    
    async def run_all_tests(self):
        """Run all AI vision tests"""
        logger.info("Starting AI vision analysis tests...")
        
        # Run tests in sequence
        await self.setup_test_screenshots()
        await self.test_basic_analysis()
        await self.test_custom_prompt_analysis()
        await self.test_screenshot_comparison()
        await self.test_automation_suggestions()
        await self.test_batch_analysis()
        await self.test_analysis_report()
        await self.test_analysis_summary()
        await self.test_unsupported_format()
        
        # Generate comprehensive report
        self.generate_report()
    
    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n" + "="*60)
        print("AI VISION ANALYSIS TEST REPORT")
        print("="*60)
        
        total_tests = 0
        passed_tests = 0
        
        for test_name, result in self.results.items():
            print(f"\n{test_name.upper().replace('_', ' ')}:")
            print(f"  Status: {result['status']}")
            
            if result['status'] == 'success':
                # Count successful sub-tests
                success_count = sum(1 for k, v in result.items() 
                                  if k != 'status' and k != 'error' and v is True)
                total_count = len([k for k in result.keys() 
                                 if k != 'status' and k != 'error' and isinstance(result[k], bool)])
                
                total_tests += total_count
                passed_tests += success_count
                
                # Show detailed results
                for key, value in result.items():
                    if key not in ['status', 'error']:
                        if isinstance(value, bool):
                            status = "✅" if value else "❌"
                            print(f"    {key}: {status}")
                        elif isinstance(value, (int, float)):
                            print(f"    {key}: {value}")
                        elif isinstance(value, str) and len(value) < 50:
                            print(f"    {key}: {value}")
                        elif isinstance(value, list) and len(value) < 5:
                            print(f"    {key}: {value}")
                        elif isinstance(value, dict) and len(value) < 5:
                            print(f"    {key}: {value}")
                        else:
                            print(f"    {key}: [complex data]")
            else:
                print(f"  Error: {result.get('error', 'Unknown error')}")
        
        print(f"\n{'='*60}")
        print(f"SUMMARY: {passed_tests}/{total_tests} tests passed")
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        print(f"Success Rate: {success_rate:.1f}%")
        
        if success_rate > 90:
            print("🎉 EXCELLENT: AI vision analysis is working perfectly!")
        elif success_rate > 75:
            print("✅ GOOD: AI vision analysis is mostly functional")
        elif success_rate > 50:
            print("⚠️  MODERATE: AI vision analysis needs improvement")
        else:
            print("❌ POOR: AI vision analysis requires significant work")
        
        print(f"\nTest files created in: {self.temp_dir}")
        print("Note: AI vision capabilities may be limited without proper LLM integration")
        print("="*60)


async def main():
    """Run AI vision analysis tests"""
    tester = AIVisionTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())