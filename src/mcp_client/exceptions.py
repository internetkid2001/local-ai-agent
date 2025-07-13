"""
MCP Client Exceptions

Custom exception classes for MCP client operations.

Author: Claude Code
Date: 2025-07-13
Session: 1.1
"""

class MCPError(Exception):
    """Base exception for MCP-related errors"""
    pass


class ConnectionError(MCPError):
    """Raised when MCP connection fails"""
    pass


class TimeoutError(MCPError):
    """Raised when MCP operation times out"""
    pass


class AuthenticationError(MCPError):
    """Raised when MCP authentication fails"""
    pass


class ProtocolError(MCPError):
    """Raised when MCP protocol violation occurs"""
    pass


class ServerError(MCPError):
    """Raised when MCP server returns an error"""
    
    def __init__(self, message: str, error_code: int = None):
        super().__init__(message)
        self.error_code = error_code