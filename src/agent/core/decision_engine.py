"""
Decision Engine

Coordinates task routing decisions with orchestrator execution,
providing intelligent decision-making for complex task workflows.

Author: Claude Code
Date: 2025-07-13
Session: 1.3
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .orchestrator import AgentOrchestrator, Task, TaskStatus, TaskPriority
from .task_router import TaskRouter, RoutingDecision, TaskCategory, ExecutionStrategy
from ...utils.logger import get_logger

logger = get_logger(__name__)


class DecisionType(Enum):
    """Types of decisions the engine can make"""
    EXECUTE_IMMEDIATELY = "execute_immediately"
    QUEUE_FOR_LATER = "queue_for_later"
    REQUEST_APPROVAL = "request_approval"
    DECOMPOSE_TASK = "decompose_task"
    GATHER_CONTEXT = "gather_context"
    REJECT_TASK = "reject_task"


@dataclass
class ExecutionDecision:
    """Decision on how to execute a task"""
    decision_type: DecisionType
    routing_decision: RoutingDecision
    execution_plan: Dict[str, Any]
    dependencies: List[str] = None
    approval_reason: Optional[str] = None
    context_requirements: List[str] = None
    decomposed_tasks: List[Task] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.context_requirements is None:
            self.context_requirements = []
        if self.decomposed_tasks is None:
            self.decomposed_tasks = []


class DecisionEngine:
    """
    Intelligent decision engine that coordinates between task routing and execution.
    
    Features:
    - Analyzes routing decisions against current system state
    - Makes intelligent execution decisions
    - Handles task decomposition for complex workflows
    - Manages resource allocation and dependencies
    - Provides approval and context gathering workflows
    """
    
    def __init__(self, orchestrator: AgentOrchestrator, router: TaskRouter):
        """
        Initialize decision engine.
        
        Args:
            orchestrator: Agent orchestrator instance
            router: Task router instance
        """
        self.orchestrator = orchestrator
        self.router = router
        
        # Decision configuration
        self.max_queue_size = 20
        self.approval_complexity_threshold = 4
        self.resource_usage_threshold = 0.8
        
        # State tracking
        self.pending_approvals: Dict[str, ExecutionDecision] = {}
        self.context_requests: Dict[str, ExecutionDecision] = {}
        
        logger.info("Decision engine initialized")
    
    async def make_execution_decision(self, task: Task, context: Dict[str, Any] = None) -> ExecutionDecision:
        """
        Make intelligent decision on how to execute a task.
        
        Args:
            task: Task to analyze
            context: Additional context for decision making
            
        Returns:
            Execution decision with detailed plan
        """
        logger.info(f"Making execution decision for task: {task.id}")
        
        # Get routing decision from router
        routing_decision = await self.router.route_task(
            description=task.description,
            context=task.context,
            user_preferences=context.get('user_preferences') if context else None
        )
        
        # Analyze current system state
        system_state = await self._analyze_system_state()
        
        # Make decision based on routing + system state
        decision = await self._decide_execution_approach(task, routing_decision, system_state)
        
        logger.info(f"Decision made: {decision.decision_type.value} for task {task.id}")
        return decision
    
    async def execute_decision(self, decision: ExecutionDecision, task: Task) -> str:
        """
        Execute a decision by coordinating with the orchestrator.
        
        Args:
            decision: Execution decision to implement
            task: Original task
            
        Returns:
            Task ID or decision ID for tracking
        """
        decision_type = decision.decision_type
        
        if decision_type == DecisionType.EXECUTE_IMMEDIATELY:
            return await self._execute_immediately(decision, task)
        
        elif decision_type == DecisionType.QUEUE_FOR_LATER:
            return await self._queue_for_later(decision, task)
        
        elif decision_type == DecisionType.REQUEST_APPROVAL:
            return await self._request_approval(decision, task)
        
        elif decision_type == DecisionType.DECOMPOSE_TASK:
            return await self._decompose_and_execute(decision, task)
        
        elif decision_type == DecisionType.GATHER_CONTEXT:
            return await self._gather_context(decision, task)
        
        elif decision_type == DecisionType.REJECT_TASK:
            return await self._reject_task(decision, task)
        
        else:
            raise ValueError(f"Unknown decision type: {decision_type}")
    
    async def _analyze_system_state(self) -> Dict[str, Any]:
        """Analyze current system state for decision making"""
        queue_status = self.orchestrator.get_queue_status()
        active_tasks = self.orchestrator.get_active_tasks()
        
        # Calculate resource utilization
        max_concurrent = self.orchestrator.config.max_concurrent_tasks
        current_active = len(active_tasks)
        resource_utilization = current_active / max_concurrent if max_concurrent > 0 else 0
        
        # Analyze task types in queue
        task_types = {}
        for task in active_tasks:
            task_type = task.task_type
            task_types[task_type] = task_types.get(task_type, 0) + 1
        
        return {
            "queue_status": queue_status,
            "resource_utilization": resource_utilization,
            "active_task_types": task_types,
            "pending_approvals": len(self.pending_approvals),
            "context_requests": len(self.context_requests),
            "system_busy": resource_utilization > self.resource_usage_threshold
        }
    
    async def _decide_execution_approach(
        self, 
        task: Task, 
        routing_decision: RoutingDecision, 
        system_state: Dict[str, Any]
    ) -> ExecutionDecision:
        """Core decision logic"""
        
        # Check for immediate rejection conditions
        if routing_decision.confidence < 0.3:
            return ExecutionDecision(
                decision_type=DecisionType.REJECT_TASK,
                routing_decision=routing_decision,
                execution_plan={"reason": "Low confidence in task understanding"},
                approval_reason="Task description too ambiguous"
            )
        
        # Check if human approval is required
        if routing_decision.requires_human_approval:
            return ExecutionDecision(
                decision_type=DecisionType.REQUEST_APPROVAL,
                routing_decision=routing_decision,
                execution_plan=self._create_execution_plan(routing_decision),
                approval_reason=f"High complexity ({routing_decision.estimated_complexity}/5) or potentially destructive operation"
            )
        
        # Check if additional context is needed
        if routing_decision.requires_context:
            context_reqs = self._determine_context_requirements(routing_decision, task)
            if context_reqs:
                return ExecutionDecision(
                    decision_type=DecisionType.GATHER_CONTEXT,
                    routing_decision=routing_decision,
                    execution_plan=self._create_execution_plan(routing_decision),
                    context_requirements=context_reqs
                )
        
        # Check if task should be decomposed
        if await self._should_decompose_task(routing_decision, system_state):
            decomposed = await self._decompose_task(task, routing_decision)
            return ExecutionDecision(
                decision_type=DecisionType.DECOMPOSE_TASK,
                routing_decision=routing_decision,
                execution_plan=self._create_execution_plan(routing_decision),
                decomposed_tasks=decomposed
            )
        
        # Check system load
        if system_state["system_busy"] and routing_decision.estimated_complexity >= 3:
            return ExecutionDecision(
                decision_type=DecisionType.QUEUE_FOR_LATER,
                routing_decision=routing_decision,
                execution_plan=self._create_execution_plan(routing_decision)
            )
        
        # Default: execute immediately
        return ExecutionDecision(
            decision_type=DecisionType.EXECUTE_IMMEDIATELY,
            routing_decision=routing_decision,
            execution_plan=self._create_execution_plan(routing_decision)
        )
    
    def _create_execution_plan(self, routing_decision: RoutingDecision) -> Dict[str, Any]:
        """Create detailed execution plan from routing decision"""
        return {
            "strategy": routing_decision.strategy.value,
            "tools": routing_decision.suggested_tools,
            "estimated_duration": routing_decision.estimated_duration,
            "complexity": routing_decision.estimated_complexity,
            "confidence": routing_decision.confidence,
            "reasoning": routing_decision.reasoning
        }
    
    def _determine_context_requirements(self, routing_decision: RoutingDecision, task: Task) -> List[str]:
        """Determine what additional context is needed"""
        requirements = []
        
        # Check for file-related context needs
        if routing_decision.category == TaskCategory.FILE_OPERATIONS:
            if "current directory" in task.description.lower():
                requirements.append("working_directory")
            if "recent files" in task.description.lower():
                requirements.append("recent_file_list")
        
        # Check for code-related context needs
        if routing_decision.category == TaskCategory.CODE_GENERATION:
            if any(ref in task.description.lower() for ref in ["this project", "current code", "existing"]):
                requirements.append("project_structure")
                requirements.append("recent_code_changes")
        
        # Check for analysis context needs
        if routing_decision.category == TaskCategory.DATA_ANALYSIS:
            if "previous analysis" in task.description.lower():
                requirements.append("analysis_history")
        
        return requirements
    
    async def _should_decompose_task(self, routing_decision: RoutingDecision, system_state: Dict[str, Any]) -> bool:
        """Determine if task should be decomposed into smaller tasks"""
        # Decompose if multi-step strategy or high complexity
        if routing_decision.strategy == ExecutionStrategy.MULTI_STEP:
            return True
        
        if routing_decision.estimated_complexity >= 4:
            return True
        
        # Decompose if task duration is very long and system is busy
        if routing_decision.estimated_duration > 600 and system_state["system_busy"]:
            return True
        
        return False
    
    async def _decompose_task(self, task: Task, routing_decision: RoutingDecision) -> List[Task]:
        """Decompose a complex task into smaller subtasks"""
        subtasks = []
        
        # Basic decomposition based on task type
        if routing_decision.category == TaskCategory.HYBRID:
            # Split hybrid tasks into LLM + MCP components
            subtasks.append(Task(
                id=f"{task.id}_analysis",
                description=f"Analyze requirements for: {task.description}",
                task_type="llm_query",
                priority=task.priority,
                context=task.context.copy() if task.context else {}
            ))
            
            subtasks.append(Task(
                id=f"{task.id}_execution",
                description=f"Execute file operations for: {task.description}",
                task_type="file_operation",
                priority=task.priority,
                context=task.context.copy() if task.context else {}
            ))
        
        elif routing_decision.estimated_complexity >= 4:
            # Split high complexity tasks into preparation + execution
            subtasks.append(Task(
                id=f"{task.id}_prepare",
                description=f"Prepare for: {task.description}",
                task_type="analysis",
                priority=TaskPriority.HIGH,
                context=task.context.copy() if task.context else {}
            ))
            
            subtasks.append(Task(
                id=f"{task.id}_execute",
                description=f"Execute: {task.description}",
                task_type=task.task_type,
                priority=task.priority,
                context=task.context.copy() if task.context else {}
            ))
        
        return subtasks
    
    async def _execute_immediately(self, decision: ExecutionDecision, task: Task) -> str:
        """Execute task immediately via orchestrator"""
        # Update task type based on routing decision
        task.task_type = decision.routing_decision.strategy.value
        
        # Submit to orchestrator
        task_id = await self.orchestrator.submit_task(task)
        
        logger.info(f"Task {task.id} submitted for immediate execution as {task_id}")
        return task_id
    
    async def _queue_for_later(self, decision: ExecutionDecision, task: Task) -> str:
        """Queue task for later execution"""
        # Lower priority for queued tasks
        if task.priority != TaskPriority.CRITICAL:
            task.priority = TaskPriority.LOW
        
        task.task_type = decision.routing_decision.strategy.value
        task_id = await self.orchestrator.submit_task(task)
        
        logger.info(f"Task {task.id} queued for later execution as {task_id}")
        return task_id
    
    async def _request_approval(self, decision: ExecutionDecision, task: Task) -> str:
        """Request human approval for task execution"""
        approval_id = f"approval_{task.id}"
        self.pending_approvals[approval_id] = decision
        
        logger.info(f"Task {task.id} requires approval: {decision.approval_reason}")
        
        # In a real implementation, this would integrate with a UI or notification system
        # For now, we'll log the approval request
        logger.warning(f"APPROVAL REQUIRED for task {task.id}: {decision.approval_reason}")
        
        return approval_id
    
    async def _decompose_and_execute(self, decision: ExecutionDecision, task: Task) -> str:
        """Decompose task and execute subtasks"""
        subtask_ids = []
        
        for subtask in decision.decomposed_tasks:
            # Submit each subtask
            subtask_id = await self.orchestrator.submit_task(subtask)
            subtask_ids.append(subtask_id)
        
        logger.info(f"Task {task.id} decomposed into {len(subtask_ids)} subtasks: {subtask_ids}")
        return f"decomposed_{task.id}"
    
    async def _gather_context(self, decision: ExecutionDecision, task: Task) -> str:
        """Gather additional context before execution"""
        context_id = f"context_{task.id}"
        self.context_requests[context_id] = decision
        
        logger.info(f"Gathering context for task {task.id}: {decision.context_requirements}")
        
        # TODO: Implement context gathering logic
        # This would involve calling MCP servers or other context providers
        
        return context_id
    
    async def _reject_task(self, decision: ExecutionDecision, task: Task) -> str:
        """Reject task with explanation"""
        reason = decision.execution_plan.get("reason", "Unknown reason")
        
        logger.warning(f"Task {task.id} rejected: {reason}")
        
        # Mark task as failed
        task.status = TaskStatus.FAILED
        task.error = f"Rejected: {reason}"
        
        return f"rejected_{task.id}"
    
    async def approve_task(self, approval_id: str, approved: bool) -> Optional[str]:
        """
        Approve or reject a pending task.
        
        Args:
            approval_id: ID of approval request
            approved: Whether task is approved
            
        Returns:
            Task ID if approved and executed, None otherwise
        """
        if approval_id not in self.pending_approvals:
            logger.error(f"Approval ID not found: {approval_id}")
            return None
        
        decision = self.pending_approvals.pop(approval_id)
        task_id = approval_id.replace("approval_", "")
        
        if approved:
            logger.info(f"Task {task_id} approved for execution")
            # Create new task for execution
            approved_task = Task(
                id=task_id,
                description=f"Approved task: {task_id}",
                task_type=decision.routing_decision.strategy.value,
                priority=TaskPriority.HIGH
            )
            return await self._execute_immediately(decision, approved_task)
        else:
            logger.info(f"Task {task_id} rejected by user")
            return None
    
    async def provide_context(self, context_id: str, context_data: Dict[str, Any]) -> Optional[str]:
        """
        Provide requested context and execute task.
        
        Args:
            context_id: ID of context request
            context_data: Provided context data
            
        Returns:
            Task ID if executed, None otherwise
        """
        if context_id not in self.context_requests:
            logger.error(f"Context ID not found: {context_id}")
            return None
        
        decision = self.context_requests.pop(context_id)
        task_id = context_id.replace("context_", "")
        
        # Create task with additional context
        context_task = Task(
            id=task_id,
            description=f"Task with context: {task_id}",
            task_type=decision.routing_decision.strategy.value,
            priority=TaskPriority.MEDIUM,
            context=context_data
        )
        
        logger.info(f"Context provided for task {task_id}, executing...")
        return await self._execute_immediately(decision, context_task)
    
    def get_pending_approvals(self) -> Dict[str, Dict[str, Any]]:
        """Get list of pending approval requests"""
        approvals = {}
        for approval_id, decision in self.pending_approvals.items():
            approvals[approval_id] = {
                "reason": decision.approval_reason,
                "complexity": decision.routing_decision.estimated_complexity,
                "strategy": decision.routing_decision.strategy.value,
                "tools": decision.routing_decision.suggested_tools
            }
        return approvals
    
    def get_context_requests(self) -> Dict[str, Dict[str, Any]]:
        """Get list of pending context requests"""
        requests = {}
        for context_id, decision in self.context_requests.items():
            requests[context_id] = {
                "requirements": decision.context_requirements,
                "strategy": decision.routing_decision.strategy.value,
                "reasoning": decision.routing_decision.reasoning
            }
        return requests
    
    async def get_decision_summary(self, task: Task) -> str:
        """Get a summary of the decision-making process for a task"""
        decision = await self.make_execution_decision(task)
        
        summary = f"""
Decision Summary for Task: {task.id}

Task: {task.description}
Category: {decision.routing_decision.category.value}
Strategy: {decision.routing_decision.strategy.value}
Decision: {decision.decision_type.value}

Reasoning: {decision.routing_decision.reasoning}

Execution Plan:
- Complexity: {decision.routing_decision.estimated_complexity}/5
- Duration: {decision.routing_decision.estimated_duration:.0f}s
- Tools: {', '.join(decision.routing_decision.suggested_tools) if decision.routing_decision.suggested_tools else 'None'}
- Confidence: {decision.routing_decision.confidence:.1%}

Requirements:
- Approval: {'Yes' if decision.decision_type == DecisionType.REQUEST_APPROVAL else 'No'}
- Context: {'Yes' if decision.decision_type == DecisionType.GATHER_CONTEXT else 'No'}
- Decomposition: {'Yes' if decision.decision_type == DecisionType.DECOMPOSE_TASK else 'No'}
"""
        return summary.strip()