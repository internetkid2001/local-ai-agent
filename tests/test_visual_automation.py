#!/usr/bin/env python3
"""
Visual Automation Test Suite

Tests visual automation capabilities including screenshot analysis,
element detection, and automated interaction.

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

from src.agent.automation.visual_automation import VisualAutomationEngine, VisualElement, ScreenAnalysis

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class VisualAutomationTester:
    """Test suite for visual automation"""
    
    def __init__(self):
        self.engine = VisualAutomationEngine()
        self.results = {}
        self.temp_dir = tempfile.mkdtemp()
        
    async def test_screenshot_capture(self):
        """Test screenshot capture functionality"""
        logger.info("Testing screenshot capture...")
        
        try:
            screenshot_path = f"{self.temp_dir}/test_screenshot.png"
            
            # Take screenshot
            result_path = await self.engine.take_screenshot(screenshot_path)
            
            # Verify screenshot was created
            screenshot_exists = Path(screenshot_path).exists()
            file_size = Path(screenshot_path).stat().st_size if screenshot_exists else 0
            
            self.results["screenshot_capture"] = {
                "status": "success",
                "screenshot_created": screenshot_exists,
                "file_size": file_size,
                "path": result_path,
                "file_size_valid": file_size > 1000  # At least 1KB
            }
            
        except Exception as e:
            logger.error(f"Screenshot capture test failed: {e}")
            self.results["screenshot_capture"] = {
                "status": "failed",
                "error": str(e)
            }
    
    async def test_screen_analysis(self):
        """Test screen analysis functionality"""
        logger.info("Testing screen analysis...")
        
        try:
            # First take a screenshot
            screenshot_path = f"{self.temp_dir}/analysis_screenshot.png"
            await self.engine.take_screenshot(screenshot_path)
            
            # Analyze the screen
            analysis = await self.engine.analyze_screen(screenshot_path)
            
            # Verify analysis results
            self.results["screen_analysis"] = {
                "status": "success",
                "analysis_created": isinstance(analysis, ScreenAnalysis),
                "has_timestamp": analysis.timestamp > 0,
                "has_resolution": len(analysis.resolution) == 2,
                "elements_found": len(analysis.elements),
                "has_metadata": analysis.analysis_metadata is not None,
                "screenshot_path_correct": analysis.screenshot_path == screenshot_path
            }
            
            # Store analysis for other tests
            self.test_analysis = analysis
            
        except Exception as e:
            logger.error(f"Screen analysis test failed: {e}")
            self.results["screen_analysis"] = {
                "status": "failed",
                "error": str(e)
            }
    
    async def test_element_detection(self):
        """Test element detection capabilities"""
        logger.info("Testing element detection...")
        
        try:
            if not hasattr(self, 'test_analysis'):
                # Create a test analysis if it doesn't exist
                screenshot_path = f"{self.temp_dir}/element_test_screenshot.png"
                await self.engine.take_screenshot(screenshot_path)
                self.test_analysis = await self.engine.analyze_screen(screenshot_path)
            
            analysis = self.test_analysis
            
            # Count different element types
            element_types = {}
            for element in analysis.elements:
                element_types[element.element_type] = element_types.get(element.element_type, 0) + 1
            
            # Test element properties
            valid_elements = 0
            for element in analysis.elements:
                if (element.x >= 0 and element.y >= 0 and 
                    element.width > 0 and element.height > 0 and
                    element.confidence > 0):
                    valid_elements += 1
            
            self.results["element_detection"] = {
                "status": "success",
                "total_elements": len(analysis.elements),
                "valid_elements": valid_elements,
                "element_types": element_types,
                "text_elements": element_types.get("text", 0),
                "button_elements": element_types.get("button", 0),
                "input_elements": element_types.get("input", 0),
                "icon_elements": element_types.get("icon", 0),
                "all_elements_valid": valid_elements == len(analysis.elements)
            }
            
        except Exception as e:
            logger.error(f"Element detection test failed: {e}")
            self.results["element_detection"] = {
                "status": "failed",
                "error": str(e)
            }
    
    async def test_text_finding(self):
        """Test finding elements by text"""
        logger.info("Testing text finding...")
        
        try:
            if not hasattr(self, 'test_analysis'):
                screenshot_path = f"{self.temp_dir}/text_test_screenshot.png"
                await self.engine.take_screenshot(screenshot_path)
                self.test_analysis = await self.engine.analyze_screen(screenshot_path)
            
            screenshot_path = self.test_analysis.screenshot_path
            
            # Find text elements
            text_elements = [elem for elem in self.test_analysis.elements 
                           if elem.element_type == "text" and elem.text]
            
            found_elements = 0
            test_results = []
            
            # Test finding each text element
            for elem in text_elements[:3]:  # Test first 3 text elements
                if elem.text:
                    found_elem = await self.engine.find_element_by_text(elem.text, screenshot_path)
                    if found_elem:
                        found_elements += 1
                        test_results.append({
                            "text": elem.text,
                            "found": True,
                            "match": found_elem.text == elem.text
                        })
                    else:
                        test_results.append({
                            "text": elem.text,
                            "found": False
                        })
            
            # Test finding non-existent text
            not_found_elem = await self.engine.find_element_by_text("__NON_EXISTENT_TEXT__", screenshot_path)
            
            self.results["text_finding"] = {
                "status": "success",
                "text_elements_available": len(text_elements),
                "elements_tested": len(test_results),
                "elements_found": found_elements,
                "test_results": test_results,
                "non_existent_correctly_not_found": not_found_elem is None
            }
            
        except Exception as e:
            logger.error(f"Text finding test failed: {e}")
            self.results["text_finding"] = {
                "status": "failed",
                "error": str(e)
            }
    
    async def test_annotated_screenshot(self):
        """Test annotated screenshot creation"""
        logger.info("Testing annotated screenshot...")
        
        try:
            if not hasattr(self, 'test_analysis'):
                screenshot_path = f"{self.temp_dir}/annotated_test_screenshot.png"
                await self.engine.take_screenshot(screenshot_path)
                self.test_analysis = await self.engine.analyze_screen(screenshot_path)
            
            analysis = self.test_analysis
            annotated_path = f"{self.temp_dir}/annotated_output.png"
            
            # Create annotated screenshot
            result_path = await self.engine.create_annotated_screenshot(analysis, annotated_path)
            
            # Verify annotated screenshot was created
            annotated_exists = Path(annotated_path).exists()
            file_size = Path(annotated_path).stat().st_size if annotated_exists else 0
            
            self.results["annotated_screenshot"] = {
                "status": "success",
                "annotated_created": annotated_exists,
                "file_size": file_size,
                "path": result_path,
                "file_size_valid": file_size > 1000,
                "elements_to_annotate": len(analysis.elements)
            }
            
        except Exception as e:
            logger.error(f"Annotated screenshot test failed: {e}")
            self.results["annotated_screenshot"] = {
                "status": "failed",
                "error": str(e)
            }
    
    async def test_automation_script_generation(self):
        """Test automation script generation"""
        logger.info("Testing automation script generation...")
        
        try:
            if not hasattr(self, 'test_analysis'):
                screenshot_path = f"{self.temp_dir}/script_test_screenshot.png"
                await self.engine.take_screenshot(screenshot_path)
                self.test_analysis = await self.engine.analyze_screen(screenshot_path)
            
            analysis = self.test_analysis
            task_description = "Click on the login button and type username"
            
            # Generate automation script
            script = await self.engine.generate_automation_script(analysis, task_description)
            
            # Verify script properties
            script_lines = script.split('\n')
            has_imports = any("import" in line for line in script_lines)
            has_comments = any(line.strip().startswith('#') for line in script_lines)
            has_task_description = task_description in script or "Click" in script
            
            self.results["automation_script"] = {
                "status": "success",
                "script_generated": len(script) > 0,
                "script_lines": len(script_lines),
                "has_imports": has_imports,
                "has_comments": has_comments,
                "has_task_reference": has_task_description,
                "script_length": len(script)
            }
            
        except Exception as e:
            logger.error(f"Automation script generation test failed: {e}")
            self.results["automation_script"] = {
                "status": "failed",
                "error": str(e)
            }
    
    async def test_analysis_summary(self):
        """Test analysis summary functionality"""
        logger.info("Testing analysis summary...")
        
        try:
            # Get analysis summary
            summary = self.engine.get_analysis_summary()
            
            # Verify summary properties
            self.results["analysis_summary"] = {
                "status": "success",
                "summary_created": isinstance(summary, dict),
                "has_total_analyses": "total_analyses" in summary,
                "total_analyses": summary.get("total_analyses", 0),
                "has_element_types": "element_types_distribution" in summary,
                "summary_keys": list(summary.keys()) if isinstance(summary, dict) else []
            }
            
        except Exception as e:
            logger.error(f"Analysis summary test failed: {e}")
            self.results["analysis_summary"] = {
                "status": "failed",
                "error": str(e)
            }
    
    async def run_all_tests(self):
        """Run all visual automation tests"""
        logger.info("Starting visual automation tests...")
        
        # Run tests in order
        await self.test_screenshot_capture()
        await self.test_screen_analysis()
        await self.test_element_detection()
        await self.test_text_finding()
        await self.test_annotated_screenshot()
        await self.test_automation_script_generation()
        await self.test_analysis_summary()
        
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n" + "="*60)
        print("VISUAL AUTOMATION TEST REPORT")
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
            print("🎉 EXCELLENT: Visual automation is working perfectly!")
        elif success_rate > 75:
            print("✅ GOOD: Visual automation is mostly functional")
        elif success_rate > 50:
            print("⚠️  MODERATE: Visual automation needs improvement")
        else:
            print("❌ POOR: Visual automation requires significant work")
        
        print(f"\nTest files created in: {self.temp_dir}")
        print("="*60)


async def main():
    """Run visual automation tests"""
    tester = VisualAutomationTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())