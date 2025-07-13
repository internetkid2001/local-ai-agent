#!/usr/bin/env python3
"""
Direct Test for Filesystem MCP Server Core

Tests the filesystem server functionality without WebSocket layer.

Author: Claude Code
Date: 2025-07-13
Session: 1.2
"""

import asyncio
import tempfile
import json
import logging
from pathlib import Path

# Import our server classes
from server import FileSystemMCPServer, FileSystemConfig

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_filesystem_core():
    """Test the core filesystem functionality"""
    logger.info("Testing filesystem MCP server core functionality...")
    
    # Create temporary sandbox for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        logger.info(f"Using temporary sandbox: {temp_dir}")
        
        # Create configuration
        config = FileSystemConfig(
            allowed_paths=[temp_dir],
            sandbox_root=temp_dir,
            max_file_size=1024 * 1024,  # 1MB for testing
            read_only=False
        )
        
        # Create server instance
        server = FileSystemMCPServer(config)
        
        # Test 1: List tools
        logger.info("Test 1: Listing available tools...")
        request = {"method": "tools/list", "params": {}}
        response = await server.handle_mcp_request(request)
        
        if "tools" in response:
            logger.info(f"✓ Found {len(response['tools'])} tools")
            for tool in response['tools']:
                logger.info(f"  - {tool['name']}")
        else:
            logger.error(f"✗ Tools list failed: {response}")
            return False
        
        # Test 2: Write a file
        logger.info("Test 2: Writing a test file...")
        test_file_path = str(Path(temp_dir) / "test.txt")
        request = {
            "method": "tools/call",
            "params": {
                "name": "write_file",
                "arguments": {
                    "path": test_file_path,
                    "content": "Hello, MCP Filesystem!\nThis is a test."
                }
            }
        }
        response = await server.handle_mcp_request(request)
        
        if "error" in response:
            logger.error(f"✗ Write file failed: {response['error']}")
            return False
        else:
            logger.info("✓ File written successfully")
        
        # Test 3: Read the file back
        logger.info("Test 3: Reading the test file...")
        request = {
            "method": "tools/call",
            "params": {
                "name": "read_file",
                "arguments": {
                    "path": test_file_path
                }
            }
        }
        response = await server.handle_mcp_request(request)
        
        if "error" in response:
            logger.error(f"✗ Read file failed: {response['error']}")
            return False
        else:
            content_data = json.loads(response["content"][0]["text"])
            logger.info(f"✓ File read successfully: {len(content_data['content'])} chars")
        
        # Test 4: Create directory
        logger.info("Test 4: Creating a directory...")
        test_dir_path = str(Path(temp_dir) / "test_directory")
        request = {
            "method": "tools/call",
            "params": {
                "name": "create_directory",
                "arguments": {
                    "path": test_dir_path
                }
            }
        }
        response = await server.handle_mcp_request(request)
        
        if "error" in response:
            logger.error(f"✗ Create directory failed: {response['error']}")
            return False
        else:
            logger.info("✓ Directory created successfully")
        
        # Test 5: List directory contents
        logger.info("Test 5: Listing directory contents...")
        request = {
            "method": "tools/call",
            "params": {
                "name": "list_directory",
                "arguments": {
                    "path": temp_dir
                }
            }
        }
        response = await server.handle_mcp_request(request)
        
        if "error" in response:
            logger.error(f"✗ List directory failed: {response['error']}")
            return False
        else:
            dir_data = json.loads(response["content"][0]["text"])
            logger.info(f"✓ Directory listed: {len(dir_data['items'])} items")
            for item in dir_data['items']:
                logger.info(f"  - {item['name']} ({item['type']})")
        
        # Test 6: Get file info
        logger.info("Test 6: Getting file information...")
        request = {
            "method": "tools/call",
            "params": {
                "name": "get_file_info",
                "arguments": {
                    "path": test_file_path
                }
            }
        }
        response = await server.handle_mcp_request(request)
        
        if "error" in response:
            logger.error(f"✗ Get file info failed: {response['error']}")
            return False
        else:
            info_data = json.loads(response["content"][0]["text"])
            logger.info(f"✓ File info retrieved: {info_data['name']} ({info_data['size']} bytes)")
        
        # Test 7: Search files
        logger.info("Test 7: Searching files...")
        # Create additional test files
        for i in range(3):
            extra_file = str(Path(temp_dir) / f"extra_{i}.txt")
            request = {
                "method": "tools/call",
                "params": {
                    "name": "write_file",
                    "arguments": {
                        "path": extra_file,
                        "content": f"Extra file {i} content\nWith some test data."
                    }
                }
            }
            await server.handle_mcp_request(request)
        
        # Now search for .txt files
        request = {
            "method": "tools/call",
            "params": {
                "name": "search_files",
                "arguments": {
                    "path": temp_dir,
                    "pattern": "*.txt"
                }
            }
        }
        response = await server.handle_mcp_request(request)
        
        if "error" in response:
            logger.error(f"✗ Search files failed: {response['error']}")
            return False
        else:
            search_data = json.loads(response["content"][0]["text"])
            logger.info(f"✓ Search completed: {search_data['total_found']} files found")
        
        # Test 8: Security test - try to access outside sandbox
        logger.info("Test 8: Testing security (should fail)...")
        request = {
            "method": "tools/call",
            "params": {
                "name": "read_file",
                "arguments": {
                    "path": "/etc/passwd"  # Should be blocked
                }
            }
        }
        response = await server.handle_mcp_request(request)
        
        if "error" in response:
            logger.info("✓ Security test passed - outside access blocked")
        else:
            logger.error("✗ Security test failed - outside access allowed!")
            return False
        
        logger.info("All core functionality tests passed! 🎉")
        return True


async def main():
    """Main test runner"""
    try:
        success = await test_filesystem_core()
        if success:
            logger.info("✅ All tests completed successfully!")
            return 0
        else:
            logger.error("❌ Some tests failed!")
            return 1
    except Exception as e:
        logger.error(f"❌ Test execution failed: {e}")
        return 1


if __name__ == "__main__":
    import sys
    result = asyncio.run(main())
    sys.exit(result)