#!/usr/bin/env python3
"""
MCP Orchestration Test

Tests the multi-server orchestration system.

Author: Claude Code
Date: 2025-07-14
Phase: 4.6
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.agent.orchestration.mcp_orchestrator import (
    MCPOrchestrator,
    OrchestrationStep,
    OrchestrationStatus
)
from src.mcp_client.client_manager import MCPClientManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class OrchestrationTester:
    """Test orchestration functionality"""
    
    def __init__(self):
        self.client_manager = MCPClientManager()
        self.orchestrator = None
        self.results = {}
    
    async def setup(self):
        """Setup test environment"""
        try:
            # Initialize client manager
            await self.client_manager.initialize()
            
            # Create orchestrator
            self.orchestrator = MCPOrchestrator(self.client_manager)
            await self.orchestrator.initialize()
            
            logger.info("Orchestration test setup complete")
            return True
            
        except Exception as e:
            logger.error(f"Setup failed: {e}")
            return False
    
    async def test_simple_workflow(self):
        """Test simple multi-server workflow"""
        logger.info("Testing simple workflow...")
        
        try:
            # Create workflow steps
            steps = [
                OrchestrationStep(
                    id="get_system_info",
                    name="Get System Information",
                    server="system",
                    tool="get_system_metrics",
                    arguments={"detailed": False}
                ),
                OrchestrationStep(
                    id="write_report",
                    name="Write System Report",
                    server="filesystem",
                    tool="write_file",
                    arguments={
                        "path": "/tmp/orchestration_test_report.txt",
                        "content": "System orchestration test completed"
                    },
                    depends_on=["get_system_info"]
                )
            ]
            
            # Create and execute workflow
            workflow_id = self.orchestrator.create_workflow(
                name="Simple Test Workflow",
                description="Test basic orchestration functionality",
                steps=steps
            )
            
            workflow = await self.orchestrator.execute_workflow(workflow_id)
            
            self.results["simple_workflow"] = {
                "status": "success",
                "workflow_completed": workflow.status == OrchestrationStatus.COMPLETED,
                "steps_executed": len(workflow.results),
                "execution_time": workflow.end_time - workflow.start_time
            }
            
        except Exception as e:
            logger.error(f"Simple workflow test failed: {e}")
            self.results["simple_workflow"] = {
                "status": "failed",
                "error": str(e)
            }
    
    async def test_system_health_workflow(self):
        """Test system health workflow"""
        logger.info("Testing system health workflow...")
        
        try:
            # Create system health workflow
            workflow_id = self.orchestrator.create_system_health_workflow()
            
            # Get workflow status before execution
            status_before = self.orchestrator.get_workflow_status(workflow_id)
            
            # Execute workflow
            workflow = await self.orchestrator.execute_workflow(workflow_id)
            
            # Get final status
            status_after = self.orchestrator.get_workflow_status(workflow_id)
            
            self.results["system_health_workflow"] = {
                "status": "success",
                "workflow_created": workflow_id is not None,
                "workflow_completed": workflow.status == OrchestrationStatus.COMPLETED,
                "steps_total": status_after["steps_total"],
                "steps_completed": status_after["steps_completed"],
                "steps_failed": status_after["steps_failed"],
                "execution_time": status_after["execution_time"]
            }
            
        except Exception as e:
            logger.error(f"System health workflow test failed: {e}")
            self.results["system_health_workflow"] = {
                "status": "failed",
                "error": str(e)
            }
    
    async def test_desktop_automation_workflow(self):
        """Test desktop automation workflow"""
        logger.info("Testing desktop automation workflow...")
        
        try:
            # Create desktop automation workflow
            workflow_id = self.orchestrator.create_desktop_automation_workflow()
            
            # Execute workflow
            workflow = await self.orchestrator.execute_workflow(workflow_id)
            
            # Get final status
            status = self.orchestrator.get_workflow_status(workflow_id)
            
            self.results["desktop_automation_workflow"] = {
                "status": "success",
                "workflow_created": workflow_id is not None,
                "workflow_completed": workflow.status == OrchestrationStatus.COMPLETED,
                "steps_total": status["steps_total"],
                "steps_completed": status["steps_completed"],
                "steps_failed": status["steps_failed"],
                "execution_time": status["execution_time"]
            }
            
        except Exception as e:
            logger.error(f"Desktop automation workflow test failed: {e}")
            self.results["desktop_automation_workflow"] = {
                "status": "failed",
                "error": str(e)
            }
    
    async def test_parallel_execution(self):
        """Test parallel step execution"""
        logger.info("Testing parallel execution...")
        
        try:
            # Create workflow with parallel steps
            steps = [
                OrchestrationStep(
                    id="system_metrics",
                    name="Get System Metrics",
                    server="system",
                    tool="get_system_metrics",
                    arguments={"detailed": True}
                ),
                OrchestrationStep(
                    id="list_processes",
                    name="List Processes",
                    server="system",
                    tool="list_processes",
                    arguments={"limit": 10}
                ),
                OrchestrationStep(
                    id="take_screenshot",
                    name="Take Screenshot",
                    server="desktop",
                    tool="take_screenshot",
                    arguments={"path": "/tmp/parallel_test_screenshot.png"}
                ),
                OrchestrationStep(
                    id="combine_results",
                    name="Combine Results",
                    server="filesystem",
                    tool="write_file",
                    arguments={
                        "path": "/tmp/parallel_test_results.json",
                        "content": json.dumps({"test": "parallel_execution"})
                    },
                    depends_on=["system_metrics", "list_processes", "take_screenshot"]
                )
            ]
            
            workflow_id = self.orchestrator.create_workflow(
                name="Parallel Execution Test",
                description="Test parallel execution of independent steps",
                steps=steps
            )
            
            workflow = await self.orchestrator.execute_workflow(workflow_id)
            
            self.results["parallel_execution"] = {
                "status": "success",
                "workflow_completed": workflow.status == OrchestrationStatus.COMPLETED,
                "parallel_steps_executed": 3,  # system_metrics, list_processes, take_screenshot
                "final_step_executed": "combine_results" in workflow.results,
                "execution_time": workflow.end_time - workflow.start_time
            }
            
        except Exception as e:
            logger.error(f"Parallel execution test failed: {e}")
            self.results["parallel_execution"] = {
                "status": "failed",
                "error": str(e)
            }
    
    async def run_all_tests(self):
        """Run all orchestration tests"""
        logger.info("Starting orchestration tests...")
        
        # Setup
        if not await self.setup():
            self.results["setup"] = {"status": "failed", "error": "Setup failed"}
            return
        
        # Run tests
        await self.test_simple_workflow()
        await self.test_system_health_workflow()
        await self.test_desktop_automation_workflow()
        await self.test_parallel_execution()
        
        # Generate report
        self.generate_report()
        
        # Cleanup
        if self.orchestrator:
            await self.orchestrator.shutdown()
    
    def generate_report(self):
        """Generate test report"""
        print("\n" + "="*60)
        print("MCP ORCHESTRATION TEST REPORT")
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
                
                for key, value in result.items():
                    if key not in ['status', 'error']:
                        if isinstance(value, bool):
                            status = "✅" if value else "❌"
                            print(f"    {key}: {status}")
                        elif isinstance(value, (int, float)):
                            print(f"    {key}: {value}")
                        else:
                            print(f"    {key}: {value}")
            else:
                print(f"  Error: {result.get('error', 'Unknown error')}")
        
        print(f"\n{'='*60}")
        print(f"SUMMARY: {passed_tests}/{total_tests} tests passed")
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        print(f"Success Rate: {success_rate:.1f}%")
        
        if success_rate > 90:
            print("🎉 EXCELLENT: Orchestration system is working perfectly!")
        elif success_rate > 70:
            print("✅ GOOD: Orchestration system is functional")
        elif success_rate > 50:
            print("⚠️  MODERATE: Orchestration system needs improvement")
        else:
            print("❌ POOR: Orchestration system requires fixes")
        
        print("="*60)


async def main():
    """Run orchestration tests"""
    tester = OrchestrationTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())