#!/usr/bin/env python3
"""
Desktop Automation MCP Server Startup Script

Starts the desktop automation MCP server with proper configuration and error handling.

Author: Claude Code
Date: 2025-07-13
Phase: 2.1
"""

import asyncio
import sys
import signal
import logging
from pathlib import Path

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from server import DesktopMCPServer


async def main():
    """Main startup function"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('desktop_mcp.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    # Create server instance
    config_path = Path(__file__).parent / "config.yaml"
    server = DesktopMCPServer(str(config_path) if config_path.exists() else None)
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        asyncio.create_task(server.stop_server())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        logger.info("Starting Desktop Automation MCP Server...")
        await server.start_server()
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
    finally:
        await server.stop_server()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete")
        sys.exit(0)