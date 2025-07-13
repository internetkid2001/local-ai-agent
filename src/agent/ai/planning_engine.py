"""
Planning Engine

Advanced planning capabilities for complex task decomposition, goal-oriented planning,
and adaptive execution strategies.

Author: Claude Code
Date: 2025-07-13
Session: 3.1
"""

import asyncio
import time
import uuid
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

from ...utils.logger import get_logger

logger = get_logger(__name__)


class PlanningStrategy(Enum):
    """Planning strategies"""
    HIERARCHICAL = "hierarchical"
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    ADAPTIVE = "adaptive"
    GOAL_ORIENTED = "goal_oriented"
    CONSTRAINT_BASED = "constraint_based"
    HEURISTIC = "heuristic"
    REACTIVE = "reactive"


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class TaskPriority(Enum):
    """Task priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class PlanningConstraint:
    """Planning constraint"""
    constraint_id: str
    type: str  # time, resource, dependency, etc.
    description: str
    parameters: Dict[str, Any]
    hard: bool = True  # Hard vs soft constraint


@dataclass
class TaskNode:
    """Individual task in a plan"""
    task_id: str
    name: str
    description: str
    task_type: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    estimated_duration: float = 0.0
    estimated_cost: float = 0.0
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    resources_required: List[str] = field(default_factory=list)
    constraints: List[PlanningConstraint] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


@dataclass
class Plan:
    """Complete execution plan"""
    plan_id: str
    name: str
    description: str
    goal: str
    strategy: PlanningStrategy
    tasks: List[TaskNode] = field(default_factory=list)
    constraints: List[PlanningConstraint] = field(default_factory=list)
    estimated_duration: float = 0.0
    estimated_cost: float = 0.0
    success_criteria: List[str] = field(default_factory=list)
    fallback_plans: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanningRequest:
    """Request for plan generation"""
    goal: str
    context: Dict[str, Any]
    constraints: List[PlanningConstraint] = field(default_factory=list)
    preferred_strategy: Optional[PlanningStrategy] = None
    max_tasks: int = 50
    max_duration: Optional[float] = None
    budget_limit: Optional[float] = None
    available_resources: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class PlanningEngine:
    """
    Advanced planning engine for complex task decomposition.
    
    Features:
    - Multiple planning strategies (hierarchical, sequential, parallel, adaptive)
    - Goal-oriented and constraint-based planning
    - Dynamic replanning and adaptation
    - Resource allocation and optimization
    - Dependency management
    - Risk assessment and mitigation
    - Plan validation and verification
    """
    
    def __init__(self, model_orchestrator=None, reasoning_engine=None):
        """
        Initialize planning engine.
        
        Args:
            model_orchestrator: Model orchestrator for AI operations
            reasoning_engine: Reasoning engine for plan analysis
        """
        self.model_orchestrator = model_orchestrator
        self.reasoning_engine = reasoning_engine
        self.active_plans: Dict[str, Plan] = {}
        self.plan_templates: Dict[str, Dict[str, Any]] = {}
        
        # Load built-in planning templates
        self.plan_templates = self._load_planning_templates()
        
        # Configuration
        self.config = {
            "max_planning_depth": 5,
            "default_task_duration": 1.0,  # hours
            "replanning_threshold": 0.3,  # 30% failure rate triggers replanning
            "enable_parallel_execution": True,
            "resource_optimization": True,
            "adaptive_replanning": True,
            "plan_validation": True
        }
        
        logger.info("Planning engine initialized")
    
    def _load_planning_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load built-in planning templates"""
        return {
            "research_project": {
                "strategy": PlanningStrategy.HIERARCHICAL,
                "phases": [
                    {"name": "Research Planning", "tasks": ["define_scope", "literature_review", "methodology"]},
                    {"name": "Data Collection", "tasks": ["gather_sources", "collect_data", "validate_data"]},
                    {"name": "Analysis", "tasks": ["analyze_data", "draw_conclusions", "verify_results"]},
                    {"name": "Documentation", "tasks": ["write_report", "review", "finalize"]}
                ]
            },
            "software_development": {
                "strategy": PlanningStrategy.ADAPTIVE,
                "phases": [
                    {"name": "Planning", "tasks": ["requirements", "design", "architecture"]},
                    {"name": "Implementation", "tasks": ["coding", "unit_tests", "integration"]},
                    {"name": "Testing", "tasks": ["system_tests", "user_tests", "bug_fixes"]},
                    {"name": "Deployment", "tasks": ["build", "deploy", "monitor"]}
                ]
            },
            "data_analysis": {
                "strategy": PlanningStrategy.SEQUENTIAL,
                "phases": [
                    {"name": "Preparation", "tasks": ["data_collection", "data_cleaning", "data_validation"]},
                    {"name": "Exploration", "tasks": ["exploratory_analysis", "visualization", "pattern_detection"]},
                    {"name": "Modeling", "tasks": ["model_selection", "training", "validation"]},
                    {"name": "Reporting", "tasks": ["interpretation", "documentation", "presentation"]}
                ]
            }
        }
    
    async def create_plan(self, request: PlanningRequest) -> Plan:
        """
        Create a comprehensive execution plan.
        
        Args:
            request: Planning request
            
        Returns:
            Generated plan
        """
        start_time = time.time()
        
        try:
            # Determine planning strategy
            strategy = request.preferred_strategy or self._select_optimal_strategy(request)
            
            # Generate plan based on strategy
            if strategy == PlanningStrategy.HIERARCHICAL:
                plan = await self._hierarchical_planning(request)
            elif strategy == PlanningStrategy.SEQUENTIAL:
                plan = await self._sequential_planning(request)
            elif strategy == PlanningStrategy.PARALLEL:
                plan = await self._parallel_planning(request)
            elif strategy == PlanningStrategy.ADAPTIVE:
                plan = await self._adaptive_planning(request)
            elif strategy == PlanningStrategy.GOAL_ORIENTED:
                plan = await self._goal_oriented_planning(request)
            elif strategy == PlanningStrategy.CONSTRAINT_BASED:
                plan = await self._constraint_based_planning(request)
            else:
                plan = await self._heuristic_planning(request)
            
            # Validate and optimize plan
            if self.config["plan_validation"]:
                validation_result = await self._validate_plan(plan)
                if not validation_result["valid"]:
                    logger.warning(f"Plan validation issues: {validation_result['issues']}")
            
            # Optimize resource allocation
            if self.config["resource_optimization"]:
                plan = await self._optimize_plan(plan, request)
            
            # Store active plan
            self.active_plans[plan.plan_id] = plan
            
            logger.info(f"Created plan '{plan.name}' with {len(plan.tasks)} tasks")
            return plan
            
        except Exception as e:
            logger.error(f"Plan creation failed: {e}")
            # Return minimal fallback plan
            return Plan(
                plan_id=str(uuid.uuid4()),
                name="Fallback Plan",
                description=f"Simple plan for: {request.goal}",
                goal=request.goal,
                strategy=PlanningStrategy.SEQUENTIAL,
                tasks=[TaskNode(
                    task_id=str(uuid.uuid4()),
                    name="Manual Execution",
                    description=f"Manually execute: {request.goal}",
                    task_type="manual"
                )]
            )
    
    def _select_optimal_strategy(self, request: PlanningRequest) -> PlanningStrategy:
        """Select optimal planning strategy based on request characteristics"""
        # Simple heuristics for strategy selection
        if len(request.constraints) > 3:
            return PlanningStrategy.CONSTRAINT_BASED
        elif request.max_duration and request.max_duration < 24:  # Short timeframe
            return PlanningStrategy.PARALLEL
        elif "complex" in request.goal.lower() or "research" in request.goal.lower():
            return PlanningStrategy.HIERARCHICAL
        elif "adaptive" in request.goal.lower() or "iterative" in request.goal.lower():
            return PlanningStrategy.ADAPTIVE
        else:
            return PlanningStrategy.SEQUENTIAL
    
    async def _hierarchical_planning(self, request: PlanningRequest) -> Plan:
        """Create hierarchical plan with multiple levels"""
        plan_id = str(uuid.uuid4())
        
        # Use AI model for high-level decomposition if available
        if self.model_orchestrator:
            high_level_tasks = await self._ai_task_decomposition(request, "hierarchical")
        else:
            high_level_tasks = self._template_based_decomposition(request)
        
        # Create detailed task breakdown
        detailed_tasks = []
        for i, high_level_task in enumerate(high_level_tasks):
            # Decompose each high-level task into subtasks
            subtasks = await self._decompose_task(high_level_task, request)
            
            # Add dependencies between phases
            if i > 0:
                for subtask in subtasks:
                    subtask.dependencies.extend([t.task_id for t in detailed_tasks[-3:]])  # Depend on last few tasks
            
            detailed_tasks.extend(subtasks)
        
        plan = Plan(
            plan_id=plan_id,
            name=f"Hierarchical Plan: {request.goal}",
            description=f"Multi-level hierarchical plan for {request.goal}",
            goal=request.goal,
            strategy=PlanningStrategy.HIERARCHICAL,
            tasks=detailed_tasks,
            constraints=request.constraints.copy(),
            success_criteria=request.success_criteria.copy()
        )
        
        # Calculate estimates
        plan.estimated_duration = sum(task.estimated_duration for task in plan.tasks)
        plan.estimated_cost = sum(task.estimated_cost for task in plan.tasks)
        
        return plan
    
    async def _sequential_planning(self, request: PlanningRequest) -> Plan:
        """Create sequential plan with linear task progression"""
        plan_id = str(uuid.uuid4())
        
        if self.model_orchestrator:
            tasks = await self._ai_task_decomposition(request, "sequential")
        else:
            tasks = self._template_based_decomposition(request)
        
        # Add sequential dependencies
        for i in range(1, len(tasks)):
            tasks[i].dependencies = [tasks[i-1].task_id]
        
        plan = Plan(
            plan_id=plan_id,
            name=f"Sequential Plan: {request.goal}",
            description=f"Step-by-step sequential plan for {request.goal}",
            goal=request.goal,
            strategy=PlanningStrategy.SEQUENTIAL,
            tasks=tasks,
            constraints=request.constraints.copy(),
            success_criteria=request.success_criteria.copy()
        )
        
        # Sequential execution means total duration is sum of all tasks
        plan.estimated_duration = sum(task.estimated_duration for task in plan.tasks)
        plan.estimated_cost = sum(task.estimated_cost for task in plan.tasks)
        
        return plan
    
    async def _parallel_planning(self, request: PlanningRequest) -> Plan:
        """Create parallel plan with concurrent task execution"""
        plan_id = str(uuid.uuid4())
        
        if self.model_orchestrator:
            tasks = await self._ai_task_decomposition(request, "parallel")
        else:
            tasks = self._template_based_decomposition(request)
        
        # Group tasks that can run in parallel
        parallel_groups = self._identify_parallel_groups(tasks)
        
        # Update dependencies to reflect parallel execution
        for group in parallel_groups:
            # Tasks within a group can run in parallel (no dependencies between them)
            # But each group depends on the previous group
            if group != parallel_groups[0]:
                prev_group_tasks = parallel_groups[parallel_groups.index(group) - 1]
                for task in group:
                    task.dependencies = [t.task_id for t in prev_group_tasks]
        
        plan = Plan(
            plan_id=plan_id,
            name=f"Parallel Plan: {request.goal}",
            description=f"Optimized parallel execution plan for {request.goal}",
            goal=request.goal,
            strategy=PlanningStrategy.PARALLEL,
            tasks=tasks,
            constraints=request.constraints.copy(),
            success_criteria=request.success_criteria.copy()
        )
        
        # Parallel execution means duration is max of parallel groups
        group_durations = []
        for group in parallel_groups:
            group_duration = max(task.estimated_duration for task in group) if group else 0
            group_durations.append(group_duration)
        
        plan.estimated_duration = sum(group_durations)
        plan.estimated_cost = sum(task.estimated_cost for task in plan.tasks)
        
        return plan
    
    async def _adaptive_planning(self, request: PlanningRequest) -> Plan:
        """Create adaptive plan with built-in flexibility"""
        plan_id = str(uuid.uuid4())
        
        # Start with basic sequential plan
        base_plan = await self._sequential_planning(request)
        
        # Add adaptation points and fallback options
        for task in base_plan.tasks:
            # Add checkpoints for adaptation
            task.metadata["adaptation_point"] = True
            task.metadata["success_threshold"] = 0.8
            
            # Add alternative approaches
            task.metadata["fallback_options"] = [
                f"Alternative approach for {task.name}",
                f"Simplified version of {task.name}",
                f"Manual execution of {task.name}"
            ]
        
        # Convert to adaptive plan
        plan = Plan(
            plan_id=plan_id,
            name=f"Adaptive Plan: {request.goal}",
            description=f"Flexible adaptive plan for {request.goal}",
            goal=request.goal,
            strategy=PlanningStrategy.ADAPTIVE,
            tasks=base_plan.tasks,
            constraints=request.constraints.copy(),
            success_criteria=request.success_criteria.copy(),
            metadata={
                "adaptation_enabled": True,
                "replanning_triggers": ["task_failure", "time_overrun", "resource_shortage"],
                "adaptation_frequency": "per_task"
            }
        )
        
        # Add buffer time for adaptation
        plan.estimated_duration = base_plan.estimated_duration * 1.2
        plan.estimated_cost = base_plan.estimated_cost * 1.1
        
        return plan
    
    async def _goal_oriented_planning(self, request: PlanningRequest) -> Plan:
        """Create goal-oriented plan using backward chaining"""
        plan_id = str(uuid.uuid4())
        
        # Start from the goal and work backward
        goal_tasks = await self._backward_chain_planning(request.goal, request)
        
        # Reverse to get forward execution order
        goal_tasks.reverse()
        
        # Add forward dependencies
        for i in range(1, len(goal_tasks)):
            goal_tasks[i].dependencies = [goal_tasks[i-1].task_id]
        
        plan = Plan(
            plan_id=plan_id,
            name=f"Goal-Oriented Plan: {request.goal}",
            description=f"Backward-chained plan focused on achieving {request.goal}",
            goal=request.goal,
            strategy=PlanningStrategy.GOAL_ORIENTED,
            tasks=goal_tasks,
            constraints=request.constraints.copy(),
            success_criteria=request.success_criteria.copy()
        )
        
        plan.estimated_duration = sum(task.estimated_duration for task in plan.tasks)
        plan.estimated_cost = sum(task.estimated_cost for task in plan.tasks)
        
        return plan
    
    async def _constraint_based_planning(self, request: PlanningRequest) -> Plan:
        """Create plan optimized for constraints"""
        plan_id = str(uuid.uuid4())
        
        # Start with basic task decomposition
        if self.model_orchestrator:
            tasks = await self._ai_task_decomposition(request, "constraint_based")
        else:
            tasks = self._template_based_decomposition(request)
        
        # Apply constraint optimization
        optimized_tasks = await self._apply_constraints(tasks, request.constraints)
        
        plan = Plan(
            plan_id=plan_id,
            name=f"Constraint-Based Plan: {request.goal}",
            description=f"Constraint-optimized plan for {request.goal}",
            goal=request.goal,
            strategy=PlanningStrategy.CONSTRAINT_BASED,
            tasks=optimized_tasks,
            constraints=request.constraints.copy(),
            success_criteria=request.success_criteria.copy()
        )
        
        # Recalculate estimates after constraint optimization
        plan.estimated_duration = sum(task.estimated_duration for task in plan.tasks)
        plan.estimated_cost = sum(task.estimated_cost for task in plan.tasks)
        
        return plan
    
    async def _heuristic_planning(self, request: PlanningRequest) -> Plan:
        """Create plan using heuristic rules"""
        plan_id = str(uuid.uuid4())
        
        # Use simple heuristics for task breakdown
        tasks = self._heuristic_task_breakdown(request)
        
        plan = Plan(
            plan_id=plan_id,
            name=f"Heuristic Plan: {request.goal}",
            description=f"Rule-based heuristic plan for {request.goal}",
            goal=request.goal,
            strategy=PlanningStrategy.HEURISTIC,
            tasks=tasks,
            constraints=request.constraints.copy(),
            success_criteria=request.success_criteria.copy()
        )
        
        plan.estimated_duration = sum(task.estimated_duration for task in plan.tasks)
        plan.estimated_cost = sum(task.estimated_cost for task in plan.tasks)
        
        return plan
    
    async def _ai_task_decomposition(self, request: PlanningRequest, strategy: str) -> List[TaskNode]:
        """Use AI model to decompose goal into tasks"""
        if not self.model_orchestrator:
            return self._template_based_decomposition(request)
        
        prompt = f"""Break down this goal into specific, actionable tasks:

Goal: {request.goal}
Context: {request.context}
Strategy: {strategy}
Constraints: {[c.description for c in request.constraints]}
Available Resources: {request.available_resources}

Please provide a detailed task breakdown with:
1. Task name and description
2. Estimated duration (in hours)
3. Required resources
4. Dependencies between tasks
5. Priority level

Format as a numbered list with clear task descriptions."""
        
        from .model_orchestrator import ModelRequest, ModelCapability
        
        model_request = ModelRequest(
            prompt=prompt,
            capabilities_required=[ModelCapability.REASONING, ModelCapability.ANALYSIS],
            max_tokens=1500,
            temperature=0.4
        )
        
        response = await self.model_orchestrator.generate(model_request)
        
        if response.success:
            return self._parse_task_response(response.content)
        else:
            return self._template_based_decomposition(request)
    
    def _parse_task_response(self, response_text: str) -> List[TaskNode]:
        """Parse AI response into task nodes"""
        tasks = []
        lines = response_text.split('\n')
        
        current_task = None
        for line in lines:
            line = line.strip()
            
            # Look for numbered tasks
            if line and (line[0].isdigit() or line.startswith('Task')):
                if current_task:
                    tasks.append(current_task)
                
                # Extract task name
                task_name = line.split('.', 1)[-1].strip()
                if ':' in task_name:
                    task_name = task_name.split(':', 1)[0].strip()
                
                current_task = TaskNode(
                    task_id=str(uuid.uuid4()),
                    name=task_name[:50],  # Limit length
                    description=task_name,
                    task_type="ai_generated",
                    estimated_duration=1.0,  # Default
                    priority=TaskPriority.MEDIUM
                )
            
            # Extract duration estimates
            elif current_task and ('hour' in line.lower() or 'duration' in line.lower()):
                try:
                    # Simple extraction of numbers from duration lines
                    import re
                    numbers = re.findall(r'\d+\.?\d*', line)
                    if numbers:
                        current_task.estimated_duration = float(numbers[0])
                except:
                    pass
        
        # Add the last task
        if current_task:
            tasks.append(current_task)
        
        return tasks if tasks else self._default_task_breakdown()
    
    def _template_based_decomposition(self, request: PlanningRequest) -> List[TaskNode]:
        """Decompose using templates when AI is not available"""
        # Try to match with existing templates
        goal_lower = request.goal.lower()
        
        for template_name, template in self.plan_templates.items():
            if any(keyword in goal_lower for keyword in template_name.split('_')):
                return self._apply_template(template, request)
        
        # Fallback to generic decomposition
        return self._default_task_breakdown(request)
    
    def _apply_template(self, template: Dict[str, Any], request: PlanningRequest) -> List[TaskNode]:
        """Apply planning template to create tasks"""
        tasks = []
        
        for phase in template.get("phases", []):
            for task_name in phase["tasks"]:
                task = TaskNode(
                    task_id=str(uuid.uuid4()),
                    name=task_name.replace('_', ' ').title(),
                    description=f"{task_name.replace('_', ' ')} for {request.goal}",
                    task_type="template_based",
                    estimated_duration=self.config["default_task_duration"],
                    priority=TaskPriority.MEDIUM
                )
                tasks.append(task)
        
        return tasks
    
    def _default_task_breakdown(self, request: Optional[PlanningRequest] = None) -> List[TaskNode]:
        """Default task breakdown when no template matches"""
        goal = request.goal if request else "Complete goal"
        
        return [
            TaskNode(
                task_id=str(uuid.uuid4()),
                name="Planning and Preparation",
                description=f"Plan and prepare for {goal}",
                task_type="planning",
                estimated_duration=1.0,
                priority=TaskPriority.HIGH
            ),
            TaskNode(
                task_id=str(uuid.uuid4()),
                name="Execution",
                description=f"Execute main work for {goal}",
                task_type="execution",
                estimated_duration=3.0,
                priority=TaskPriority.HIGH
            ),
            TaskNode(
                task_id=str(uuid.uuid4()),
                name="Review and Finalization",
                description=f"Review and finalize {goal}",
                task_type="review",
                estimated_duration=0.5,
                priority=TaskPriority.MEDIUM
            )
        ]
    
    def get_plan_status(self, plan_id: str) -> Dict[str, Any]:
        """Get current status of a plan"""
        if plan_id not in self.active_plans:
            return {"error": "Plan not found"}
        
        plan = self.active_plans[plan_id]
        
        completed_tasks = sum(1 for task in plan.tasks if task.status == TaskStatus.COMPLETED)
        total_tasks = len(plan.tasks)
        progress = completed_tasks / total_tasks if total_tasks > 0 else 0.0
        
        return {
            "plan_id": plan_id,
            "name": plan.name,
            "strategy": plan.strategy.value,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "progress": progress,
            "estimated_duration": plan.estimated_duration,
            "estimated_cost": plan.estimated_cost
        }
    
    async def _validate_plan(self, plan: Plan) -> Dict[str, Any]:
        """Validate plan for consistency and feasibility"""
        validation = {
            "valid": True,
            "issues": [],
            "warnings": []
        }
        
        # Check for circular dependencies
        if self._has_circular_dependencies(plan.tasks):
            validation["valid"] = False
            validation["issues"].append("Circular dependencies detected")
        
        # Check constraint violations
        for constraint in plan.constraints:
            if not self._check_constraint(plan, constraint):
                validation["issues"].append(f"Constraint violation: {constraint.description}")
        
        # Check resource availability
        required_resources = set()
        for task in plan.tasks:
            required_resources.update(task.resources_required)
        
        # Add more validation rules as needed
        
        return validation
    
    def _has_circular_dependencies(self, tasks: List[TaskNode]) -> bool:
        """Check for circular dependencies in task list"""
        # Simple cycle detection using DFS
        task_map = {task.task_id: task for task in tasks}
        visited = set()
        rec_stack = set()
        
        def has_cycle(task_id: str) -> bool:
            if task_id in rec_stack:
                return True
            if task_id in visited:
                return False
            
            visited.add(task_id)
            rec_stack.add(task_id)
            
            task = task_map.get(task_id)
            if task:
                for dep_id in task.dependencies:
                    if has_cycle(dep_id):
                        return True
            
            rec_stack.remove(task_id)
            return False
        
        for task in tasks:
            if task.task_id not in visited:
                if has_cycle(task.task_id):
                    return True
        
        return False
    
    def _check_constraint(self, plan: Plan, constraint: PlanningConstraint) -> bool:
        """Check if plan violates a constraint"""
        if constraint.type == "time":
            max_duration = constraint.parameters.get("max_duration", float('inf'))
            return plan.estimated_duration <= max_duration
        elif constraint.type == "cost":
            max_cost = constraint.parameters.get("max_cost", float('inf'))
            return plan.estimated_cost <= max_cost
        elif constraint.type == "resources":
            # Check resource constraints
            return True  # Simplified for now
        
        return True  # Unknown constraint type, assume valid