"""
Permission Manager

Security framework for managing permissions and access controls for MCP operations.

Author: Claude Code
Date: 2025-07-13
Phase: 2.1
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

from ..utils.logger import get_logger

logger = get_logger(__name__)


class PermissionLevel(Enum):
    """Permission levels for operations"""
    DENIED = "denied"
    READ_ONLY = "read_only" 
    LIMITED = "limited"
    FULL = "full"
    ADMIN = "admin"


class OperationType(Enum):
    """Types of operations that can be controlled"""
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    DIRECTORY_CREATE = "directory_create"
    PROCESS_LIST = "process_list"
    PROCESS_KILL = "process_kill"
    SYSTEM_MONITOR = "system_monitor"
    DESKTOP_INTERACT = "desktop_interact"
    CLIPBOARD_ACCESS = "clipboard_access"
    SCREENSHOT = "screenshot"
    NETWORK_ACCESS = "network_access"
    LOG_ACCESS = "log_access"


@dataclass
class PermissionRule:
    """Individual permission rule"""
    operation: OperationType
    level: PermissionLevel
    conditions: Dict[str, Any] = None
    description: str = ""
    
    def __post_init__(self):
        if self.conditions is None:
            self.conditions = {}


@dataclass
class SecurityProfile:
    """Security profile containing permission rules"""
    name: str
    description: str
    rules: List[PermissionRule]
    blocked_paths: List[str] = None
    blocked_processes: List[str] = None
    allowed_hosts: List[str] = None
    max_file_size: int = 100 * 1024 * 1024  # 100MB default
    
    def __post_init__(self):
        if self.blocked_paths is None:
            self.blocked_paths = []
        if self.blocked_processes is None:
            self.blocked_processes = []
        if self.allowed_hosts is None:
            self.allowed_hosts = []


class PermissionManager:
    """
    Manages security permissions and access controls for MCP operations.
    
    Features:
    - Role-based permission system
    - Path-based access controls
    - Process operation restrictions
    - Network access controls
    - Audit logging
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize permission manager.
        
        Args:
            config_path: Path to security configuration file
        """
        self.config_path = config_path
        self.profiles: Dict[str, SecurityProfile] = {}
        self.current_profile: Optional[SecurityProfile] = None
        self.audit_log: List[Dict[str, Any]] = []
        
        # Load default profiles
        self._create_default_profiles()
        
        # Load custom configuration if provided
        if config_path and os.path.exists(config_path):
            self._load_config(config_path)
        
        # Set default profile
        self.set_profile("default")
        
        logger.info("Permission manager initialized")
    
    def _create_default_profiles(self):
        """Create default security profiles"""
        
        # Restrictive profile - minimal permissions
        restrictive_rules = [
            PermissionRule(OperationType.FILE_READ, PermissionLevel.LIMITED),
            PermissionRule(OperationType.FILE_WRITE, PermissionLevel.DENIED),
            PermissionRule(OperationType.FILE_DELETE, PermissionLevel.DENIED),
            PermissionRule(OperationType.DIRECTORY_CREATE, PermissionLevel.DENIED),
            PermissionRule(OperationType.PROCESS_LIST, PermissionLevel.READ_ONLY),
            PermissionRule(OperationType.PROCESS_KILL, PermissionLevel.DENIED),
            PermissionRule(OperationType.SYSTEM_MONITOR, PermissionLevel.READ_ONLY),
            PermissionRule(OperationType.DESKTOP_INTERACT, PermissionLevel.DENIED),
            PermissionRule(OperationType.CLIPBOARD_ACCESS, PermissionLevel.READ_ONLY),
            PermissionRule(OperationType.SCREENSHOT, PermissionLevel.LIMITED),
            PermissionRule(OperationType.NETWORK_ACCESS, PermissionLevel.DENIED),
            PermissionRule(OperationType.LOG_ACCESS, PermissionLevel.READ_ONLY)
        ]
        
        self.profiles["restrictive"] = SecurityProfile(
            name="restrictive",
            description="Minimal permissions for secure environments",
            rules=restrictive_rules,
            blocked_paths=["/etc", "/root", "/sys", "/proc", "/dev"],
            blocked_processes=["systemd", "kernel", "init", "ssh", "sudo"],
            max_file_size=10 * 1024 * 1024  # 10MB
        )
        
        # Default profile - balanced permissions
        default_rules = [
            PermissionRule(OperationType.FILE_READ, PermissionLevel.FULL),
            PermissionRule(OperationType.FILE_WRITE, PermissionLevel.LIMITED),
            PermissionRule(OperationType.FILE_DELETE, PermissionLevel.LIMITED),
            PermissionRule(OperationType.DIRECTORY_CREATE, PermissionLevel.LIMITED),
            PermissionRule(OperationType.PROCESS_LIST, PermissionLevel.FULL),
            PermissionRule(OperationType.PROCESS_KILL, PermissionLevel.LIMITED),
            PermissionRule(OperationType.SYSTEM_MONITOR, PermissionLevel.FULL),
            PermissionRule(OperationType.DESKTOP_INTERACT, PermissionLevel.LIMITED),
            PermissionRule(OperationType.CLIPBOARD_ACCESS, PermissionLevel.FULL),
            PermissionRule(OperationType.SCREENSHOT, PermissionLevel.FULL),
            PermissionRule(OperationType.NETWORK_ACCESS, PermissionLevel.LIMITED),
            PermissionRule(OperationType.LOG_ACCESS, PermissionLevel.FULL)
        ]
        
        self.profiles["default"] = SecurityProfile(
            name="default",
            description="Balanced permissions for general use",
            rules=default_rules,
            blocked_paths=["/etc/passwd", "/etc/shadow", "/root"],
            blocked_processes=["systemd", "kernel", "init"],
            allowed_hosts=["localhost", "127.0.0.1", "::1"]
        )
        
        # Development profile - full permissions for development
        dev_rules = [
            PermissionRule(operation, PermissionLevel.FULL) 
            for operation in OperationType
        ]
        
        self.profiles["development"] = SecurityProfile(
            name="development",
            description="Full permissions for development environments",
            rules=dev_rules,
            blocked_paths=[],
            blocked_processes=[],
            allowed_hosts=["*"],  # Allow all hosts
            max_file_size=1024 * 1024 * 1024  # 1GB
        )
    
    def set_profile(self, profile_name: str) -> bool:
        """
        Set the active security profile.
        
        Args:
            profile_name: Name of profile to activate
            
        Returns:
            True if profile was set successfully
        """
        if profile_name not in self.profiles:
            logger.error(f"Security profile not found: {profile_name}")
            return False
        
        self.current_profile = self.profiles[profile_name]
        logger.info(f"Activated security profile: {profile_name}")
        return True
    
    def check_permission(self, operation: OperationType, 
                        context: Dict[str, Any] = None) -> bool:
        """
        Check if an operation is permitted.
        
        Args:
            operation: Operation type to check
            context: Additional context for permission check
            
        Returns:
            True if operation is permitted
        """
        if not self.current_profile:
            logger.warning("No security profile active - denying operation")
            return False
        
        context = context or {}
        
        # Find applicable rule
        rule = self._find_rule(operation)
        if not rule:
            logger.warning(f"No rule found for operation: {operation.value}")
            return False
        
        # Check base permission level
        if rule.level == PermissionLevel.DENIED:
            self._log_audit(operation, context, False, "Denied by rule")
            return False
        
        if rule.level == PermissionLevel.ADMIN:
            # Admin level requires special authorization
            if not context.get("admin_authorized", False):
                self._log_audit(operation, context, False, "Admin authorization required")
                return False
        
        # Check operation-specific restrictions
        if not self._check_operation_restrictions(operation, context, rule):
            return False
        
        self._log_audit(operation, context, True, f"Allowed by {rule.level.value} rule")
        return True
    
    def _find_rule(self, operation: OperationType) -> Optional[PermissionRule]:
        """Find the applicable rule for an operation"""
        if not self.current_profile:
            return None
        
        for rule in self.current_profile.rules:
            if rule.operation == operation:
                return rule
        
        return None
    
    def _check_operation_restrictions(self, operation: OperationType, 
                                   context: Dict[str, Any], 
                                   rule: PermissionRule) -> bool:
        """Check operation-specific restrictions"""
        
        # File operation restrictions
        if operation in [OperationType.FILE_READ, OperationType.FILE_WRITE, OperationType.FILE_DELETE]:
            file_path = context.get("file_path", "")
            if self._is_blocked_path(file_path):
                self._log_audit(operation, context, False, f"Blocked path: {file_path}")
                return False
            
            # File size restrictions for write operations
            if operation == OperationType.FILE_WRITE:
                file_size = context.get("file_size", 0)
                if file_size > self.current_profile.max_file_size:
                    self._log_audit(operation, context, False, f"File too large: {file_size}")
                    return False
        
        # Process operation restrictions
        elif operation in [OperationType.PROCESS_KILL]:
            process_name = context.get("process_name", "")
            if self._is_blocked_process(process_name):
                self._log_audit(operation, context, False, f"Blocked process: {process_name}")
                return False
        
        # Network operation restrictions
        elif operation == OperationType.NETWORK_ACCESS:
            host = context.get("host", "")
            if not self._is_allowed_host(host):
                self._log_audit(operation, context, False, f"Blocked host: {host}")
                return False
        
        # Check rule-specific conditions
        if rule.conditions:
            for condition_key, condition_value in rule.conditions.items():
                context_value = context.get(condition_key)
                if context_value != condition_value:
                    self._log_audit(operation, context, False, 
                                  f"Condition failed: {condition_key}={context_value}")
                    return False
        
        return True
    
    def _is_blocked_path(self, file_path: str) -> bool:
        """Check if a file path is blocked"""
        if not self.current_profile or not file_path:
            return False
        
        file_path = os.path.abspath(file_path)
        
        for blocked_path in self.current_profile.blocked_paths:
            if file_path.startswith(blocked_path):
                return True
        
        return False
    
    def _is_blocked_process(self, process_name: str) -> bool:
        """Check if a process is blocked from operations"""
        if not self.current_profile or not process_name:
            return False
        
        return process_name.lower() in [p.lower() for p in self.current_profile.blocked_processes]
    
    def _is_allowed_host(self, host: str) -> bool:
        """Check if a host is allowed for network operations"""
        if not self.current_profile or not host:
            return False
        
        allowed_hosts = self.current_profile.allowed_hosts
        
        # Check for wildcard permission
        if "*" in allowed_hosts:
            return True
        
        # Check exact matches
        if host in allowed_hosts:
            return True
        
        # Check if it's a local address
        local_addresses = ["localhost", "127.0.0.1", "::1"]
        if host in local_addresses and any(addr in allowed_hosts for addr in local_addresses):
            return True
        
        return False
    
    def _log_audit(self, operation: OperationType, context: Dict[str, Any], 
                  allowed: bool, reason: str):
        """Log an audit entry"""
        import time
        
        audit_entry = {
            "timestamp": time.time(),
            "operation": operation.value,
            "allowed": allowed,
            "reason": reason,
            "context": context,
            "profile": self.current_profile.name if self.current_profile else "none"
        }
        
        self.audit_log.append(audit_entry)
        
        # Keep only last 1000 entries
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-1000:]
        
        # Log to standard logger based on result
        if allowed:
            logger.debug(f"ALLOWED {operation.value}: {reason}")
        else:
            logger.warning(f"DENIED {operation.value}: {reason}")
    
    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent audit log entries"""
        return self.audit_log[-limit:]
    
    def get_current_profile(self) -> Optional[SecurityProfile]:
        """Get the current security profile"""
        return self.current_profile
    
    def get_available_profiles(self) -> List[str]:
        """Get list of available security profiles"""
        return list(self.profiles.keys())
    
    def add_custom_rule(self, operation: OperationType, level: PermissionLevel,
                       conditions: Dict[str, Any] = None, description: str = ""):
        """Add a custom rule to the current profile"""
        if not self.current_profile:
            logger.error("No active profile to add rule to")
            return
        
        new_rule = PermissionRule(operation, level, conditions, description)
        
        # Remove existing rule for this operation
        self.current_profile.rules = [
            r for r in self.current_profile.rules if r.operation != operation
        ]
        
        # Add new rule
        self.current_profile.rules.append(new_rule)
        
        logger.info(f"Added custom rule: {operation.value} -> {level.value}")
    
    def _load_config(self, config_path: str):
        """Load configuration from file"""
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            
            for profile_name, profile_data in config_data.get("profiles", {}).items():
                # Convert rule data to PermissionRule objects
                rules = []
                for rule_data in profile_data.get("rules", []):
                    rule = PermissionRule(
                        operation=OperationType(rule_data["operation"]),
                        level=PermissionLevel(rule_data["level"]),
                        conditions=rule_data.get("conditions", {}),
                        description=rule_data.get("description", "")
                    )
                    rules.append(rule)
                
                profile = SecurityProfile(
                    name=profile_name,
                    description=profile_data.get("description", ""),
                    rules=rules,
                    blocked_paths=profile_data.get("blocked_paths", []),
                    blocked_processes=profile_data.get("blocked_processes", []),
                    allowed_hosts=profile_data.get("allowed_hosts", []),
                    max_file_size=profile_data.get("max_file_size", 100 * 1024 * 1024)
                )
                
                self.profiles[profile_name] = profile
            
            logger.info(f"Loaded security configuration from {config_path}")
            
        except Exception as e:
            logger.error(f"Failed to load security configuration: {e}")
    
    def save_config(self, config_path: str):
        """Save current configuration to file"""
        try:
            config_data = {
                "profiles": {}
            }
            
            for profile_name, profile in self.profiles.items():
                profile_dict = asdict(profile)
                
                # Convert enum values to strings
                for rule in profile_dict["rules"]:
                    rule["operation"] = rule["operation"]
                    rule["level"] = rule["level"]
                
                config_data["profiles"][profile_name] = profile_dict
            
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            logger.info(f"Saved security configuration to {config_path}")
            
        except Exception as e:
            logger.error(f"Failed to save security configuration: {e}")


# Global permission manager instance
_permission_manager = None

def get_permission_manager() -> PermissionManager:
    """Get the global permission manager instance"""
    global _permission_manager
    if _permission_manager is None:
        _permission_manager = PermissionManager()
    return _permission_manager