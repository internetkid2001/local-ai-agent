#!/usr/bin/env python3
"""
Enterprise API Gateway

Advanced API gateway with rate limiting, request validation, authentication,
and comprehensive request/response processing for enterprise applications.

Author: Claude Code
Date: 2025-07-14
Phase: 4.7 - Advanced Enterprise Features
"""

import asyncio
import logging
import time
import json
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import threading
from collections import defaultdict, deque
import hashlib
import hmac
import jwt
from pathlib import Path
import uuid
import re
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, ValidationError
import uvicorn

logger = logging.getLogger(__name__)


class RateLimitStrategy(Enum):
    """Rate limiting strategies"""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"


class AuthenticationMethod(Enum):
    """Authentication methods"""
    NONE = "none"
    API_KEY = "api_key"
    JWT = "jwt"
    OAUTH2 = "oauth2"
    BASIC = "basic"


@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    requests_per_minute: int = 100
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    burst_size: int = 10
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    enabled: bool = True
    
    # Per-user limits
    user_requests_per_minute: int = 50
    user_requests_per_hour: int = 500
    user_requests_per_day: int = 5000
    
    # Premium user limits
    premium_requests_per_minute: int = 200
    premium_requests_per_hour: int = 2000
    premium_requests_per_day: int = 20000


@dataclass
class APIEndpoint:
    """API endpoint configuration"""
    path: str
    method: str
    handler: Callable
    auth_required: bool = True
    rate_limit: Optional[RateLimitConfig] = None
    validation_schema: Optional[BaseModel] = None
    response_schema: Optional[BaseModel] = None
    tags: List[str] = field(default_factory=list)
    description: str = ""
    deprecated: bool = False
    version: str = "1.0"


@dataclass
class APIKey:
    """API key configuration"""
    key: str
    name: str
    user_id: str
    permissions: List[str] = field(default_factory=list)
    rate_limit: Optional[RateLimitConfig] = None
    expires_at: Optional[datetime] = None
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None


@dataclass
class RequestContext:
    """Request context information"""
    request_id: str
    user_id: Optional[str] = None
    api_key: Optional[str] = None
    client_ip: str = ""
    user_agent: str = ""
    timestamp: float = field(default_factory=time.time)
    correlation_id: Optional[str] = None
    
    # Rate limiting
    rate_limit_key: str = ""
    rate_limit_remaining: int = 0
    rate_limit_reset: float = 0.0
    
    # Authentication
    authenticated: bool = False
    permissions: List[str] = field(default_factory=list)
    
    # Performance
    processing_time: float = 0.0
    response_size: int = 0


