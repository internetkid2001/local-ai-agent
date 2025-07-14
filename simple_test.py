#!/usr/bin/env python3
"""
Simple test script for Local AI Agent
Tests individual components without complex imports
"""

import sys
import os
from pathlib import Path
import asyncio
import logging

# Add src directory to Python path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

print("🤖 Local AI Agent - Simple Component Test")
print("=" * 50)

async def test_ollama():
    """Test Ollama connection"""
    try:
        import aiohttp
        
        print("Testing Ollama connection...")
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:11434/api/version") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✓ Ollama connected (version: {data.get('version', 'unknown')})")
                    
                    # Test listing models
                    async with session.get("http://localhost:11434/api/tags") as models_response:
                        if models_response.status == 200:
                            models_data = await models_response.json()
                            models = models_data.get('models', [])
                            print(f"✓ Found {len(models)} models:")
                            for model in models[:3]:  # Show first 3
                                print(f"  - {model['name']}")
                        
                    return True
                else:
                    print(f"✗ Ollama returned status: {response.status}")
                    return False
                        
    except Exception as e:
        print(f"✗ Ollama connection failed: {e}")
        return False

async def test_simple_chat():
    """Test simple chat with Ollama"""
    try:
        import aiohttp
        import json
        
        print("\nTesting simple chat with Ollama...")
        
        # Simple chat request
        chat_data = {
            "model": "deepseek-r1:latest",
            "messages": [
                {"role": "user", "content": "Hello! Say 'Hello from Local AI Agent' in exactly those words."}
            ],
            "stream": False
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post("http://localhost:11434/api/chat", json=chat_data) as response:
                if response.status == 200:
                    result = await response.json()
                    message = result.get("message", {})
                    content = message.get("content", "")
                    print(f"✓ Chat response: {content[:100]}...")
                    return True
                else:
                    print(f"✗ Chat failed with status: {response.status}")
                    error_text = await response.text()
                    print(f"Error: {error_text}")
                    return False
                    
    except Exception as e:
        print(f"✗ Chat test failed: {e}")
        return False

async def test_memory_basic():
    """Test basic memory functionality"""
    try:
        import sqlite3
        import json
        import time
        
        print("\nTesting basic memory functionality...")
        
        # Create in-memory SQLite database
        conn = sqlite3.connect(":memory:")
        
        # Create basic table
        conn.execute("""
            CREATE TABLE memories (
                id TEXT PRIMARY KEY,
                content TEXT,
                timestamp REAL
            )
        """)
        
        # Insert test memory
        memory_id = f"test_{int(time.time())}"
        conn.execute(
            "INSERT INTO memories (id, content, timestamp) VALUES (?, ?, ?)",
            (memory_id, "Test memory content", time.time())
        )
        conn.commit()
        
        # Retrieve memory
        cursor = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
        row = cursor.fetchone()
        
        if row and row[1] == "Test memory content":
            print("✓ Basic memory operations working")
            conn.close()
            return True
        else:
            print("✗ Memory test failed")
            conn.close()
            return False
            
    except Exception as e:
        print(f"✗ Memory test error: {e}")
        return False

async def test_web_ui_components():
    """Test web UI components"""
    try:
        print("\nTesting web UI components...")
        
        # Test FastAPI import
        from fastapi import FastAPI
        print("✓ FastAPI imported")
        
        # Test WebSocket import
        from fastapi import WebSocket
        print("✓ WebSocket support available")
        
        # Test Jinja2 import
        from jinja2 import Template
        template = Template("Hello {{ name }}!")
        result = template.render(name="Local AI Agent")
        if result == "Hello Local AI Agent!":
            print("✓ Template engine working")
        
        # Test basic FastAPI app creation
        app = FastAPI(title="Local AI Agent Test")
        print("✓ FastAPI app created")
        
        return True
        
    except Exception as e:
        print(f"✗ Web UI test failed: {e}")
        return False

async def main():
    """Run all tests"""
    tests = [
        ("Ollama Connection", test_ollama),
        ("Simple Chat", test_simple_chat),
        ("Basic Memory", test_memory_basic),
        ("Web UI Components", test_web_ui_components)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            results[test_name] = await test_func()
        except Exception as e:
            print(f"✗ {test_name} crashed: {e}")
            results[test_name] = False
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 Test Results Summary:")
    print(f"{'='*50}")
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:20} {status}")
    
    passed = sum(results.values())
    total = len(results)
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All core components working! System is ready.")
        print("\nNext steps:")
        print("1. Try the web UI: python3 simple_web.py")
        print("2. Test with a simple chat")
    else:
        print(f"\n⚠️  {total - passed} tests failed.")
    
    return passed == total

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Tests failed: {e}")
        import traceback
        traceback.print_exc()