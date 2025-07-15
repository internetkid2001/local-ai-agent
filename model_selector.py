#!/usr/bin/env python3
"""
Model Selection Engine - Intelligent routing between local and cloud AI models
"""

import os
import re
import logging
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)

class ModelType(Enum):
    """Available model types"""
    OLLAMA_LLAMA = "ollama_llama"
    GEMINI = "gemini"
    CLAUDE = "claude"  # For future integration
    GPT4 = "gpt4"     # For future integration

class TaskComplexity(Enum):
    """Task complexity levels"""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    CREATIVE = "creative"
    ANALYTICAL = "analytical"

class ModelSelector:
    """Intelligent model selection based on task requirements"""
    
    def __init__(self):
        self.model_capabilities = {
            ModelType.OLLAMA_LLAMA: {
                "strengths": ["simple_queries", "basic_chat", "local_processing", "privacy"],
                "weaknesses": ["complex_reasoning", "multi-step_analysis", "creative_writing"],
                "complexity_support": [TaskComplexity.SIMPLE, TaskComplexity.MODERATE],
                "response_time": "fast",
                "requires_internet": False
            },
            ModelType.GEMINI: {
                "strengths": ["complex_reasoning", "multi-modal", "code_analysis", "creative_tasks"],
                "weaknesses": ["requires_api_key", "internet_dependent"],
                "complexity_support": [TaskComplexity.MODERATE, TaskComplexity.COMPLEX, TaskComplexity.CREATIVE],
                "response_time": "moderate",
                "requires_internet": True
            },
            ModelType.CLAUDE: {
                "strengths": ["deep_reasoning", "code_generation", "analytical_tasks", "long_context"],
                "weaknesses": ["requires_api_key", "internet_dependent", "cost"],
                "complexity_support": [TaskComplexity.COMPLEX, TaskComplexity.ANALYTICAL, TaskComplexity.CREATIVE],
                "response_time": "moderate",
                "requires_internet": True
            },
            ModelType.GPT4: {
                "strengths": ["general_intelligence", "creative_writing", "complex_tasks"],
                "weaknesses": ["requires_api_key", "internet_dependent", "cost"],
                "complexity_support": [TaskComplexity.COMPLEX, TaskComplexity.CREATIVE],
                "response_time": "moderate",
                "requires_internet": True
            }
        }
        
        # Keywords for task complexity detection
        self.complexity_indicators = {
            TaskComplexity.SIMPLE: [
                "what time", "hello", "hi", "thanks", "yes", "no", "ok",
                "simple", "basic", "tell me", "show me", "list"
            ],
            TaskComplexity.MODERATE: [
                "explain", "how does", "why", "compare", "summarize",
                "what is", "describe", "help me understand"
            ],
            TaskComplexity.COMPLEX: [
                "analyze", "evaluate", "design", "implement", "optimize",
                "debug", "solve", "complex", "advanced", "detailed analysis"
            ],
            TaskComplexity.CREATIVE: [
                "create", "generate", "write a story", "imagine", "invent",
                "creative", "brainstorm", "innovative", "unique"
            ],
            TaskComplexity.ANALYTICAL: [
                "analyze data", "statistical", "research", "investigate",
                "deep dive", "comprehensive analysis", "technical review"
            ]
        }
        
        # Task type patterns
        self.task_patterns = {
            "code_related": r"(code|program|function|class|debug|implement|syntax|error|bug)",
            "system_command": r"(screenshot|process|memory|disk|system info|file|directory)",
            "creative_writing": r"(story|poem|creative|imagine|write about)",
            "data_analysis": r"(analyze|data|statistics|trends|patterns|insights)",
            "general_chat": r"(hello|hi|how are you|thanks|bye|good)"
        }
    
    def analyze_message_complexity(self, message: str) -> TaskComplexity:
        """Analyze the complexity of a user message"""
        message_lower = message.lower()
        
        # Check for complexity indicators
        complexity_scores = {}
        for complexity, keywords in self.complexity_indicators.items():
            score = sum(1 for keyword in keywords if keyword in message_lower)
            complexity_scores[complexity] = score
        
        # Weighted scoring based on message length
        message_length = len(message.split())
        if message_length > 50:
            complexity_scores[TaskComplexity.COMPLEX] += 2
        elif message_length > 20:
            complexity_scores[TaskComplexity.MODERATE] += 1
        else:
            complexity_scores[TaskComplexity.SIMPLE] += 1
        
        # Return the complexity with highest score
        return max(complexity_scores, key=complexity_scores.get)
    
    def detect_task_type(self, message: str) -> str:
        """Detect the type of task from the message"""
        message_lower = message.lower()
        
        for task_type, pattern in self.task_patterns.items():
            if re.search(pattern, message_lower):
                return task_type
        
        return "general_chat"
    
    def select_model(self, 
                    message: str, 
                    context: Optional[List[Dict[str, str]]] = None,
                    prefer_local: bool = False,  # Changed default to prefer cloud models
                    require_internet: bool = True) -> ModelType:
        """
        Select the best model for the given message and context
        
        Args:
            message: The user's message
            context: Conversation history
            prefer_local: Prefer local models when possible
            require_internet: Whether internet is available
        
        Returns:
            The selected model type
        """
        complexity = self.analyze_message_complexity(message)
        task_type = self.detect_task_type(message)
        
        logger.info(f"Task complexity: {complexity}, Task type: {task_type}")
        
        # For system commands, always use local model
        if task_type == "system_command":
            return ModelType.OLLAMA_LLAMA
        
        # For simple tasks or when preferring local
        if complexity == TaskComplexity.SIMPLE and prefer_local:
            return ModelType.OLLAMA_LLAMA
        
        # For code-related tasks, prefer Gemini or Claude
        if task_type == "code_related":
            if require_internet and complexity in [TaskComplexity.COMPLEX, TaskComplexity.ANALYTICAL]:
                return ModelType.GEMINI  # Or CLAUDE when available
            else:
                return ModelType.OLLAMA_LLAMA
        
        # For creative tasks
        if task_type == "creative_writing" or complexity == TaskComplexity.CREATIVE:
            if require_internet:
                return ModelType.GEMINI
            else:
                return ModelType.OLLAMA_LLAMA
        
        # For complex analytical tasks
        if complexity in [TaskComplexity.COMPLEX, TaskComplexity.ANALYTICAL]:
            if require_internet:
                return ModelType.GEMINI  # Or CLAUDE when available
            else:
                return ModelType.OLLAMA_LLAMA
        
        # Default fallback
        if prefer_local or not require_internet:
            return ModelType.OLLAMA_LLAMA
        else:
            return ModelType.GEMINI
    
    def get_model_info(self, model_type: ModelType) -> Dict[str, Any]:
        """Get information about a specific model"""
        return self.model_capabilities.get(model_type, {})
    
    def explain_selection(self, message: str, selected_model: ModelType) -> str:
        """Explain why a particular model was selected"""
        complexity = self.analyze_message_complexity(message)
        task_type = self.detect_task_type(message)
        model_info = self.get_model_info(selected_model)
        
        explanation = f"Selected {selected_model.value} because:\n"
        explanation += f"- Task complexity: {complexity.value}\n"
        explanation += f"- Task type: {task_type}\n"
        explanation += f"- Model strengths: {', '.join(model_info.get('strengths', []))}\n"
        explanation += f"- Response time: {model_info.get('response_time', 'unknown')}"
        
        return explanation


# Example usage and testing
if __name__ == "__main__":
    selector = ModelSelector()
    
    # Test messages
    test_messages = [
        "Hello, how are you?",
        "Write a complex algorithm to solve the traveling salesman problem",
        "Take a screenshot of my desktop",
        "Analyze this code and find potential security vulnerabilities",
        "Write a creative story about a robot learning to paint",
        "What's the weather like?",
        "Explain quantum computing in detail with examples",
        "Show me the system processes"
    ]
    
    for msg in test_messages:
        selected = selector.select_model(msg)
        print(f"\nMessage: {msg}")
        print(f"Selected model: {selected.value}")
        print(selector.explain_selection(msg, selected))
        print("-" * 50)
