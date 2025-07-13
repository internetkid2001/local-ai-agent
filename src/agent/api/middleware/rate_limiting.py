import time
from typing import Dict, Optional, Callable
from collections import defaultdict
from fastapi import Request, HTTPException, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging

logger = logging.getLogger(__name__)


class InMemoryRateLimiter:
    def __init__(self):
        self.requests: Dict[str, list] = defaultdict(list)
    
    def is_allowed(self, key: str, limit: int, window: int) -> bool:
        now = time.time()
        request_times = self.requests[key]
        
        request_times[:] = [req_time for req_time in request_times if now - req_time < window]
        
        if len(request_times) >= limit:
            return False
        
        request_times.append(now)
        return True
    
    def get_remaining(self, key: str, limit: int, window: int) -> int:
        now = time.time()
        request_times = self.requests[key]
        
        request_times[:] = [req_time for req_time in request_times if now - req_time < window]
        
        return max(0, limit - len(request_times))


class TenantRateLimiter:
    def __init__(self):
        self.limiter = InMemoryRateLimiter()
        self.tenant_limits = {
            "default": {"requests_per_minute": 100, "requests_per_hour": 1000},
            "premium": {"requests_per_minute": 500, "requests_per_hour": 10000},
            "enterprise": {"requests_per_minute": 1000, "requests_per_hour": 50000}
        }
    
    def get_tenant_tier(self, tenant_id: Optional[str]) -> str:
        return "default"
    
    def check_rate_limit(self, tenant_id: Optional[str], user_id: str) -> bool:
        if not tenant_id:
            tenant_id = "default"
        
        tier = self.get_tenant_tier(tenant_id)
        limits = self.tenant_limits.get(tier, self.tenant_limits["default"])
        
        minute_key = f"{tenant_id}:{user_id}:minute"
        hour_key = f"{tenant_id}:{user_id}:hour"
        
        minute_allowed = self.limiter.is_allowed(minute_key, limits["requests_per_minute"], 60)
        hour_allowed = self.limiter.is_allowed(hour_key, limits["requests_per_hour"], 3600)
        
        return minute_allowed and hour_allowed
    
    def get_rate_limit_info(self, tenant_id: Optional[str], user_id: str) -> Dict[str, int]:
        if not tenant_id:
            tenant_id = "default"
        
        tier = self.get_tenant_tier(tenant_id)
        limits = self.tenant_limits.get(tier, self.tenant_limits["default"])
        
        minute_key = f"{tenant_id}:{user_id}:minute"
        hour_key = f"{tenant_id}:{user_id}:hour"
        
        return {
            "requests_per_minute_remaining": self.limiter.get_remaining(
                minute_key, limits["requests_per_minute"], 60
            ),
            "requests_per_hour_remaining": self.limiter.get_remaining(
                hour_key, limits["requests_per_hour"], 3600
            ),
            "requests_per_minute_limit": limits["requests_per_minute"],
            "requests_per_hour_limit": limits["requests_per_hour"]
        }


def get_identifier_for_rate_limiting(request: Request) -> str:
    user = getattr(request.state, 'user', None)
    if user:
        return f"user:{user.username}"
    
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=get_identifier_for_rate_limiting)
tenant_rate_limiter = TenantRateLimiter()


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    logger.warning(f"Rate limit exceeded for {get_identifier_for_rate_limiting(request)}")
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Rate limit exceeded. Please try again later.",
        headers={"Retry-After": str(exc.retry_after)}
    )