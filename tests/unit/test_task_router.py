"""
Unit Tests for Task Router

Tests for the task router component including task classification,
strategy determination, and routing decisions.

Author: Claude Code
Date: 2025-07-13
Session: 1.3
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.agent.core.task_router import (
    TaskRouter, TaskClassifier, TaskCategory, ExecutionStrategy, 
    RoutingDecision
)


class TestTaskClassifier:
    """Test TaskClassifier functionality"""
    
    @pytest.fixture
    def classifier(self):
        """Create classifier instance for testing"""
        return TaskClassifier()
    
    def test_file_operations_classification(self, classifier):
        """Test classification of file operation tasks"""
        file_tasks = [
            "read the config.yaml file",
            "write content to output.txt", 
            "list files in the directory",
            "create a new folder called data",
            "copy file1.txt to file2.txt",
            "delete the temporary files"
        ]
        
        for task in file_tasks:
            category = classifier.classify_task(task)
            assert category == TaskCategory.FILE_OPERATIONS
    
    def test_code_generation_classification(self, classifier):
        """Test classification of code generation tasks"""
        code_tasks = [
            "write a Python function to sort a list",
            "create a JavaScript class for user management",
            "implement a binary search algorithm",
            "debug this code snippet",
            "refactor the main function",
            "compile the C++ program"
        ]
        
        for task in code_tasks:
            category = classifier.classify_task(task)
            assert category == TaskCategory.CODE_GENERATION
    
    def test_data_analysis_classification(self, classifier):
        """Test classification of data analysis tasks"""
        analysis_tasks = [
            "analyze the sales data",
            "create a summary report of user statistics",
            "compare performance between two datasets",
            "evaluate the effectiveness of the campaign",
            "examine the log files for errors",
            "study the user behavior patterns"
        ]
        
        for task in analysis_tasks:
            category = classifier.classify_task(task)
            assert category == TaskCategory.DATA_ANALYSIS
    
    def test_system_interaction_classification(self, classifier):
        """Test classification of system interaction tasks"""
        system_tasks = [
            "check the system status",
            "monitor CPU performance",
            "install the required dependencies",
            "configure the database settings",
            "start the web server process",
            "update system configurations"
        ]
        
        for task in system_tasks:
            category = classifier.classify_task(task)
            assert category == TaskCategory.SYSTEM_INTERACTION
    
    def test_research_classification(self, classifier):
        """Test classification of research tasks"""
        research_tasks = [
            "research the latest trends in AI",
            "find information about Python decorators",
            "search for best practices in database design",
            "investigate the cause of the performance issue",
            "explore different machine learning algorithms",
            "learn about containerization technologies"
        ]
        
        for task in research_tasks:
            category = classifier.classify_task(task)
            assert category == TaskCategory.RESEARCH
    
    def test_hybrid_classification(self, classifier):
        """Test classification of hybrid tasks"""
        hybrid_tasks = [
            "read the data file and analyze its contents and create a report",
            "research best practices and implement a solution",
            "analyze the code and write documentation",
            "find configuration issues and fix them"
        ]
        
        for task in hybrid_tasks:
            category = classifier.classify_task(task)
            # Should be classified as hybrid due to multiple categories
            assert category in [TaskCategory.HYBRID, TaskCategory.DATA_ANALYSIS, TaskCategory.FILE_OPERATIONS]
    
    def test_general_classification(self, classifier):
        """Test classification of general tasks"""
        general_tasks = [
            "hello world",
            "what is the time",
            "help me understand this concept",
            "tell me a joke"
        ]
        
        for task in general_tasks:
            category = classifier.classify_task(task)
            assert category in [TaskCategory.GENERAL, TaskCategory.RESEARCH]
    
    def test_keyword_score_calculation(self, classifier):
        """Test keyword score calculation"""
        # Test with known keywords
        text = "read write file directory"
        score = classifier._calculate_keyword_score(text, classifier.file_keywords)
        assert score > 0
        
        # Test with no matching keywords
        text = "hello world"
        score = classifier._calculate_keyword_score(text, classifier.file_keywords)
        assert score >= 0
        
        # Test with empty text
        score = classifier._calculate_keyword_score("", classifier.file_keywords)
        assert score == 0.0
    
    def test_strategy_determination(self, classifier):
        """Test execution strategy determination"""
        # File operations should use MCP
        strategy = classifier.determine_strategy(
            TaskCategory.FILE_OPERATIONS, 
            "read the config file"
        )
        assert strategy == ExecutionStrategy.MCP_ONLY
        
        # Code generation should use LLM or hybrid
        strategy = classifier.determine_strategy(
            TaskCategory.CODE_GENERATION,
            "write a function"
        )
        assert strategy == ExecutionStrategy.LOCAL_LLM_ONLY
        
        # Code generation with file operations should be hybrid
        strategy = classifier.determine_strategy(
            TaskCategory.CODE_GENERATION,
            "create a new file with Python code"
        )
        assert strategy == ExecutionStrategy.HYBRID_LLM_MCP
        
        # Research should use LLM
        strategy = classifier.determine_strategy(
            TaskCategory.RESEARCH,
            "research machine learning"
        )
        assert strategy == ExecutionStrategy.LOCAL_LLM_ONLY
        
        # Hybrid category should use multi-step
        strategy = classifier.determine_strategy(
            TaskCategory.HYBRID,
            "complex multi-step task"
        )
        assert strategy == ExecutionStrategy.MULTI_STEP


class TestTaskRouter:
    """Test TaskRouter functionality"""
    
    @pytest.fixture
    def router(self):
        """Create router instance for testing"""
        return TaskRouter()
    
    @pytest.mark.asyncio
    async def test_route_task_basic(self, router):
        """Test basic task routing"""
        decision = await router.route_task("read the config.yaml file")
        
        assert isinstance(decision, RoutingDecision)
        assert decision.category == TaskCategory.FILE_OPERATIONS
        assert decision.strategy == ExecutionStrategy.MCP_ONLY
        assert decision.confidence > 0
        assert decision.reasoning is not None
        assert len(decision.suggested_tools) > 0
        assert decision.estimated_complexity >= 1
        assert decision.estimated_duration > 0
    
    @pytest.mark.asyncio
    async def test_route_task_with_context(self, router):
        """Test task routing with additional context"""
        context = {
            "user_id": "test_user",
            "workspace": "/home/user/project"
        }
        
        decision = await router.route_task(
            "analyze the project structure", 
            context=context
        )
        
        assert isinstance(decision, RoutingDecision)
        assert decision.confidence > 0
    
    @pytest.mark.asyncio
    async def test_route_task_with_preferences(self, router):
        """Test task routing with user preferences"""
        preferences = {
            "prefer_local": True,
            "max_duration": 60
        }
        
        decision = await router.route_task(
            "write a simple function",
            user_preferences=preferences
        )
        
        assert isinstance(decision, RoutingDecision)
    
    def test_complexity_estimation(self, router):
        """Test task complexity estimation"""
        # Simple task
        complexity = router._estimate_complexity("read file", TaskCategory.FILE_OPERATIONS)
        assert 1 <= complexity <= 5
        
        # Complex task
        complexity = router._estimate_complexity(
            "analyze multiple files and create comprehensive detailed report",
            TaskCategory.DATA_ANALYSIS
        )
        assert complexity >= 3
        
        # Hybrid task should have higher complexity
        complexity = router._estimate_complexity("complex task", TaskCategory.HYBRID)
        assert complexity >= 4
    
    def test_duration_estimation(self, router):
        """Test task duration estimation"""
        # Low complexity, MCP-only strategy
        duration = router._estimate_duration(1, ExecutionStrategy.MCP_ONLY)
        assert duration == 30 * 0.5  # Base duration * strategy multiplier
        
        # High complexity, multi-step strategy
        duration = router._estimate_duration(5, ExecutionStrategy.MULTI_STEP)
        assert duration == 1800 * 2.0  # Base duration * strategy multiplier
        
        # Medium complexity, hybrid strategy
        duration = router._estimate_duration(3, ExecutionStrategy.HYBRID_LLM_MCP)
        assert duration == 300 * 1.5  # Base duration * strategy multiplier
    
    def test_tool_suggestion(self, router):
        """Test tool suggestion functionality"""
        # File operations
        tools = router._suggest_tools(
            TaskCategory.FILE_OPERATIONS,
            "read config.yaml file",
            ExecutionStrategy.MCP_ONLY
        )
        assert "read_file" in tools
        assert len(tools) <= 5
        
        # Code generation with hybrid strategy
        tools = router._suggest_tools(
            TaskCategory.CODE_GENERATION,
            "write and save Python script",
            ExecutionStrategy.HYBRID_LLM_MCP
        )
        assert any(tool in ["write_file", "ollama_generate", "function_call"] for tool in tools)
        
        # Research (LLM-only)
        tools = router._suggest_tools(
            TaskCategory.RESEARCH,
            "research machine learning",
            ExecutionStrategy.LOCAL_LLM_ONLY
        )
        # Research typically has fewer specific tools
        assert len(tools) <= 5
    
    def test_confidence_calculation(self, router):
        """Test confidence calculation"""
        # Clear file operation task
        confidence = router._calculate_confidence(
            TaskCategory.FILE_OPERATIONS,
            ExecutionStrategy.MCP_ONLY,
            "read the configuration file"
        )
        assert confidence > 0.5
        
        # Ambiguous task
        confidence = router._calculate_confidence(
            TaskCategory.GENERAL,
            ExecutionStrategy.LOCAL_LLM_ONLY,
            "do it"
        )
        assert confidence < 0.8  # Should be lower for ambiguous tasks
        
        # Detailed task should have higher confidence
        confidence = router._calculate_confidence(
            TaskCategory.CODE_GENERATION,
            ExecutionStrategy.LOCAL_LLM_ONLY,
            "write a Python function that takes a list of numbers and returns the sum"
        )
        assert confidence > 0.6
    
    def test_reasoning_generation(self, router):
        """Test reasoning text generation"""
        reasoning = router._generate_reasoning(
            TaskCategory.FILE_OPERATIONS,
            ExecutionStrategy.MCP_ONLY,
            2,
            ["read_file", "write_file"]
        )
        
        assert "file operations" in reasoning.lower()
        assert "mcp only" in reasoning.lower()
        assert "complexity level 2" in reasoning.lower()
        assert "read_file" in reasoning
    
    def test_human_approval_detection(self, router):
        """Test human approval requirement detection"""
        # High complexity task
        requires_approval = router._requires_human_approval("complex comprehensive analysis", 4)
        assert requires_approval is True
        
        # Destructive operation
        requires_approval = router._requires_human_approval("delete all files", 2)
        assert requires_approval is True
        
        # System modification
        requires_approval = router._requires_human_approval("install new software", 2)
        assert requires_approval is True
        
        # Simple safe task
        requires_approval = router._requires_human_approval("read configuration", 1)
        assert requires_approval is False
    
    def test_context_requirement_detection(self, router):
        """Test context requirement detection"""
        # Multi-step strategy
        requires_context = router._requires_context("task", ExecutionStrategy.MULTI_STEP)
        assert requires_context is True
        
        # Hybrid strategy
        requires_context = router._requires_context("task", ExecutionStrategy.HYBRID_LLM_MCP)
        assert requires_context is True
        
        # Task with reference words
        requires_context = router._requires_context("analyze this file", ExecutionStrategy.LOCAL_LLM_ONLY)
        assert requires_context is True
        
        # Simple task without references
        requires_context = router._requires_context("hello world", ExecutionStrategy.LOCAL_LLM_ONLY)
        assert requires_context is False
    
    @pytest.mark.asyncio
    async def test_routing_explanation(self, router):
        """Test routing explanation generation"""
        decision = await router.route_task("read config.yaml and summarize contents")
        explanation = await router.get_routing_explanation(decision)
        
        assert isinstance(explanation, str)
        assert "Category:" in explanation
        assert "Strategy:" in explanation
        assert "Confidence:" in explanation
        assert "Reasoning:" in explanation
        assert "Execution Plan:" in explanation
        assert "Requirements:" in explanation


class TestRoutingDecision:
    """Test RoutingDecision dataclass"""
    
    def test_routing_decision_creation(self):
        """Test creating routing decision"""
        decision = RoutingDecision(
            category=TaskCategory.FILE_OPERATIONS,
            strategy=ExecutionStrategy.MCP_ONLY,
            confidence=0.85,
            reasoning="Test reasoning",
            suggested_tools=["read_file", "write_file"],
            estimated_complexity=2,
            estimated_duration=120.0
        )
        
        assert decision.category == TaskCategory.FILE_OPERATIONS
        assert decision.strategy == ExecutionStrategy.MCP_ONLY
        assert decision.confidence == 0.85
        assert decision.reasoning == "Test reasoning"
        assert decision.suggested_tools == ["read_file", "write_file"]
        assert decision.estimated_complexity == 2
        assert decision.estimated_duration == 120.0
        assert decision.requires_context is False
        assert decision.requires_human_approval is False


class TestIntegrationScenarios:
    """Test integration scenarios with realistic tasks"""
    
    @pytest.fixture
    def router(self):
        """Create router for integration tests"""
        return TaskRouter()
    
    @pytest.mark.asyncio
    async def test_file_analysis_workflow(self, router):
        """Test file analysis workflow routing"""
        task = "read the log files in /var/log and analyze error patterns"
        decision = await router.route_task(task)
        
        # Should be classified as hybrid (file ops + analysis)
        assert decision.category in [TaskCategory.HYBRID, TaskCategory.DATA_ANALYSIS]
        assert decision.strategy in [ExecutionStrategy.HYBRID_LLM_MCP, ExecutionStrategy.MULTI_STEP]
        assert decision.confidence > 0.5
        assert any(tool in decision.suggested_tools for tool in ["read_file", "search_files"])
    
    @pytest.mark.asyncio
    async def test_code_development_workflow(self, router):
        """Test code development workflow routing"""
        task = "create a new Python module for database connections with error handling"
        decision = await router.route_task(task)
        
        assert decision.category == TaskCategory.CODE_GENERATION
        assert decision.strategy in [ExecutionStrategy.LOCAL_LLM_ONLY, ExecutionStrategy.HYBRID_LLM_MCP]
        assert decision.estimated_complexity >= 3
        assert decision.estimated_duration > 180  # Should be substantial
    
    @pytest.mark.asyncio
    async def test_system_administration_workflow(self, router):
        """Test system administration workflow routing"""
        task = "check system disk usage and clean up temporary files if usage is high"
        decision = await router.route_task(task)
        
        assert decision.category in [TaskCategory.SYSTEM_INTERACTION, TaskCategory.HYBRID]
        assert decision.requires_human_approval is True  # Potentially destructive
        assert decision.estimated_complexity >= 3
    
    @pytest.mark.asyncio
    async def test_research_and_documentation_workflow(self, router):
        """Test research and documentation workflow routing"""
        task = "research REST API best practices and create documentation"
        decision = await router.route_task(task)
        
        assert decision.category in [TaskCategory.RESEARCH, TaskCategory.HYBRID]
        assert decision.strategy in [ExecutionStrategy.LOCAL_LLM_ONLY, ExecutionStrategy.HYBRID_LLM_MCP]
        assert decision.confidence > 0.6
    
    @pytest.mark.asyncio
    async def test_ambiguous_task_handling(self, router):
        """Test handling of ambiguous tasks"""
        ambiguous_tasks = [
            "help me",
            "fix this",
            "do something useful",
            "make it better"
        ]
        
        for task in ambiguous_tasks:
            decision = await router.route_task(task)
            # Ambiguous tasks should have lower confidence
            assert decision.confidence < 0.7
            # May require context or human approval
            assert decision.requires_context or decision.requires_human_approval


if __name__ == "__main__":
    pytest.main([__file__, "-v"])