#!/usr/bin/env python3
"""
Advanced Logging Manager

Structured logging system with correlation IDs, distributed tracing support,
and comprehensive audit trails for enterprise applications.

Author: Claude Code
Date: 2025-07-14
Phase: 4.7 - Enhanced Error Handling
"""

import asyncio
import logging
import json
import time
import threading
import uuid
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
import traceback
from pathlib import Path
import queue
import os
from datetime import datetime, timezone
from contextlib import contextmanager
from contextvars import ContextVar

# Context variable for correlation ID
correlation_context: ContextVar[str] = ContextVar('correlation_id', default='')


class LogLevel(Enum):
    """Enhanced log levels"""
    TRACE = 5
    DEBUG = 10
    INFO = 20
    WARN = 30
    ERROR = 40
    CRITICAL = 50
    AUDIT = 60


class LogCategory(Enum):
    """Log categories for filtering and analysis"""
    SYSTEM = "system"
    SECURITY = "security"
    PERFORMANCE = "performance"
    BUSINESS = "business"
    AUDIT = "audit"
    INTEGRATION = "integration"
    USER = "user"


@dataclass
class LogEntry:
    """Structured log entry"""
    timestamp: float
    level: LogLevel
    category: LogCategory
    message: str
    correlation_id: str
    component: str
    operation: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    
    # Additional context
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    # Error information
    exception_type: Optional[str] = None
    exception_message: Optional[str] = None
    stack_trace: Optional[str] = None
    
    # Performance metrics
    duration: Optional[float] = None
    memory_usage: Optional[int] = None
    cpu_usage: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to dictionary"""
        entry_dict = asdict(self)
        entry_dict['timestamp_iso'] = datetime.fromtimestamp(
            self.timestamp, tz=timezone.utc
        ).isoformat()
        entry_dict['level'] = self.level.name
        entry_dict['category'] = self.category.value
        return entry_dict
    
    def to_json(self) -> str:
        """Convert log entry to JSON string"""
        return json.dumps(self.to_dict())


@dataclass
class LogConfig:
    """Logging configuration"""
    log_level: LogLevel = LogLevel.INFO
    log_dir: str = "logs"
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    max_files: int = 10
    buffer_size: int = 1000
    flush_interval: float = 1.0
    
    # Output formats
    console_format: str = "structured"  # structured, json, simple
    file_format: str = "json"
    
    # Filters
    enabled_categories: List[LogCategory] = field(default_factory=lambda: list(LogCategory))
    
    # Correlation ID settings
    correlation_id_header: str = "X-Correlation-ID"
    generate_correlation_ids: bool = True
    
    # Performance monitoring
    enable_performance_logging: bool = True
    slow_operation_threshold: float = 1.0
    
    # Security settings
    mask_sensitive_data: bool = True
    sensitive_fields: List[str] = field(default_factory=lambda: [
        "password", "token", "secret", "key", "auth", "credential"
    ])


class LogHandler:
    """Base class for log handlers"""
    
    def __init__(self, config: LogConfig):
        self.config = config
        self.enabled = True
    
    async def handle(self, entry: LogEntry):
        """Handle log entry"""
        raise NotImplementedError
    
    async def flush(self):
        """Flush any buffered logs"""
        pass
    
    async def close(self):
        """Close handler and clean up resources"""
        pass


class ConsoleLogHandler(LogHandler):
    """Console output handler"""
    
    def __init__(self, config: LogConfig):
        super().__init__(config)
        self.lock = threading.Lock()
    
    async def handle(self, entry: LogEntry):
        """Handle console output"""
        if not self.enabled:
            return
        
        try:
            if self.config.console_format == "json":
                output = entry.to_json()
            elif self.config.console_format == "structured":
                output = self._format_structured(entry)
            else:  # simple
                output = self._format_simple(entry)
            
            with self.lock:
                print(output)
                
        except Exception as e:
            print(f"Error in console log handler: {e}")
    
    def _format_structured(self, entry: LogEntry) -> str:
        """Format entry in structured format"""
        timestamp = datetime.fromtimestamp(entry.timestamp, tz=timezone.utc)
        
        parts = [
            timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            f"[{entry.correlation_id[:8]}]",
            f"{entry.level.name}",
            f"{entry.category.value}",
            f"{entry.component}",
            f"{entry.operation}",
            entry.message
        ]
        
        if entry.duration:
            parts.append(f"({entry.duration:.3f}s)")
        
        return " | ".join(parts)
    
    def _format_simple(self, entry: LogEntry) -> str:
        """Format entry in simple format"""
        timestamp = datetime.fromtimestamp(entry.timestamp, tz=timezone.utc)
        return f"{timestamp.strftime('%H:%M:%S')} {entry.level.name} {entry.message}"


class FileLogHandler(LogHandler):
    """File output handler with rotation"""
    
    def __init__(self, config: LogConfig):
        super().__init__(config)
        self.log_dir = Path(config.log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.current_file = None
        self.current_size = 0
        self.buffer = []
        self.lock = threading.Lock()
        self.last_flush = time.time()
    
    async def handle(self, entry: LogEntry):
        """Handle file output"""
        if not self.enabled:
            return
        
        try:
            log_line = entry.to_json() + "\n"
            
            with self.lock:
                self.buffer.append(log_line)
                
                # Check if we need to flush
                if (len(self.buffer) >= self.config.buffer_size or 
                    time.time() - self.last_flush > self.config.flush_interval):
                    await self._flush_buffer()
                    
        except Exception as e:
            print(f"Error in file log handler: {e}")
    
    async def _flush_buffer(self):
        """Flush buffer to file"""
        if not self.buffer:
            return
        
        try:
            # Ensure we have a current file
            if not self.current_file:
                self._rotate_if_needed()
            
            # Write buffer to file
            with open(self.current_file, 'a') as f:
                for line in self.buffer:
                    f.write(line)
                    self.current_size += len(line.encode('utf-8'))
            
            self.buffer.clear()
            self.last_flush = time.time()
            
            # Check if rotation is needed
            if self.current_size > self.config.max_file_size:
                self._rotate_if_needed()
                
        except Exception as e:
            print(f"Error flushing log buffer: {e}")
    
    def _rotate_if_needed(self):
        """Rotate log file if needed"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"app_{timestamp}.log"
        new_file = self.log_dir / filename
        
        self.current_file = new_file
        self.current_size = 0
        
        # Clean up old files
        self._cleanup_old_files()
    
    def _cleanup_old_files(self):
        """Clean up old log files"""
        try:
            log_files = sorted(self.log_dir.glob("app_*.log"))
            
            if len(log_files) > self.config.max_files:
                files_to_remove = log_files[:-self.config.max_files]
                for file_path in files_to_remove:
                    file_path.unlink()
                    
        except Exception as e:
            print(f"Error cleaning up old log files: {e}")
    
    async def flush(self):
        """Flush any buffered logs"""
        with self.lock:
            await self._flush_buffer()
    
    async def close(self):
        """Close handler and flush remaining logs"""
        await self.flush()


