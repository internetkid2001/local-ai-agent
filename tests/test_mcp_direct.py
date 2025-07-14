#!/usr/bin/env python3
"""
Direct MCP Server Test

Tests MCP servers directly via WebSocket connections to verify functionality.

Author: Claude Code
Date: 2025-07-14
Phase: 4.6
"""

import asyncio
import json
import logging
import websockets
import uuid
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DirectMCPTester:
    """Direct MCP server tester"""
    
    def __init__(self):
        self.servers = {
            "filesystem": "ws://localhost:8765",
            "desktop": "ws://localhost:8766", 
            "system": "ws://localhost:8767"
        }
        self.results = {}
    
    async def test_server_connection(self, server_name: str, uri: str) -> Dict[str, Any]:
        """Test connection to a specific MCP server"""
        logger.info(f"Testing {server_name} server at {uri}")
        
        try:
            async with websockets.connect(uri) as websocket:
                # Send initialize request
                init_request = {
                    "jsonrpc": "2.0",
                    "id": str(uuid.uuid4()),
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "roots": {
                                "listChanged": True
                            },
                            "sampling": {}
                        },
                        "clientInfo": {
                            "name": "test-client",
                            "version": "1.0.0"
                        }
                    }
                }
                
                await websocket.send(json.dumps(init_request))
                response = await websocket.recv()
                init_response = json.loads(response)
                
                logger.info(f"{server_name} initialize response: {init_response}")
                
                # Send list tools request
                tools_request = {
                    "jsonrpc": "2.0",
                    "id": str(uuid.uuid4()),
                    "method": "tools/list",
                    "params": {}
                }
                
                await websocket.send(json.dumps(tools_request))
                response = await websocket.recv()
                tools_response = json.loads(response)
                
                tools = tools_response.get("result", {}).get("tools", [])
                logger.info(f"{server_name} has {len(tools)} tools available")
                
                return {
                    "status": "success",
                    "connected": True,
                    "initialized": "result" in init_response,
                    "tools_count": len(tools),
                    "tools": [tool["name"] for tool in tools]
                }
                
        except Exception as e:
            logger.error(f"Failed to test {server_name}: {e}")
            return {
                "status": "failed",
                "connected": False,
                "error": str(e)
            }
    
    async def test_filesystem_operations(self) -> Dict[str, Any]:
        """Test filesystem MCP operations"""
        logger.info("Testing filesystem operations...")
        
        try:
            async with websockets.connect(self.servers["filesystem"]) as websocket:
                # Initialize
                init_request = {
                    "jsonrpc": "2.0",
                    "id": str(uuid.uuid4()),
                    "method": "initialize",
                    "params": {"protocolVersion": "2024-11-05", "capabilities": {}}
                }
                await websocket.send(json.dumps(init_request))
                await websocket.recv()
                
                # Test write file
                write_request = {
                    "jsonrpc": "2.0",
                    "id": str(uuid.uuid4()),
                    "method": "tools/call",
                    "params": {
                        "name": "write_file",
                        "arguments": {
                            "path": "/tmp/mcp_test.txt",
                            "content": "Hello MCP World!"
                        }
                    }
                }
                
                await websocket.send(json.dumps(write_request))
                response = await websocket.recv()
                write_response = json.loads(response)
                
                # Test read file
                read_request = {
                    "jsonrpc": "2.0",
                    "id": str(uuid.uuid4()),
                    "method": "tools/call",
                    "params": {
                        "name": "read_file",
                        "arguments": {
                            "path": "/tmp/mcp_test.txt"
                        }
                    }
                }
                
                await websocket.send(json.dumps(read_request))
                response = await websocket.recv()
                read_response = json.loads(response)
                
                return {
                    "status": "success",
                    "write_success": "result" in write_response,
                    "read_success": "result" in read_response,
                    "content_match": "Hello MCP World!" in str(read_response.get("result", {}))
                }
                
        except Exception as e:
            logger.error(f"Filesystem operations test failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def test_system_operations(self) -> Dict[str, Any]:
        """Test system MCP operations"""
        logger.info("Testing system operations...")
        
        try:
            async with websockets.connect(self.servers["system"]) as websocket:
                # Initialize
                init_request = {
                    "jsonrpc": "2.0",
                    "id": str(uuid.uuid4()),
                    "method": "initialize",
                    "params": {"protocolVersion": "2024-11-05", "capabilities": {}}
                }
                await websocket.send(json.dumps(init_request))
                await websocket.recv()
                
                # Test get system metrics
                metrics_request = {
                    "jsonrpc": "2.0",
                    "id": str(uuid.uuid4()),
                    "method": "tools/call",
                    "params": {
                        "name": "get_system_metrics",
                        "arguments": {"detailed": True}
                    }
                }
                
                await websocket.send(json.dumps(metrics_request))
                response = await websocket.recv()
                metrics_response = json.loads(response)
                
                return {
                    "status": "success",
                    "metrics_success": "result" in metrics_response,
                    "has_cpu_info": "cpu" in str(metrics_response.get("result", {})),
                    "has_memory_info": "memory" in str(metrics_response.get("result", {}))
                }
                
        except Exception as e:
            logger.error(f"System operations test failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def test_desktop_operations(self) -> Dict[str, Any]:
        """Test desktop MCP operations"""
        logger.info("Testing desktop operations...")
        
        try:
            async with websockets.connect(self.servers["desktop"]) as websocket:
                # Initialize
                init_request = {
                    "jsonrpc": "2.0",
                    "id": str(uuid.uuid4()),
                    "method": "initialize",
                    "params": {"protocolVersion": "2024-11-05", "capabilities": {}}
                }
                await websocket.send(json.dumps(init_request))
                await websocket.recv()
                
                # Test get screen info
                screen_request = {
                    "jsonrpc": "2.0",
                    "id": str(uuid.uuid4()),
                    "method": "tools/call",
                    "params": {
                        "name": "get_screen_info",
                        "arguments": {}
                    }
                }
                
                await websocket.send(json.dumps(screen_request))
                response = await websocket.recv()
                screen_response = json.loads(response)
                
                return {
                    "status": "success",
                    "screen_info_success": "result" in screen_response,
                    "has_dimensions": "width" in str(screen_response.get("result", {}))
                }
                
        except Exception as e:
            logger.error(f"Desktop operations test failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def run_all_tests(self):
        """Run all tests"""
        logger.info("Starting MCP server tests...")
        
        # Test server connections
        for server_name, uri in self.servers.items():
            self.results[f"{server_name}_connection"] = await self.test_server_connection(server_name, uri)
        
        # Test specific operations
        self.results["filesystem_ops"] = await self.test_filesystem_operations()
        self.results["system_ops"] = await self.test_system_operations()
        self.results["desktop_ops"] = await self.test_desktop_operations()
        
        self.generate_report()
    
    def generate_report(self):
        """Generate test report"""
        print("\n" + "="*60)
        print("MCP SERVER TEST REPORT")
        print("="*60)
        
        total_tests = 0
        passed_tests = 0
        
        for test_name, result in self.results.items():
            print(f"\n{test_name.upper()}:")
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
        print("="*60)


async def main():
    """Run direct MCP tests"""
    tester = DirectMCPTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())