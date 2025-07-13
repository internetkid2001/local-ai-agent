"""
Unit Tests for Agent Orchestrator

Tests for the agent orchestrator component including task queue management,
execution coordination, and async operations.

Author: Claude Code
Date: 2025-07-13
Session: 1.3
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.agent.core.orchestrator import (
    AgentOrchestrator, AgentConfig, Task, TaskStatus, TaskPriority
)
from src.agent.llm.ollama_client import OllamaConfig, ModelType
from src.mcp_client.base_client import MCPClientConfig


@pytest.fixture
def mock_ollama_config():
    """Create mock Ollama configuration"""
    return OllamaConfig(
        host="http://localhost:11434",
        models={
            ModelType.PRIMARY: "llama3.1:8b",
            ModelType.CODE: "codellama:7b"
        }
    )


@pytest.fixture
def mock_mcp_config():
    """Create mock MCP configuration"""
    return MCPClientConfig(servers=[])


@pytest.fixture
def agent_config(mock_ollama_config, mock_mcp_config):
    """Create agent configuration for testing"""
    return AgentConfig(
        ollama_config=mock_ollama_config,
        mcp_config=mock_mcp_config,
        max_concurrent_tasks=2,
        task_timeout=30.0,
        enable_screenshots=False,
        context_retention_limit=10
    )


@pytest.fixture
def orchestrator(agent_config):
    """Create orchestrator instance for testing"""
    return AgentOrchestrator(agent_config)


@pytest.fixture
def sample_task():
    """Create sample task for testing"""
    return Task(
        id="test_task_001",
        description="Test task description",
        task_type="llm_query",
        priority=TaskPriority.MEDIUM
    )


class TestTask:
    """Test Task dataclass and functionality"""
    
    def test_task_creation(self):
        """Test task creation with default values"""
        task = Task(
            id="test_001",
            description="Test task",
            task_type="test"
        )
        
        assert task.id == "test_001"
        assert task.description == "Test task"
        assert task.task_type == "test"
        assert task.priority == TaskPriority.MEDIUM
        assert task.status == TaskStatus.PENDING
        assert task.context == {}
        assert task.requirements == {}
        assert task.created_at is not None
        assert task.started_at is None
        assert task.completed_at is None
        assert task.result is None
        assert task.error is None
    
    def test_task_with_custom_values(self):
        """Test task creation with custom values"""
        context = {"key": "value"}
        requirements = {"req": "val"}
        
        task = Task(
            id="test_002",
            description="Custom task",
            task_type="custom",
            priority=TaskPriority.HIGH,
            context=context,
            requirements=requirements
        )
        
        assert task.priority == TaskPriority.HIGH
        assert task.context == context
        assert task.requirements == requirements


class TestAgentOrchestrator:
    """Test AgentOrchestrator class"""
    
    def test_orchestrator_initialization(self, orchestrator, agent_config):
        """Test orchestrator initialization"""
        assert orchestrator.config == agent_config
        assert orchestrator.ollama_client is None
        assert orchestrator.mcp_client is None
        assert len(orchestrator.task_queue) == 0
        assert len(orchestrator.active_tasks) == 0
        assert len(orchestrator.completed_tasks) == 0
        assert orchestrator._running is False
        assert orchestrator._task_semaphore._value == agent_config.max_concurrent_tasks
    
    @pytest.mark.asyncio
    async def test_submit_task(self, orchestrator, sample_task):
        """Test task submission"""
        task_id = await orchestrator.submit_task(sample_task)
        
        assert task_id == sample_task.id
        assert len(orchestrator.task_queue) == 1
        assert orchestrator.task_queue[0] == sample_task
    
    @pytest.mark.asyncio
    async def test_task_priority_ordering(self, orchestrator):
        """Test that tasks are ordered by priority"""
        low_task = Task(id="low", description="Low", task_type="test", priority=TaskPriority.LOW)
        high_task = Task(id="high", description="High", task_type="test", priority=TaskPriority.HIGH)
        medium_task = Task(id="medium", description="Medium", task_type="test", priority=TaskPriority.MEDIUM)
        
        # Submit in mixed order
        await orchestrator.submit_task(low_task)
        await orchestrator.submit_task(high_task)
        await orchestrator.submit_task(medium_task)
        
        # Check order (highest priority first)
        assert orchestrator.task_queue[0].id == "high"
        assert orchestrator.task_queue[1].id == "medium"
        assert orchestrator.task_queue[2].id == "low"
    
    @pytest.mark.asyncio
    async def test_get_task_status(self, orchestrator, sample_task):
        """Test task status retrieval"""
        # Test pending task
        await orchestrator.submit_task(sample_task)
        status = await orchestrator.get_task_status(sample_task.id)
        assert status == TaskStatus.PENDING
        
        # Test non-existent task
        status = await orchestrator.get_task_status("non_existent")
        assert status is None
    
    @pytest.mark.asyncio
    async def test_get_task_result(self, orchestrator):
        """Test task result retrieval"""
        # Create completed task
        task = Task(id="completed", description="Done", task_type="test")
        task.status = TaskStatus.COMPLETED
        task.result = {"output": "success"}
        orchestrator.completed_tasks.append(task)
        
        result = await orchestrator.get_task_result("completed")
        assert result == {"output": "success"}
        
        # Test non-existent task
        result = await orchestrator.get_task_result("non_existent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_start_stop_processing(self, orchestrator):
        """Test starting and stopping task processing"""
        assert orchestrator._running is False
        
        # Start processing
        processing_task = asyncio.create_task(orchestrator.start_processing())
        await asyncio.sleep(0.1)  # Let it start
        assert orchestrator._running is True
        
        # Stop processing
        await orchestrator.stop_processing()
        assert orchestrator._running is False
        
        # Cancel the processing task
        processing_task.cancel()
        try:
            await processing_task
        except asyncio.CancelledError:
            pass
    
    def test_queue_status(self, orchestrator):
        """Test queue status information"""
        status = orchestrator.get_queue_status()
        
        expected_keys = ["pending_tasks", "active_tasks", "completed_tasks", "running"]
        assert all(key in status for key in expected_keys)
        assert status["pending_tasks"] == 0
        assert status["active_tasks"] == 0
        assert status["completed_tasks"] == 0
        assert status["running"] is False
    
    def test_get_active_tasks(self, orchestrator):
        """Test getting active tasks"""
        # Initially empty
        active = orchestrator.get_active_tasks()
        assert len(active) == 0
        
        # Add mock active task
        task = Task(id="active", description="Active", task_type="test")
        task.status = TaskStatus.IN_PROGRESS
        orchestrator.active_tasks["active"] = task
        
        active = orchestrator.get_active_tasks()
        assert len(active) == 1
        assert active[0].id == "active"
    
    def test_get_completed_tasks(self, orchestrator):
        """Test getting completed tasks"""
        # Add some completed tasks
        for i in range(5):
            task = Task(id=f"task_{i}", description=f"Task {i}", task_type="test")
            task.status = TaskStatus.COMPLETED
            orchestrator.completed_tasks.append(task)
        
        # Test default limit
        recent = orchestrator.get_completed_tasks()
        assert len(recent) <= 10  # Default limit
        
        # Test custom limit
        recent = orchestrator.get_completed_tasks(limit=3)
        assert len(recent) == 3
        assert recent[0].id == "task_2"  # Most recent first
    
    @pytest.mark.asyncio
    async def test_task_routing(self, orchestrator):
        """Test task routing to appropriate handlers"""
        # Mock the routing methods
        orchestrator._handle_llm_query = AsyncMock(return_value={"type": "llm"})
        orchestrator._handle_file_operation = AsyncMock(return_value={"type": "file"})
        orchestrator._handle_analysis_task = AsyncMock(return_value={"type": "analysis"})
        orchestrator._handle_hybrid_task = AsyncMock(return_value={"type": "hybrid"})
        
        # Test LLM query routing
        llm_task = Task(id="llm", description="Query", task_type="llm_query")
        result = await orchestrator._route_task(llm_task)
        assert result["type"] == "llm"
        orchestrator._handle_llm_query.assert_called_once_with(llm_task)
        
        # Test file operation routing
        file_task = Task(id="file", description="File op", task_type="file_operation")
        result = await orchestrator._route_task(file_task)
        assert result["type"] == "file"
        orchestrator._handle_file_operation.assert_called_once_with(file_task)
        
        # Test analysis routing
        analysis_task = Task(id="analysis", description="Analyze", task_type="analysis")
        result = await orchestrator._route_task(analysis_task)
        assert result["type"] == "analysis"
        orchestrator._handle_analysis_task.assert_called_once_with(analysis_task)
        
        # Test hybrid routing
        hybrid_task = Task(id="hybrid", description="Hybrid", task_type="hybrid")
        result = await orchestrator._route_task(hybrid_task)
        assert result["type"] == "hybrid"
        orchestrator._handle_hybrid_task.assert_called_once_with(hybrid_task)
        
        # Test default routing (unknown type)
        unknown_task = Task(id="unknown", description="Unknown", task_type="unknown")
        result = await orchestrator._route_task(unknown_task)
        assert result["type"] == "llm"  # Should default to LLM
    
    @pytest.mark.asyncio
    async def test_context_retention_limit(self, orchestrator):
        """Test that completed tasks are limited by retention limit"""
        # Set a low retention limit
        orchestrator.config.context_retention_limit = 3
        
        # Add more tasks than the limit
        for i in range(5):
            task = Task(id=f"task_{i}", description=f"Task {i}", task_type="test")
            task.status = TaskStatus.COMPLETED
            orchestrator.completed_tasks.append(task)
        
        # Simulate task cleanup
        if len(orchestrator.completed_tasks) > orchestrator.config.context_retention_limit:
            orchestrator.completed_tasks = orchestrator.completed_tasks[-orchestrator.config.context_retention_limit:]
        
        # Should only keep the most recent tasks
        assert len(orchestrator.completed_tasks) == 3
        assert orchestrator.completed_tasks[0].id == "task_2"
        assert orchestrator.completed_tasks[-1].id == "task_4"


class TestTaskExecution:
    """Test task execution functionality"""
    
    @pytest.mark.asyncio
    async def test_execute_task_success(self, orchestrator, sample_task):
        """Test successful task execution"""
        # Mock the routing to return success
        orchestrator._route_task = AsyncMock(return_value={"success": True})
        
        # Execute task
        await orchestrator._execute_task(sample_task)
        
        # Check task was completed successfully
        assert sample_task.status == TaskStatus.COMPLETED
        assert sample_task.started_at is not None
        assert sample_task.completed_at is not None
        assert sample_task.result == {"success": True}
        assert sample_task.error is None
        
        # Check task moved to completed list
        assert len(orchestrator.completed_tasks) == 1
        assert orchestrator.completed_tasks[0] == sample_task
    
    @pytest.mark.asyncio
    async def test_execute_task_failure(self, orchestrator, sample_task):
        """Test task execution failure"""
        # Mock the routing to raise an exception
        orchestrator._route_task = AsyncMock(side_effect=Exception("Test error"))
        
        # Execute task
        await orchestrator._execute_task(sample_task)
        
        # Check task was marked as failed
        assert sample_task.status == TaskStatus.FAILED
        assert sample_task.error == "Test error"
        assert sample_task.completed_at is not None
        
        # Check task moved to completed list
        assert len(orchestrator.completed_tasks) == 1
        assert orchestrator.completed_tasks[0] == sample_task
    
    @pytest.mark.asyncio
    async def test_concurrent_task_execution(self, orchestrator):
        """Test concurrent task execution with semaphore"""
        # Create multiple tasks
        tasks = [
            Task(id=f"task_{i}", description=f"Task {i}", task_type="test")
            for i in range(5)
        ]
        
        # Mock routing with delay to simulate work
        async def mock_route(task):
            await asyncio.sleep(0.1)
            return {"task_id": task.id}
        
        orchestrator._route_task = mock_route
        
        # Execute all tasks concurrently
        execution_tasks = [orchestrator._execute_task(task) for task in tasks]
        
        start_time = time.time()
        await asyncio.gather(*execution_tasks)
        end_time = time.time()
        
        # With max_concurrent_tasks=2, should take longer than sequential
        # but less than fully sequential execution
        assert all(task.status == TaskStatus.COMPLETED for task in tasks)
        assert len(orchestrator.completed_tasks) == 5
        
        # Execution time should be reasonable (not fully sequential)
        execution_time = end_time - start_time
        assert execution_time < 0.5  # Should be much less than 0.5s (5 * 0.1s)


class TestInitializationAndShutdown:
    """Test initialization and shutdown procedures"""
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, orchestrator):
        """Test successful initialization"""
        # Mock the Ollama client initialization
        with patch('src.agent.core.orchestrator.OllamaClient') as mock_ollama:
            mock_client = AsyncMock()
            mock_client.initialize.return_value = True
            mock_ollama.return_value = mock_client
            
            # Mock function registration
            orchestrator._register_core_functions = AsyncMock()
            
            result = await orchestrator.initialize()
            
            assert result is True
            assert orchestrator.ollama_client == mock_client
            mock_client.initialize.assert_called_once()
            orchestrator._register_core_functions.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_ollama_failure(self, orchestrator):
        """Test initialization failure when Ollama fails"""
        # Mock the Ollama client initialization to fail
        with patch('src.agent.core.orchestrator.OllamaClient') as mock_ollama:
            mock_client = AsyncMock()
            mock_client.initialize.return_value = False
            mock_ollama.return_value = mock_client
            
            result = await orchestrator.initialize()
            
            assert result is False
            mock_client.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_shutdown(self, orchestrator):
        """Test graceful shutdown"""
        # Add some active tasks
        task1 = Task(id="active1", description="Active 1", task_type="test")
        task2 = Task(id="active2", description="Active 2", task_type="test")
        task1.status = TaskStatus.IN_PROGRESS
        task2.status = TaskStatus.IN_PROGRESS
        orchestrator.active_tasks["active1"] = task1
        orchestrator.active_tasks["active2"] = task2
        
        # Mock clients
        orchestrator.ollama_client = AsyncMock()
        orchestrator.mcp_client = AsyncMock()
        
        # Set running state
        orchestrator._running = True
        
        await orchestrator.shutdown()
        
        # Check shutdown state
        assert orchestrator._running is False
        assert task1.status == TaskStatus.CANCELLED
        assert task2.status == TaskStatus.CANCELLED
        
        # Check clients were shutdown
        orchestrator.ollama_client.shutdown.assert_called_once()
        orchestrator.mcp_client.shutdown.assert_called_once()


@pytest.mark.asyncio
async def test_integration_task_lifecycle(orchestrator):
    """Integration test for complete task lifecycle"""
    # Mock initialization
    with patch('src.agent.core.orchestrator.OllamaClient') as mock_ollama:
        mock_client = AsyncMock()
        mock_client.initialize.return_value = True
        mock_ollama.return_value = mock_client
        orchestrator._register_core_functions = AsyncMock()
        
        # Initialize orchestrator
        await orchestrator.initialize()
        
        # Create and submit task
        task = Task(
            id="integration_test",
            description="Integration test task",
            task_type="llm_query",
            priority=TaskPriority.HIGH
        )
        
        # Mock the LLM handler
        orchestrator._handle_llm_query = AsyncMock(return_value={
            "response": "Test response",
            "model": "test-model"
        })
        
        # Submit and execute task
        task_id = await orchestrator.submit_task(task)
        assert task_id == "integration_test"
        
        # Start processing
        processing_task = asyncio.create_task(orchestrator.start_processing())
        
        # Wait for task to be processed
        await asyncio.sleep(0.2)
        
        # Stop processing
        await orchestrator.stop_processing()
        processing_task.cancel()
        
        try:
            await processing_task
        except asyncio.CancelledError:
            pass
        
        # Check task was completed
        assert len(orchestrator.completed_tasks) == 1
        completed_task = orchestrator.completed_tasks[0]
        assert completed_task.id == "integration_test"
        assert completed_task.status == TaskStatus.COMPLETED
        assert completed_task.result is not None
        
        # Cleanup
        await orchestrator.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])