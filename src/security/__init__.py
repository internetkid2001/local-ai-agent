"""
Security Module

Security framework for the local AI agent including permission management,
access controls, and audit logging.

Author: Claude Code
Date: 2025-07-13
Phase: 2.1
"""

from .permission_manager import (
    PermissionManager,
    PermissionLevel,
    OperationType,
    PermissionRule,
    SecurityProfile,
    get_permission_manager
)

__all__ = [
    "PermissionManager",
    "PermissionLevel", 
    "OperationType",
    "PermissionRule",
    "SecurityProfile",
    "get_permission_manager"
]