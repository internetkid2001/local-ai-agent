#!/usr/bin/env python3
"""
Simple Screenshot Test

Basic command-line interface to test the desktop MCP server screenshot functionality.
Takes a screenshot and places it on the desktop.

Author: Claude Code
Date: 2025-07-14
"""

import asyncio
import logging
import sys
from pathlib import Path
import os

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from src.mcp_client.desktop_client import DesktopMCPClient
from src.mcp_client.base_client import MCPClientConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_screenshot():
    """Test taking a screenshot and placing it on desktop"""
    
    print("🖥️  Testing Screenshot Functionality")
    print("="*50)
    
    try:
        # Create desktop client
        from src.mcp_client.base_client import MCPServerConfig
        
        server_config = MCPServerConfig(
            name="desktop_server",
            url="ws://localhost:8766",
            enabled=True
        )
        
        config = MCPClientConfig(
            servers=[server_config]
        )
        
        client = DesktopMCPClient(config)
        
        # Initialize client
        print("📡 Connecting to desktop MCP server...")
        if not await client.initialize():
            print("❌ Failed to connect to desktop MCP server")
            return False
        
        print("✅ Connected to desktop MCP server")
        
        # Get desktop path
        desktop_path = os.path.expanduser("~/Desktop")
        if not os.path.exists(desktop_path):
            # Try common alternatives
            desktop_path = os.path.expanduser("~/desktop")
            if not os.path.exists(desktop_path):
                desktop_path = "/tmp"  # Fallback
        
        screenshot_path = os.path.join(desktop_path, "ai_screenshot.png")
        
        print(f"📸 Taking screenshot and saving to: {screenshot_path}")
        
        # Take screenshot
        result = await client.execute_tool("take_screenshot", {
            "filename": screenshot_path
        })
        
        if isinstance(result, dict):
            print("✅ Screenshot taken successfully!")
            print(f"📂 Screenshot saved to: {screenshot_path}")
            print(f"📋 Result: {result}")
            
            # Verify file exists
            if os.path.exists(screenshot_path):
                file_size = os.path.getsize(screenshot_path)
                print(f"📊 File size: {file_size} bytes")
                
                # Try to get more info about the screenshot
                try:
                    info_result = await client.execute_tool("get_screen_info", {})
                    if isinstance(info_result, dict):
                        screen_info = info_result
                        print(f"🖥️  Screen resolution: {screen_info.get('width', 'unknown')}x{screen_info.get('height', 'unknown')}")
                except Exception as e:
                    logger.debug(f"Could not get screen info: {e}")
                
                return True
            else:
                print("❌ Screenshot file was not created")
                return False
        else:
            print("❌ Failed to take screenshot")
            if isinstance(result, dict):
                print(f"Error: {result.get('error', 'Unknown error')}")
            return False
    
    except Exception as e:
        print(f"❌ Error during screenshot test: {e}")
        logger.error(f"Screenshot test failed: {e}")
        return False
    
    finally:
        # Clean up
        try:
            await client.shutdown()
            print("🔌 Disconnected from desktop MCP server")
        except:
            pass


async def main():
    """Main function"""
    print("🤖 Local AI Agent - Screenshot Test")
    print("="*50)
    
    success = await test_screenshot()
    
    print("\n" + "="*50)
    if success:
        print("✅ Screenshot test completed successfully!")
        print("📂 Check your desktop for 'ai_screenshot.png'")
    else:
        print("❌ Screenshot test failed!")
        print("🔧 Check that the desktop MCP server is running on port 8766")
    
    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())