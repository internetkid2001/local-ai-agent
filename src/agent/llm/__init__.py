"""
LLM Integration Package

Local Large Language Model integration for the AI Agent.
Provides Ollama client with function calling support.

Author: Claude Code
Date: 2025-07-13
Session: 1.2
"""

from .ollama_client import OllamaClient, OllamaConfig
from .function_calling import FunctionCallHandler, FunctionSchema
from .prompt_templates import PromptTemplateManager, TaskAnalysisPrompt

__all__ = [
    'OllamaClient',
    'OllamaConfig',
    'FunctionCallHandler', 
    'FunctionSchema',
    'PromptTemplateManager',
    'TaskAnalysisPrompt'
]