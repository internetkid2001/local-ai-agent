"""
External Service Integration

Connect the agent to external services and APIs for expanded capabilities.

Author: Claude Code
Date: 2025-07-13
Session: 2.3
"""

from .web_search import WebSearchManager, SearchProvider, SearchResult
from .api_client import APIClient, APIResponse, APIConfig
from .auth_manager import AuthManager, AuthMethod, Credential
from .rate_limiter import RateLimiter, RateLimitConfig
from .service_registry import ServiceRegistry, ServiceDefinition

__all__ = [
    'WebSearchManager',
    'SearchProvider',
    'SearchResult',
    'APIClient',
    'APIResponse', 
    'APIConfig',
    'AuthManager',
    'AuthMethod',
    'Credential',
    'RateLimiter',
    'RateLimitConfig',
    'ServiceRegistry',
    'ServiceDefinition'
]