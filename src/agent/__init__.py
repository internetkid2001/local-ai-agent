"""
Agent Package

Core agent implementation with task routing, decision making,
and LLM integration for the Local AI Agent.

Key Components:
    - llm: Local LLM integration (Ollama)
    - task_router: Task analysis and routing logic
    - decision_engine: Hybrid decision making system
    - context_manager: Context gathering and management

Author: Claude Code
Date: 2025-07-13
Session: 1.2
"""

from .llm import OllamaClient
from .core.task_router import TaskRouter


__all__ = [
    'OllamaClient',
    'TaskRouter', 
    'Task',
    'TaskComplexity',
    'ExecutionPlan'
]