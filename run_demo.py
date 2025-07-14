#!/usr/bin/env python3
"""
Simple launcher for the Local AI Agent demo
Handles Python path issues
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Now we can import our modules
try:
    import asyncio
    import logging
    
    print("🤖 Local AI Agent - Simple Demo")
    print("=" * 40)
    
    async def test_basic_imports():
        """Test basic imports"""
        try:
            print("Testing imports...")
            
            # Test utils first
            from utils.logger import get_logger
            logger = get_logger(__name__)
            print("✓ Utils imported successfully")
            
            # Test LLM components
            from agent.llm.providers.base import LLMProvider, LLMConfig
            print("✓ LLM base components imported")
            
            # Test memory store
            from agent.context.memory_store import MemoryStore
            print("✓ Memory store imported")
            
            # Test basic agent components
            from agent.core.agent import Agent, AgentConfig, AgentRequest, AgentMode
            print("✓ Core agent imported")
            
            print("\n✅ All core imports successful!")
            return True
            
        except Exception as e:
            print(f"✗ Import failed: {e}")
            return False
    
    async def test_ollama_connection():
        """Test Ollama connection"""
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:11434/api/version") as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✓ Ollama connected (version: {data.get('version', 'unknown')})")
                        return True
                    else:
                        print(f"✗ Ollama returned status: {response.status}")
                        return False
                        
        except Exception as e:
            print(f"✗ Ollama connection failed: {e}")
            return False
    
    async def test_memory_system():
        """Test memory system"""
        try:
            from agent.context.memory_store import MemoryStore
            
            # Create in-memory store for testing
            memory = MemoryStore(":memory:")
            await memory.initialize()
            
            # Test storing and retrieving memory
            memory_id = await memory.store_memory(
                content="Test memory entry",
                memory_type="test",
                metadata={"test": True}
            )
            
            retrieved = await memory.retrieve_memory(memory_id)
            
            if retrieved and retrieved.content["content"] == "Test memory entry":
                print("✓ Memory system working")
                await memory.shutdown()
                return True
            else:
                print("✗ Memory system failed")
                return False
                
        except Exception as e:
            print(f"✗ Memory system error: {e}")
            return False
    
    async def test_basic_agent():
        """Test basic agent creation"""
        try:
            from agent.core.agent import create_basic_agent_config, Agent
            from agent.llm.providers.base import LLMProvider, LLMConfig
            from agent.llm.manager import LLMManagerConfig
            
            # Create minimal config
            llm_config = LLMManagerConfig()
            llm_config.provider_configs[LLMProvider.OLLAMA] = LLMConfig(
                provider=LLMProvider.OLLAMA,
                model="deepseek-r1:latest",  # Use available model
                base_url="http://localhost:11434"
            )
            
            agent_config = create_basic_agent_config()
            agent_config.llm_manager_config = llm_config
            
            # Create agent
            agent = Agent(agent_config)
            print("✓ Agent created successfully")
            
            # Try to initialize (this might fail but that's OK for testing)
            try:
                success = await agent.initialize()
                if success:
                    print("✓ Agent initialized successfully")
                    
                    # Test basic status
                    status = agent.get_status()
                    print(f"✓ Agent status: {status['name']} - {status['initialized']}")
                    
                    await agent.shutdown()
                else:
                    print("⚠ Agent initialization failed (expected if Ollama model not available)")
            except Exception as init_error:
                print(f"⚠ Agent initialization error: {init_error}")
            
            return True
            
        except Exception as e:
            print(f"✗ Agent creation failed: {e}")
            return False
    
    async def main():
        """Main demo function"""
        print("Starting Local AI Agent Demo...\n")
        
        # Test each component
        tests = [
            ("Basic Imports", test_basic_imports),
            ("Ollama Connection", test_ollama_connection), 
            ("Memory System", test_memory_system),
            ("Basic Agent", test_basic_agent)
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            print(f"\n--- {test_name} ---")
            try:
                results[test_name] = await test_func()
            except Exception as e:
                print(f"✗ {test_name} crashed: {e}")
                results[test_name] = False
        
        # Summary
        print("\n" + "=" * 40)
        print("📊 Test Results Summary:")
        print("=" * 40)
        
        for test_name, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{test_name:20} {status}")
        
        passed = sum(results.values())
        total = len(results)
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n🎉 All tests passed! The system is ready to use.")
        else:
            print(f"\n⚠️  {total - passed} tests failed. Check the errors above.")
        
        return passed == total

    if __name__ == "__main__":
        asyncio.run(main())
        
except KeyboardInterrupt:
    print("\n👋 Demo interrupted by user")
except Exception as e:
    print(f"\n❌ Demo failed: {e}")
    import traceback
    traceback.print_exc()