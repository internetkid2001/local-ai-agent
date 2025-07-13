"""
MCP Client Package

This package provides the Model Context Protocol (MCP) client implementation
for the Local AI Agent. It handles connections to MCP servers and provides
a unified interface for tool execution.

Key Components:
    - BaseMCPClient: Abstract base class for MCP clients
    - ConnectionPool: Manages multiple MCP server connections
    - MCPMessage: Data structures for MCP communication

Author: Claude Code
Date: 2025-07-13
Session: 1.1
"""

from .base_client import BaseMCPClient, MCPClientConfig
from .connection import MCPConnection, ConnectionState
from .exceptions import MCPError, ConnectionError, TimeoutError

__all__ = [
    'BaseMCPClient',
    'MCPClientConfig', 
    'MCPConnection',
    'ConnectionState',
    'MCPError',
    'ConnectionError',
    'TimeoutError'
]