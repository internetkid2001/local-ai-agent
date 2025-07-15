#!/usr/bin/env python3
"""
Simple test client for testing natural language commands via WebSocket
"""

import asyncio
import json
import websockets

async def test_natural_language_commands():
    """Test various natural language commands"""
    
    # Test commands to try
    test_commands = [
        "Show me system info",
        "List running processes", 
        "Take a screenshot",
        "Memory status",
        "Disk usage",
        "List files in current folder",
        "Show me CPU usage",
        "Display network info",
        "/system_info",  # Direct command for comparison
        "/help",
        "What's the current time?",
        "Hello, how are you?",  # Should trigger AI response
    ]
    
    uri = "ws://localhost:8090/ws"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("🔗 Connected to WebSocket server")
            print("=" * 50)
            
            for i, command in enumerate(test_commands, 1):
                print(f"\n{i}. Testing: '{command}'")
                print("-" * 30)
                
                # Send the command
                message = {
                    "type": "chat_message",
                    "message": command
                }
                
                await websocket.send(json.dumps(message))
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_data = json.loads(response)
                    
                    print(f"Type: {response_data.get('type', 'unknown')}")
                    print(f"Message: {response_data.get('message', 'No message')}")
                    
                except asyncio.TimeoutError:
                    print("❌ Timeout waiting for response")
                except Exception as e:
                    print(f"❌ Error processing response: {e}")
                
                # Small delay between commands
                await asyncio.sleep(1)
                
    except websockets.exceptions.ConnectionRefused:
        print("❌ Could not connect to WebSocket server. Make sure simple_terminal_bridge.py is running.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🤖 Testing Natural Language Commands")
    print("Make sure simple_terminal_bridge.py is running on port 8090")
    print("")
    
    asyncio.run(test_natural_language_commands())
