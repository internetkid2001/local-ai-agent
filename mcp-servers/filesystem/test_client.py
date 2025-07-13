#!/usr/bin/env python3
"""
Test Client for Filesystem MCP Server

Tests the filesystem MCP server functionality.

Author: Claude Code
Date: 2025-07-13
Session: 1.2
"""

import asyncio
import json
import websockets
import sys
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FilesystemMCPTestClient:
    """Test client for filesystem MCP server"""
    
    def __init__(self, uri: str = "ws://localhost:8765"):
        self.uri = uri
        self.websocket = None
        self.message_id = 0
    
    async def connect(self):
        """Connect to MCP server"""
        try:
            self.websocket = await websockets.connect(self.uri)
            logger.info(f"Connected to MCP server at {self.uri}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from MCP server"""
        if self.websocket:
            await self.websocket.close()
            logger.info("Disconnected from MCP server")
    
    async def send_request(self, method: str, params: dict = None) -> dict:
        """Send MCP request and get response"""
        if not self.websocket:
            raise RuntimeError("Not connected to server")
        
        self.message_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.message_id,
            "method": method,
            "params": params or {}
        }
        
        logger.debug(f"Sending: {json.dumps(request, indent=2)}")
        await self.websocket.send(json.dumps(request))
        
        response_str = await self.websocket.recv()
        response = json.loads(response_str)
        
        logger.debug(f"Received: {json.dumps(response, indent=2)}")
        return response
    
    async def list_tools(self):
        """Test tools/list"""
        logger.info("Testing tools/list...")
        response = await self.send_request("tools/list")
        
        if "tools" in response:
            logger.info(f"Found {len(response['tools'])} tools:")
            for tool in response['tools']:
                logger.info(f"  - {tool['name']}: {tool['description']}")
            return True
        else:
            logger.error(f"Error: {response.get('error', 'Unknown error')}")
            return False
    
    async def test_file_operations(self):
        """Test basic file operations"""
        logger.info("Testing file operations...")
        
        # Test write file
        logger.info("Testing write_file...")
        response = await self.send_request("tools/call", {
            "name": "write_file",
            "arguments": {
                "path": "/tmp/mcp_filesystem_sandbox/test_file.txt",
                "content": "Hello, MCP World!\nThis is a test file.",
                "create_dirs": True
            }
        })
        
        if "error" in response:
            logger.error(f"Write failed: {response['error']}")
            return False
        
        logger.info("File written successfully")
        
        # Test read file
        logger.info("Testing read_file...")
        response = await self.send_request("tools/call", {
            "name": "read_file",
            "arguments": {
                "path": "/tmp/mcp_filesystem_sandbox/test_file.txt"
            }
        })
        
        if "error" in response:
            logger.error(f"Read failed: {response['error']}")
            return False
        
        content_data = json.loads(response["content"][0]["text"])
        logger.info(f"File content: {content_data['content']}")
        
        # Test get file info
        logger.info("Testing get_file_info...")
        response = await self.send_request("tools/call", {
            "name": "get_file_info",
            "arguments": {
                "path": "/tmp/mcp_filesystem_sandbox/test_file.txt"
            }
        })
        
        if "error" in response:
            logger.error(f"Get info failed: {response['error']}")
            return False
        
        info_data = json.loads(response["content"][0]["text"])
        logger.info(f"File info: {info_data['name']} ({info_data['size']} bytes)")
        
        return True
    
    async def test_directory_operations(self):
        """Test directory operations"""
        logger.info("Testing directory operations...")
        
        # Test create directory
        logger.info("Testing create_directory...")
        response = await self.send_request("tools/call", {
            "name": "create_directory",
            "arguments": {
                "path": "/tmp/mcp_filesystem_sandbox/test_dir",
                "parents": True
            }
        })
        
        if "error" in response:
            logger.error(f"Create directory failed: {response['error']}")
            return False
        
        logger.info("Directory created successfully")
        
        # Test list directory
        logger.info("Testing list_directory...")
        response = await self.send_request("tools/call", {
            "name": "list_directory",
            "arguments": {
                "path": "/tmp/mcp_filesystem_sandbox"
            }
        })
        
        if "error" in response:
            logger.error(f"List directory failed: {response['error']}")
            return False
        
        dir_data = json.loads(response["content"][0]["text"])
        logger.info(f"Directory contains {len(dir_data['items'])} items:")
        for item in dir_data['items']:
            logger.info(f"  - {item['name']} ({item['type']})")
        
        return True
    
    async def test_search_operations(self):
        """Test search operations"""
        logger.info("Testing search operations...")
        
        # Create some test files first
        test_files = [
            ("test1.py", "def hello():\n    print('Hello World')"),
            ("test2.txt", "This is a sample text file\nwith multiple lines"),
            ("config.json", '{"name": "test", "value": 42}')
        ]
        
        for filename, content in test_files:
            await self.send_request("tools/call", {
                "name": "write_file",
                "arguments": {
                    "path": f"/tmp/mcp_filesystem_sandbox/{filename}",
                    "content": content
                }
            })
        
        # Test search by pattern
        logger.info("Testing search_files with pattern...")
        response = await self.send_request("tools/call", {
            "name": "search_files",
            "arguments": {
                "path": "/tmp/mcp_filesystem_sandbox",
                "pattern": "*.py"
            }
        })
        
        if "error" in response:
            logger.error(f"Search failed: {response['error']}")
            return False
        
        search_data = json.loads(response["content"][0]["text"])
        logger.info(f"Found {search_data['total_found']} Python files")
        
        # Test content search
        logger.info("Testing search_files with content...")
        response = await self.send_request("tools/call", {
            "name": "search_files",
            "arguments": {
                "path": "/tmp/mcp_filesystem_sandbox",
                "content_search": "Hello"
            }
        })
        
        if "error" in response:
            logger.error(f"Content search failed: {response['error']}")
            return False
        
        search_data = json.loads(response["content"][0]["text"])
        logger.info(f"Found {search_data['total_found']} files containing 'Hello'")
        
        return True
    
    async def run_all_tests(self):
        """Run all tests"""
        logger.info("Starting filesystem MCP server tests...")
        
        if not await self.connect():
            return False
        
        try:
            # Test tools discovery
            if not await self.list_tools():
                return False
            
            # Test file operations
            if not await self.test_file_operations():
                return False
            
            # Test directory operations
            if not await self.test_directory_operations():
                return False
            
            # Test search operations
            if not await self.test_search_operations():
                return False
            
            logger.info("All tests passed successfully!")
            return True
            
        finally:
            await self.disconnect()


async def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Filesystem MCP Server")
    parser.add_argument("--uri", default="ws://localhost:8765", help="MCP server URI")
    args = parser.parse_args()
    
    client = FilesystemMCPTestClient(args.uri)
    success = await client.run_all_tests()
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())