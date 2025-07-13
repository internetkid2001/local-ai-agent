"""
Prompt Templates

Template system for generating structured prompts for different tasks
with the local LLM integration.

Author: Claude Code
Date: 2025-07-13
Session: 1.2
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import json
import logging

from ...utils.logger import get_logger

logger = get_logger(__name__)


class TaskType(Enum):
    """Types of tasks for prompt templates"""
    ANALYSIS = "analysis"
    ROUTING = "routing"
    EXECUTION = "execution"
    PLANNING = "planning"
    SUMMARIZATION = "summarization"


@dataclass
class PromptTemplate:
    """Structured prompt template"""
    name: str
    template: str
    variables: List[str]
    task_type: TaskType
    description: str = ""
    
    def render(self, **kwargs) -> str:
        """Render template with provided variables"""
        missing_vars = set(self.variables) - set(kwargs.keys())
        if missing_vars:
            raise ValueError(f"Missing required variables: {missing_vars}")
        
        return self.template.format(**kwargs)


class PromptTemplateManager:
    """
    Manages prompt templates for different AI agent tasks.
    
    Features:
    - Template registration and retrieval
    - Variable validation
    - Task-specific templates
    - Dynamic template generation
    """
    
    def __init__(self):
        """Initialize template manager with default templates"""
        self._templates: Dict[str, PromptTemplate] = {}
        self._register_default_templates()
        
        logger.info("Prompt template manager initialized")
    
    def register_template(self, template: PromptTemplate):
        """Register a new template"""
        self._templates[template.name] = template
        logger.debug(f"Registered template: {template.name}")
    
    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """Get template by name"""
        return self._templates.get(name)
    
    def render_template(self, name: str, **kwargs) -> str:
        """Render a template with variables"""
        template = self.get_template(name)
        if not template:
            raise ValueError(f"Template not found: {name}")
        
        return template.render(**kwargs)
    
    def list_templates(self, task_type: Optional[TaskType] = None) -> List[str]:
        """List available templates, optionally filtered by task type"""
        if task_type:
            return [
                name for name, template in self._templates.items()
                if template.task_type == task_type
            ]
        return list(self._templates.keys())
    
    def _register_default_templates(self):
        """Register default templates for common tasks"""
        
        # Task Analysis Template
        task_analysis_template = PromptTemplate(
            name="task_analysis",
            task_type=TaskType.ANALYSIS,
            description="Analyze task complexity and requirements",
            variables=["task", "available_tools", "context"],
            template="""You are an AI agent task analyzer. Analyze the following task and provide a structured assessment.

Task: {task}

Available Tools: {available_tools}

Context: {context}

Please analyze this task and respond with JSON in the following format:
{{
    "complexity_score": <integer 1-100>,
    "task_type": "<classification>",
    "required_tools": ["tool1", "tool2"],
    "estimated_duration": <seconds>,
    "requires_confirmation": <boolean>,
    "requires_advanced_ai": <boolean>,
    "reasoning": "<explanation of analysis>"
}}

Consider:
- Complexity (1-10: trivial, 11-30: simple, 31-60: moderate, 61-80: complex, 81-100: very complex)
- What tools or capabilities are needed
- Whether this requires human confirmation
- Whether this needs advanced AI (Claude Code/Google CLI) vs local LLM
- Potential risks or considerations"""
        )
        
        # Task Routing Template
        task_routing_template = PromptTemplate(
            name="task_routing",
            task_type=TaskType.ROUTING,
            description="Determine how to route and execute a task",
            variables=["task", "analysis", "system_state"],
            template="""You are an AI agent task router. Based on the task analysis, determine the execution strategy.

Task: {task}

Analysis: {analysis}

System State: {system_state}

Provide an execution plan in JSON format:
{{
    "execution_strategy": "<local|advanced_ai|hybrid>",
    "primary_model": "<model_to_use>",
    "required_steps": [
        {{
            "step": 1,
            "action": "<action_description>",
            "tool": "<tool_name>",
            "parameters": {{}},
            "fallback": "<fallback_strategy>"
        }}
    ],
    "estimated_time": <seconds>,
    "risk_level": "<low|medium|high>",
    "confirmation_required": <boolean>
}}

