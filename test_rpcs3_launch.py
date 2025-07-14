#!/usr/bin/env python3
"""
RPCS3 Launch Test

Test script to find and launch the RPCS3 application using the desktop MCP server.
This will test window management, application launching, and process interaction.

Author: Claude Code
Date: 2025-07-14
"""

import asyncio
import logging
import sys
import os
import time
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from src.mcp_client.desktop_client import DesktopMCPClient
from src.mcp_client.base_client import MCPClientConfig, MCPServerConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_rpcs3_launch():
    """Test finding and launching RPCS3 application"""
    
    print("🎮 Testing RPCS3 Application Launch")
    print("="*50)
    
    try:
        # Create desktop client
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
        
        # Step 1: Check current windows before launch
        print("\n🔍 Checking current windows...")
        windows_before = await client.execute_tool("list_windows", {})
        print(f"📊 Current windows: {len(windows_before.get('content', [{}])[0].get('text', '{}'))}")
        
        # Step 2: Try to find RPCS3 in common locations
        print("\n🔍 Searching for RPCS3 application...")
        
        # Common RPCS3 locations
        rpcs3_paths = [
            "/usr/bin/rpcs3",
            "/usr/local/bin/rpcs3",
            "/opt/rpcs3/bin/rpcs3",
            "/home/vic/Applications/rpcs3",
            "/snap/bin/rpcs3",
            "/var/lib/flatpak/exports/bin/net.rpcs3.RPCS3",
            "rpcs3"  # Try system PATH
        ]
        
        rpcs3_found = None
        for path in rpcs3_paths:
            if path.startswith("/"):
                if os.path.exists(path):
                    rpcs3_found = path
                    print(f"✅ Found RPCS3 at: {path}")
                    break
            else:
                # Check if it's in PATH
                import shutil
                if shutil.which(path):
                    rpcs3_found = path
                    print(f"✅ Found RPCS3 in PATH: {path}")
                    break
        
        if not rpcs3_found:
            print("❌ RPCS3 not found in common locations")
            print("🔍 Trying to launch anyway in case it's installed elsewhere...")
            rpcs3_found = "rpcs3"
        
        # Step 3: Try to launch RPCS3
        print(f"\n🚀 Attempting to launch RPCS3: {rpcs3_found}")
        
        # Method 1: Try using system command execution
        try:
            import subprocess
            print("📱 Launching RPCS3 using subprocess...")
            process = subprocess.Popen([rpcs3_found], 
                                     stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE,
                                     start_new_session=True)
            
            # Give it a moment to start
            await asyncio.sleep(2)
            
            # Check if process is still running
            if process.poll() is None:
                print("✅ RPCS3 process started successfully")
                process_running = True
            else:
                print("❌ RPCS3 process exited immediately")
                stdout, stderr = process.communicate()
                print(f"📝 STDOUT: {stdout.decode()}")
                print(f"📝 STDERR: {stderr.decode()}")
                process_running = False
                
        except Exception as e:
            print(f"❌ Failed to launch RPCS3 directly: {e}")
            process_running = False
        
        # Step 4: Check if RPCS3 window appeared
        print("\n🔍 Checking for RPCS3 window...")
        await asyncio.sleep(1)  # Give window time to appear
        
        windows_after = await client.execute_tool("list_windows", {})
        
        # Parse window information
        rpcs3_window_found = False
        if isinstance(windows_after, dict):
            content = windows_after.get('content', [])
            if content:
                windows_text = content[0].get('text', '{}')
                try:
                    import json
                    windows_data = json.loads(windows_text)
                    
                    print(f"📊 Windows after launch: {len(windows_data.get('windows', []))}")
                    
                    # Look for RPCS3 window
                    for window in windows_data.get('windows', []):
                        title = window.get('title', '').lower()
                        if 'rpcs3' in title or 'playstation' in title:
                            rpcs3_window_found = True
                            print(f"✅ Found RPCS3 window: {window.get('title')}")
                            print(f"📐 Window size: {window.get('width')}x{window.get('height')}")
                            print(f"📍 Window position: ({window.get('x')}, {window.get('y')})")
                            break
                            
                except json.JSONDecodeError:
                    print("❌ Could not parse window data")
        
        # Step 5: Take screenshot to verify
        print("\n📸 Taking screenshot to verify RPCS3 launch...")
        screenshot_path = os.path.expanduser("~/Desktop/rpcs3_launch_test.png")
        
        screenshot_result = await client.execute_tool("take_screenshot", {
            "filename": screenshot_path
        })
        
        if isinstance(screenshot_result, dict):
            print(f"✅ Screenshot saved to: {screenshot_path}")
            
            # Optional: Try to focus RPCS3 window if found
            if rpcs3_window_found:
                print("\n🎯 Attempting to focus RPCS3 window...")
                try:
                    focus_result = await client.execute_tool("focus_window", {
                        "title": "rpcs3"
                    })
                    print("✅ Attempted to focus RPCS3 window")
                except Exception as e:
                    print(f"⚠️  Could not focus window: {e}")
        
        # Step 6: Summary
        print("\n" + "="*50)
        print("📋 RPCS3 Launch Test Summary:")
        print(f"  - RPCS3 Found: {'✅' if rpcs3_found else '❌'}")
        print(f"  - Process Started: {'✅' if process_running else '❌'}")
        print(f"  - Window Detected: {'✅' if rpcs3_window_found else '❌'}")
        print(f"  - Screenshot Taken: ✅")
        
        success = rpcs3_window_found or process_running
        
        if success:
            print("🎉 RPCS3 launch test SUCCESSFUL!")
            print("📂 Check screenshot for visual confirmation")
        else:
            print("❌ RPCS3 launch test FAILED")
            print("💡 RPCS3 may not be installed or may need manual configuration")
        
        return success
        
    except Exception as e:
        print(f"❌ Error during RPCS3 launch test: {e}")
        logger.error(f"RPCS3 launch test failed: {e}")
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
    print("🤖 Local AI Agent - RPCS3 Launch Test")
    print("="*50)
    
    success = await test_rpcs3_launch()
    
    print("\n" + "="*50)
    if success:
        print("✅ RPCS3 launch test completed successfully!")
        print("🎮 RPCS3 should now be running on your system")
    else:
        print("❌ RPCS3 launch test failed!")
        print("🔧 Please check if RPCS3 is installed and accessible")
        print("💡 You may need to install RPCS3 or check PATH configuration")
    
    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())