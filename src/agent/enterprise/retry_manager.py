#!/usr/bin/env python3
"""
Advanced Retry Manager

Comprehensive retry management system with exponential backoff, circuit breakers,
and intelligent failure analysis for enterprise-grade reliability.

Author: Claude Code
Date: 2025-07-14
Phase: 4.7 - Enhanced Error Handling
"""

import asyncio
import logging
import time
import random
from typing import Dict, Any, Optional, List, Callable, Type, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import threading
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """Retry strategy types"""
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIBONACCI = "fibonacci"
    CUSTOM = "custom"


class FailurePattern(Enum):
    """Common failure patterns"""
    TRANSIENT = "transient"
    PERSISTENT = "persistent"
    INTERMITTENT = "intermittent"
    CASCADING = "cascading"
    UNKNOWN = "unknown"


@dataclass
class RetryConfig:
    """Advanced retry configuration"""
    max_attempts: int = 5
    base_delay: float = 1.0
    max_delay: float = 300.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    backoff_multiplier: float = 2.0
    jitter: bool = True
    jitter_factor: float = 0.1
    timeout: Optional[float] = None
    
    # Circuit breaker configuration
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 60.0
    circuit_breaker_recovery_timeout: float = 300.0
    
    # Failure analysis
    failure_analysis_enabled: bool = True
    failure_pattern_threshold: int = 3
    
    # Custom retry conditions
    retryable_exceptions: List[Type[Exception]] = field(default_factory=lambda: [
        ConnectionError, TimeoutError, asyncio.TimeoutError, OSError
    ])
    non_retryable_exceptions: List[Type[Exception]] = field(default_factory=lambda: [
        ValueError, TypeError, KeyError, AttributeError
    ])


@dataclass
class RetryAttempt:
    """Information about a single retry attempt"""
    attempt_number: int
    timestamp: float
    delay: float
    exception: Optional[Exception] = None
    duration: float = 0.0
    success: bool = False
    correlation_id: str = ""


@dataclass
class RetryResult:
    """Result of retry operation"""
    success: bool
    result: Any = None
    final_exception: Optional[Exception] = None
    total_attempts: int = 0
    total_duration: float = 0.0
    attempts: List[RetryAttempt] = field(default_factory=list)
    failure_pattern: FailurePattern = FailurePattern.UNKNOWN
    correlation_id: str = ""


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerInfo:
    """Circuit breaker state information"""
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    failure_count: int = 0
    last_failure_time: float = 0.0
    last_success_time: float = 0.0
    half_open_attempts: int = 0
    total_requests: int = 0
    total_failures: int = 0