Execution strategies:
- local: Use local LLM and MCP servers only
- advanced_ai: Delegate to Claude Code or Google CLI
- hybrid: Combine local and advanced AI capabilities"""
        )
        
        # Function Selection Template
        function_selection_template = PromptTemplate(
            name="function_selection",
            task_type=TaskType.PLANNING,
            description="Select appropriate functions for task execution",
            variables=["task", "available_functions", "context"],
            template="""You are helping select the right functions to accomplish a task.

Task: {task}

Available Functions:
{available_functions}

Current Context: {context}

Select the most appropriate functions and provide parameters. Respond with JSON:
{{
    "selected_functions": [
        {{
            "function": "<function_name>",
            "parameters": {{}},
            "reasoning": "<why this function>"
        }}
    ],
    "execution_order": ["function1", "function2"],
    "expected_outcome": "<description>"
}}

Only select functions that are actually needed. Consider the order of execution."""
        )
        
        # Error Analysis Template
        error_analysis_template = PromptTemplate(
            name="error_analysis",
            task_type=TaskType.ANALYSIS,
            description="Analyze errors and suggest recovery strategies",
            variables=["error", "context", "previous_attempts"],
            template="""You are analyzing an error that occurred during task execution.

Error: {error}

Context: {context}

Previous Attempts: {previous_attempts}

Analyze the error and provide recovery suggestions in JSON:
{{
    "error_type": "<classification>",
    "root_cause": "<analysis>",
    "severity": "<low|medium|high|critical>",
    "recovery_strategies": [
        {{
            "strategy": "<description>",
            "probability_success": <0-100>,
            "risk_level": "<low|medium|high>"
        }}
    ],
    "preventive_measures": ["<suggestion1>", "<suggestion2>"],
    "requires_human_intervention": <boolean>
}}

Focus on actionable recovery strategies."""
        )
        
        # Context Summarization Template
        context_summary_template = PromptTemplate(
            name="context_summary",
            task_type=TaskType.SUMMARIZATION,
            description="Summarize context for advanced AI delegation",
            variables=["task", "system_context", "user_context", "history"],
            template="""Prepare a comprehensive context summary for delegating to an advanced AI system.

Original Task: {task}

System Context: {system_context}

User Context: {user_context}

Recent History: {history}

Create a structured summary that provides all necessary context for the advanced AI to understand and complete the task effectively. Include:

1. Task Description: Clear, specific description of what needs to be done
2. Environment: Current system state, file structures, running processes
3. Constraints: Security requirements, limitations, user preferences  
4. Resources: Available tools, files, data sources
5. Context: Background information, previous related work
6. Success Criteria: How to determine if the task is completed successfully

Format as clear, detailed text that another AI can use to understand the full situation."""
        )
        
        # Register all templates
        templates = [
            task_analysis_template,
            task_routing_template,
            function_selection_template,
            error_analysis_template,
            context_summary_template
        ]
        
        for template in templates:
            self.register_template(template)


class TaskAnalysisPrompt:
    """Specialized prompt builder for task analysis"""
    
    def __init__(self, template_manager: PromptTemplateManager):
        self.template_manager = template_manager
    
    def create_analysis_prompt(
        self,
        task: str,
        available_tools: List[str],
        system_context: Dict[str, Any],
        user_context: Dict[str, Any] = None
    ) -> str:
        """Create a comprehensive task analysis prompt"""
        
        context_parts = []
        
        # System context
        if system_context:
            context_parts.append("System Context:")
            context_parts.append(json.dumps(system_context, indent=2))
        
        # User context
        if user_context:
            context_parts.append("\nUser Context:")
            context_parts.append(json.dumps(user_context, indent=2))
        
        context_str = "\n".join(context_parts) if context_parts else "No additional context"
        tools_str = "\n".join(f"- {tool}" for tool in available_tools)
        
        return self.template_manager.render_template(
            "task_analysis",
            task=task,
            available_tools=tools_str,
            context=context_str
        )
    
    def create_routing_prompt(
        self,
        task: str,
        analysis_result: Dict[str, Any],
        system_state: Dict[str, Any]
    ) -> str:
        """Create a task routing prompt"""
        
        return self.template_manager.render_template(
            "task_routing",
            task=task,
            analysis=json.dumps(analysis_result, indent=2),
            system_state=json.dumps(system_state, indent=2)
        )


# Global template manager instance
_template_manager: Optional[PromptTemplateManager] = None


def get_template_manager() -> PromptTemplateManager:
    """Get global template manager instance"""
    global _template_manager
    if _template_manager is None:
        _template_manager = PromptTemplateManager()
    return _template_manager