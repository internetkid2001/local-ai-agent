"""
User Interface Module

Web-based user interface for the Local AI Agent, inspired by Cluely.

Author: Claude Code
Date: 2025-07-13
Session: 4.4
"""

from .webapp import create_app, WebUIConfig
from .api import APIRouter

__all__ = [
    'create_app',
    'WebUIConfig',
    'APIRouter'
]