class AdvancedRetryManager:
    """
    Advanced retry management system with enterprise features.
    
    Features:
    - Multiple retry strategies with intelligent backoff
    - Circuit breaker pattern with auto-recovery
    - Failure pattern analysis and prediction
    - Correlation ID tracking for distributed systems
    - Real-time metrics and health monitoring
    - Custom retry conditions and exception handling
    """
    
    def __init__(self, config: RetryConfig = None):
        self.config = config or RetryConfig()
        self.circuit_breakers: Dict[str, CircuitBreakerInfo] = {}
        self.failure_history: Dict[str, List[RetryAttempt]] = defaultdict(list)
        self.metrics = {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "retry_operations": 0,
            "circuit_breaker_trips": 0,
            "avg_retry_count": 0.0,
            "avg_operation_duration": 0.0
        }
        
        # Thread-safe metrics updates
        self._metrics_lock = threading.Lock()
        
        # Correlation ID counter
        self._correlation_counter = 0
        self._correlation_lock = threading.Lock()
    
    def _generate_correlation_id(self) -> str:
        """Generate unique correlation ID"""
        with self._correlation_lock:
            self._correlation_counter += 1
            return f"retry-{int(time.time())}-{self._correlation_counter:06d}"
    
    def _calculate_delay(self, attempt: int, correlation_id: str) -> float:
        """Calculate delay for given attempt using configured strategy"""
        if self.config.strategy == RetryStrategy.FIXED:
            delay = self.config.base_delay
        elif self.config.strategy == RetryStrategy.LINEAR:
            delay = self.config.base_delay * attempt
        elif self.config.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.config.base_delay * (self.config.backoff_multiplier ** (attempt - 1))
        elif self.config.strategy == RetryStrategy.FIBONACCI:
            delay = self.config.base_delay * self._fibonacci(attempt)
        else:  # CUSTOM
            delay = self.config.base_delay
        
        # Apply jitter to prevent thundering herd
        if self.config.jitter:
            jitter_range = delay * self.config.jitter_factor
            jitter = random.uniform(-jitter_range, jitter_range)
            delay = max(0, delay + jitter)
        
        # Ensure delay is within bounds
        delay = min(delay, self.config.max_delay)
        
        logger.debug(f"[{correlation_id}] Calculated delay for attempt {attempt}: {delay:.2f}s")
        return delay
    
    def _fibonacci(self, n: int) -> int:
        """Calculate Fibonacci number for retry delays"""
        if n <= 1:
            return n
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b
    
    def _is_retryable_exception(self, exception: Exception) -> bool:
        """Check if exception is retryable based on configuration"""
        # Check non-retryable exceptions first
        for exc_type in self.config.non_retryable_exceptions:
            if isinstance(exception, exc_type):
                return False
        
        # Check retryable exceptions
        for exc_type in self.config.retryable_exceptions:
            if isinstance(exception, exc_type):
                return True
        
        # Default to retryable for unknown exceptions
        return True
    
    def _get_circuit_breaker(self, operation_key: str) -> CircuitBreakerInfo:
        """Get or create circuit breaker for operation"""
        if operation_key not in self.circuit_breakers:
            self.circuit_breakers[operation_key] = CircuitBreakerInfo()
        return self.circuit_breakers[operation_key]
    
    def _update_circuit_breaker(self, operation_key: str, success: bool):
        """Update circuit breaker state based on operation result"""
        cb = self._get_circuit_breaker(operation_key)
        cb.total_requests += 1
        
        if success:
            cb.failure_count = 0
            cb.last_success_time = time.time()
            
            if cb.state == CircuitBreakerState.HALF_OPEN:
                cb.state = CircuitBreakerState.CLOSED
                cb.half_open_attempts = 0
                logger.info(f"Circuit breaker for {operation_key} closed after successful recovery")
        else:
            cb.failure_count += 1
            cb.total_failures += 1
            cb.last_failure_time = time.time()
            
            if cb.state == CircuitBreakerState.CLOSED:
                if cb.failure_count >= self.config.circuit_breaker_threshold:
                    cb.state = CircuitBreakerState.OPEN
                    with self._metrics_lock:
                        self.metrics["circuit_breaker_trips"] += 1
                    logger.warning(f"Circuit breaker for {operation_key} opened after {cb.failure_count} failures")
            elif cb.state == CircuitBreakerState.HALF_OPEN:
                cb.state = CircuitBreakerState.OPEN
                cb.half_open_attempts = 0
                logger.warning(f"Circuit breaker for {operation_key} re-opened after failed recovery attempt")
    
    def _should_allow_request(self, operation_key: str) -> bool:
        """Check if request should be allowed based on circuit breaker state"""
        cb = self._get_circuit_breaker(operation_key)
        
        if cb.state == CircuitBreakerState.CLOSED:
            return True
        elif cb.state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has passed
            if time.time() - cb.last_failure_time > self.config.circuit_breaker_recovery_timeout:
                cb.state = CircuitBreakerState.HALF_OPEN
                cb.half_open_attempts = 0
                logger.info(f"Circuit breaker for {operation_key} entering half-open state")
                return True
            return False
        else:  # HALF_OPEN
            # Allow limited requests to test recovery
            if cb.half_open_attempts < 3:
                cb.half_open_attempts += 1
                return True
            return False
    
    def _analyze_failure_pattern(self, attempts: List[RetryAttempt]) -> FailurePattern:
        """Analyze failure pattern from retry attempts"""
        if not attempts or len(attempts) < 2:
            return FailurePattern.UNKNOWN
        
        # Calculate time intervals between failures
        intervals = []
        for i in range(1, len(attempts)):
            interval = attempts[i].timestamp - attempts[i-1].timestamp
            intervals.append(interval)
        
        if not intervals:
            return FailurePattern.UNKNOWN
        
        # Analyze pattern
        avg_interval = statistics.mean(intervals)
        std_interval = statistics.stdev(intervals) if len(intervals) > 1 else 0
        
        # Classify pattern
        if std_interval < avg_interval * 0.2:  # Low variance
            if avg_interval < 5.0:  # Frequent failures
                return FailurePattern.PERSISTENT
            else:
                return FailurePattern.INTERMITTENT
        elif len(attempts) > 3 and all(a.exception for a in attempts):
            return FailurePattern.CASCADING
        else:
            return FailurePattern.TRANSIENT
    
    def _update_metrics(self, result: RetryResult):
        """Update retry metrics"""
        with self._metrics_lock:
            self.metrics["total_operations"] += 1
            
            if result.success:
                self.metrics["successful_operations"] += 1
            else:
                self.metrics["failed_operations"] += 1
            
            if result.total_attempts > 1:
                self.metrics["retry_operations"] += 1
            
            # Update averages
            total_ops = self.metrics["total_operations"]
            self.metrics["avg_retry_count"] = (
                (self.metrics["avg_retry_count"] * (total_ops - 1) + result.total_attempts) / total_ops
            )
            self.metrics["avg_operation_duration"] = (
                (self.metrics["avg_operation_duration"] * (total_ops - 1) + result.total_duration) / total_ops
            )
    
    async def execute_with_retry(self, 
                               operation: Callable,
                               operation_key: str,
                               *args, 
                               **kwargs) -> RetryResult:
        """
        Execute operation with advanced retry logic.
        
        Args:
            operation: Async function to execute
            operation_key: Unique key for circuit breaker and metrics
            *args: Arguments for operation
            **kwargs: Keyword arguments for operation
            
        Returns:
            RetryResult with detailed execution information
        """
        correlation_id = self._generate_correlation_id()
        logger.info(f"[{correlation_id}] Starting operation: {operation_key}")
        
        # Check circuit breaker
        if not self._should_allow_request(operation_key):
            logger.warning(f"[{correlation_id}] Operation {operation_key} blocked by circuit breaker")
            return RetryResult(
                success=False,
                final_exception=Exception(f"Circuit breaker open for {operation_key}"),
                correlation_id=correlation_id
            )
        
        result = RetryResult(correlation_id=correlation_id)
        start_time = time.time()
        
        for attempt in range(1, self.config.max_attempts + 1):
            attempt_start = time.time()
            
            try:
                logger.debug(f"[{correlation_id}] Attempt {attempt}/{self.config.max_attempts}")
                
                # Execute operation with optional timeout
                if self.config.timeout:
                    operation_result = await asyncio.wait_for(
                        operation(*args, **kwargs),
                        timeout=self.config.timeout
                    )
                else:
                    operation_result = await operation(*args, **kwargs)
                
                # Success!
                attempt_duration = time.time() - attempt_start
                
                attempt_info = RetryAttempt(
                    attempt_number=attempt,
                    timestamp=attempt_start,
                    delay=0.0,
                    duration=attempt_duration,
                    success=True,
                    correlation_id=correlation_id
                )
                
                result.attempts.append(attempt_info)
                result.success = True
                result.result = operation_result
                result.total_attempts = attempt
                
                # Update circuit breaker
                self._update_circuit_breaker(operation_key, True)
                
                logger.info(f"[{correlation_id}] Operation {operation_key} succeeded on attempt {attempt}")
                break
                
            except Exception as e:
                attempt_duration = time.time() - attempt_start
                
                attempt_info = RetryAttempt(
                    attempt_number=attempt,
                    timestamp=attempt_start,
                    delay=0.0,
                    duration=attempt_duration,
                    success=False,
                    exception=e,
                    correlation_id=correlation_id
                )
                
                result.attempts.append(attempt_info)
                result.final_exception = e
                
                logger.warning(f"[{correlation_id}] Attempt {attempt} failed: {e}")
                
                # Check if exception is retryable
                if not self._is_retryable_exception(e):
                    logger.error(f"[{correlation_id}] Non-retryable exception: {e}")
                    break
                
                # Check if we have more attempts
                if attempt < self.config.max_attempts:
                    delay = self._calculate_delay(attempt, correlation_id)
                    attempt_info.delay = delay
                    
                    logger.info(f"[{correlation_id}] Retrying in {delay:.2f}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"[{correlation_id}] All retry attempts exhausted")
        
        # Finalize result
        result.total_duration = time.time() - start_time
        result.total_attempts = len(result.attempts)
        
        # Update circuit breaker
        self._update_circuit_breaker(operation_key, result.success)
        
        # Analyze failure pattern
        if self.config.failure_analysis_enabled and not result.success:
            result.failure_pattern = self._analyze_failure_pattern(result.attempts)
            
            # Store failure history for pattern analysis
            self.failure_history[operation_key].extend(result.attempts)
            
            # Keep only recent failures
            cutoff_time = time.time() - 3600  # 1 hour
            self.failure_history[operation_key] = [
                a for a in self.failure_history[operation_key] 
                if a.timestamp > cutoff_time
            ]
        
        # Update metrics
        self._update_metrics(result)
        
        logger.info(f"[{correlation_id}] Operation {operation_key} completed: "
                   f"success={result.success}, attempts={result.total_attempts}, "
                   f"duration={result.total_duration:.2f}s")
        
        return result
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive retry metrics"""
        with self._metrics_lock:
            return {
                "operations": self.metrics.copy(),
                "circuit_breakers": {
                    key: {
                        "state": cb.state.value,
                        "failure_count": cb.failure_count,
                        "total_requests": cb.total_requests,
                        "total_failures": cb.total_failures,
                        "success_rate": (cb.total_requests - cb.total_failures) / cb.total_requests if cb.total_requests > 0 else 0,
                        "last_failure_time": cb.last_failure_time,
                        "last_success_time": cb.last_success_time
                    }
                    for key, cb in self.circuit_breakers.items()
                },
                "failure_patterns": {
                    key: {
                        "pattern": self._analyze_failure_pattern(attempts).value,
                        "recent_failures": len(attempts),
                        "avg_interval": statistics.mean([
                            attempts[i].timestamp - attempts[i-1].timestamp 
                            for i in range(1, len(attempts))
                        ]) if len(attempts) > 1 else 0
                    }
                    for key, attempts in self.failure_history.items()
                    if attempts
                }
            }
    
    def reset_circuit_breaker(self, operation_key: str):
        """Manually reset circuit breaker"""
        if operation_key in self.circuit_breakers:
            cb = self.circuit_breakers[operation_key]
            cb.state = CircuitBreakerState.CLOSED
            cb.failure_count = 0
            cb.half_open_attempts = 0
            logger.info(f"Circuit breaker for {operation_key} manually reset")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status"""
        total_ops = self.metrics["total_operations"]
        success_rate = self.metrics["successful_operations"] / total_ops if total_ops > 0 else 1.0
        
        # Determine health status
        if success_rate > 0.95:
            health = "healthy"
        elif success_rate > 0.8:
            health = "degraded"
        else:
            health = "unhealthy"
        
        # Check circuit breakers
        open_breakers = sum(1 for cb in self.circuit_breakers.values() 
                          if cb.state == CircuitBreakerState.OPEN)
        
        return {
            "status": health,
            "success_rate": success_rate,
            "total_operations": total_ops,
            "open_circuit_breakers": open_breakers,
            "avg_retry_count": self.metrics["avg_retry_count"],
            "avg_operation_duration": self.metrics["avg_operation_duration"]
        }