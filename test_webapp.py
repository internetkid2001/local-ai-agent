#!/usr/bin/env python3
"""
Quick test script for the web application
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agent.ui.webapp import WebUIConfig, run_server
from agent.core.agent import create_basic_agent_config

async def main():
    """Run the web application for testing"""
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    print("Starting Local AI Agent Web UI...")
    print("Open http://localhost:8080 in your browser")
    print("Press Ctrl+C to stop")
    
    # Create configuration
    agent_config = create_basic_agent_config()
    
    config = WebUIConfig(
        host="localhost",
        port=8080,
        debug=True,
        agent_config=agent_config
    )
    
    try:
        await run_server(config)
    except KeyboardInterrupt:
        print("\nShutting down...")

if __name__ == "__main__":
    asyncio.run(main())