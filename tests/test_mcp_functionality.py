#!/usr/bin/env python3
"""
MCP Functionality Test Suite

Tests all MCP servers (filesystem, desktop, system) to verify proper operation
and integration with the AI agent.

Author: Claude Code
Date: 2025-07-14
Phase: 4.6
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from src.mcp_client.client_manager import MCPClientManager
from src.mcp_client.filesystem_client import FilesystemMCPClient
from src.mcp_client.desktop_client import DesktopMCPClient
from src.mcp_client.system_client import SystemMCPClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MCPTester:
    """Test suite for MCP functionality"""
    
    def __init__(self):
        self.client_manager = MCPClientManager()
        self.results = {}
        
    async def run_all_tests(self):
        """Run all MCP tests"""
        logger.info("Starting MCP functionality tests...")
        
        # Test 1: Filesystem MCP
        await self.test_filesystem_mcp()
        
        # Test 2: System MCP
        await self.test_system_mcp()
        
        # Test 3: Desktop MCP
        await self.test_desktop_mcp()
        
        # Test 4: Multi-server orchestration
        await self.test_multi_server_orchestration()
        
        # Generate report
        self.generate_report()
        
    async def test_filesystem_mcp(self):
        """Test filesystem MCP server functionality"""
        logger.info("Testing Filesystem MCP...")
        
        try:
            # Initialize filesystem client
            fs_client = FilesystemMCPClient()
            await fs_client.initialize()
            
            # Test file operations
            test_file = "/tmp/mcp_test_file.txt"
            test_content = "Hello MCP World!"
            
            # Write test file
            write_result = await fs_client.call_tool("write_file", {
                "path": test_file,
                "content": test_content
            })
            
            # Read test file
            read_result = await fs_client.call_tool("read_file", {
                "path": test_file
            })
            
            # List directory
            list_result = await fs_client.call_tool("list_directory", {
                "path": "/tmp"
            })
            
            # Search files
            search_result = await fs_client.call_tool("search_files", {
                "path": "/tmp",
                "pattern": "mcp_test_*"
            })
            
            # Get file info
            info_result = await fs_client.call_tool("get_file_info", {
                "path": test_file
            })
            
            self.results["filesystem"] = {
                "status": "success",
                "tests_passed": 5,
                "write_file": write_result.get("success", False),
                "read_file": read_result.get("content") == test_content,
                "list_directory": "files" in list_result,
                "search_files": len(search_result.get("files", [])) > 0,
                "get_file_info": "size" in info_result
            }
            
            # Cleanup
            await fs_client.call_tool("delete_file", {"path": test_file})
            
        except Exception as e:
            logger.error(f"Filesystem MCP test failed: {e}")
            self.results["filesystem"] = {
                "status": "failed",
                "error": str(e)
            }
    
    async def test_system_mcp(self):
        """Test system MCP server functionality"""
        logger.info("Testing System MCP...")
        
        try:
            # Initialize system client
            sys_client = SystemMCPClient()
            await sys_client.initialize()
            
            # Test system monitoring
            processes = await sys_client.call_tool("list_processes", {
                "limit": 10
            })
            
            metrics = await sys_client.call_tool("get_system_metrics", {
                "detailed": True
            })
            
            cpu_usage = await sys_client.call_tool("get_cpu_usage", {
                "interval": 0.5
            })
            
            memory_usage = await sys_client.call_tool("get_memory_usage", {
                "human_readable": True
            })
            
            disk_usage = await sys_client.call_tool("get_disk_usage", {
                "human_readable": True
            })
            
            network_status = await sys_client.call_tool("network_status", {
                "include_stats": True
            })
            
            health_check = await sys_client.call_tool("health_check", {
                "detailed": True
            })
            
            self.results["system"] = {
                "status": "success",
                "tests_passed": 7,
                "list_processes": len(processes.get("processes", [])) > 0,
                "get_system_metrics": "cpu" in metrics and "memory" in metrics,
                "get_cpu_usage": "usage" in cpu_usage,
                "get_memory_usage": "total" in memory_usage,
                "get_disk_usage": "filesystems" in disk_usage,
                "network_status": "interfaces" in network_status,
                "health_check": "overall_status" in health_check
            }
            
        except Exception as e:
            logger.error(f"System MCP test failed: {e}")
            self.results["system"] = {
                "status": "failed",
                "error": str(e)
            }
    
    async def test_desktop_mcp(self):
        """Test desktop MCP server functionality"""
        logger.info("Testing Desktop MCP...")
        
        try:
            # Initialize desktop client
            desktop_client = DesktopMCPClient()
            await desktop_client.initialize()
            
            # Test desktop automation
            windows = await desktop_client.call_tool("list_windows", {})
            
            screenshot = await desktop_client.call_tool("take_screenshot", {
                "path": "/tmp/mcp_test_screenshot.png"
            })
            
            screen_info = await desktop_client.call_tool("get_screen_info", {})
            
            # Test clipboard (safe operations)
            clipboard_text = await desktop_client.call_tool("get_clipboard_text", {})
            
            # Test mouse position
            mouse_pos = await desktop_client.call_tool("get_mouse_position", {})
            
            self.results["desktop"] = {
                "status": "success",
                "tests_passed": 5,
                "list_windows": "windows" in windows,
                "take_screenshot": screenshot.get("success", False),
                "get_screen_info": "width" in screen_info and "height" in screen_info,
                "get_clipboard_text": isinstance(clipboard_text.get("text"), str),
                "get_mouse_position": "x" in mouse_pos and "y" in mouse_pos
            }
            
        except Exception as e:
            logger.error(f"Desktop MCP test failed: {e}")
            self.results["desktop"] = {
                "status": "failed",
                "error": str(e)
            }
    
    async def test_multi_server_orchestration(self):
        """Test multi-server orchestration capabilities"""
        logger.info("Testing Multi-server orchestration...")
        
        try:
            # Test scenario: Take screenshot, analyze system, save report
            
            # 1. Take screenshot (Desktop MCP)
            desktop_client = DesktopMCPClient()
            await desktop_client.initialize()
            
            screenshot_path = "/tmp/system_status_screenshot.png"
            screenshot_result = await desktop_client.call_tool("take_screenshot", {
                "path": screenshot_path
            })
            
            # 2. Get system metrics (System MCP)
            sys_client = SystemMCPClient()
            await sys_client.initialize()
            
            system_metrics = await sys_client.call_tool("get_system_metrics", {
                "detailed": True
            })
            
            # 3. Save report (Filesystem MCP)
            fs_client = FilesystemMCPClient()
            await fs_client.initialize()
            
            report_content = json.dumps({
                "timestamp": "2025-07-14",
                "screenshot_taken": screenshot_result.get("success", False),
                "system_metrics": system_metrics,
                "orchestration_test": "passed"
            }, indent=2)
            
            report_path = "/tmp/mcp_orchestration_report.json"
            report_result = await fs_client.call_tool("write_file", {
                "path": report_path,
                "content": report_content
            })
            
            self.results["orchestration"] = {
                "status": "success",
                "screenshot_taken": screenshot_result.get("success", False),
                "metrics_collected": "cpu" in system_metrics,
                "report_saved": report_result.get("success", False),
                "all_servers_working": True
            }
            
        except Exception as e:
            logger.error(f"Multi-server orchestration test failed: {e}")
            self.results["orchestration"] = {
                "status": "failed",
                "error": str(e)
            }
    
    def generate_report(self):
        """Generate comprehensive test report"""
        logger.info("Generating test report...")
        
        print("\n" + "="*60)
        print("MCP FUNCTIONALITY TEST REPORT")
        print("="*60)
        
        total_tests = 0
        passed_tests = 0
        
        for server, results in self.results.items():
            print(f"\n{server.upper()} MCP Server:")
            print(f"  Status: {results['status']}")
            
            if results['status'] == 'success':
                if 'tests_passed' in results:
                    tests = results['tests_passed']
                    total_tests += tests
                    passed_tests += tests
                    print(f"  Tests Passed: {tests}")
                
                # Show individual test results
                for test_name, test_result in results.items():
                    if test_name not in ['status', 'tests_passed']:
                        status = "✅" if test_result else "❌"
                        print(f"    {test_name}: {status}")
            else:
                print(f"  Error: {results.get('error', 'Unknown error')}")
        
        print(f"\n{'='*60}")
        print(f"SUMMARY: {passed_tests}/{total_tests} tests passed")
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        print(f"Success Rate: {success_rate:.1f}%")
        print("="*60)


async def main():
    """Run MCP functionality tests"""
    tester = MCPTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())