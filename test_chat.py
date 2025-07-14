#!/usr/bin/env python3
"""
Simple chat test for the Local AI Agent web UI
"""

import asyncio
import aiohttp
import json

async def test_chat():
    """Test the chat functionality"""
    print("🧪 Testing Local AI Agent Chat...")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Test health first
            async with session.get("http://localhost:8080/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    print(f"✓ Health check: {health_data['status']}")
                    print(f"✓ Ollama version: {health_data['ollama_version']}")
                else:
                    print(f"✗ Health check failed: {response.status}")
                    return False
            
            # Test chat
            chat_data = {"message": "Hello! Please respond with exactly: 'Hi there from your local AI agent!'"}
            
            async with session.post("http://localhost:8080/chat", json=chat_data) as response:
                if response.status == 200:
                    result = await response.json()
                    ai_response = result.get("response", "")
                    print(f"✓ Chat working! AI responded: '{ai_response[:100]}...'")
                    return True
                else:
                    error_text = await response.text()
                    print(f"✗ Chat failed: {response.status} - {error_text}")
                    return False
                    
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_chat())
    if success:
        print("\n🎉 Local AI Agent is working!")
        print("🌐 Open http://localhost:8080 in your browser to chat!")
    else:
        print("\n❌ Test failed. Check if the web server is running.")