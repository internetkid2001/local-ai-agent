#!/usr/bin/env python3
"""
Filesystem MCP Server Startup Script

Starts the filesystem MCP server with configuration from YAML file.

Author: Claude Code
Date: 2025-07-13
Session: 1.2
"""

import asyncio
import logging
import argparse
import sys
from pathlib import Path
import yaml

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from server import FileSystemMCPServer, MCPWebSocketServer, FileSystemConfig


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config file {config_path}: {e}")
        sys.exit(1)


def setup_logging(config: dict):
    """Setup logging based on configuration"""
    log_config = config.get('logging', {})
    
    level = getattr(logging, log_config.get('level', 'INFO'))
    format_str = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    handlers = [logging.StreamHandler()]
    
    if 'file' in log_config:
        handlers.append(logging.FileHandler(log_config['file']))
    
    logging.basicConfig(
        level=level,
        format=format_str,
        handlers=handlers
    )


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Start Filesystem MCP Server")
    parser.add_argument(
        "--config", 
        default="config.yaml",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--host",
        help="Override host from config"
    )
    parser.add_argument(
        "--port",
        type=int,
        help="Override port from config"
    )
    parser.add_argument(
        "--sandbox",
        help="Override sandbox root from config"
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    setup_logging(config)
    
    logger = logging.getLogger(__name__)
    logger.info("Starting Filesystem MCP Server")
    
    # Extract configuration values
    server_config = config.get('server', {})
    fs_config = config.get('filesystem', {})
    
    # Apply command line overrides
    host = args.host or server_config.get('host', 'localhost')
    port = args.port or server_config.get('port', 8765)
    sandbox_root = args.sandbox or fs_config.get('sandbox_root', '/tmp/mcp_filesystem_sandbox')
    
    # Create sandbox directory if it doesn't exist
    sandbox_path = Path(sandbox_root)
    sandbox_path.mkdir(parents=True, exist_ok=True)
    
    # Create default subdirectories
    (sandbox_path / "documents").mkdir(exist_ok=True)
    (sandbox_path / "workspace").mkdir(exist_ok=True)
    
    logger.info(f"Created sandbox structure at: {sandbox_root}")
    
    # Create filesystem configuration
    filesystem_config = FileSystemConfig(
        allowed_paths=fs_config.get('allowed_paths', [sandbox_root]),
        sandbox_root=sandbox_root,
        max_file_size=fs_config.get('max_file_size', 50 * 1024 * 1024),
        max_search_results=fs_config.get('max_search_results', 1000),
        allowed_extensions=fs_config.get('allowed_extensions', []),
        denied_extensions=fs_config.get('denied_extensions', []),
        read_only=fs_config.get('read_only', False)
    )
    
    # Create and start servers
    fs_server = FileSystemMCPServer(filesystem_config)
    ws_server = MCPWebSocketServer(fs_server, host, port)
    
    try:
        logger.info(f"Starting WebSocket server on {host}:{port}")
        await ws_server.start_server()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())