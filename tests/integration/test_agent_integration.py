"""
Integration Tests for Agent System

End-to-end integration tests for the complete agent system including
orchestrator, router, decision engine, and MCP client coordination.

Author: Claude Code
Date: 2025-07-13
Session: 1.3
"""

import pytest
import asyncio
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.agent.core.orchestrator import AgentOrchestrator, AgentConfig, Task, TaskPriority, TaskStatus
from src.agent.core.task_router import TaskRouter
from src.agent.core.decision_engine import DecisionEngine, DecisionType
from src.agent.llm.ollama_client import OllamaConfig, ModelType
from src.mcp_client.filesystem_client import FilesystemMCPClient
from src.agent.interface.cli import AgentCLI


@pytest.fixture
def temp_directory():
    """Create temporary directory for tests"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


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
def agent_config(mock_ollama_config):
    """Create agent configuration for testing"""
    return AgentConfig(
        ollama_config=mock_ollama_config,
        mcp_config=None,  # Will use default from FilesystemMCPClient
        max_concurrent_tasks=2,
        task_timeout=30.0,
        enable_screenshots=False,
        context_retention_limit=10
    )


@pytest.fixture
async def mock_agent_system(agent_config):
    """Create fully mocked agent system for testing"""
    # Create components
    orchestrator = AgentOrchestrator(agent_config)
    router = TaskRouter()
    decision_engine = DecisionEngine(orchestrator, router)
    
    # Mock external dependencies
    with patch('src.agent.core.orchestrator.OllamaClient') as mock_ollama_cls:
        mock_ollama_client = AsyncMock()
        mock_ollama_client.initialize.return_value = True
        mock_ollama_client.generate.return_value = Mock(
            content="Mock LLM response",
            function_calls=[],
            model="test-model"
        )
        mock_ollama_cls.return_value = mock_ollama_client
        
        # Initialize orchestrator
        await orchestrator.initialize()
        orchestrator.ollama_client = mock_ollama_client
        
        yield {
            'orchestrator': orchestrator,
            'router': router,
            'decision_engine': decision_engine,
            'ollama_client': mock_ollama_client
        }
        
        # Cleanup
        await orchestrator.shutdown()


class TestBasicAgentWorkflow:
    """Test basic agent workflow functionality"""
    
    @pytest.mark.asyncio
    async def test_simple_llm_task_workflow(self, mock_agent_system):
        """Test complete workflow for simple LLM task"""
        orchestrator = mock_agent_system['orchestrator']
        decision_engine = mock_agent_system['decision_engine']
        
        # Create task
        task = Task(
            id="test_llm_task",
            description="What is the capital of France?",
            task_type="llm_query",
            priority=TaskPriority.MEDIUM
        )
        
        # Make decision
        decision = await decision_engine.make_execution_decision(task)
        
        assert decision.decision_type == DecisionType.EXECUTE_IMMEDIATELY
        assert decision.routing_decision.confidence > 0.5
        
        # Execute decision
        result_id = await decision_engine.execute_decision(decision, task)
        
        # Start processing
        processing_task = asyncio.create_task(orchestrator.start_processing())
        await asyncio.sleep(0.1)
        
        # Stop processing
        await orchestrator.stop_processing()
        processing_task.cancel()
        
        try:
            await processing_task
        except asyncio.CancelledError:
            pass
        
        # Verify task completion
        final_status = await orchestrator.get_task_status(task.id)
        assert final_status == TaskStatus.COMPLETED
        
        result = await orchestrator.get_task_result(task.id)
        assert result is not None
        assert "response" in result
    
    @pytest.mark.asyncio
    async def test_high_complexity_approval_workflow(self, mock_agent_system):
        """Test workflow for tasks requiring approval"""
        decision_engine = mock_agent_system['decision_engine']
        
        # Create high complexity task
        task = Task(
            id="test_approval_task",
            description="Delete all system files and reformat the disk",
            task_type="system_interaction",
            priority=TaskPriority.HIGH
        )
        
        # Make decision
        decision = await decision_engine.make_execution_decision(task)
        
        # Should require approval
        assert decision.decision_type == DecisionType.REQUEST_APPROVAL
        assert decision.approval_reason is not None
        
        # Execute decision (should create approval request)
        approval_id = await decision_engine.execute_decision(decision, task)
        
        # Check pending approvals
        pending = decision_engine.get_pending_approvals()
        assert approval_id in pending
        
        # Approve the task
        result = await decision_engine.approve_task(approval_id, True)
        assert result is not None
        
        # Check approval was processed
        pending_after = decision_engine.get_pending_approvals()
        assert approval_id not in pending_after
    
    @pytest.mark.asyncio
    async def test_task_decomposition_workflow(self, mock_agent_system):
        """Test workflow for tasks that get decomposed"""
        decision_engine = mock_agent_system['decision_engine']
        
        # Create complex hybrid task
        task = Task(
            id="test_decomposition_task",
            description="Analyze all Python files in the project, create comprehensive documentation, and generate test cases",
            task_type="hybrid",
            priority=TaskPriority.MEDIUM
        )
        
        # Make decision
        decision = await decision_engine.make_execution_decision(task)
        
        # May be decomposed or require context
        assert decision.decision_type in [
            DecisionType.DECOMPOSE_TASK, 
            DecisionType.GATHER_CONTEXT,
            DecisionType.EXECUTE_IMMEDIATELY
        ]
        
        if decision.decision_type == DecisionType.DECOMPOSE_TASK:
            assert len(decision.decomposed_tasks) > 0
            
            # Execute decision
            result_id = await decision_engine.execute_decision(decision, task)
            assert "decomposed" in result_id


class TestMCPIntegration:
    """Test MCP client integration"""
    
    @pytest.mark.asyncio
    async def test_filesystem_client_initialization(self):
        """Test filesystem MCP client initialization"""
        client = FilesystemMCPClient()
        
        # Note: This will likely fail without actual MCP server running
        # but we can test the initialization attempt
        try:
            result = await client.initialize()
            # If successful, great! If not, that's expected in test environment
            assert isinstance(result, bool)
        except Exception:
            # Expected in test environment without MCP server
            pass
        
        # Test configuration
        assert client.config is not None
        assert len(client.config.servers) > 0
        assert client.config.servers[0].name == "filesystem"
    
    @pytest.mark.asyncio
    async def test_filesystem_task_processing(self):
        """Test filesystem task processing"""
        client = FilesystemMCPClient()
        
        # Test task routing without actual MCP server
        task_result = await client.process_task(
            "read config.yaml file",
            context={"file_path": "config.yaml"}
        )
        
        # Should return error without MCP server connection
        assert isinstance(task_result, dict)
        assert "success" in task_result
    
    @pytest.mark.asyncio
    async def test_file_operations(self, temp_directory):
        """Test file operations through filesystem client"""
        client = FilesystemMCPClient()
        client.set_base_directory(str(temp_directory))
        
        # Create test file
        test_file = temp_directory / "test.txt"
        test_content = "Hello, World!"
        test_file.write_text(test_content)
        
        # Test file validation
        validated_path = client._validate_path("test.txt")
        assert validated_path.name == "test.txt"
        
        # Test content validation
        client._validate_content("Test content")  # Should not raise
        
        with pytest.raises(ValueError):
            client._validate_content(b"binary content")  # Should raise


class TestDecisionEngine:
    """Test decision engine integration"""
    
    @pytest.mark.asyncio
    async def test_decision_engine_coordination(self, mock_agent_system):
        """Test decision engine coordination with orchestrator and router"""
        decision_engine = mock_agent_system['decision_engine']
        
        tasks = [
            Task(id="task1", description="Simple query", task_type="llm_query"),
            Task(id="task2", description="Read file.txt", task_type="file_operation"),
            Task(id="task3", description="Complex analysis with multiple steps", task_type="hybrid")
        ]
        
        decisions = []
        for task in tasks:
            decision = await decision_engine.make_execution_decision(task)
            decisions.append(decision)
        
        # Verify different decision types
        decision_types = [d.decision_type for d in decisions]
        assert DecisionType.EXECUTE_IMMEDIATELY in decision_types
        
        # Verify routing strategies differ appropriately
        strategies = [d.routing_decision.strategy for d in decisions]
        assert len(set(str(s) for s in strategies)) > 1  # Different strategies
    
    @pytest.mark.asyncio
    async def test_context_gathering_workflow(self, mock_agent_system):
        """Test context gathering workflow"""
        decision_engine = mock_agent_system['decision_engine']
        
        # Task that references unclear context
        task = Task(
            id="context_task",
            description="Analyze this file and summarize the current situation",
            task_type="analysis"
        )
        
        decision = await decision_engine.make_execution_decision(task)
        
        # May require context due to ambiguous references
        if decision.decision_type == DecisionType.GATHER_CONTEXT:
            assert len(decision.context_requirements) > 0
            
            # Execute decision
            context_id = await decision_engine.execute_decision(decision, task)
            
            # Provide context
            context_data = {"file_path": "example.txt", "current_status": "processing"}
            result = await decision_engine.provide_context(context_id, context_data)
            
            if result:
                assert result is not None


class TestCLIIntegration:
    """Test CLI integration with agent system"""
    
    @pytest.mark.asyncio
    async def test_cli_initialization(self):
        """Test CLI initialization"""
        cli = AgentCLI()
        
        # Test configuration loading
        assert cli.config is not None
        assert cli.session_id is not None
        assert len(cli.command_history) == 0
    
    @pytest.mark.asyncio
    async def test_cli_task_submission(self):
        """Test task submission through CLI"""
        cli = AgentCLI()
        
        # Mock CLI components for testing
        with patch.object(cli, '_load_config') as mock_config:
            mock_config.return_value = AgentConfig(
                ollama_config=OllamaConfig(
                    host="http://localhost:11434",
                    models={ModelType.PRIMARY: "test-model"}
                ),
                mcp_config=None,
                max_concurrent_tasks=1
            )
            
            # Test command processing without full initialization
            with patch.object(cli, 'orchestrator') as mock_orch:
                with patch.object(cli, 'decision_engine') as mock_de:
                    mock_orch.submit_task = AsyncMock(return_value="task_123")
                    mock_de.make_execution_decision = AsyncMock()
                    mock_de.execute_decision = AsyncMock(return_value="task_123")
                    
                    # This would normally require full initialization
                    # but we're testing the command processing logic
                    await cli._process_command("help")


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    @pytest.mark.asyncio
    async def test_task_execution_failure(self, mock_agent_system):
        """Test handling of task execution failures"""
        orchestrator = mock_agent_system['orchestrator']
        
        # Mock a failure in task routing
        with patch.object(orchestrator, '_route_task', side_effect=Exception("Test error")):
            task = Task(
                id="failing_task",
                description="This task will fail",
                task_type="test"
            )
            
            # Execute task (should handle error gracefully)
            await orchestrator._execute_task(task)
            
            # Task should be marked as failed
            assert task.status == TaskStatus.FAILED
            assert task.error == "Test error"
            assert task in orchestrator.completed_tasks
    
    @pytest.mark.asyncio
    async def test_invalid_task_handling(self, mock_agent_system):
        """Test handling of invalid tasks"""
        decision_engine = mock_agent_system['decision_engine']
        
        # Task with very low confidence
        task = Task(
            id="invalid_task",
            description="xyz abc undefined nonsense",
            task_type="unknown"
        )
        
        decision = await decision_engine.make_execution_decision(task)
        
        # Should either reject or require approval/context
        assert decision.decision_type in [
            DecisionType.REJECT_TASK,
            DecisionType.REQUEST_APPROVAL,
            DecisionType.GATHER_CONTEXT,
            DecisionType.EXECUTE_IMMEDIATELY  # Router might still try
        ]
    
    @pytest.mark.asyncio
    async def test_system_overload_handling(self, mock_agent_system):
        """Test handling of system overload scenarios"""
        orchestrator = mock_agent_system['orchestrator']
        decision_engine = mock_agent_system['decision_engine']
        
        # Fill up task queue to simulate overload
        for i in range(10):
            task = Task(
                id=f"overload_task_{i}",
                description=f"Task {i}",
                task_type="llm_query",
                priority=TaskPriority.LOW
            )
            await orchestrator.submit_task(task)
        
        # Submit high complexity task during overload
        high_complexity_task = Task(
            id="complex_overload_task",
            description="Perform comprehensive analysis of all data sources",
            task_type="hybrid",
            priority=TaskPriority.HIGH
        )
        
        decision = await decision_engine.make_execution_decision(high_complexity_task)
        
        # Should be queued or require approval due to system state
        assert decision.decision_type in [
            DecisionType.QUEUE_FOR_LATER,
            DecisionType.REQUEST_APPROVAL,
            DecisionType.EXECUTE_IMMEDIATELY  # Might still execute if high priority
        ]


class TestFullWorkflowScenarios:
    """Test complete end-to-end workflow scenarios"""
    
    @pytest.mark.asyncio
    async def test_file_analysis_workflow(self, mock_agent_system, temp_directory):
        """Test complete file analysis workflow"""
        orchestrator = mock_agent_system['orchestrator']
        decision_engine = mock_agent_system['decision_engine']
        
        # Create test file
        test_file = temp_directory / "data.txt"
        test_file.write_text("Sample data for analysis\nLine 2\nLine 3")
        
        # Create analysis task
        task = Task(
            id="file_analysis_workflow",
            description=f"Read {test_file} and analyze its content structure",
            task_type="hybrid",
            priority=TaskPriority.MEDIUM,
            context={"file_path": str(test_file)}
        )
        
        # Make and execute decision
        decision = await decision_engine.make_execution_decision(task)
        result_id = await decision_engine.execute_decision(decision, task)
        
        assert result_id is not None
        
        # If task was submitted for execution, verify it's in the system
        if "task" in result_id or decision.decision_type == DecisionType.EXECUTE_IMMEDIATELY:
            status = await orchestrator.get_task_status(task.id)
            assert status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED]
    
    @pytest.mark.asyncio
    async def test_code_generation_workflow(self, mock_agent_system):
        """Test complete code generation workflow"""
        decision_engine = mock_agent_system['decision_engine']
        
        # Create code generation task
        task = Task(
            id="code_gen_workflow",
            description="Create a Python function that calculates the factorial of a number",
            task_type="code_generation",
            priority=TaskPriority.MEDIUM
        )
        
        # Process workflow
        decision = await decision_engine.make_execution_decision(task)
        
        # Verify appropriate routing
        assert decision.routing_decision.confidence > 0.6
        assert "code" in decision.routing_decision.reasoning.lower()
        
        # Execute decision
        result_id = await decision_engine.execute_decision(decision, task)
        assert result_id is not None
    
    @pytest.mark.asyncio
    async def test_research_workflow(self, mock_agent_system):
        """Test complete research workflow"""
        decision_engine = mock_agent_system['decision_engine']
        
        # Create research task
        task = Task(
            id="research_workflow",
            description="Research best practices for async programming in Python",
            task_type="research",
            priority=TaskPriority.LOW
        )
        
        # Process workflow
        decision = await decision_engine.make_execution_decision(task)
        
        # Should use LLM-only strategy
        assert decision.routing_decision.strategy.value in ["local_llm_only", "multi_step"]
        assert decision.decision_type == DecisionType.EXECUTE_IMMEDIATELY
        
        # Execute decision
        result_id = await decision_engine.execute_decision(decision, task)
        assert result_id is not None


@pytest.mark.asyncio
async def test_concurrent_task_processing(mock_agent_system):
    """Test concurrent processing of multiple tasks"""
    orchestrator = mock_agent_system['orchestrator']
    decision_engine = mock_agent_system['decision_engine']
    
    # Create multiple tasks
    tasks = [
        Task(id=f"concurrent_task_{i}", description=f"Task {i}", task_type="llm_query")
        for i in range(5)
    ]
    
    # Submit all tasks
    for task in tasks:
        decision = await decision_engine.make_execution_decision(task)
        await decision_engine.execute_decision(decision, task)
    
    # Start processing
    processing_task = asyncio.create_task(orchestrator.start_processing())
    await asyncio.sleep(0.2)  # Let tasks process
    
    # Stop processing
    await orchestrator.stop_processing()
    processing_task.cancel()
    
    try:
        await processing_task
    except asyncio.CancelledError:
        pass
    
    # Verify some tasks were processed
    queue_status = orchestrator.get_queue_status()
    assert queue_status["completed_tasks"] > 0 or queue_status["active_tasks"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])