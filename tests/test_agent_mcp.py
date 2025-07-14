#!/usr/bin/env python3
"""
Agent MCP Integration Test

Tests MCP functionality through the agent's WebSocket interface.

Author: Claude Code
Date: 2025-07-14
Phase: 4.6
"""

import asyncio
import json
import logging
import websockets
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AgentMCPTester:
    """Test MCP functionality through agent WebSocket interface"""
    
    def __init__(self):
        self.agent_uri = "ws://localhost:8080/ws"
        self.results = {}
    
    async def test_mcp_through_agent(self):
        """Test MCP functionality through agent"""
        logger.info("Testing MCP functionality through agent WebSocket...")
        
        try:
            async with websockets.connect(self.agent_uri) as websocket:
                # Test 1: System monitoring
                await self.test_system_monitoring(websocket)
                
                # Test 2: File operations
                await self.test_file_operations(websocket)
                
                # Test 3: Desktop automation
                await self.test_desktop_automation(websocket)
                
                # Test 4: Multi-tool orchestration
                await self.test_orchestration(websocket)
                
        except Exception as e:
            logger.error(f"Agent MCP test failed: {e}")
            self.results["connection"] = {"status": "failed", "error": str(e)}
    
    async def send_chat_message(self, websocket, message: str) -> Dict[str, Any]:
        """Send chat message to agent and get response"""
        request = {
            "type": "chat",
            "content": message,
            "conversation_id": "test-conversation",
            "mode": "chat",
            "use_memory": False,
            "use_reasoning": True
        }
        
        await websocket.send(json.dumps(request))
        response = await websocket.recv()
        return json.loads(response)
    
    async def test_system_monitoring(self, websocket):
        """Test system monitoring through agent"""
        logger.info("Testing system monitoring...")
        
        try:
            # Ask agent to get system metrics
            response = await self.send_chat_message(
                websocket,
                "Please get current system metrics including CPU and memory usage"
            )
            
            self.results["system_monitoring"] = {
                "status": "success",
                "response_received": response.get("type") == "chat_response",
                "has_content": bool(response.get("content")),
                "success": response.get("success", False)
            }
            
        except Exception as e:
            logger.error(f"System monitoring test failed: {e}")
            self.results["system_monitoring"] = {"status": "failed", "error": str(e)}
    
    async def test_file_operations(self, websocket):
        """Test file operations through agent"""
        logger.info("Testing file operations...")
        
        try:
            # Ask agent to create a test file
            response = await self.send_chat_message(
                websocket,
                "Please create a test file at /tmp/agent_test.txt with content 'Hello from AI Agent'"
            )
            
            self.results["file_operations"] = {
                "status": "success",
                "response_received": response.get("type") == "chat_response",
                "has_content": bool(response.get("content")),
                "success": response.get("success", False)
            }
            
        except Exception as e:
            logger.error(f"File operations test failed: {e}")
            self.results["file_operations"] = {"status": "failed", "error": str(e)}
    
    async def test_desktop_automation(self, websocket):
        """Test desktop automation through agent"""
        logger.info("Testing desktop automation...")
        
        try:
            # Ask agent to get screen information
            response = await self.send_chat_message(
                websocket,
                "Please get the current screen resolution and display information"
            )
            
            self.results["desktop_automation"] = {
                "status": "success",
                "response_received": response.get("type") == "chat_response",
                "has_content": bool(response.get("content")),
                "success": response.get("success", False)
            }
            
        except Exception as e:
            logger.error(f"Desktop automation test failed: {e}")
            self.results["desktop_automation"] = {"status": "failed", "error": str(e)}
    
    async def test_orchestration(self, websocket):
        """Test multi-tool orchestration through agent"""
        logger.info("Testing multi-tool orchestration...")
        
        try:
            # Ask agent to perform a complex task using multiple tools
            response = await self.send_chat_message(
                websocket,
                "Please take a screenshot, check system resources, and save a report to /tmp/system_report.txt"
            )
            
            self.results["orchestration"] = {
                "status": "success",
                "response_received": response.get("type") == "chat_response",
                "has_content": bool(response.get("content")),
                "success": response.get("success", False)
            }
            
        except Exception as e:
            logger.error(f"Orchestration test failed: {e}")
            self.results["orchestration"] = {"status": "failed", "error": str(e)}
    
    async def run_tests(self):
        """Run all tests"""
        logger.info("Starting Agent MCP integration tests...")
        await self.test_mcp_through_agent()
        self.generate_report()
    
    def generate_report(self):
        """Generate test report"""
        print("\n" + "="*60)
        print("AGENT MCP INTEGRATION TEST REPORT")
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
                        else:
                            print(f"    {key}: {value}")
            else:
                print(f"  Error: {result.get('error', 'Unknown error')}")
        
        print(f"\n{'='*60}")
        print(f"SUMMARY: {passed_tests}/{total_tests} tests passed")
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        print(f"Success Rate: {success_rate:.1f}%")
        
        if success_rate > 80:
            print("🎉 EXCELLENT: MCP integration is working well!")
        elif success_rate > 60:
            print("✅ GOOD: MCP integration is functional with minor issues")
        elif success_rate > 40:
            print("⚠️  MODERATE: MCP integration needs improvement")
        else:
            print("❌ POOR: MCP integration requires significant fixes")
        
        print("="*60)


async def main():
    """Run agent MCP tests"""
    tester = AgentMCPTester()
    await tester.run_tests()


if __name__ == "__main__":
    asyncio.run(main())