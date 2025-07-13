"""
Workflow Engine

Core workflow execution engine that orchestrates complex multi-step tasks
with dependency management, error recovery, and parallel execution.

Author: Claude Code
Date: 2025-07-13
Session: 2.2
"""

import asyncio
import time
import uuid
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import logging

from .step_executor import StepExecutor, StepResult, StepType
from .condition_evaluator import ConditionEvaluator
from .dependency_manager import DependencyManager, Dependency, DependencyType
from ...utils.logger import get_logger

logger = get_logger(__name__)


class WorkflowStatus(Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(Enum):
    """Individual step status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING = "waiting"  # Waiting for dependencies


@dataclass
class WorkflowStep:
    """Individual workflow step definition"""
    id: str
    name: str
    step_type: StepType
    action: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    conditions: List[str] = field(default_factory=list)
    retry_count: int = 3
    timeout: float = 300.0
    parallel_group: Optional[str] = None
    
    # Runtime state
    status: StepStatus = StepStatus.PENDING
    result: Optional[StepResult] = None
    attempts: int = 0
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None


@dataclass 
class WorkflowDefinition:
    """Complete workflow definition"""
    id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    global_timeout: float = 1800.0  # 30 minutes
    max_retries: int = 3
    failure_strategy: str = "stop"  # stop, continue, rollback
    context: Dict[str, Any] = field(default_factory=dict)
    
    # Runtime state
    status: WorkflowStatus = WorkflowStatus.PENDING
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    current_step: Optional[str] = None
    execution_context: Dict[str, Any] = field(default_factory=dict)


class WorkflowEngine:
    """
    Advanced workflow execution engine.
    
    Features:
    - Multi-step task orchestration
    - Dependency management
    - Parallel execution groups
    - Conditional logic
    - Error recovery and retry
    - Context sharing between steps
    - Workflow templates
    """
    
    def __init__(self, orchestrator=None):
        """
        Initialize workflow engine.
        
        Args:
            orchestrator: Agent orchestrator for task execution
        """
        self.orchestrator = orchestrator
        self.step_executor = StepExecutor(orchestrator)
        self.condition_evaluator = ConditionEvaluator()
        self.dependency_manager = DependencyManager()
        
        # Active workflows
        self.running_workflows: Dict[str, WorkflowDefinition] = {}
        self.workflow_history: List[WorkflowDefinition] = []
        
        # Execution control
        self._max_concurrent_workflows = 5
        self._workflow_semaphore = asyncio.Semaphore(self._max_concurrent_workflows)
        
        logger.info("Workflow engine initialized")
    
    async def execute_workflow(self, workflow: WorkflowDefinition) -> WorkflowDefinition:
        """
        Execute a complete workflow.
        
        Args:
            workflow: Workflow definition to execute
            
        Returns:
            Updated workflow with execution results
        """
        async with self._workflow_semaphore:
            workflow_id = workflow.id
            logger.info(f"Starting workflow execution: {workflow_id} - {workflow.name}")
            
            try:
                # Initialize workflow
                workflow.status = WorkflowStatus.RUNNING
                workflow.started_at = time.time()
                self.running_workflows[workflow_id] = workflow
                
                # Execute workflow steps
                await self._execute_workflow_steps(workflow)
                
                # Mark as completed
                workflow.status = WorkflowStatus.COMPLETED
                workflow.completed_at = time.time()
                
                logger.info(f"Workflow completed: {workflow_id}")
                
            except Exception as e:
                logger.error(f"Workflow failed: {workflow_id} - {e}")
                workflow.status = WorkflowStatus.FAILED
                workflow.completed_at = time.time()
                
                # Handle failure strategy
                await self._handle_workflow_failure(workflow, str(e))
            
            finally:
                # Move to history
                self.running_workflows.pop(workflow_id, None)
                self.workflow_history.append(workflow)
                
                # Cleanup old history
                if len(self.workflow_history) > 100:
                    self.workflow_history = self.workflow_history[-100:]
            
            return workflow
    
    async def _execute_workflow_steps(self, workflow: WorkflowDefinition):
        """Execute all steps in a workflow with advanced dependency management"""
        # Setup dependency manager
        self.dependency_manager.clear()
        
        # Add all steps to dependency manager
        for step in workflow.steps:
            dependencies = []
            for dep_id in step.dependencies:
                dependencies.append(Dependency(
                    step_id=dep_id,
                    dependency_type=DependencyType.SUCCESS
                ))
            self.dependency_manager.add_step(step.id, dependencies)
        
        # Validate dependencies
        is_valid, errors = self.dependency_manager.validate_dependencies()
        if not is_valid:
            raise Exception(f"Invalid workflow dependencies: {'; '.join(errors)}")
        
        # Calculate execution order
        execution_order = self.dependency_manager.calculate_execution_order()
        logger.info(f"Workflow execution plan: {len(execution_order)} levels")
        
        steps_by_id = {step.id: step for step in workflow.steps}
        completed_steps: Set[str] = set()
        failed_steps: Set[str] = set()
        step_results: Dict[str, Any] = {}
        
        # Execute steps level by level
        for level, step_ids in enumerate(execution_order):
            logger.info(f"Executing level {level}: {step_ids}")
            
            # Filter steps that are ready and not failed
            ready_step_ids = []
            for step_id in step_ids:
                if step_id in steps_by_id:
                    step = steps_by_id[step_id]
                    if step.status == StepStatus.PENDING:
                        # Check conditions
                        if await self._check_step_conditions(step, workflow):
                            ready_step_ids.append(step_id)
                        else:
                            step.status = StepStatus.SKIPPED
                            completed_steps.add(step_id)
            
            if not ready_step_ids:
                continue
            
            # Execute steps in parallel within this level
            if len(ready_step_ids) == 1:
                # Single step
                step = steps_by_id[ready_step_ids[0]]
                workflow.current_step = step.id
                result = await self._execute_step_with_recovery(step, workflow)
                
                if result.success:
                    step.status = StepStatus.COMPLETED
                    completed_steps.add(step.id)
                    step_results[step.id] = result.output_data or {}
                    await self.dependency_manager.mark_step_completed(step.id, True, result.output_data)
                else:
                    failed_steps.add(step.id)
                    await self._handle_step_failure(step, workflow, result.error)
            else:
                # Multiple steps - execute in parallel
                tasks = []
                for step_id in ready_step_ids:
                    step = steps_by_id[step_id]
                    workflow.current_step = step.id
                    task = asyncio.create_task(self._execute_step_with_recovery(step, workflow))
                    tasks.append((step, task))
                
                # Wait for all parallel steps
                for step, task in tasks:
                    try:
                        result = await task
                        if result.success:
                            step.status = StepStatus.COMPLETED
                            completed_steps.add(step.id)
                            step_results[step.id] = result.output_data or {}
                            await self.dependency_manager.mark_step_completed(step.id, True, result.output_data)
                        else:
                            failed_steps.add(step.id)
                            await self._handle_step_failure(step, workflow, result.error)
                    except Exception as e:
                        failed_steps.add(step.id)
                        await self._handle_step_failure(step, workflow, str(e))
            
            # Check if we should continue after failures
            if failed_steps and workflow.failure_strategy == "stop":
                logger.error(f"Stopping workflow due to failed steps: {failed_steps}")
                break
    
    async def _execute_step(self, step: WorkflowStep, workflow: WorkflowDefinition) -> StepResult:
        """Execute a single workflow step with retry logic"""
        step.status = StepStatus.RUNNING
        step.started_at = time.time()
        
        logger.info(f"Executing step: {step.id} - {step.name}")
        
        for attempt in range(step.retry_count + 1):
            step.attempts = attempt + 1
            
            try:
                # Execute the step
                result = await self.step_executor.execute_step(step, workflow.execution_context)
                
                if result.success:
                    step.completed_at = time.time()
                    step.result = result
                    
                    # Update workflow context with step results
                    if result.output_data:
                        workflow.execution_context.update(result.output_data)
                    
                    logger.info(f"Step completed: {step.id}")
                    return result
                else:
                    logger.warning(f"Step failed (attempt {attempt + 1}): {step.id} - {result.error}")
                    
                    if attempt < step.retry_count:
                        # Wait before retry
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        step.error = result.error
                        step.completed_at = time.time()
                        return result
                        
            except asyncio.TimeoutError:
                error = f"Step timed out after {step.timeout} seconds"
                logger.error(f"Step timeout: {step.id} - {error}")
                
                if attempt < step.retry_count:
                    await asyncio.sleep(2 ** attempt)
                else:
                    step.error = error
                    step.completed_at = time.time()
                    return StepResult(success=False, error=error)
                    
            except Exception as e:
                error = f"Step execution error: {str(e)}"
                logger.error(f"Step error: {step.id} - {error}")
                
                if attempt < step.retry_count:
                    await asyncio.sleep(2 ** attempt)
                else:
                    step.error = error
                    step.completed_at = time.time()
                    return StepResult(success=False, error=error)
        
        # Should not reach here
        return StepResult(success=False, error="Maximum retries exceeded")
    
    async def _execute_step_with_recovery(self, step: WorkflowStep, workflow: WorkflowDefinition) -> StepResult:
        """Execute step with enhanced error recovery and adaptive retry logic"""
        step.status = StepStatus.RUNNING
        step.started_at = time.time()
        
        logger.info(f"Executing step with recovery: {step.id} - {step.name}")
        
        last_error = None
        recovery_strategies = ["retry", "fallback", "skip_non_critical"]
        
        for attempt in range(step.retry_count + 1):
            step.attempts = attempt + 1
            
            try:
                # Calculate dynamic timeout based on previous attempts
                timeout = step.timeout * (1.2 ** attempt)  # Increase timeout each attempt
                
                # Execute the step with timeout
                result = await asyncio.wait_for(
                    self.step_executor.execute_step(step, workflow.execution_context),
                    timeout=timeout
                )
                
                if result.success:
                    step.completed_at = time.time()
                    step.result = result
                    
                    # Update workflow context with step results
                    if result.output_data:
                        workflow.execution_context.update(result.output_data)
                    
                    logger.info(f"Step completed successfully: {step.id}")
                    return result
                else:
                    last_error = result.error
                    logger.warning(f"Step failed (attempt {attempt + 1}): {step.id} - {result.error}")
                    
                    # Try recovery strategies
                    if attempt < step.retry_count:
                        recovery_result = await self._apply_recovery_strategy(
                            step, workflow, result.error, attempt, recovery_strategies
                        )
                        
                        if recovery_result:
                            # Recovery successful, continue to next attempt
                            wait_time = min(2 ** attempt, 30)  # Cap at 30 seconds
                            logger.info(f"Applying recovery strategy, waiting {wait_time}s before retry")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            # Recovery failed, exit early
                            break
                    
            except asyncio.TimeoutError:
                last_error = f"Step timed out after {timeout:.1f} seconds"
                logger.error(f"Step timeout: {step.id} - {last_error}")
                
                if attempt < step.retry_count:
                    # Try timeout recovery
                    if await self._recover_from_timeout(step, workflow, attempt):
                        continue
                    
            except Exception as e:
                last_error = f"Step execution error: {str(e)}"
                logger.error(f"Step error: {step.id} - {last_error}")
                
                if attempt < step.retry_count:
                    # General error recovery
                    if await self._recover_from_error(step, workflow, e, attempt):
                        continue
        
        # All attempts failed
        step.error = last_error
        step.completed_at = time.time()
        step.status = StepStatus.FAILED
        
        return StepResult(success=False, error=last_error)
    
    async def _apply_recovery_strategy(self, step: WorkflowStep, workflow: WorkflowDefinition,
                                     error: str, attempt: int, 
                                     strategies: List[str]) -> bool:
        """Apply recovery strategies based on error type and attempt number"""
        
        # Analyze error type
        error_lower = error.lower()
        
        # Network/connectivity errors
        if any(keyword in error_lower for keyword in ["connection", "network", "timeout", "unreachable"]):
            logger.info(f"Applying network recovery for step {step.id}")
            return True  # Allow retry
        
        # Permission errors
        elif any(keyword in error_lower for keyword in ["permission", "access", "forbidden", "unauthorized"]):
            logger.warning(f"Permission error in step {step.id}, checking alternative approaches")
            # Could try alternative execution methods
            return False  # Don't retry permission errors
        
        # Resource errors
        elif any(keyword in error_lower for keyword in ["memory", "disk", "resource", "quota"]):
            logger.info(f"Resource error in step {step.id}, attempting cleanup")
            # Could trigger cleanup operations
            await asyncio.sleep(5)  # Wait for resources to free up
            return True
        
        # File not found errors
        elif any(keyword in error_lower for keyword in ["not found", "missing", "does not exist"]):
            logger.info(f"Missing resource error in step {step.id}, checking alternatives")
            # Could try creating missing resources or using alternatives
            return attempt < 2  # Only retry a couple times
        
        # Default recovery
        return attempt < 3  # Default retry limit
    
    async def _recover_from_timeout(self, step: WorkflowStep, workflow: WorkflowDefinition,
                                   attempt: int) -> bool:
        """Recover from timeout errors"""
        logger.info(f"Attempting timeout recovery for step {step.id}")
        
        # Increase timeout for next attempt
        step.timeout = min(step.timeout * 1.5, 600)  # Cap at 10 minutes
        
        # For file operations, try smaller chunks
        if step.step_type == StepType.FILE_OPERATION:
            if "batch_size" in step.parameters:
                step.parameters["batch_size"] = max(step.parameters["batch_size"] // 2, 1)
            
        return True
    
    async def _recover_from_error(self, step: WorkflowStep, workflow: WorkflowDefinition,
                                error: Exception, attempt: int) -> bool:
        """Recover from general errors"""
        logger.info(f"Attempting error recovery for step {step.id}: {type(error).__name__}")
        
        # For network-related steps, wait longer between retries
        if step.step_type in [StepType.MCP_TOOL, StepType.SYSTEM_COMMAND]:
            await asyncio.sleep(min(5 * (attempt + 1), 30))
        
        # Try alternative parameters for certain step types
        if step.step_type == StepType.LLM_QUERY and "model_type" in step.parameters:
            # Try alternative model
            current_model = step.parameters.get("model_type", "primary")
            if current_model == "primary":
                step.parameters["model_type"] = "fallback"
                logger.info(f"Switching to fallback model for step {step.id}")
        
        return True
    
    async def _check_step_conditions(self, step: WorkflowStep, workflow: WorkflowDefinition) -> bool:
        """Check if step conditions are satisfied"""
        if not step.conditions:
            return True
        
        for condition in step.conditions:
            if not await self.condition_evaluator.evaluate(condition, workflow.execution_context):
                logger.debug(f"Step condition not met: {step.id} - {condition}")
                return False
        
        return True
    
    async def _handle_step_failure(self, step: WorkflowStep, workflow: WorkflowDefinition, error: str):
        """Handle step failure based on workflow failure strategy"""
        step.status = StepStatus.FAILED
        step.error = error
        
        logger.error(f"Step failed: {step.id} - {error}")
        
        if workflow.failure_strategy == "stop":
            raise Exception(f"Workflow stopped due to step failure: {step.id} - {error}")
        elif workflow.failure_strategy == "continue":
            logger.warning(f"Continuing workflow despite step failure: {step.id}")
        elif workflow.failure_strategy == "rollback":
            await self._rollback_workflow(workflow, step.id)
            raise Exception(f"Workflow rolled back due to step failure: {step.id}")
    
    async def _handle_workflow_failure(self, workflow: WorkflowDefinition, error: str):
        """Handle overall workflow failure"""
        logger.error(f"Workflow failure: {workflow.id} - {error}")
        
        # Mark remaining steps as skipped
        for step in workflow.steps:
            if step.status == StepStatus.PENDING:
                step.status = StepStatus.SKIPPED
    
    async def _rollback_workflow(self, workflow: WorkflowDefinition, failed_step_id: str):
        """Rollback workflow by reversing completed steps"""
        logger.info(f"Rolling back workflow: {workflow.id}")
        
        # Find completed steps that should be rolled back
        rollback_steps = []
        for step in reversed(workflow.steps):
            if step.status == StepStatus.COMPLETED:
                rollback_steps.append(step)
            if step.id == failed_step_id:
                break
        
        # Execute rollback for each step
        for step in rollback_steps:
            try:
                await self.step_executor.rollback_step(step, workflow.execution_context)
                logger.info(f"Rolled back step: {step.id}")
            except Exception as e:
                logger.error(f"Rollback failed for step: {step.id} - {e}")
    
    async def pause_workflow(self, workflow_id: str) -> bool:
        """Pause a running workflow"""
        if workflow_id in self.running_workflows:
            workflow = self.running_workflows[workflow_id]
            workflow.status = WorkflowStatus.PAUSED
            logger.info(f"Workflow paused: {workflow_id}")
            return True
        return False
    
    async def resume_workflow(self, workflow_id: str) -> bool:
        """Resume a paused workflow"""
        if workflow_id in self.running_workflows:
            workflow = self.running_workflows[workflow_id]
            if workflow.status == WorkflowStatus.PAUSED:
                workflow.status = WorkflowStatus.RUNNING
                logger.info(f"Workflow resumed: {workflow_id}")
                return True
        return False
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow"""
        if workflow_id in self.running_workflows:
            workflow = self.running_workflows[workflow_id]
            workflow.status = WorkflowStatus.CANCELLED
            workflow.completed_at = time.time()
            
            # Mark remaining steps as skipped
            for step in workflow.steps:
                if step.status in [StepStatus.PENDING, StepStatus.RUNNING]:
                    step.status = StepStatus.SKIPPED
            
            logger.info(f"Workflow cancelled: {workflow_id}")
            return True
        return False
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed status of a workflow"""
        # Check running workflows
        if workflow_id in self.running_workflows:
            workflow = self.running_workflows[workflow_id]
        else:
            # Check history
            workflow = next((w for w in self.workflow_history if w.id == workflow_id), None)
            if not workflow:
                return None
        
        step_statuses = {}
        for step in workflow.steps:
            step_statuses[step.id] = {
                "status": step.status.value,
                "attempts": step.attempts,
                "started_at": step.started_at,
                "completed_at": step.completed_at,
                "error": step.error
            }
        
        return {
            "id": workflow.id,
            "name": workflow.name,
            "status": workflow.status.value,
            "started_at": workflow.started_at,
            "completed_at": workflow.completed_at,
            "current_step": workflow.current_step,
            "step_statuses": step_statuses,
            "execution_context": workflow.execution_context
        }
    
    def get_running_workflows(self) -> List[Dict[str, Any]]:
        """Get summary of all running workflows"""
        return [
            {
                "id": workflow.id,
                "name": workflow.name,
                "status": workflow.status.value,
                "started_at": workflow.started_at,
                "current_step": workflow.current_step
            }
            for workflow in self.running_workflows.values()
        ]
    
    async def create_workflow_from_template(self, template_name: str, parameters: Dict[str, Any]) -> WorkflowDefinition:
        """Create a workflow from a template"""
        # This will be implemented when we create workflow templates
        pass