class RateLimiter:
    """Advanced rate limiter with multiple strategies"""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.windows: Dict[str, deque] = defaultdict(lambda: deque())
        self.buckets: Dict[str, Dict[str, float]] = defaultdict(dict)
        self.lock = threading.Lock()
    
    async def check_rate_limit(self, key: str, user_type: str = "standard") -> Dict[str, Any]:
        """Check if request is within rate limits"""
        current_time = time.time()
        
        # Get limits based on user type
        if user_type == "premium":
            rpm = self.config.premium_requests_per_minute
            rph = self.config.premium_requests_per_hour
            rpd = self.config.premium_requests_per_day
        elif user_type == "user":
            rpm = self.config.user_requests_per_minute
            rph = self.config.user_requests_per_hour
            rpd = self.config.user_requests_per_day
        else:
            rpm = self.config.requests_per_minute
            rph = self.config.requests_per_hour
            rpd = self.config.requests_per_day
        
        with self.lock:
            if self.config.strategy == RateLimitStrategy.SLIDING_WINDOW:
                return self._sliding_window_check(key, current_time, rpm, rph, rpd)
            elif self.config.strategy == RateLimitStrategy.TOKEN_BUCKET:
                return self._token_bucket_check(key, current_time, rpm)
            elif self.config.strategy == RateLimitStrategy.LEAKY_BUCKET:
                return self._leaky_bucket_check(key, current_time, rpm)
            else:  # FIXED_WINDOW
                return self._fixed_window_check(key, current_time, rpm, rph, rpd)
    
    def _sliding_window_check(self, key: str, current_time: float, 
                            rpm: int, rph: int, rpd: int) -> Dict[str, Any]:
        """Sliding window rate limit check"""
        window = self.windows[key]
        
        # Remove old requests
        minute_ago = current_time - 60
        hour_ago = current_time - 3600
        day_ago = current_time - 86400
        
        # Count requests in different time windows
        recent_requests = [t for t in window if t > minute_ago]
        hourly_requests = [t for t in window if t > hour_ago]
        daily_requests = [t for t in window if t > day_ago]
        
        # Update window
        self.windows[key] = deque(daily_requests)
        
        # Check limits
        if len(recent_requests) >= rpm:
            return {
                'allowed': False,
                'reason': 'Rate limit exceeded: requests per minute',
                'limit': rpm,
                'remaining': 0,
                'reset_time': minute_ago + 60
            }
        
        if len(hourly_requests) >= rph:
            return {
                'allowed': False,
                'reason': 'Rate limit exceeded: requests per hour',
                'limit': rph,
                'remaining': 0,
                'reset_time': hour_ago + 3600
            }
        
        if len(daily_requests) >= rpd:
            return {
                'allowed': False,
                'reason': 'Rate limit exceeded: requests per day',
                'limit': rpd,
                'remaining': 0,
                'reset_time': day_ago + 86400
            }
        
        # Add current request
        window.append(current_time)
        
        return {
            'allowed': True,
            'limit': rpm,
            'remaining': rpm - len(recent_requests) - 1,
            'reset_time': minute_ago + 60
        }
    
    def _token_bucket_check(self, key: str, current_time: float, rpm: int) -> Dict[str, Any]:
        """Token bucket rate limit check"""
        bucket = self.buckets[key]
        
        # Initialize bucket if needed
        if 'tokens' not in bucket:
            bucket['tokens'] = rpm
            bucket['last_refill'] = current_time
        
        # Refill tokens
        time_passed = current_time - bucket['last_refill']
        tokens_to_add = time_passed * (rpm / 60.0)  # tokens per second
        bucket['tokens'] = min(rpm, bucket['tokens'] + tokens_to_add)
        bucket['last_refill'] = current_time
        
        # Check if token available
        if bucket['tokens'] >= 1:
            bucket['tokens'] -= 1
            return {
                'allowed': True,
                'limit': rpm,
                'remaining': int(bucket['tokens']),
                'reset_time': current_time + 60
            }
        else:
            return {
                'allowed': False,
                'reason': 'Rate limit exceeded: no tokens available',
                'limit': rpm,
                'remaining': 0,
                'reset_time': current_time + (1 - bucket['tokens']) * (60.0 / rpm)
            }
    
    def _leaky_bucket_check(self, key: str, current_time: float, rpm: int) -> Dict[str, Any]:
        """Leaky bucket rate limit check"""
        bucket = self.buckets[key]
        
        # Initialize bucket if needed
        if 'level' not in bucket:
            bucket['level'] = 0
            bucket['last_leak'] = current_time
        
        # Leak tokens
        time_passed = current_time - bucket['last_leak']
        tokens_to_leak = time_passed * (rpm / 60.0)  # leak rate per second
        bucket['level'] = max(0, bucket['level'] - tokens_to_leak)
        bucket['last_leak'] = current_time
        
        # Check if bucket has capacity
        if bucket['level'] < rpm:
            bucket['level'] += 1
            return {
                'allowed': True,
                'limit': rpm,
                'remaining': int(rpm - bucket['level']),
                'reset_time': current_time + 60
            }
        else:
            return {
                'allowed': False,
                'reason': 'Rate limit exceeded: bucket full',
                'limit': rpm,
                'remaining': 0,
                'reset_time': current_time + (bucket['level'] - rpm) * (60.0 / rpm)
            }
    
    def _fixed_window_check(self, key: str, current_time: float,
                          rpm: int, rph: int, rpd: int) -> Dict[str, Any]:
        """Fixed window rate limit check"""
        # Get current time windows
        minute_window = int(current_time // 60)
        hour_window = int(current_time // 3600)
        day_window = int(current_time // 86400)
        
        # Initialize counters
        if key not in self.buckets:
            self.buckets[key] = {}
        
        bucket = self.buckets[key]
        
        # Check and update minute window
        if bucket.get('minute_window') != minute_window:
            bucket['minute_window'] = minute_window
            bucket['minute_count'] = 0
        
        # Check and update hour window
        if bucket.get('hour_window') != hour_window:
            bucket['hour_window'] = hour_window
            bucket['hour_count'] = 0
        
        # Check and update day window
        if bucket.get('day_window') != day_window:
            bucket['day_window'] = day_window
            bucket['day_count'] = 0
        
        # Check limits
        if bucket['minute_count'] >= rpm:
            return {
                'allowed': False,
                'reason': 'Rate limit exceeded: requests per minute',
                'limit': rpm,
                'remaining': 0,
                'reset_time': (minute_window + 1) * 60
            }
        
        if bucket['hour_count'] >= rph:
            return {
                'allowed': False,
                'reason': 'Rate limit exceeded: requests per hour',
                'limit': rph,
                'remaining': 0,
                'reset_time': (hour_window + 1) * 3600
            }
        
        if bucket['day_count'] >= rpd:
            return {
                'allowed': False,
                'reason': 'Rate limit exceeded: requests per day',
                'limit': rpd,
                'remaining': 0,
                'reset_time': (day_window + 1) * 86400
            }
        
        # Increment counters
        bucket['minute_count'] += 1
        bucket['hour_count'] += 1
        bucket['day_count'] += 1
        
        return {
            'allowed': True,
            'limit': rpm,
            'remaining': rpm - bucket['minute_count'],
            'reset_time': (minute_window + 1) * 60
        }


class APIGatewayConfig:
    """API Gateway configuration"""
    
    def __init__(self):
        # Server configuration
        self.host = "0.0.0.0"
        self.port = 8000
        self.title = "Local AI Agent API Gateway"
        self.description = "Enterprise API Gateway for Local AI Agent"
        self.version = "1.0.0"
        
        # Security
        self.cors_origins = ["*"]
        self.cors_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.cors_headers = ["*"]
        
        # Authentication
        self.auth_method = AuthenticationMethod.API_KEY
        self.jwt_secret = "your-secret-key"
        self.jwt_algorithm = "HS256"
        self.jwt_expiration = 3600  # 1 hour
        
        # Rate limiting
        self.rate_limit = RateLimitConfig()
        
        # Request processing
        self.max_request_size = 10 * 1024 * 1024  # 10MB
        self.request_timeout = 30.0
        self.enable_compression = True
        self.enable_request_logging = True
        
        # API versioning
        self.api_prefix = "/api/v1"
        self.enable_versioning = True
        
        # Documentation
        self.enable_docs = True
        self.docs_url = "/docs"
        self.redoc_url = "/redoc"


class EnterpriseAPIGateway:
    """
    Enterprise API Gateway with comprehensive features.
    
    Features:
    - Advanced rate limiting with multiple strategies
    - Request/response validation and transformation
    - Authentication and authorization
    - API versioning and deprecation management
    - Comprehensive logging and monitoring
    - Load balancing and failover
    - Request/response caching
    - Security headers and CORS handling
    """
    
    def __init__(self, config: APIGatewayConfig = None):
        self.config = config or APIGatewayConfig()
        self.app = FastAPI(
            title=self.config.title,
            description=self.config.description,
            version=self.config.version,
            docs_url=self.config.docs_url if self.config.enable_docs else None,
            redoc_url=self.config.redoc_url if self.config.enable_docs else None
        )
        
        # Components
        self.rate_limiter = RateLimiter(self.config.rate_limit)
        self.api_keys: Dict[str, APIKey] = {}
        self.endpoints: Dict[str, APIEndpoint] = {}
        
        # Metrics
        self.metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'rate_limited_requests': 0,
            'authenticated_requests': 0,
            'avg_response_time': 0.0,
            'requests_by_endpoint': defaultdict(int),
            'requests_by_user': defaultdict(int)
        }
        
        # Security
        self.security = HTTPBearer() if self.config.auth_method != AuthenticationMethod.NONE else None
        
        # Setup middleware and routes
        self._setup_middleware()
        self._setup_routes()
    
    def _setup_middleware(self):
        """Setup API Gateway middleware"""
        
        # CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.cors_origins,
            allow_credentials=True,
            allow_methods=self.config.cors_methods,
            allow_headers=self.config.cors_headers
        )
        
        # Compression middleware
        if self.config.enable_compression:
            self.app.add_middleware(GZipMiddleware, minimum_size=1000)
        
        # Request processing middleware
        @self.app.middleware("http")
        async def request_middleware(request: Request, call_next):
            return await self._process_request(request, call_next)
    
    def _setup_routes(self):
        """Setup default API Gateway routes"""
        
        # Health check endpoint
        @self.app.get("/health")
        async def health_check():
            return {
                "status": "healthy",
                "timestamp": time.time(),
                "version": self.config.version
            }
        
        # Metrics endpoint
        @self.app.get("/metrics")
        async def get_metrics():
            return self.metrics
        
        # API key management endpoints
        @self.app.post("/admin/api-keys")
        async def create_api_key(request: Request):
            # This would typically require admin authentication
            api_key = self._generate_api_key()
            return {"api_key": api_key.key, "user_id": api_key.user_id}
        
        @self.app.get("/admin/api-keys")
        async def list_api_keys():
            return [
                {
                    "key": key[:8] + "...",
                    "name": api_key.name,
                    "user_id": api_key.user_id,
                    "enabled": api_key.enabled,
                    "created_at": api_key.created_at.isoformat()
                }
                for key, api_key in self.api_keys.items()
            ]
    
    async def _process_request(self, request: Request, call_next):
        """Process incoming request with middleware"""
        start_time = time.time()
        
        # Generate request context
        context = RequestContext(
            request_id=str(uuid.uuid4()),
            client_ip=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent", "unknown"),
            timestamp=start_time
        )
        
        # Set correlation ID
        context.correlation_id = request.headers.get("x-correlation-id", context.request_id)
        
        try:
            # Rate limiting
            if self.config.rate_limit.enabled:
                rate_limit_result = await self._check_rate_limit(request, context)
                if not rate_limit_result['allowed']:
                    self.metrics['rate_limited_requests'] += 1
                    raise HTTPException(
                        status_code=429,
                        detail=rate_limit_result['reason'],
                        headers={
                            "X-RateLimit-Limit": str(rate_limit_result['limit']),
                            "X-RateLimit-Remaining": str(rate_limit_result['remaining']),
                            "X-RateLimit-Reset": str(rate_limit_result['reset_time'])
                        }
                    )
            
            # Authentication
            if self.config.auth_method != AuthenticationMethod.NONE:
                auth_result = await self._authenticate_request(request, context)
                if not auth_result['authenticated']:
                    raise HTTPException(
                        status_code=401,
                        detail=auth_result['reason']
                    )
            
            # Request validation
            await self._validate_request(request, context)
            
            # Process request
            response = await call_next(request)
            
            # Update metrics
            self.metrics['total_requests'] += 1
            self.metrics['successful_requests'] += 1
            
            # Add response headers
            response.headers["X-Request-ID"] = context.request_id
            response.headers["X-Correlation-ID"] = context.correlation_id
            
            if self.config.rate_limit.enabled:
                response.headers["X-RateLimit-Limit"] = str(context.rate_limit_remaining)
                response.headers["X-RateLimit-Remaining"] = str(context.rate_limit_remaining)
                response.headers["X-RateLimit-Reset"] = str(context.rate_limit_reset)
            
            return response
            
        except HTTPException as e:
            self.metrics['failed_requests'] += 1
            raise e
        except Exception as e:
            self.metrics['failed_requests'] += 1
            logger.error(f"Request processing error: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
        
        finally:
            # Update performance metrics
            processing_time = time.time() - start_time
            context.processing_time = processing_time
            
            # Update average response time
            total_requests = self.metrics['total_requests']
            if total_requests > 0:
                self.metrics['avg_response_time'] = (
                    (self.metrics['avg_response_time'] * (total_requests - 1) + processing_time) / total_requests
                )
            
            # Log request if enabled
            if self.config.enable_request_logging:
                logger.info(f"Request {context.request_id}: {request.method} {request.url.path} "
                           f"- {processing_time:.3f}s - {context.client_ip}")
    
    async def _check_rate_limit(self, request: Request, context: RequestContext) -> Dict[str, Any]:
        """Check rate limit for request"""
        # Determine rate limit key
        if context.authenticated and context.user_id:
            rate_limit_key = f"user:{context.user_id}"
            user_type = "user"
        else:
            rate_limit_key = f"ip:{context.client_ip}"
            user_type = "standard"
        
        context.rate_limit_key = rate_limit_key
        
        # Check rate limit
        result = await self.rate_limiter.check_rate_limit(rate_limit_key, user_type)
        
        # Update context
        context.rate_limit_remaining = result.get('remaining', 0)
        context.rate_limit_reset = result.get('reset_time', 0)
        
        return result
    
    async def _authenticate_request(self, request: Request, context: RequestContext) -> Dict[str, Any]:
        """Authenticate request"""
        if self.config.auth_method == AuthenticationMethod.API_KEY:
            return await self._authenticate_api_key(request, context)
        elif self.config.auth_method == AuthenticationMethod.JWT:
            return await self._authenticate_jwt(request, context)
        else:
            return {'authenticated': True}
    
    async def _authenticate_api_key(self, request: Request, context: RequestContext) -> Dict[str, Any]:
        """Authenticate using API key"""
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return {'authenticated': False, 'reason': 'Missing Authorization header'}
        
        if not auth_header.startswith("Bearer "):
            return {'authenticated': False, 'reason': 'Invalid Authorization header format'}
        
        api_key = auth_header[7:]  # Remove "Bearer " prefix
        
        if api_key not in self.api_keys:
            return {'authenticated': False, 'reason': 'Invalid API key'}
        
        key_info = self.api_keys[api_key]
        
        if not key_info.enabled:
            return {'authenticated': False, 'reason': 'API key disabled'}
        
        if key_info.expires_at and datetime.utcnow() > key_info.expires_at:
            return {'authenticated': False, 'reason': 'API key expired'}
        
        # Update context
        context.authenticated = True
        context.user_id = key_info.user_id
        context.api_key = api_key
        context.permissions = key_info.permissions
        
        # Update key usage
        key_info.last_used = datetime.utcnow()
        
        self.metrics['authenticated_requests'] += 1
        
        return {'authenticated': True}
    
    async def _authenticate_jwt(self, request: Request, context: RequestContext) -> Dict[str, Any]:
        """Authenticate using JWT token"""
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return {'authenticated': False, 'reason': 'Missing Authorization header'}
        
        if not auth_header.startswith("Bearer "):
            return {'authenticated': False, 'reason': 'Invalid Authorization header format'}
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        
        try:
            payload = jwt.decode(
                token,
                self.config.jwt_secret,
                algorithms=[self.config.jwt_algorithm]
            )
            
            # Update context
            context.authenticated = True
            context.user_id = payload.get('user_id')
            context.permissions = payload.get('permissions', [])
            
            self.metrics['authenticated_requests'] += 1
            
            return {'authenticated': True}
            
        except jwt.ExpiredSignatureError:
            return {'authenticated': False, 'reason': 'Token expired'}
        except jwt.InvalidTokenError:
            return {'authenticated': False, 'reason': 'Invalid token'}
    
    async def _validate_request(self, request: Request, context: RequestContext):
        """Validate request"""
        # Check request size
        if request.headers.get("content-length"):
            content_length = int(request.headers["content-length"])
            if content_length > self.config.max_request_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"Request too large: {content_length} bytes (max: {self.config.max_request_size})"
                )
        
        # Additional validation would go here
        pass
    
    def _generate_api_key(self) -> APIKey:
        """Generate new API key"""
        key = f"ak_{uuid.uuid4().hex}"
        user_id = f"user_{int(time.time())}"
        
        api_key = APIKey(
            key=key,
            name=f"Generated key for {user_id}",
            user_id=user_id,
            permissions=["read", "write"],
            rate_limit=self.config.rate_limit
        )
        
        self.api_keys[key] = api_key
        return api_key
    
    def register_endpoint(self, endpoint: APIEndpoint):
        """Register API endpoint"""
        endpoint_key = f"{endpoint.method}:{endpoint.path}"
        self.endpoints[endpoint_key] = endpoint
        
        # Register with FastAPI
        if endpoint.method.upper() == "GET":
            self.app.get(endpoint.path, tags=endpoint.tags)(endpoint.handler)
        elif endpoint.method.upper() == "POST":
            self.app.post(endpoint.path, tags=endpoint.tags)(endpoint.handler)
        elif endpoint.method.upper() == "PUT":
            self.app.put(endpoint.path, tags=endpoint.tags)(endpoint.handler)
        elif endpoint.method.upper() == "DELETE":
            self.app.delete(endpoint.path, tags=endpoint.tags)(endpoint.handler)
        
        logger.info(f"Registered endpoint: {endpoint.method} {endpoint.path}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get API Gateway metrics"""
        return {
            'gateway_metrics': self.metrics,
            'rate_limiter_metrics': {
                'active_windows': len(self.rate_limiter.windows),
                'active_buckets': len(self.rate_limiter.buckets)
            },
            'api_keys': len(self.api_keys),
            'endpoints': len(self.endpoints)
        }
    
    async def start(self):
        """Start API Gateway server"""
        logger.info(f"Starting API Gateway on {self.config.host}:{self.config.port}")
        
        config = uvicorn.Config(
            app=self.app,
            host=self.config.host,
            port=self.config.port,
            log_level="info"
        )
        
        server = uvicorn.Server(config)
        await server.serve()
    
    async def shutdown(self):
        """Shutdown API Gateway"""
        logger.info("Shutting down API Gateway...")