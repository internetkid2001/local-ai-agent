"""
Task Router

Intelligent task routing and classification system that determines
the best execution strategy for different types of tasks.

Author: Claude Code  
Date: 2025-07-13
Session: 1.3
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from ..llm.prompt_templates import PromptTemplates
from ...utils.logger import get_logger

logger = get_logger(__name__)


class TaskCategory(Enum):
    """High-level task categories"""
    FILE_OPERATIONS = "file_operations"
    CODE_GENERATION = "code_generation"
    DATA_ANALYSIS = "data_analysis"
    SYSTEM_INTERACTION = "system_interaction"
    DESKTOP_AUTOMATION = "desktop_automation"
    SYSTEM_MONITORING = "system_monitoring"
    RESEARCH = "research"
    HYBRID = "hybrid"
    GENERAL = "general"


class ExecutionStrategy(Enum):
    """Task execution strategies"""
    LOCAL_LLM_ONLY = "local_llm_only"
    MCP_ONLY = "mcp_only"
    HYBRID_LLM_MCP = "hybrid_llm_mcp"
    MULTI_STEP = "multi_step"
    PARALLEL = "parallel"


@dataclass
class RoutingDecision:
    """Task routing decision with reasoning"""
    category: TaskCategory
    strategy: ExecutionStrategy
    confidence: float
    reasoning: str
    suggested_tools: List[str]
    estimated_complexity: int  # 1-5 scale
    estimated_duration: float  # seconds
    requires_context: bool = False
    requires_human_approval: bool = False


class TaskClassifier:
    """Classifies tasks into categories and determines execution strategy"""
    
    def __init__(self):
        """Initialize task classifier"""
        self.file_keywords = {
            'read', 'write', 'create', 'delete', 'copy', 'move', 'list', 
            'directory', 'folder', 'file', 'save', 'load', 'download', 'upload'
        }
        
        self.code_keywords = {
            'code', 'program', 'script', 'function', 'class', 'debug', 'refactor',
            'python', 'javascript', 'java', 'cpp', 'rust', 'go', 'implement',
            'algorithm', 'syntax', 'compile', 'execute', 'test'
        }
        
        self.analysis_keywords = {
            'analyze', 'analysis', 'data', 'statistics', 'report', 'summary',
            'compare', 'evaluate', 'assess', 'review', 'examine', 'study'
        }
        
        self.system_keywords = {
            'system', 'process', 'service', 'configuration', 'settings',
            'install', 'setup', 'status', 'performance'
        }
        
        self.desktop_keywords = {
            'window', 'desktop', 'click', 'mouse', 'keyboard', 'screenshot',
            'clipboard', 'focus', 'ui', 'automation', 'gui', 'interface',
            'type', 'press', 'key', 'button', 'screen'
        }
        
        self.monitoring_keywords = {
            'monitor', 'monitoring', 'cpu', 'memory', 'disk', 'network',
            'resource', 'usage', 'stats', 'statistics', 'performance',
            'log', 'logs', 'ping', 'connectivity', 'health'
        }
        
        self.research_keywords = {
            'research', 'find', 'search', 'lookup', 'investigate', 'explore',
            'information', 'facts', 'learn', 'understand', 'explain'
        }
    
    def classify_task(self, description: str, context: Dict[str, Any] = None) -> TaskCategory:
        """
        Classify a task into a category.
        
        Args:
            description: Task description
            context: Additional context
            
        Returns:
            Task category
        """
        text = description.lower()
        context = context or {}
        
        # Calculate keyword scores
        file_score = self._calculate_keyword_score(text, self.file_keywords)
        code_score = self._calculate_keyword_score(text, self.code_keywords)
        analysis_score = self._calculate_keyword_score(text, self.analysis_keywords)
        system_score = self._calculate_keyword_score(text, self.system_keywords)
        desktop_score = self._calculate_keyword_score(text, self.desktop_keywords)
        monitoring_score = self._calculate_keyword_score(text, self.monitoring_keywords)
        research_score = self._calculate_keyword_score(text, self.research_keywords)
        
        # Determine category based on highest score
        scores = {
            TaskCategory.FILE_OPERATIONS: file_score,
            TaskCategory.CODE_GENERATION: code_score,
            TaskCategory.DATA_ANALYSIS: analysis_score,
            TaskCategory.SYSTEM_INTERACTION: system_score,
            TaskCategory.DESKTOP_AUTOMATION: desktop_score,
            TaskCategory.SYSTEM_MONITORING: monitoring_score,
            TaskCategory.RESEARCH: research_score
        }
        
        max_score = max(scores.values())
        
        # If no clear category or multiple high scores, check for hybrid
        if max_score < 0.3 or list(scores.values()).count(max_score) > 1:
            return TaskCategory.HYBRID
        
        # Return category with highest score
        for category, score in scores.items():
            if score == max_score:
                return category
        
        return TaskCategory.GENERAL
    
    def _calculate_keyword_score(self, text: str, keywords: set) -> float:
        """Calculate keyword presence score"""
        word_count = len(text.split())
        if word_count == 0:
            return 0.0
        
        matches = sum(1 for keyword in keywords if keyword in text)
        return matches / word_count
    
    def determine_strategy(self, category: TaskCategory, description: str, 
                         context: Dict[str, Any] = None) -> ExecutionStrategy:
        """
        Determine execution strategy based on task category and complexity.
        
        Args:
            category: Task category
            description: Task description  
            context: Additional context
            
        Returns:
            Execution strategy
        """
        text = description.lower()
        
        # Strategy mapping based on category
        if category == TaskCategory.FILE_OPERATIONS:
            # File operations typically use MCP servers
            return ExecutionStrategy.MCP_ONLY
        
        elif category == TaskCategory.CODE_GENERATION:
            # Code generation benefits from LLM + file operations
            if any(word in text for word in ['save', 'write', 'create file']):
                return ExecutionStrategy.HYBRID_LLM_MCP
            else:
                return ExecutionStrategy.LOCAL_LLM_ONLY
        
        elif category == TaskCategory.DATA_ANALYSIS:
            # Analysis may need data loading + LLM processing
            if any(word in text for word in ['file', 'data', 'csv', 'json']):
                return ExecutionStrategy.HYBRID_LLM_MCP
            else:
                return ExecutionStrategy.LOCAL_LLM_ONLY
        
        elif category == TaskCategory.SYSTEM_INTERACTION:
            # System tasks usually need MCP servers
            return ExecutionStrategy.MCP_ONLY
        
        elif category == TaskCategory.DESKTOP_AUTOMATION:
            # Desktop automation uses dedicated MCP server
            return ExecutionStrategy.MCP_ONLY
        
        elif category == TaskCategory.SYSTEM_MONITORING:
            # System monitoring uses dedicated MCP server
            return ExecutionStrategy.MCP_ONLY
        
        elif category == TaskCategory.RESEARCH:
            # Research is typically LLM-based
            return ExecutionStrategy.LOCAL_LLM_ONLY
        
        elif category == TaskCategory.HYBRID:
            # Complex multi-step tasks
            return ExecutionStrategy.MULTI_STEP
        
        else:
            # Default to LLM for general tasks
            return ExecutionStrategy.LOCAL_LLM_ONLY


class TaskRouter:
    """
    Intelligent task router that analyzes tasks and determines optimal execution paths.
    
    Features:
    - Task classification and categorization
    - Execution strategy determination
    - Tool recommendation
    - Complexity estimation
    - Resource requirement analysis
    """
    
    def __init__(self):
        """Initialize task router"""
        self.classifier = TaskClassifier()
        self.prompt_templates = PromptTemplates()
        
        # Tool mappings
        self.category_tools = {
            TaskCategory.FILE_OPERATIONS: [
                'read_file', 'write_file', 'list_directory', 'create_directory',
                'copy_file', 'move_file', 'delete_file', 'search_files', 'get_file_info'
            ],
            TaskCategory.CODE_GENERATION: [
                'read_file', 'write_file', 'search_files'
            ],
            TaskCategory.DATA_ANALYSIS: [
                'read_file', 'search_files', 'get_file_info'
            ],
            TaskCategory.SYSTEM_INTERACTION: [
                'list_directory', 'get_file_info'
            ],
            TaskCategory.DESKTOP_AUTOMATION: [
                'list_windows', 'focus_window', 'click_coordinates', 'type_text',
                'take_screenshot', 'get_clipboard', 'set_clipboard', 'press_key'
            ],
            TaskCategory.SYSTEM_MONITORING: [
                'list_processes', 'get_cpu_stats', 'get_memory_stats', 'get_disk_stats',
                'get_network_stats', 'ping_host', 'check_port', 'parse_log_file'
            ],
            TaskCategory.RESEARCH: [],  # Primarily LLM-based
            TaskCategory.HYBRID: [],   # Determined dynamically
            TaskCategory.GENERAL: []   # Determined dynamically
        }
        
        logger.info("Task router initialized")
    
    async def route_task(self, description: str, context: Dict[str, Any] = None,
                        user_preferences: Dict[str, Any] = None) -> RoutingDecision:
        """
        Route a task and provide execution recommendations.
        
        Args:
            description: Task description
            context: Task context
            user_preferences: User preferences for execution
            
        Returns:
            Routing decision with execution plan
        """
        context = context or {}
        user_preferences = user_preferences or {}
        
        logger.info(f"Routing task: {description[:100]}...")
        
        # Classify task
        category = self.classifier.classify_task(description, context)
        logger.debug(f"Task classified as: {category.value}")
        
        # Determine execution strategy
        strategy = self.classifier.determine_strategy(category, description, context)
        logger.debug(f"Execution strategy: {strategy.value}")
        
        # Estimate complexity and duration
        complexity = self._estimate_complexity(description, category)
        duration = self._estimate_duration(complexity, strategy)
        
        # Determine required tools
        suggested_tools = self._suggest_tools(category, description, strategy)
        
        # Calculate confidence
        confidence = self._calculate_confidence(category, strategy, description)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(category, strategy, complexity, suggested_tools)
        
        # Check if human approval needed
        requires_approval = self._requires_human_approval(description, complexity)
        
        # Check if context needed
        requires_context = self._requires_context(description, strategy)
        
        decision = RoutingDecision(
            category=category,
            strategy=strategy,
            confidence=confidence,
            reasoning=reasoning,
            suggested_tools=suggested_tools,
            estimated_complexity=complexity,
            estimated_duration=duration,
            requires_context=requires_context,
            requires_human_approval=requires_approval
        )
        
        logger.info(f"Task routed: {category.value} via {strategy.value} (confidence: {confidence:.2f})")
        return decision
    
    def _estimate_complexity(self, description: str, category: TaskCategory) -> int:
        """Estimate task complexity on 1-5 scale"""
        text = description.lower()
        
        # Base complexity by category
        base_complexity = {
            TaskCategory.FILE_OPERATIONS: 2,
            TaskCategory.CODE_GENERATION: 3,
            TaskCategory.DATA_ANALYSIS: 3,
            TaskCategory.SYSTEM_INTERACTION: 3,
            TaskCategory.DESKTOP_AUTOMATION: 2,
            TaskCategory.SYSTEM_MONITORING: 2,
            TaskCategory.RESEARCH: 2,
            TaskCategory.HYBRID: 4,
            TaskCategory.GENERAL: 2
        }
        
        complexity = base_complexity.get(category, 2)
        
        # Adjust based on description complexity
        complexity_indicators = [
            ('multiple', 1), ('several', 1), ('complex', 1), ('advanced', 1),
            ('integrate', 1), ('combine', 1), ('analyze', 1), ('optimize', 1),
            ('comprehensive', 2), ('detailed', 1), ('thorough', 1)
        ]
        
        for indicator, adjustment in complexity_indicators:
            if indicator in text:
                complexity += adjustment
        
        return min(max(complexity, 1), 5)  # Clamp to 1-5 range
    
    def _estimate_duration(self, complexity: int, strategy: ExecutionStrategy) -> float:
        """Estimate task duration in seconds"""
        base_duration = {
            1: 30,    # 30 seconds
            2: 120,   # 2 minutes
            3: 300,   # 5 minutes
            4: 600,   # 10 minutes
            5: 1800   # 30 minutes
        }
        
        duration = base_duration.get(complexity, 300)
        
        # Adjust based on strategy
        strategy_multipliers = {
            ExecutionStrategy.LOCAL_LLM_ONLY: 1.0,
            ExecutionStrategy.MCP_ONLY: 0.5,
            ExecutionStrategy.HYBRID_LLM_MCP: 1.5,
            ExecutionStrategy.MULTI_STEP: 2.0,
            ExecutionStrategy.PARALLEL: 0.8
        }
        
        multiplier = strategy_multipliers.get(strategy, 1.0)
        return duration * multiplier
    
    def _suggest_tools(self, category: TaskCategory, description: str, 
                      strategy: ExecutionStrategy) -> List[str]:
        """Suggest appropriate tools for task execution"""
        tools = self.category_tools.get(category, []).copy()
        
        # Add strategy-specific tools
        if strategy == ExecutionStrategy.HYBRID_LLM_MCP:
            # Combine LLM and MCP tools
            tools.extend(['ollama_generate', 'function_call'])
        
        # Filter based on description keywords
        text = description.lower()
        
        if 'read' in text and 'read_file' in tools:
            tools = ['read_file'] + [t for t in tools if t != 'read_file']
        
        if 'write' in text and 'write_file' in tools:
            tools = ['write_file'] + [t for t in tools if t != 'write_file']
        
        if 'search' in text and 'search_files' in tools:
            tools = ['search_files'] + [t for t in tools if t != 'search_files']
        
        return tools[:5]  # Limit to top 5 tools
    
    def _calculate_confidence(self, category: TaskCategory, strategy: ExecutionStrategy,
                            description: str) -> float:
        """Calculate confidence in routing decision"""
        base_confidence = 0.7
        
        # Adjust based on category clarity
        text = description.lower()
        category_keywords = {
            TaskCategory.FILE_OPERATIONS: ['file', 'directory', 'read', 'write'],
            TaskCategory.CODE_GENERATION: ['code', 'program', 'script', 'function'],
            TaskCategory.DATA_ANALYSIS: ['analyze', 'data', 'report'],
            TaskCategory.SYSTEM_INTERACTION: ['system', 'process', 'configuration'],
            TaskCategory.DESKTOP_AUTOMATION: ['window', 'click', 'screenshot', 'desktop'],
            TaskCategory.SYSTEM_MONITORING: ['monitor', 'cpu', 'memory', 'performance'],
            TaskCategory.RESEARCH: ['research', 'find', 'search', 'explain']
        }
        
        if category in category_keywords:
            keyword_matches = sum(1 for kw in category_keywords[category] if kw in text)
            confidence_boost = min(keyword_matches * 0.1, 0.3)
            base_confidence += confidence_boost
        
        # Adjust based on description clarity
        if len(description.split()) < 5:
            base_confidence -= 0.2  # Very short descriptions are ambiguous
        elif len(description.split()) > 20:
            base_confidence += 0.1  # Detailed descriptions are clearer
        
        return min(max(base_confidence, 0.1), 1.0)
    
    def _generate_reasoning(self, category: TaskCategory, strategy: ExecutionStrategy,
                          complexity: int, tools: List[str]) -> str:
        """Generate human-readable reasoning for the routing decision"""
        reasoning_parts = [
            f"Task categorized as {category.value.replace('_', ' ')}",
            f"using {strategy.value.replace('_', ' ')} strategy",
            f"with complexity level {complexity}/5"
        ]
        
        if tools:
            reasoning_parts.append(f"requiring tools: {', '.join(tools[:3])}")
        
        return ". ".join(reasoning_parts) + "."
    
    def _requires_human_approval(self, description: str, complexity: int) -> bool:
        """Determine if task requires human approval"""
        text = description.lower()
        
        # High complexity tasks
        if complexity >= 4:
            return True
        
        # Potentially destructive operations
        destructive_keywords = ['delete', 'remove', 'destroy', 'wipe', 'format']
        if any(keyword in text for keyword in destructive_keywords):
            return True
        
        # System modifications
        system_keywords = ['install', 'uninstall', 'configure', 'modify system']
        if any(keyword in text for keyword in system_keywords):
            return True
        
        return False
    
    def _requires_context(self, description: str, strategy: ExecutionStrategy) -> bool:
        """Determine if task requires additional context"""
        text = description.lower()
        
        # Multi-step strategies often need context
        if strategy in [ExecutionStrategy.MULTI_STEP, ExecutionStrategy.HYBRID_LLM_MCP]:
            return True
        
        # Tasks referencing "this", "that", "current" need context
        context_indicators = ['this', 'that', 'current', 'existing', 'previous']
        if any(indicator in text for indicator in context_indicators):
            return True
        
        return False
    
    async def get_routing_explanation(self, decision: RoutingDecision) -> str:
        """Get detailed explanation of routing decision"""
        explanation = f"""
Task Routing Analysis:

Category: {decision.category.value.replace('_', ' ').title()}
Strategy: {decision.strategy.value.replace('_', ' ').title()}
Confidence: {decision.confidence:.1%}

Reasoning: {decision.reasoning}

Execution Plan:
- Complexity: {decision.estimated_complexity}/5
- Estimated Duration: {decision.estimated_duration:.0f} seconds
- Suggested Tools: {', '.join(decision.suggested_tools) if decision.suggested_tools else 'None specific'}

Requirements:
- Additional Context: {'Yes' if decision.requires_context else 'No'}
- Human Approval: {'Yes' if decision.requires_human_approval else 'No'}
"""
        return explanation.strip()