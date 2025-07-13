"""
Logging Framework

Centralized logging configuration and utilities for the Local AI Agent.
Provides structured logging with component-specific levels and formatters.

Author: Claude Code
Date: 2025-07-13
Session: 1.1
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import os


class ColoredFormatter(logging.Formatter):
    """Formatter that adds color to log messages for console output"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        if hasattr(record, 'levelname') and record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)


class SecurityFilter(logging.Filter):
    """Filter to remove sensitive information from logs"""
    
    SENSITIVE_PATTERNS = [
        'password', 'token', 'api_key', 'secret', 'auth',
        'credential', 'private_key', 'ssh_key'
    ]
    
    def filter(self, record):
        """Filter log record to remove sensitive information"""
        if hasattr(record, 'msg'):
            msg = str(record.msg).lower()
            for pattern in self.SENSITIVE_PATTERNS:
                if pattern in msg:
                    record.msg = f"[REDACTED - contains '{pattern}']"
                    break
        return True


class LogManager:
    """
    Manages logging configuration for the entire application.
    
    Features:
    - Component-specific log levels
    - Multiple output handlers (console, file, rotating file)
    - Security filtering for sensitive data
    - Structured logging format
    - Performance monitoring integration
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize log manager with configuration.
        
        Args:
            config: Logging configuration dictionary
        """
        self.config = config
        self._loggers: Dict[str, logging.Logger] = {}
        self._setup_root_logger()
    
    def setup_logging(self) -> None:
        """Set up logging configuration for the entire application"""
        # Get configuration values
        log_level = self.config.get('level', 'INFO')
        log_file = self.config.get('file', '~/.local/share/ai-agent/agent.log')
        max_size_mb = self.config.get('max_size_mb', 100)
        backup_count = self.config.get('backup_count', 5)
        log_format = self.config.get('format', 
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        date_format = self.config.get('date_format', '%Y-%m-%d %H:%M:%S')
        
        # Expand user path
        log_file_path = Path(log_file).expanduser()
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create formatters
        file_formatter = logging.Formatter(log_format, date_format)
        console_formatter = ColoredFormatter(log_format, date_format)
        
        # Set up root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper()))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_handler.setFormatter(console_formatter)
        console_handler.addFilter(SecurityFilter())
        root_logger.addHandler(console_handler)
        
        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path,
            maxBytes=max_size_mb * 1024 * 1024,
            backupCount=backup_count
        )
        file_handler.setLevel(logging.DEBUG)  # Log everything to file
        file_handler.setFormatter(file_formatter)
        file_handler.addFilter(SecurityFilter())
        root_logger.addHandler(file_handler)
        
        # Set up component-specific loggers
        self._setup_component_loggers()
        
        # Log startup message
        logger = logging.getLogger(__name__)
        logger.info("Logging system initialized")
        logger.info(f"Log file: {log_file_path}")
        logger.info(f"Console log level: {log_level}")
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get or create a logger for a specific component.
        
        Args:
            name: Logger name (typically module name)
            
        Returns:
            Configured logger instance
        """
        if name not in self._loggers:
            logger = logging.getLogger(name)
            
            # Set component-specific level if configured
            component_levels = self.config.get('components', {})
            if name in component_levels:
                level = component_levels[name].upper()
                logger.setLevel(getattr(logging, level))
            
            self._loggers[name] = logger
        
        return self._loggers[name]
    
    def _setup_root_logger(self):
        """Set up the root logger with basic configuration"""
        # Prevent duplicate setup
        if hasattr(logging.getLogger(), '_ai_agent_configured'):
            return
        
        logging.getLogger()._ai_agent_configured = True
    
    def _setup_component_loggers(self):
        """Set up component-specific loggers"""
        component_levels = self.config.get('components', {})
        
        for component, level in component_levels.items():
            logger = logging.getLogger(component)
            logger.setLevel(getattr(logging, level.upper()))
            
            # Add component-specific handlers if needed
            if component == 'security':
                # Security component gets extra scrutiny
                security_handler = self._create_security_handler()
                if security_handler:
                    logger.addHandler(security_handler)
    
    def _create_security_handler(self) -> Optional[logging.Handler]:
        """Create a special handler for security-related logs"""
        try:
            security_log_path = Path("~/.local/share/ai-agent/security.log").expanduser()
            security_log_path.parent.mkdir(parents=True, exist_ok=True)
            
            handler = logging.handlers.RotatingFileHandler(
                security_log_path,
                maxBytes=50 * 1024 * 1024,  # 50MB
                backupCount=10
            )
            
            # More detailed format for security logs
            security_format = (
                '%(asctime)s - %(name)s - %(levelname)s - '
                '[PID:%(process)d] [%(filename)s:%(lineno)d] - %(message)s'
            )
            handler.setFormatter(logging.Formatter(security_format))
            handler.setLevel(logging.INFO)
            
            return handler
            
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to create security handler: {e}")
            return None


# Global log manager instance
_log_manager: Optional[LogManager] = None


def setup_logging(config: Dict[str, Any]) -> None:
    """
    Set up logging for the entire application.
    
    Args:
        config: Logging configuration dictionary
    """
    global _log_manager
    _log_manager = LogManager(config)
    _log_manager.setup_logging()


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific component.
    
    Args:
        name: Logger name
        
    Returns:
        Configured logger instance
    """
    global _log_manager
    
    if _log_manager is None:
        # Fallback to basic logging if not configured
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(name)
    
    return _log_manager.get_logger(name)


def log_performance(operation: str, duration: float, **kwargs):
    """
    Log performance metrics for operations.
    
    Args:
        operation: Name of the operation
        duration: Duration in seconds
        **kwargs: Additional metrics to log
    """
    perf_logger = get_logger('performance')
    
    metrics = {'duration': f'{duration:.3f}s'}
    metrics.update(kwargs)
    
    metric_str = ', '.join(f'{k}={v}' for k, v in metrics.items())
    perf_logger.info(f"Performance [{operation}]: {metric_str}")


def log_security_event(event_type: str, details: Dict[str, Any], level: str = 'INFO'):
    """
    Log security-related events with structured format.
    
    Args:
        event_type: Type of security event
        details: Event details
        level: Log level (INFO, WARNING, ERROR)
    """
    security_logger = get_logger('security')
    
    # Sanitize details to remove sensitive information
    sanitized_details = {}
    for key, value in details.items():
        if any(sensitive in key.lower() for sensitive in ['password', 'token', 'key']):
            sanitized_details[key] = '[REDACTED]'
        else:
            sanitized_details[key] = value
    
    log_level = getattr(logging, level.upper())
    security_logger.log(log_level, f"Security Event [{event_type}]: {sanitized_details}")


def configure_third_party_loggers():
    """Configure third-party library loggers to reduce noise"""
    # Reduce websockets verbosity
    logging.getLogger('websockets').setLevel(logging.WARNING)
    
    # Reduce HTTP client verbosity
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    # Reduce async library verbosity
    logging.getLogger('asyncio').setLevel(logging.WARNING)