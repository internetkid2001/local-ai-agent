"""
REST API Client Framework

Generic REST API client with authentication, rate limiting, and error handling.

Author: Claude Code
Date: 2025-07-13
Session: 2.3
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging

from .rate_limiter import RateLimiter
from .auth_manager import AuthManager
from ...utils.logger import get_logger

logger = get_logger(__name__)


class HTTPMethod(Enum):
    """HTTP methods"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class ResponseFormat(Enum):
    """Response format types"""
    JSON = "json"
    TEXT = "text"
    BINARY = "binary"
    XML = "xml"


@dataclass
class APIConfig:
    """API configuration"""
    base_url: str
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    auth_required: bool = False
    auth_type: str = "bearer"  # bearer, api_key, basic
    rate_limit: Optional[int] = None  # requests per minute
    default_headers: Dict[str, str] = field(default_factory=dict)
    verify_ssl: bool = True


@dataclass
class APIResponse:
    """API response wrapper"""
    status_code: int
    data: Any
    headers: Dict[str, str]
    url: str
    method: str
    elapsed_time: float
    success: bool = True
    error: Optional[str] = None
    raw_response: Optional[str] = None


class APIClient:
    """
    Generic REST API client with advanced features.
    
    Features:
    - HTTP method support (GET, POST, PUT, DELETE, etc.)
    - Authentication integration
    - Rate limiting and retry logic
    - Response format handling (JSON, XML, text, binary)
    - Request/response middleware
    - Error handling and recovery
    - Request caching
    - Async/await support
    """
    
    def __init__(self, config: APIConfig, auth_manager: Optional[AuthManager] = None,
                 rate_limiter: Optional[RateLimiter] = None):
        """
        Initialize API client.
        
        Args:
            config: API configuration
            auth_manager: Authentication manager
            rate_limiter: Rate limiter instance
        """
        self.config = config
        self.auth_manager = auth_manager or AuthManager()
        self.rate_limiter = rate_limiter or RateLimiter()
        
        # Session management
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Middleware
        self.request_middlewares: List[Callable] = []
        self.response_middlewares: List[Callable] = []
        
        # Request cache
        self.cache: Dict[str, APIResponse] = {}
        self.cache_ttl = 300  # 5 minutes
        
        # Statistics
        self.stats = {
            "requests_made": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cache_hits": 0,
            "total_elapsed_time": 0.0
        }
        
        logger.info(f"API client initialized for {config.base_url}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def initialize(self):
        """Initialize HTTP session"""
        if self.session is None:
            connector = aiohttp.TCPConnector(
                ssl=self.config.verify_ssl,
                limit=100,
                limit_per_host=30
            )
            
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self.config.default_headers
            )
            
            logger.debug("HTTP session initialized")
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
            logger.debug("HTTP session closed")
    
    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None,
                  headers: Optional[Dict[str, str]] = None,
                  response_format: ResponseFormat = ResponseFormat.JSON,
                  cache: bool = True) -> APIResponse:
        """
        Perform GET request.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            headers: Additional headers
            response_format: Expected response format
            cache: Whether to cache the response
            
        Returns:
            API response
        """
        return await self.request(
            method=HTTPMethod.GET,
            endpoint=endpoint,
            params=params,
            headers=headers,
            response_format=response_format,
            cache=cache
        )
    
    async def post(self, endpoint: str, data: Optional[Any] = None,
                   json_data: Optional[Dict[str, Any]] = None,
                   headers: Optional[Dict[str, str]] = None,
                   response_format: ResponseFormat = ResponseFormat.JSON) -> APIResponse:
        """
        Perform POST request.
        
        Args:
            endpoint: API endpoint
            data: Request body data
            json_data: JSON data to send
            headers: Additional headers
            response_format: Expected response format
            
        Returns:
            API response
        """
        return await self.request(
            method=HTTPMethod.POST,
            endpoint=endpoint,
            data=data,
            json_data=json_data,
            headers=headers,
            response_format=response_format,
            cache=False
        )
    
    async def put(self, endpoint: str, data: Optional[Any] = None,
                  json_data: Optional[Dict[str, Any]] = None,
                  headers: Optional[Dict[str, str]] = None,
                  response_format: ResponseFormat = ResponseFormat.JSON) -> APIResponse:
        """Perform PUT request"""
        return await self.request(
            method=HTTPMethod.PUT,
            endpoint=endpoint,
            data=data,
            json_data=json_data,
            headers=headers,
            response_format=response_format,
            cache=False
        )
    
    async def delete(self, endpoint: str, headers: Optional[Dict[str, str]] = None,
                     response_format: ResponseFormat = ResponseFormat.JSON) -> APIResponse:
        """Perform DELETE request"""
        return await self.request(
            method=HTTPMethod.DELETE,
            endpoint=endpoint,
            headers=headers,
            response_format=response_format,
            cache=False
        )
    
    async def request(self, method: HTTPMethod, endpoint: str,
                     params: Optional[Dict[str, Any]] = None,
                     data: Optional[Any] = None,
                     json_data: Optional[Dict[str, Any]] = None,
                     headers: Optional[Dict[str, str]] = None,
                     response_format: ResponseFormat = ResponseFormat.JSON,
                     cache: bool = False) -> APIResponse:
        """
        Perform generic HTTP request with retry logic.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            data: Request body data
            json_data: JSON data to send
            headers: Additional headers
            response_format: Expected response format
            cache: Whether to cache the response
            
        Returns:
            API response
        """
        # Ensure session is initialized
        if not self.session:
            await self.initialize()
        
        # Build full URL
        url = self._build_url(endpoint)
        
        # Check cache for GET requests
        cache_key = None
        if cache and method == HTTPMethod.GET:
            cache_key = self._get_cache_key(url, params)
            cached_response = self._get_cached_response(cache_key)
            if cached_response:
                self.stats["cache_hits"] += 1
                return cached_response
        
        # Rate limiting
        if self.config.rate_limit:
            await self.rate_limiter.acquire(f"api_{self.config.base_url}")
        
        # Prepare request
        request_kwargs = await self._prepare_request(method, url, params, data, json_data, headers)
        
        # Execute request with retry logic
        response = await self._execute_request_with_retry(method, url, request_kwargs, response_format)
        
        # Cache response if successful and caching is enabled
        if cache and cache_key and response.success:
            self._cache_response(cache_key, response)
        
        # Update statistics
        self._update_stats(response)
        
        return response
    
    async def _execute_request_with_retry(self, method: HTTPMethod, url: str,
                                        request_kwargs: Dict[str, Any],
                                        response_format: ResponseFormat) -> APIResponse:
        """Execute request with retry logic"""
        last_error = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                start_time = time.time()
                
                # Apply request middleware
                for middleware in self.request_middlewares:
                    request_kwargs = await middleware(request_kwargs)
                
                # Make the request
                async with self.session.request(method.value, url, **request_kwargs) as response:
                    elapsed_time = time.time() - start_time
                    
                    # Parse response
                    api_response = await self._parse_response(
                        response, method.value, url, elapsed_time, response_format
                    )
                    
                    # Apply response middleware
                    for middleware in self.response_middlewares:
                        api_response = await middleware(api_response)
                    
                    # Check if request was successful
                    if response.status < 400:
                        api_response.success = True
                        return api_response
                    else:
                        # Handle HTTP errors
                        api_response.success = False
                        api_response.error = f"HTTP {response.status}: {response.reason}"
                        
                        # Don't retry client errors (4xx)
                        if 400 <= response.status < 500:
                            return api_response
                        
                        # Retry server errors (5xx)
                        last_error = api_response.error
                        
            except asyncio.TimeoutError:
                last_error = "Request timeout"
                logger.warning(f"Request timeout for {url} (attempt {attempt + 1})")
                
            except aiohttp.ClientError as e:
                last_error = f"Client error: {str(e)}"
                logger.warning(f"Client error for {url} (attempt {attempt + 1}): {e}")
                
            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                logger.error(f"Unexpected error for {url} (attempt {attempt + 1}): {e}")
            
            # Wait before retry
            if attempt < self.config.max_retries:
                delay = self.config.retry_delay * (2 ** attempt)  # Exponential backoff
                await asyncio.sleep(delay)
        
        # All retries failed
        return APIResponse(
            status_code=0,
            data=None,
            headers={},
            url=url,
            method=method.value,
            elapsed_time=0.0,
            success=False,
            error=last_error or "Request failed after all retries"
        )
    
    async def _prepare_request(self, method: HTTPMethod, url: str,
                             params: Optional[Dict[str, Any]],
                             data: Optional[Any],
                             json_data: Optional[Dict[str, Any]],
                             headers: Optional[Dict[str, str]]) -> Dict[str, Any]:
        """Prepare request arguments"""
        request_kwargs = {}
        
        # Add parameters
        if params:
            request_kwargs["params"] = params
        
        # Add data
        if json_data:
            request_kwargs["json"] = json_data
        elif data:
            request_kwargs["data"] = data
        
        # Prepare headers
        request_headers = {}
        if headers:
            request_headers.update(headers)
        
        # Add authentication
        if self.config.auth_required:
            auth_headers = await self._get_auth_headers()
            request_headers.update(auth_headers)
        
        if request_headers:
            request_kwargs["headers"] = request_headers
        
        return request_kwargs
    
    async def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        headers = {}
        
        if self.config.auth_type == "bearer":
            token = await self.auth_manager.get_credential(
                f"api_{self.config.base_url}", "access_token"
            )
            if token:
                headers["Authorization"] = f"Bearer {token}"
        
        elif self.config.auth_type == "api_key":
            api_key = await self.auth_manager.get_credential(
                f"api_{self.config.base_url}", "api_key"
            )
            if api_key:
                headers["X-API-Key"] = api_key
        
        elif self.config.auth_type == "basic":
            username = await self.auth_manager.get_credential(
                f"api_{self.config.base_url}", "username"
            )
            password = await self.auth_manager.get_credential(
                f"api_{self.config.base_url}", "password"
            )
            if username and password:
                import base64
                credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
                headers["Authorization"] = f"Basic {credentials}"
        
        return headers
    
    async def _parse_response(self, response: aiohttp.ClientResponse,
                            method: str, url: str, elapsed_time: float,
                            response_format: ResponseFormat) -> APIResponse:
        """Parse HTTP response based on format"""
        headers = dict(response.headers)
        
        try:
            if response_format == ResponseFormat.JSON:
                data = await response.json()
            elif response_format == ResponseFormat.TEXT:
                data = await response.text()
            elif response_format == ResponseFormat.BINARY:
                data = await response.read()
            elif response_format == ResponseFormat.XML:
                text = await response.text()
                # In a real implementation, you'd parse XML here
                data = text
            else:
                data = await response.text()
            
            return APIResponse(
                status_code=response.status,
                data=data,
                headers=headers,
                url=url,
                method=method,
                elapsed_time=elapsed_time
            )
            
        except Exception as e:
            # Fallback to text if parsing fails
            try:
                raw_text = await response.text()
            except:
                raw_text = str(await response.read())
            
            return APIResponse(
                status_code=response.status,
                data=None,
                headers=headers,
                url=url,
                method=method,
                elapsed_time=elapsed_time,
                success=False,
                error=f"Response parsing error: {str(e)}",
                raw_response=raw_text
            )
    
    def _build_url(self, endpoint: str) -> str:
        """Build full URL from base URL and endpoint"""
        base_url = self.config.base_url.rstrip("/")
        endpoint = endpoint.lstrip("/")
        return f"{base_url}/{endpoint}"
    
    def _get_cache_key(self, url: str, params: Optional[Dict[str, Any]]) -> str:
        """Generate cache key"""
        cache_key = url
        if params:
            sorted_params = sorted(params.items())
            param_str = "&".join(f"{k}={v}" for k, v in sorted_params)
            cache_key = f"{url}?{param_str}"
        return cache_key
    
    def _get_cached_response(self, cache_key: str) -> Optional[APIResponse]:
        """Get cached response if not expired"""
        if cache_key in self.cache:
            cached_response = self.cache[cache_key]
            # Simple TTL check (in production, use proper expiry)
            if time.time() - cached_response.elapsed_time < self.cache_ttl:
                return cached_response
            else:
                del self.cache[cache_key]
        return None
    
    def _cache_response(self, cache_key: str, response: APIResponse):
        """Cache response"""
        self.cache[cache_key] = response
        
        # Simple cache cleanup
        if len(self.cache) > 100:
            oldest_keys = list(self.cache.keys())[:20]
            for key in oldest_keys:
                del self.cache[key]
    
    def _update_stats(self, response: APIResponse):
        """Update request statistics"""
        self.stats["requests_made"] += 1
        self.stats["total_elapsed_time"] += response.elapsed_time
        
        if response.success:
            self.stats["successful_requests"] += 1
        else:
            self.stats["failed_requests"] += 1
    
    def add_request_middleware(self, middleware: Callable):
        """Add request middleware"""
        self.request_middlewares.append(middleware)
    
    def add_response_middleware(self, middleware: Callable):
        """Add response middleware"""
        self.response_middlewares.append(middleware)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get request statistics"""
        stats = self.stats.copy()
        if stats["requests_made"] > 0:
            stats["average_response_time"] = stats["total_elapsed_time"] / stats["requests_made"]
            stats["success_rate"] = stats["successful_requests"] / stats["requests_made"]
        else:
            stats["average_response_time"] = 0.0
            stats["success_rate"] = 0.0
        
        return stats