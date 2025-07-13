"""
Context Management

Context-aware decision making and memory management for enhanced agent capabilities.

Author: Claude Code
Date: 2025-07-13
Session: 2.2
"""

from .context_manager import ContextManager, ContextType, ContextScope
from .memory_store import MemoryStore, MemoryEntry, MemoryType
from .learning_engine import LearningEngine, LearningFeedback
from .pattern_recognizer import PatternRecognizer, TaskPattern

__all__ = [
    'ContextManager',
    'ContextType', 
    'ContextScope',
    'MemoryStore',
    'MemoryEntry',
    'MemoryType',
    'LearningEngine',
    'LearningFeedback',
    'PatternRecognizer',
    'TaskPattern'
]