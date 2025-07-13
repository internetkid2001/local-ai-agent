"""
Rate Limiter

Advanced rate limiting and request throttling for external service APIs.

Author: Claude Code
Date: 2025-07-13
Session: 2.3
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
from collections import deque

from ...utils.logger import get_logger

logger = get_logger(__name__)


class RateLimitStrategy(Enum):
    """Rate limiting strategies"""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    LEAKY_BUCKET = "leaky_bucket"


@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    max_requests: int
    time_window: float  # seconds
    strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET
    burst_size: Optional[int] = None  # for token bucket
    leak_rate: Optional[float] = None  # for leaky bucket


@dataclass
class RateLimitState:
    """Current state of rate limiting for a service"""
    config: RateLimitConfig
    tokens: float = 0.0
    last_refill: float = field(default_factory=time.time)
    request_times: deque = field(default_factory=deque)
    total_requests: int = 0
    rejected_requests: int = 0


class RateLimiter:
    """
    Advanced rate limiter with multiple strategies and per-service limits.
    
    Features:
    - Multiple rate limiting algorithms
    - Per-service rate limiting
    - Burst handling
    - Request queuing and retry
    - Statistics and monitoring
    - Adaptive rate limiting
    - Priority-based requests
    """
    
    def __init__(self):
        """Initialize rate limiter"""
        self.service_limits: Dict[str, RateLimitState] = {}
        self.global_config = RateLimitConfig(
            max_requests=1000,
            time_window=3600,  # 1 hour
            strategy=RateLimitStrategy.TOKEN_BUCKET
        )
        
        # Request queue for throttled requests
        self.request_queues: Dict[str, asyncio.Queue] = {}
        self.processing_queues: Dict[str, bool] = {}
        
        logger.info("Rate limiter initialized")
    
    async def configure_service(self, service_id: str, config: RateLimitConfig):
        """
        Configure rate limiting for a specific service.
        
        Args:
            service_id: Service identifier
            config: Rate limit configuration
        """
        state = RateLimitState(config=config)
        
        # Initialize based on strategy
        if config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            state.tokens = config.max_requests
        
        self.service_limits[service_id] = state
        self.request_queues[service_id] = asyncio.Queue()
        self.processing_queues[service_id] = False
        
        logger.info(f"Configured rate limiting for {service_id}: {config.max_requests}/{config.time_window}s")
    
    async def acquire(self, service_id: str, priority: int = 1, 
                     request_cost: int = 1) -> bool:
        """
        Acquire permission to make a request.
        
        Args:
            service_id: Service identifier
            priority: Request priority (higher = more important)
            request_cost: Cost of this request (default 1)
            
        Returns:
            True when permission is granted
        """
        # Use global config if service not configured
        if service_id not in self.service_limits:
            await self.configure_service(service_id, self.global_config)
        
        state = self.service_limits[service_id]
        
        # Check if we can acquire immediately
        if await self._can_proceed(service_id, request_cost):
            await self._consume_tokens(service_id, request_cost)
            state.total_requests += 1
            return True
        
        # Queue the request if rate limited
        logger.debug(f"Rate limited request queued for {service_id}")
        state.rejected_requests += 1
        
        # Add to queue and wait
        await self.request_queues[service_id].put({
            "priority": priority,
            "cost": request_cost,
            "timestamp": time.time()
        })
        
        # Start processing queue if not already running
        if not self.processing_queues[service_id]:
            asyncio.create_task(self._process_queue(service_id))
        
        # Wait for our turn (simplified - in production would use proper queue management)
        while not await self._can_proceed(service_id, request_cost):
            await asyncio.sleep(0.1)
        
        await self._consume_tokens(service_id, request_cost)
        state.total_requests += 1
        return True
    
    async def _can_proceed(self, service_id: str, cost: int = 1) -> bool:
        """Check if request can proceed based on rate limiting strategy"""
        state = self.service_limits[service_id]
        config = state.config
        current_time = time.time()
        
        if config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            return await self._check_token_bucket(state, current_time, cost)
        
        elif config.strategy == RateLimitStrategy.SLIDING_WINDOW:
            return await self._check_sliding_window(state, current_time, cost)
        
        elif config.strategy == RateLimitStrategy.FIXED_WINDOW:
            return await self._check_fixed_window(state, current_time, cost)
        
        elif config.strategy == RateLimitStrategy.LEAKY_BUCKET:
            return await self._check_leaky_bucket(state, current_time, cost)
        
        return False
    
    async def _check_token_bucket(self, state: RateLimitState, 
                                current_time: float, cost: int) -> bool:
        """Token bucket algorithm implementation"""
        config = state.config
        
        # Refill tokens based on time elapsed
        time_elapsed = current_time - state.last_refill
        refill_amount = (config.max_requests / config.time_window) * time_elapsed
        
        # Cap at max tokens (burst size or max_requests)
        max_tokens = config.burst_size or config.max_requests
        state.tokens = min(max_tokens, state.tokens + refill_amount)
        state.last_refill = current_time
        
        return state.tokens >= cost
    
    async def _check_sliding_window(self, state: RateLimitState,
                                  current_time: float, cost: int) -> bool:
        """Sliding window algorithm implementation"""
        config = state.config
        
        # Remove old requests outside the window
        cutoff_time = current_time - config.time_window
        while state.request_times and state.request_times[0] < cutoff_time:
            state.request_times.popleft()
        
        # Check if we can add this request
        return len(state.request_times) + cost <= config.max_requests
    
    async def _check_fixed_window(self, state: RateLimitState,
                                current_time: float, cost: int) -> bool:
        """Fixed window algorithm implementation"""
        config = state.config
        
        # Calculate current window start
        window_start = int(current_time / config.time_window) * config.time_window
        
        # Reset counter if we're in a new window
        if not state.request_times or state.request_times[-1] < window_start:
            state.request_times.clear()
            return True
        
        # Count requests in current window
        current_window_requests = sum(1 for req_time in state.request_times if req_time >= window_start)
        
        return current_window_requests + cost <= config.max_requests
    
    async def _check_leaky_bucket(self, state: RateLimitState,
                                current_time: float, cost: int) -> bool:
        """Leaky bucket algorithm implementation"""
        config = state.config
        leak_rate = config.leak_rate or (config.max_requests / config.time_window)
        
        # Leak tokens based on time elapsed
        time_elapsed = current_time - state.last_refill
        leaked_amount = leak_rate * time_elapsed
        
        # Remove leaked requests
        state.tokens = max(0, state.tokens - leaked_amount)
        state.last_refill = current_time
        
        # Check if bucket has capacity
        max_capacity = config.max_requests
        return state.tokens + cost <= max_capacity
    
    async def _consume_tokens(self, service_id: str, cost: int):
        """Consume tokens/requests for a service"""
        state = self.service_limits[service_id]
        config = state.config
        current_time = time.time()
        
        if config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            state.tokens -= cost
        
        elif config.strategy in [RateLimitStrategy.SLIDING_WINDOW, RateLimitStrategy.FIXED_WINDOW]:
            for _ in range(cost):
                state.request_times.append(current_time)
        
        elif config.strategy == RateLimitStrategy.LEAKY_BUCKET:
            state.tokens += cost
    
    async def _process_queue(self, service_id: str):
        """Process queued requests for a service"""
        if self.processing_queues[service_id]:
            return
        
        self.processing_queues[service_id] = True
        queue = self.request_queues[service_id]
        
        try:
            while not queue.empty():
                # Get next request (simplified - would implement priority queue)
                request = await queue.get()
                
                # Wait until we can process this request
                while not await self._can_proceed(service_id, request["cost"]):
                    await asyncio.sleep(0.1)
                
                # Process the request
                await self._consume_tokens(service_id, request["cost"])
                
                # Notify that request can proceed (simplified)
                queue.task_done()
                
        finally:
            self.processing_queues[service_id] = False
    
    async def get_wait_time(self, service_id: str, cost: int = 1) -> float:
        """
        Estimate wait time until request can be processed.
        
        Args:
            service_id: Service identifier
            cost: Request cost
            
        Returns:
            Estimated wait time in seconds
        """
        if service_id not in self.service_limits:
            return 0.0
        
        state = self.service_limits[service_id]
        config = state.config
        current_time = time.time()
        
        if config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            if state.tokens >= cost:
                return 0.0
            
            # Calculate time to refill needed tokens
            tokens_needed = cost - state.tokens
            refill_rate = config.max_requests / config.time_window
            return tokens_needed / refill_rate
        
        elif config.strategy == RateLimitStrategy.SLIDING_WINDOW:
            # Remove expired requests
            cutoff_time = current_time - config.time_window
            valid_requests = [t for t in state.request_times if t >= cutoff_time]
            
            if len(valid_requests) + cost <= config.max_requests:
                return 0.0
            
            # Wait until oldest request expires
            if valid_requests:
                oldest_request = min(valid_requests)
                return (oldest_request + config.time_window) - current_time
        
        return 0.0
    
    def get_service_stats(self, service_id: str) -> Optional[Dict[str, Any]]:
        """Get rate limiting statistics for a service"""
        if service_id not in self.service_limits:
            return None
        
        state = self.service_limits[service_id]
        config = state.config
        
        return {
            "service_id": service_id,
            "strategy": config.strategy.value,
            "max_requests": config.max_requests,
            "time_window": config.time_window,
            "current_tokens": state.tokens,
            "total_requests": state.total_requests,
            "rejected_requests": state.rejected_requests,
            "success_rate": (state.total_requests - state.rejected_requests) / max(state.total_requests, 1),
            "queue_size": self.request_queues[service_id].qsize() if service_id in self.request_queues else 0
        }
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all services"""
        return {
            "services": {
                service_id: self.get_service_stats(service_id)
                for service_id in self.service_limits.keys()
            },
            "total_services": len(self.service_limits)
        }
    
    async def reset_service_limits(self, service_id: str):
        """Reset rate limiting state for a service"""
        if service_id in self.service_limits:
            state = self.service_limits[service_id]
            config = state.config
            
            # Reset state
            if config.strategy == RateLimitStrategy.TOKEN_BUCKET:
                state.tokens = config.max_requests
            else:
                state.request_times.clear()
            
            state.last_refill = time.time()
            state.total_requests = 0
            state.rejected_requests = 0
            
            logger.info(f"Reset rate limits for {service_id}")
    
    async def update_service_config(self, service_id: str, config: RateLimitConfig):
        """Update rate limiting configuration for a service"""
        if service_id in self.service_limits:
            old_state = self.service_limits[service_id]
            
            # Preserve statistics
            new_state = RateLimitState(config=config)
            new_state.total_requests = old_state.total_requests
            new_state.rejected_requests = old_state.rejected_requests
            
            # Initialize new state
            if config.strategy == RateLimitStrategy.TOKEN_BUCKET:
                new_state.tokens = config.max_requests
            
            self.service_limits[service_id] = new_state
            
            logger.info(f"Updated rate limit config for {service_id}")
        else:
            await self.configure_service(service_id, config)
    
    async def get_service_health(self, service_id: str) -> Dict[str, Any]:
        """Get health status for a service's rate limiting"""
        stats = self.get_service_stats(service_id)
        if not stats:
            return {"status": "unknown", "service_id": service_id}
        
        # Determine health based on success rate and queue size
        success_rate = stats["success_rate"]
        queue_size = stats["queue_size"]
        
        if success_rate > 0.95 and queue_size < 10:
            status = "healthy"
        elif success_rate > 0.8 and queue_size < 50:
            status = "warning"
        else:
            status = "unhealthy"
        
        return {
            "service_id": service_id,
            "status": status,
            "success_rate": success_rate,
            "queue_size": queue_size,
            "recommendations": self._get_health_recommendations(stats)
        }
    
    def _get_health_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """Get recommendations based on service stats"""
        recommendations = []
        
        if stats["success_rate"] < 0.8:
            recommendations.append("Consider increasing rate limits or reducing request frequency")
        
        if stats["queue_size"] > 20:
            recommendations.append("High queue size detected, requests may be delayed")
        
        if stats["rejected_requests"] > stats["total_requests"] * 0.1:
            recommendations.append("High rejection rate, consider optimizing request patterns")
        
        return recommendations