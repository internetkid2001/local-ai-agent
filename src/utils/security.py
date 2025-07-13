"""
Security Manager

Provides security utilities, path validation, and permission management
for the Local AI Agent.

Author: Claude Code
Date: 2025-07-13
Session: 1.1
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PermissionLevel(Enum):
    """Permission levels for operations"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"


class SecurityError(Exception):
    """Raised when security policy is violated"""
    pass


class SecurityManager:
    """
    Manages security policies and validates operations.
    
    Features:
    - Path traversal prevention
    - File access validation
    - Command injection prevention
    - Permission checking
    - Audit logging
    - Sandbox enforcement
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize security manager.
        
        Args:
            config: Security configuration
        """
        self.config = config
        self.sandbox_enabled = config.get('sandbox_enabled', True)
        self.require_confirmation = config.get('require_confirmation', True)
        
        # Path configuration
        self.allowed_paths = self._normalize_paths(config.get('allowed_paths', []))
        self.forbidden_paths = self._normalize_paths(config.get('forbidden_paths', []))
        
        # Operations requiring confirmation
        self.confirmation_required = set(config.get('require_confirmation_for', []))
        
        # File size limits
        self.max_file_size = config.get('max_file_size_mb', 100) * 1024 * 1024
        
        # Dangerous command patterns
        self.dangerous_commands = {
            r'rm\s+-rf\s+/',
            r'mkfs\.',
            r'dd\s+if=.*of=/dev/',
            r':(){ :|:& };:',  # Fork bomb
            r'sudo\s+',
            r'chmod\s+777',
            r'chown\s+.*:.*\s+/',
            r'mount\s+',
            r'umount\s+'
        }
        
        logger.info("Security manager initialized")
        logger.info(f"Sandbox enabled: {self.sandbox_enabled}")
        logger.info(f"Confirmation required: {self.require_confirmation}")
        logger.info(f"Allowed paths: {len(self.allowed_paths)}")
    
    def validate_file_path(self, path: str, operation: str = "read") -> Path:
        """
        Validate file path against security policies.
        
        Args:
            path: File path to validate
            operation: Type of operation (read, write, execute)
            
        Returns:
            Validated and normalized Path object
            
        Raises:
            SecurityError: If path violates security policy
        """
        # Normalize and resolve path
        try:
            normalized_path = Path(path).expanduser().resolve()
        except Exception as e:
            raise SecurityError(f"Invalid path: {path} - {e}")
        
        # Check for path traversal attempts
        if self._is_path_traversal(path):
            logger.warning(f"Path traversal attempt blocked: {path}")
            raise SecurityError(f"Path traversal not allowed: {path}")
        
        # Check against forbidden paths
        if self._is_forbidden_path(normalized_path):
            logger.warning(f"Access to forbidden path blocked: {normalized_path}")
            raise SecurityError(f"Access denied to forbidden path: {normalized_path}")
        
        # Check against allowed paths (if sandbox enabled)
        if self.sandbox_enabled and not self._is_allowed_path(normalized_path):
            logger.warning(f"Access outside sandbox blocked: {normalized_path}")
            raise SecurityError(f"Path outside allowed sandbox: {normalized_path}")
        
        # Check file size for read operations
        if operation == "read" and normalized_path.exists():
            if normalized_path.stat().st_size > self.max_file_size:
                raise SecurityError(f"File too large: {normalized_path}")
        
        logger.debug(f"Path validation passed: {normalized_path} ({operation})")
        return normalized_path
    
    def validate_command(self, command: str) -> str:
        """
        Validate command for dangerous patterns.
        
        Args:
            command: Command string to validate
            
        Returns:
            Sanitized command
            
        Raises:
            SecurityError: If command contains dangerous patterns
        """
        # Check for dangerous command patterns
        for pattern in self.dangerous_commands:
            if re.search(pattern, command, re.IGNORECASE):
                logger.error(f"Dangerous command blocked: {command}")
                raise SecurityError(f"Dangerous command pattern detected: {pattern}")
        
        # Basic injection prevention
        if self._has_command_injection(command):
            logger.error(f"Command injection attempt blocked: {command}")
            raise SecurityError("Command injection attempt detected")
        
        logger.debug(f"Command validation passed: {command}")
        return command
    
    def check_permission(self, operation: str, context: Dict[str, Any] = None) -> bool:
        """
        Check if operation requires permission confirmation.
        
        Args:
            operation: Operation type
            context: Additional context for permission check
            
        Returns:
            True if permission granted, False if confirmation needed
        """
        if not self.require_confirmation:
            return True
        
        if operation in self.confirmation_required:
            logger.info(f"Operation requires confirmation: {operation}")
            return self._request_confirmation(operation, context)
        
        return True
    
    def audit_log(self, operation: str, details: Dict[str, Any], success: bool = True):
        """
        Log security audit event.
        
        Args:
            operation: Operation performed
            details: Operation details
            success: Whether operation succeeded
        """
        log_level = "INFO" if success else "ERROR"
        event_type = f"AUDIT_{operation.upper()}"
        
        audit_details = {
            'operation': operation,
            'success': success,
            'user': os.getenv('USER', 'unknown'),
            'pid': os.getpid(),
            **details
        }
        
        from .logger import log_security_event
        log_security_event(event_type, audit_details, log_level)
    
    def sanitize_input(self, input_data: Any) -> Any:
        """
        Sanitize input data to remove potential security threats.
        
        Args:
            input_data: Data to sanitize
            
        Returns:
            Sanitized data
        """
        if isinstance(input_data, str):
            # Remove null bytes
            sanitized = input_data.replace('\x00', '')
            
            # Limit length
            max_length = 10000
            if len(sanitized) > max_length:
                sanitized = sanitized[:max_length]
                logger.warning(f"Input truncated to {max_length} characters")
            
            return sanitized
        
        elif isinstance(input_data, dict):
            return {k: self.sanitize_input(v) for k, v in input_data.items()}
        
        elif isinstance(input_data, list):
            return [self.sanitize_input(item) for item in input_data]
        
        else:
            return input_data
    
    def _normalize_paths(self, paths: List[str]) -> List[Path]:
        """Normalize and expand user paths"""
        normalized = []
        for path_str in paths:
            try:
                path = Path(path_str).expanduser().resolve()
                normalized.append(path)
            except Exception as e:
                logger.warning(f"Invalid path in configuration: {path_str} - {e}")
        return normalized
    
    def _is_path_traversal(self, path: str) -> bool:
        """Check for path traversal patterns"""
        traversal_patterns = [
            '../', '..\\', 
            '%2e%2e%2f', '%2e%2e%5c',  # URL encoded
            '..%2f', '..%5c',
            '%252e%252e%252f'  # Double URL encoded
        ]
        
        path_lower = path.lower()
        return any(pattern in path_lower for pattern in traversal_patterns)
    
    def _is_forbidden_path(self, path: Path) -> bool:
        """Check if path is in forbidden list"""
        for forbidden in self.forbidden_paths:
            try:
                if path == forbidden or forbidden in path.parents:
                    return True
            except Exception:
                continue
        return False
    
    def _is_allowed_path(self, path: Path) -> bool:
        """Check if path is in allowed list"""
        if not self.allowed_paths:
            return True  # No restrictions if no allowed paths specified
        
        for allowed in self.allowed_paths:
            try:
                if path == allowed or allowed in path.parents or path in allowed.parents:
                    return True
            except Exception:
                continue
        return False
    
    def _has_command_injection(self, command: str) -> bool:
        """Check for command injection patterns"""
        injection_patterns = [
            ';', '&&', '||', '|', 
            '$(', '`', 
            '${', '}',
            'eval', 'exec'
        ]
        
        # Allow some safe patterns in specific contexts
        safe_contexts = ['echo', 'printf']
        if any(command.strip().startswith(ctx) for ctx in safe_contexts):
            return False
        
        return any(pattern in command for pattern in injection_patterns)
    
    def _request_confirmation(self, operation: str, context: Dict[str, Any] = None) -> bool:
        """
        Request user confirmation for operation.
        
        This is a placeholder implementation. In a real system, this would
        integrate with the UI to prompt for user confirmation.
        
        Args:
            operation: Operation requiring confirmation
            context: Additional context
            
        Returns:
            True if confirmed, False otherwise
        """
        logger.warning(f"Operation requires confirmation: {operation}")
        logger.info(f"Context: {context}")
        
        # For now, auto-approve in development
        # TODO: Implement actual user confirmation mechanism
        return True