class AdvancedLoggingManager:
    """
    Advanced logging manager with enterprise features.
    
    Features:
    - Structured logging with correlation IDs
    - Multiple output handlers (console, file, external)
    - Distributed tracing support
    - Performance monitoring integration
    - Security-aware logging with data masking
    - Audit trail capabilities
    - Real-time log aggregation
    """
    
    def __init__(self, config: LogConfig = None):
        self.config = config or LogConfig()
        self.handlers: List[LogHandler] = []
        self.metrics = {
            "total_logs": 0,
            "logs_by_level": {},
            "logs_by_category": {},
            "error_count": 0,
            "slow_operations": 0
        }
        
        # Thread-safe metrics
        self._metrics_lock = threading.Lock()
        
        # Correlation ID management
        self._correlation_counter = 0
        self._correlation_lock = threading.Lock()
        
        # Background tasks
        self._flush_task = None
        self._running = False
        
        # Initialize handlers
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup default log handlers"""
        # Console handler
        console_handler = ConsoleLogHandler(self.config)
        self.handlers.append(console_handler)
        
        # File handler
        file_handler = FileLogHandler(self.config)
        self.handlers.append(file_handler)
    
    async def initialize(self):
        """Initialize logging manager"""
        self._running = True
        
        # Start background flush task
        self._flush_task = asyncio.create_task(self._flush_loop())
        
        # Log initialization
        await self.log(
            level=LogLevel.INFO,
            category=LogCategory.SYSTEM,
            message="Advanced logging manager initialized",
            component="logging_manager",
            operation="initialize"
        )
    
    def generate_correlation_id(self) -> str:
        """Generate unique correlation ID"""
        with self._correlation_lock:
            self._correlation_counter += 1
            return f"log-{int(time.time())}-{self._correlation_counter:08d}"
    
    def set_correlation_id(self, correlation_id: str):
        """Set correlation ID in context"""
        correlation_context.set(correlation_id)
    
    def get_correlation_id(self) -> str:
        """Get current correlation ID"""
        return correlation_context.get()
    
    @contextmanager
    def correlation_context_manager(self, correlation_id: str = None):
        """Context manager for correlation ID"""
        if correlation_id is None:
            correlation_id = self.generate_correlation_id()
        
        token = correlation_context.set(correlation_id)
        try:
            yield correlation_id
        finally:
            correlation_context.reset(token)
    
    def _mask_sensitive_data(self, data: Any) -> Any:
        """Mask sensitive data in log entries"""
        if not self.config.mask_sensitive_data:
            return data
        
        if isinstance(data, dict):
            masked_data = {}
            for key, value in data.items():
                if any(sensitive in key.lower() for sensitive in self.config.sensitive_fields):
                    masked_data[key] = "***MASKED***"
                else:
                    masked_data[key] = self._mask_sensitive_data(value)
            return masked_data
        elif isinstance(data, list):
            return [self._mask_sensitive_data(item) for item in data]
        else:
            return data
    
    def _update_metrics(self, entry: LogEntry):
        """Update logging metrics"""
        with self._metrics_lock:
            self.metrics["total_logs"] += 1
            
            # Update level metrics
            level_name = entry.level.name
            if level_name not in self.metrics["logs_by_level"]:
                self.metrics["logs_by_level"][level_name] = 0
            self.metrics["logs_by_level"][level_name] += 1
            
            # Update category metrics
            category_name = entry.category.value
            if category_name not in self.metrics["logs_by_category"]:
                self.metrics["logs_by_category"][category_name] = 0
            self.metrics["logs_by_category"][category_name] += 1
            
            # Update error count
            if entry.level in [LogLevel.ERROR, LogLevel.CRITICAL]:
                self.metrics["error_count"] += 1
            
            # Update slow operations
            if entry.duration and entry.duration > self.config.slow_operation_threshold:
                self.metrics["slow_operations"] += 1
    
    async def log(self,
                  level: LogLevel,
                  category: LogCategory,
                  message: str,
                  component: str,
                  operation: str,
                  correlation_id: str = None,
                  user_id: str = None,
                  session_id: str = None,
                  trace_id: str = None,
                  span_id: str = None,
                  metadata: Dict[str, Any] = None,
                  tags: List[str] = None,
                  exception: Exception = None,
                  duration: float = None,
                  memory_usage: int = None,
                  cpu_usage: float = None):
        """Log structured entry"""
        
        # Get correlation ID
        if correlation_id is None:
            correlation_id = self.get_correlation_id()
            if not correlation_id and self.config.generate_correlation_ids:
                correlation_id = self.generate_correlation_id()
        
        # Mask sensitive data
        if metadata:
            metadata = self._mask_sensitive_data(metadata)
        
        # Create log entry
        entry = LogEntry(
            timestamp=time.time(),
            level=level,
            category=category,
            message=message,
            correlation_id=correlation_id,
            component=component,
            operation=operation,
            user_id=user_id,
            session_id=session_id,
            trace_id=trace_id,
            span_id=span_id,
            metadata=metadata or {},
            tags=tags or [],
            duration=duration,
            memory_usage=memory_usage,
            cpu_usage=cpu_usage
        )
        
        # Add exception information
        if exception:
            entry.exception_type = type(exception).__name__
            entry.exception_message = str(exception)
            entry.stack_trace = traceback.format_exc()
        
        # Check if logging is enabled for this level and category
        if level.value < self.config.log_level.value:
            return
        
        if category not in self.config.enabled_categories:
            return
        
        # Update metrics
        self._update_metrics(entry)
        
        # Send to handlers
        for handler in self.handlers:
            try:
                await handler.handle(entry)
            except Exception as e:
                print(f"Error in log handler: {e}")
    
    async def trace(self, message: str, **kwargs):
        """Log trace message"""
        await self.log(LogLevel.TRACE, LogCategory.SYSTEM, message, **kwargs)
    
    async def debug(self, message: str, **kwargs):
        """Log debug message"""
        await self.log(LogLevel.DEBUG, LogCategory.SYSTEM, message, **kwargs)
    
    async def info(self, message: str, **kwargs):
        """Log info message"""
        await self.log(LogLevel.INFO, LogCategory.SYSTEM, message, **kwargs)
    
    async def warn(self, message: str, **kwargs):
        """Log warning message"""
        await self.log(LogLevel.WARN, LogCategory.SYSTEM, message, **kwargs)
    
    async def error(self, message: str, **kwargs):
        """Log error message"""
        await self.log(LogLevel.ERROR, LogCategory.SYSTEM, message, **kwargs)
    
    async def critical(self, message: str, **kwargs):
        """Log critical message"""
        await self.log(LogLevel.CRITICAL, LogCategory.SYSTEM, message, **kwargs)
    
    async def audit(self, message: str, **kwargs):
        """Log audit message"""
        await self.log(LogLevel.AUDIT, LogCategory.AUDIT, message, **kwargs)
    
    async def performance(self, message: str, duration: float, **kwargs):
        """Log performance message"""
        await self.log(
            LogLevel.INFO, 
            LogCategory.PERFORMANCE, 
            message, 
            duration=duration, 
            **kwargs
        )
    
    async def security(self, message: str, **kwargs):
        """Log security message"""
        await self.log(LogLevel.WARN, LogCategory.SECURITY, message, **kwargs)
    
    def operation_timer(self, operation: str, component: str = "unknown"):
        """Context manager for timing operations"""
        return OperationTimer(self, operation, component)
    
    async def _flush_loop(self):
        """Background task to flush handlers"""
        while self._running:
            try:
                await asyncio.sleep(self.config.flush_interval)
                
                for handler in self.handlers:
                    await handler.flush()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in flush loop: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get logging metrics"""
        with self._metrics_lock:
            return self.metrics.copy()
    
    def add_handler(self, handler: LogHandler):
        """Add custom log handler"""
        self.handlers.append(handler)
    
    def remove_handler(self, handler: LogHandler):
        """Remove log handler"""
        if handler in self.handlers:
            self.handlers.remove(handler)
    
    async def shutdown(self):
        """Shutdown logging manager"""
        self._running = False
        
        # Cancel flush task
        if self._flush_task:
            self._flush_task.cancel()
        
        # Close all handlers
        for handler in self.handlers:
            await handler.close()
        
        # Final log
        await self.log(
            level=LogLevel.INFO,
            category=LogCategory.SYSTEM,
            message="Advanced logging manager shutdown",
            component="logging_manager",
            operation="shutdown"
        )


class OperationTimer:
    """Context manager for timing operations"""
    
    def __init__(self, logger: AdvancedLoggingManager, operation: str, component: str):
        self.logger = logger
        self.operation = operation
        self.component = component
        self.start_time = None
    
    async def __aenter__(self):
        self.start_time = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            
            if exc_type:
                await self.logger.error(
                    f"Operation {self.operation} failed",
                    component=self.component,
                    operation=self.operation,
                    duration=duration,
                    exception=exc_val
                )
            else:
                await self.logger.performance(
                    f"Operation {self.operation} completed",
                    duration=duration,
                    component=self.component,
                    operation=self.operation
                )


# Global logging manager instance
_global_logger: Optional[AdvancedLoggingManager] = None


def get_logger() -> AdvancedLoggingManager:
    """Get global logging manager instance"""
    global _global_logger
    if _global_logger is None:
        _global_logger = AdvancedLoggingManager()
    return _global_logger


def setup_logging(config: LogConfig = None):
    """Setup global logging configuration"""
    global _global_logger
    _global_logger = AdvancedLoggingManager(config)
    return _global_logger