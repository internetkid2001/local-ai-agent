#!/usr/bin/env python3
"""
Enhanced Error Handler

Comprehensive error handling system with retry logic, graceful degradation,
and intelligent failure recovery for the MCP orchestration system.

Author: Claude Code
Date: 2025-07-14
Phase: 4.7 - Enhanced Error Handling
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Callable, Type, Union
from dataclasses import dataclass, field
from enum import Enum
import traceback
from pathlib import Path
import json
import random

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification"""
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    TIMEOUT = "timeout"
    RESOURCE = "resource"
    VALIDATION = "validation"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class RecoveryAction(Enum):
    """Recovery actions for different error types"""
    RETRY = "retry"
    FALLBACK = "fallback"
    CIRCUIT_BREAK = "circuit_break"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    ESCALATE = "escalate"


@dataclass
class ErrorContext:
    """Context information for error handling"""
    operation: str
    client_type: str
    tool_name: str
    parameters: Dict[str, Any]
    attempt_number: int
    start_time: float
    error_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_error(self, error: Exception, context: Dict[str, Any] = None):
        """Add error to history"""
        self.error_history.append({
            "timestamp": time.time(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "attempt": self.attempt_number,
            "context": context or {}
        })


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    backoff_strategy: str = "exponential"  # linear, exponential, constant
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt"""
        if self.backoff_strategy == "constant":
            delay = self.base_delay
        elif self.backoff_strategy == "linear":
            delay = self.base_delay * attempt
        else:  # exponential
            delay = self.base_delay * (self.exponential_base ** (attempt - 1))
        
        # Apply jitter to prevent thundering herd
        if self.jitter:
            delay = delay * (0.5 + random.random() * 0.5)
        
        return min(delay, self.max_delay)


@dataclass
class ErrorRule:
    """Rule for handling specific error types"""
    error_types: List[Type[Exception]]
    category: ErrorCategory
    severity: ErrorSeverity
    action: RecoveryAction
    retry_config: Optional[RetryConfig] = None
    fallback_handler: Optional[Callable] = None
    circuit_breaker_threshold: int = 5
    description: str = ""


class CircuitBreaker:
    """Circuit breaker pattern implementation"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half-open
    
    def can_execute(self) -> bool:
        """Check if execution is allowed"""
        if self.state == "closed":
            return True
        elif self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half-open"
                return True
            return False
        else:  # half-open
            return True
    
    def record_success(self):
        """Record successful execution"""
        self.failure_count = 0
        self.state = "closed"
    
    def record_failure(self):
        """Record failed execution"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"


class EnhancedErrorHandler:
    """
    Enhanced error handling system with comprehensive recovery mechanisms.
    
    Features:
    - Intelligent retry logic with multiple backoff strategies
    - Circuit breaker pattern for failing services
    - Graceful degradation mechanisms
    - Error classification and routing
    - Fallback handlers for critical operations
    - Comprehensive error tracking and analytics
    """
    
    def __init__(self):
        self.error_rules: List[ErrorRule] = []
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.error_stats = {
            "total_errors": 0,
            "errors_by_category": {},
            "errors_by_severity": {},
            "recovery_actions": {},
            "circuit_breaker_trips": 0
        }
        
        # Initialize default error rules
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Initialize default error handling rules"""
        
        # Network-related errors
        self.add_error_rule(ErrorRule(
            error_types=[ConnectionError, TimeoutError, asyncio.TimeoutError],
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            action=RecoveryAction.RETRY,
            retry_config=RetryConfig(max_attempts=3, base_delay=2.0),
            description="Network connectivity issues"
        ))
        
        # Authentication errors
        self.add_error_rule(ErrorRule(
            error_types=[PermissionError],
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            action=RecoveryAction.ESCALATE,
            description="Authentication/authorization failures"
        ))
        
        # Resource errors
        self.add_error_rule(ErrorRule(
            error_types=[MemoryError, OSError],
            category=ErrorCategory.RESOURCE,
            severity=ErrorSeverity.HIGH,
            action=RecoveryAction.GRACEFUL_DEGRADATION,
            description="Resource exhaustion or system errors"
        ))
        
        # Validation errors
        self.add_error_rule(ErrorRule(
            error_types=[ValueError, TypeError],
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            action=RecoveryAction.ESCALATE,
            description="Input validation failures"
        ))
    
    def add_error_rule(self, rule: ErrorRule):
        """Add error handling rule"""
        self.error_rules.append(rule)
        logger.debug(f"Added error rule for {rule.error_types}: {rule.description}")
    
    def _classify_error(self, error: Exception) -> ErrorRule:
        """Classify error and return appropriate rule"""
        error_type = type(error)
        
        # Find matching rule
        for rule in self.error_rules:
            if any(issubclass(error_type, rule_type) for rule_type in rule.error_types):
                return rule
        
        # Default rule for unknown errors
        return ErrorRule(
            error_types=[Exception],
            category=ErrorCategory.UNKNOWN,
            severity=ErrorSeverity.MEDIUM,
            action=RecoveryAction.RETRY,
            retry_config=RetryConfig(max_attempts=2),
            description="Unknown error type"
        )
    
    def _get_circuit_breaker(self, service_id: str) -> CircuitBreaker:
        """Get circuit breaker for service"""
        if service_id not in self.circuit_breakers:
            self.circuit_breakers[service_id] = CircuitBreaker()
        return self.circuit_breakers[service_id]
    
    async def handle_with_retry(self, 
                              operation: Callable,
                              context: ErrorContext,
                              service_id: str = None) -> Any:
        """
        Execute operation with comprehensive error handling and retry logic.
        
        Args:
            operation: Async function to execute
            context: Error context information
            service_id: Service identifier for circuit breaker
            
        Returns:
            Operation result or raises final exception
        """
        service_id = service_id or f"{context.client_type}:{context.tool_name}"
        circuit_breaker = self._get_circuit_breaker(service_id)
        
        # Check circuit breaker
        if not circuit_breaker.can_execute():
            self.error_stats["circuit_breaker_trips"] += 1
            raise RuntimeError(f"Circuit breaker open for {service_id}")
        
        last_error = None
        
        for attempt in range(1, 10):  # Maximum reasonable attempts
            context.attempt_number = attempt
            
            try:
                # Execute operation
                result = await operation()
                
                # Record success
                circuit_breaker.record_success()
                
                return result
                
            except Exception as error:
                last_error = error
                context.add_error(error)
                
                # Classify error
                error_rule = self._classify_error(error)
                
                # Update statistics
                self._update_error_stats(error_rule)
                
                logger.warning(f"Operation failed (attempt {attempt}): {error}")
                
                # Determine recovery action
                if error_rule.action == RecoveryAction.ESCALATE:
                    logger.error(f"Escalating error: {error}")
                    circuit_breaker.record_failure()
                    raise error
                
                elif error_rule.action == RecoveryAction.CIRCUIT_BREAK:
                    circuit_breaker.record_failure()
                    raise error
                
                elif error_rule.action == RecoveryAction.FALLBACK:
                    if error_rule.fallback_handler:
                        try:
                            result = await error_rule.fallback_handler(context, error)
                            return result
                        except Exception as fallback_error:
                            logger.error(f"Fallback handler failed: {fallback_error}")
                            raise error
                    else:
                        raise error
                
                elif error_rule.action == RecoveryAction.GRACEFUL_DEGRADATION:
                    # Return partial result or safe default
                    degraded_result = await self._graceful_degradation(context, error)
                    return degraded_result
                
                elif error_rule.action == RecoveryAction.RETRY:
                    retry_config = error_rule.retry_config or RetryConfig()
                    
                    if attempt >= retry_config.max_attempts:
                        logger.error(f"Max retry attempts reached for {service_id}")
                        circuit_breaker.record_failure()
                        raise error
                    
                    # Calculate delay
                    delay = retry_config.calculate_delay(attempt)
                    
                    logger.info(f"Retrying operation in {delay:.2f}s (attempt {attempt + 1})")
                    await asyncio.sleep(delay)
                    continue
        
        # Should not reach here, but handle it gracefully
        circuit_breaker.record_failure()
        raise last_error
    
    async def _graceful_degradation(self, context: ErrorContext, error: Exception) -> Dict[str, Any]:
        """Handle graceful degradation"""
        logger.warning(f"Graceful degradation for {context.operation}: {error}")
        
        # Return safe default response
        return {
            "success": False,
            "error": str(error),
            "degraded": True,
            "operation": context.operation,
            "client_type": context.client_type,
            "tool_name": context.tool_name,
            "message": "Service temporarily unavailable, returning safe default"
        }
    
    def _update_error_stats(self, error_rule: ErrorRule):
        """Update error statistics"""
        self.error_stats["total_errors"] += 1
        
        # Update category stats
        category = error_rule.category.value
        if category not in self.error_stats["errors_by_category"]:
            self.error_stats["errors_by_category"][category] = 0
        self.error_stats["errors_by_category"][category] += 1
        
        # Update severity stats
        severity = error_rule.severity.value
        if severity not in self.error_stats["errors_by_severity"]:
            self.error_stats["errors_by_severity"][severity] = 0
        self.error_stats["errors_by_severity"][severity] += 1
        
        # Update recovery action stats
        action = error_rule.action.value
        if action not in self.error_stats["recovery_actions"]:
            self.error_stats["recovery_actions"][action] = 0
        self.error_stats["recovery_actions"][action] += 1
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get comprehensive error statistics"""
        circuit_breaker_stats = {}
        
        for service_id, cb in self.circuit_breakers.items():
            circuit_breaker_stats[service_id] = {
                "state": cb.state,
                "failure_count": cb.failure_count,
                "last_failure_time": cb.last_failure_time,
                "threshold": cb.failure_threshold
            }
        
        return {
            "error_stats": self.error_stats,
            "circuit_breakers": circuit_breaker_stats,
            "error_rules": len(self.error_rules),
            "total_services": len(self.circuit_breakers)
        }
    
    def get_service_health(self) -> Dict[str, Any]:
        """Get health status of all services"""
        health_status = {}
        
        for service_id, cb in self.circuit_breakers.items():
            if cb.state == "closed":
                health = "healthy"
            elif cb.state == "half-open":
                health = "recovering"
            else:
                health = "unhealthy"
            
            health_status[service_id] = {
                "health": health,
                "failure_count": cb.failure_count,
                "last_failure": cb.last_failure_time
            }
        
        return health_status
    
    def reset_circuit_breaker(self, service_id: str):
        """Manually reset circuit breaker"""
        if service_id in self.circuit_breakers:
            cb = self.circuit_breakers[service_id]
            cb.failure_count = 0
            cb.state = "closed"
            logger.info(f"Reset circuit breaker for {service_id}")
    
    def create_error_context(self, 
                           operation: str,
                           client_type: str,
                           tool_name: str,
                           parameters: Dict[str, Any]) -> ErrorContext:
        """Create error context for operation"""
        return ErrorContext(
            operation=operation,
            client_type=client_type,
            tool_name=tool_name,
            parameters=parameters,
            attempt_number=0,
            start_time=time.time()
        )


class ResilientMCPClient:
    """
    Wrapper for MCP clients that adds resilient error handling.
    """
    
    def __init__(self, client, error_handler: EnhancedErrorHandler):
        self.client = client
        self.error_handler = error_handler
        self.client_type = getattr(client, 'client_type', 'unknown')
    
    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Call tool with resilient error handling"""
        
        # Create error context
        context = self.error_handler.create_error_context(
            operation=f"call_tool",
            client_type=self.client_type,
            tool_name=tool_name,
            parameters=parameters
        )
        
        # Define operation
        async def operation():
            return await self.client.call_tool(tool_name, parameters)
        
        # Execute with error handling
        return await self.error_handler.handle_with_retry(
            operation=operation,
            context=context,
            service_id=f"{self.client_type}:{tool_name}"
        )
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics for this client"""
        return self.error_handler.get_error_stats()
    
    def __getattr__(self, name):
        """Delegate other attributes to wrapped client"""
        return getattr(self.client, name)