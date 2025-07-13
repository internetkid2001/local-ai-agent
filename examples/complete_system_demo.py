#!/usr/bin/env python3
"""
Complete System Demo

Demonstrates the full Local AI Agent system with:
- Multi-provider LLM integration
- Core Agent with reasoning
- Memory system
- MCP protocol support
- Web UI interface

Author: Claude Code
Date: 2025-07-13
Session: 4.4
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent.core.agent import Agent, AgentConfig, AgentRequest, AgentMode, create_basic_agent_config
from agent.llm.manager import LLMManager, LLMManagerConfig
from agent.llm.providers.base import LLMProvider, LLMConfig
from agent.mcp.client import MCPClient, MCPServerConfig
from agent.mcp.protocol import MCPClientInfo, MCPCapabilities
from agent.mcp.server import create_basic_server
from agent.ui.webapp import WebUIConfig, run_server


async def demo_basic_agent():
    """Demo basic agent functionality"""
    print("\n=== Basic Agent Demo ===")
    
    # Create and initialize agent
    config = create_basic_agent_config()
    agent = Agent(config)
    
    try:
        await agent.initialize()
        print(f"✓ Agent initialized: {agent.config.name}")
        
        # Test basic chat
        request = AgentRequest(
            content="Hello! Can you tell me about yourself?",
            mode=AgentMode.CHAT
        )
        
        response = await agent.process(request)
        print(f"✓ Agent response: {response.content[:100]}...")
        
        # Test reasoning mode
        request = AgentRequest(
            content="If all cats are mammals, and Fluffy is a cat, what can we conclude about Fluffy?",
            mode=AgentMode.REASONING,
            use_reasoning=True
        )
        
        response = await agent.process(request)
        print(f"✓ Reasoning response: {response.content[:100]}...")
        
        if response.reasoning_result:
            print(f"  - Confidence: {response.reasoning_result.confidence.value}")
            print(f"  - Steps: {len(response.reasoning_result.steps)}")
        
    except Exception as e:
        print(f"✗ Agent demo failed: {e}")
    finally:
        await agent.shutdown()


async def demo_llm_manager():
    """Demo LLM manager with multiple providers"""
    print("\n=== LLM Manager Demo ===")
    
    try:
        # Create LLM manager config
        config = LLMManagerConfig()
        
        # Add Ollama provider (assuming it's running)
        config.provider_configs[LLMProvider.OLLAMA] = LLMConfig(
            provider=LLMProvider.OLLAMA,
            model="llama3.1:8b",
            base_url="http://localhost:11434"
        )
        
        # Create and initialize manager
        manager = LLMManager(config)
        
        if await manager.initialize():
            print("✓ LLM Manager initialized")
            
            # Get provider status
            status = manager.get_provider_status()
            for provider, info in status.items():
                print(f"  - {provider}: {'✓' if info['healthy'] else '✗'}")
            
        else:
            print("✗ LLM Manager initialization failed")
            
        await manager.shutdown()
        
    except Exception as e:
        print(f"✗ LLM Manager demo failed: {e}")


async def demo_mcp_system():
    """Demo MCP client/server system"""
    print("\n=== MCP System Demo ===")
    
    try:
        # Create MCP client
        client_info = MCPClientInfo(name="DemoClient", version="1.0.0")
        capabilities = MCPCapabilities(tools={})
        
        client = MCPClient(client_info, capabilities)
        
        # In a real scenario, you would connect to external MCP servers
        # For demo, we'll just show the client is working
        print("✓ MCP Client created")
        print(f"  - Available tools: {len(client.get_available_tools())}")
        print(f"  - Connected servers: {len(client.get_connected_servers())}")
        
        await client.shutdown()
        
    except Exception as e:
        print(f"✗ MCP demo failed: {e}")


async def demo_web_ui():
    """Demo web UI (just configuration, not actually starting server)"""
    print("\n=== Web UI Demo ===")
    
    try:
        # Create agent config for web UI
        agent_config = create_basic_agent_config()
        
        # Create web UI config
        ui_config = WebUIConfig(
            host="localhost",
            port=8080,
            debug=True,
            agent_config=agent_config
        )
        
        print("✓ Web UI configuration created")
        print(f"  - Host: {ui_config.host}")
        print(f"  - Port: {ui_config.port}")
        print(f"  - Agent: {ui_config.agent_config.name}")
        print("  - To start web UI, run: python -m agent.ui.webapp")
        
    except Exception as e:
        print(f"✗ Web UI demo failed: {e}")


async def demo_memory_system():
    """Demo memory system"""
    print("\n=== Memory System Demo ===")
    
    try:
        from agent.context.memory_store import MemoryStore
        
        # Create memory store
        memory = MemoryStore(":memory:")  # In-memory SQLite for demo
        await memory.initialize()
        
        # Store some memories
        memory_id1 = await memory.store_memory(
            content="User likes Python programming",
            memory_type="preference",
            metadata={"user": "demo", "category": "programming"}
        )
        
        memory_id2 = await memory.store_memory(
            content="Successfully completed task about file operations",
            memory_type="task_execution",
            metadata={"task": "file_ops", "success": True}
        )
        
        print("✓ Memory store initialized and populated")
        print(f"  - Stored memory 1: {memory_id1}")
        print(f"  - Stored memory 2: {memory_id2}")
        
        # Search memories
        results = await memory.search_memories("Python")
        print(f"  - Search results for 'Python': {len(results)}")
        
        # Get stats
        stats = await memory.get_memory_stats()
        print(f"  - Total memories: {stats['total_memories']}")
        
        await memory.shutdown()
        
    except Exception as e:
        print(f"✗ Memory demo failed: {e}")


async def run_complete_system_demo():
    """Run complete system demonstration"""
    print("🤖 Local AI Agent - Complete System Demo")
    print("=" * 50)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run individual demos
    await demo_memory_system()
    await demo_llm_manager()
    await demo_basic_agent()
    await demo_mcp_system()
    await demo_web_ui()
    
    print("\n" + "=" * 50)
    print("✓ Complete system demo finished!")
    print("\nNext steps:")
    print("1. Start Ollama: ollama serve")
    print("2. Pull a model: ollama pull llama3.1:8b")
    print("3. Run web UI: python examples/complete_system_demo.py --web")
    print("4. Connect MCP servers as needed")


async def start_web_ui():
    """Start the web UI for interactive demo"""
    print("🌐 Starting Local AI Agent Web UI...")
    
    # Configure logging for web mode
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Create agent config
    agent_config = create_basic_agent_config()
    
    # Create web UI config
    ui_config = WebUIConfig(
        host="localhost",
        port=8080,
        debug=True,
        agent_config=agent_config
    )
    
    print(f"Web UI will be available at: http://{ui_config.host}:{ui_config.port}")
    
    # Start server
    await run_server(ui_config)


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Local AI Agent System Demo")
    parser.add_argument("--web", action="store_true", help="Start web UI instead of demo")
    
    args = parser.parse_args()
    
    if args.web:
        await start_web_ui()
    else:
        await run_complete_system_demo()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        sys.exit(1)