"""
Dependency Manager

Advanced dependency management for workflow execution with cycle detection,
conditional dependencies, and dynamic dependency resolution.

Author: Claude Code
Date: 2025-07-13
Session: 2.2
"""

import asyncio
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

from ...utils.logger import get_logger

logger = get_logger(__name__)


class DependencyType(Enum):
    """Types of dependencies"""
    COMPLETION = "completion"      # Wait for step completion
    SUCCESS = "success"           # Wait for successful completion
    DATA = "data"                # Wait for specific data output
    CONDITIONAL = "conditional"   # Conditional dependency
    RESOURCE = "resource"        # Resource availability dependency


@dataclass
class Dependency:
    """Individual dependency definition"""
    step_id: str
    dependency_type: DependencyType = DependencyType.COMPLETION
    condition: Optional[str] = None  # For conditional dependencies
    data_key: Optional[str] = None   # For data dependencies
    timeout: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class DependencyNode:
    """Node in dependency graph"""
    step_id: str
    dependencies: List[Dependency] = field(default_factory=list)
    dependents: Set[str] = field(default_factory=set)
    satisfied: bool = False
    blocked_by: Set[str] = field(default_factory=set)
    execution_order: int = -1


class DependencyManager:
    """
    Advanced dependency management for workflow steps.
    
    Features:
    - Cycle detection and prevention
    - Conditional dependencies
    - Data-driven dependencies
    - Dynamic dependency resolution
    - Parallel execution optimization
    - Dependency timeout handling
    """
    
    def __init__(self):
        """Initialize dependency manager"""
        self.dependency_graph: Dict[str, DependencyNode] = {}
        self.execution_order: List[List[str]] = []  # Groups of steps that can run in parallel
        self.blocked_steps: Set[str] = set()
        
        logger.info("Dependency manager initialized")
    
    def add_step(self, step_id: str, dependencies: List[Dependency] = None):
        """
        Add a step to the dependency graph.
        
        Args:
            step_id: Step identifier
            dependencies: List of dependencies for this step
        """
        if dependencies is None:
            dependencies = []
        
        node = DependencyNode(
            step_id=step_id,
            dependencies=dependencies,
            blocked_by=set()
        )
        
        # Set initial blocked status
        node.blocked_by = {dep.step_id for dep in dependencies}
        
        self.dependency_graph[step_id] = node
        
        # Update dependents for referenced steps
        for dep in dependencies:
            if dep.step_id in self.dependency_graph:
                self.dependency_graph[dep.step_id].dependents.add(step_id)
            else:
                # Create placeholder node for dependency
                self.dependency_graph[dep.step_id] = DependencyNode(
                    step_id=dep.step_id,
                    dependents={step_id}
                )
        
        logger.debug(f"Added step to dependency graph: {step_id}")
    
    def validate_dependencies(self) -> Tuple[bool, List[str]]:
        """
        Validate dependency graph for cycles and missing dependencies.
        
        Returns:
            (is_valid, error_messages)
        """
        errors = []
        
        # Check for circular dependencies
        cycles = self._detect_cycles()
        if cycles:
            errors.extend([f"Circular dependency detected: {' -> '.join(cycle)}" for cycle in cycles])
        
        # Check for missing step references
        all_step_ids = set(self.dependency_graph.keys())
        for step_id, node in self.dependency_graph.items():
            for dep in node.dependencies:
                if dep.step_id not in all_step_ids:
                    errors.append(f"Step '{step_id}' depends on non-existent step '{dep.step_id}'")
        
        return len(errors) == 0, errors
    
    def calculate_execution_order(self) -> List[List[str]]:
        """
        Calculate optimal execution order with parallel groups.
        
        Returns:
            List of step groups that can be executed in parallel
        """
        # Reset execution order
        self.execution_order = []
        remaining_steps = set(self.dependency_graph.keys())
        execution_level = 0
        
        while remaining_steps:
            # Find steps with no unsatisfied dependencies
            ready_steps = []
            for step_id in remaining_steps:
                node = self.dependency_graph[step_id]
                if not node.blocked_by:
                    ready_steps.append(step_id)
                    node.execution_order = execution_level
            
            if not ready_steps:
                # Check for deadlock
                logger.error(f"Dependency deadlock detected. Remaining steps: {remaining_steps}")
                break
            
            # Add ready steps as parallel group
            self.execution_order.append(ready_steps)
            
            # Remove ready steps and update dependencies
            for step_id in ready_steps:
                remaining_steps.remove(step_id)
                node = self.dependency_graph[step_id]
                
                # Update dependents
                for dependent_id in node.dependents:
                    if dependent_id in self.dependency_graph:
                        dependent_node = self.dependency_graph[dependent_id]
                        dependent_node.blocked_by.discard(step_id)
            
            execution_level += 1
        
        logger.info(f"Calculated execution order with {len(self.execution_order)} levels")
        return self.execution_order
    
    async def check_step_ready(self, step_id: str, completed_steps: Set[str],
                              step_results: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Check if a step is ready for execution.
        
        Args:
            step_id: Step to check
            completed_steps: Set of completed step IDs
            step_results: Results from completed steps
            
        Returns:
            (is_ready, blocking_reasons)
        """
        if step_id not in self.dependency_graph:
            return True, []
        
        node = self.dependency_graph[step_id]
        blocking_reasons = []
        
        for dep in node.dependencies:
            ready = await self._check_dependency_satisfied(dep, completed_steps, step_results)
            if not ready:
                blocking_reasons.append(
                    f"Dependency '{dep.step_id}' ({dep.dependency_type.value}) not satisfied"
                )
        
        is_ready = len(blocking_reasons) == 0
        return is_ready, blocking_reasons
    
    async def mark_step_completed(self, step_id: str, success: bool, 
                                 result_data: Optional[Dict[str, Any]] = None):
        """
        Mark a step as completed and update dependent steps.
        
        Args:
            step_id: Completed step ID
            success: Whether step completed successfully
            result_data: Result data from step
        """
        if step_id not in self.dependency_graph:
            return
        
        node = self.dependency_graph[step_id]
        node.satisfied = success
        
        # Update blocked status for dependents
        for dependent_id in node.dependents:
            if dependent_id in self.dependency_graph:
                dependent_node = self.dependency_graph[dependent_id]
                
                # Check if this dependency is now satisfied
                for dep in dependent_node.dependencies:
                    if dep.step_id == step_id:
                        if await self._check_dependency_satisfied(dep, {step_id}, {step_id: result_data}):
                            dependent_node.blocked_by.discard(step_id)
        
        logger.debug(f"Marked step completed: {step_id} (success: {success})")
    
    def get_ready_steps(self, completed_steps: Set[str]) -> List[str]:
        """Get steps that are ready for execution"""
        ready_steps = []
        
        for step_id, node in self.dependency_graph.items():
            if step_id not in completed_steps and not node.blocked_by:
                ready_steps.append(step_id)
        
        return ready_steps
    
    def get_parallel_groups(self) -> List[List[str]]:
        """Get steps grouped by execution level for parallel execution"""
        return self.execution_order
    
    def get_dependency_info(self, step_id: str) -> Optional[Dict[str, Any]]:
        """Get dependency information for a step"""
        if step_id not in self.dependency_graph:
            return None
        
        node = self.dependency_graph[step_id]
        return {
            "step_id": step_id,
            "dependencies": [
                {
                    "step_id": dep.step_id,
                    "type": dep.dependency_type.value,
                    "condition": dep.condition,
                    "data_key": dep.data_key
                }
                for dep in node.dependencies
            ],
            "dependents": list(node.dependents),
            "blocked_by": list(node.blocked_by),
            "execution_order": node.execution_order,
            "satisfied": node.satisfied
        }
    
    def visualize_dependencies(self) -> str:
        """Generate a text visualization of the dependency graph"""
        lines = ["Dependency Graph:"]
        
        for level, steps in enumerate(self.execution_order):
            lines.append(f"  Level {level}: {', '.join(steps)}")
            
            # Show dependencies for each step
            for step_id in steps:
                node = self.dependency_graph[step_id]
                if node.dependencies:
                    dep_strs = []
                    for dep in node.dependencies:
                        dep_str = f"{dep.step_id}({dep.dependency_type.value})"
                        if dep.condition:
                            dep_str += f"[{dep.condition}]"
                        dep_strs.append(dep_str)
                    lines.append(f"    {step_id} depends on: {', '.join(dep_strs)}")
        
        return "\n".join(lines)
    
    async def _check_dependency_satisfied(self, dependency: Dependency,
                                        completed_steps: Set[str],
                                        step_results: Dict[str, Any]) -> bool:
        """Check if a specific dependency is satisfied"""
        dep_step_id = dependency.step_id
        
        # Check if dependency step is completed
        if dep_step_id not in completed_steps:
            return False
        
        # Get step result
        step_result = step_results.get(dep_step_id, {})
        
        # Check dependency type
        if dependency.dependency_type == DependencyType.COMPLETION:
            return True  # Step completed
        
        elif dependency.dependency_type == DependencyType.SUCCESS:
            # Check if step completed successfully
            return step_result.get("success", False)
        
        elif dependency.dependency_type == DependencyType.DATA:
            # Check if required data is available
            if dependency.data_key:
                return dependency.data_key in step_result.get("output_data", {})
            return True
        
        elif dependency.dependency_type == DependencyType.CONDITIONAL:
            # Evaluate condition
            if dependency.condition:
                return await self._evaluate_condition(dependency.condition, step_result)
            return True
        
        elif dependency.dependency_type == DependencyType.RESOURCE:
            # Check resource availability (placeholder)
            return True
        
        return True
    
    async def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate a conditional dependency"""
        # Simple condition evaluation - can be enhanced with proper parser
        try:
            # Replace context variables
            eval_condition = condition
            for key, value in context.items():
                eval_condition = eval_condition.replace(f"{{{key}}}", str(value))
            
            # Simple evaluation (in production, use a proper expression evaluator)
            if "==" in eval_condition:
                left, right = eval_condition.split("==", 1)
                return left.strip() == right.strip()
            elif "!=" in eval_condition:
                left, right = eval_condition.split("!=", 1)
                return left.strip() != right.strip()
            elif condition.lower() in ["true", "false"]:
                return condition.lower() == "true"
            
            return True
            
        except Exception as e:
            logger.warning(f"Failed to evaluate condition '{condition}': {e}")
            return False
    
    def _detect_cycles(self) -> List[List[str]]:
        """Detect circular dependencies using DFS"""
        cycles = []
        visited = set()
        rec_stack = set()
        
        def dfs(step_id: str, path: List[str]) -> bool:
            if step_id in rec_stack:
                # Found cycle
                cycle_start = path.index(step_id)
                cycles.append(path[cycle_start:] + [step_id])
                return True
            
            if step_id in visited:
                return False
            
            visited.add(step_id)
            rec_stack.add(step_id)
            path.append(step_id)
            
            if step_id in self.dependency_graph:
                node = self.dependency_graph[step_id]
                for dep in node.dependencies:
                    if dfs(dep.step_id, path.copy()):
                        return True
            
            rec_stack.remove(step_id)
            return False
        
        for step_id in self.dependency_graph:
            if step_id not in visited:
                dfs(step_id, [])
        
        return cycles
    
    def add_dynamic_dependency(self, step_id: str, dependency: Dependency):
        """Add a dependency dynamically during execution"""
        if step_id not in self.dependency_graph:
            self.add_step(step_id, [dependency])
        else:
            node = self.dependency_graph[step_id]
            node.dependencies.append(dependency)
            node.blocked_by.add(dependency.step_id)
            
            # Update dependent's dependents
            if dependency.step_id in self.dependency_graph:
                self.dependency_graph[dependency.step_id].dependents.add(step_id)
        
        logger.debug(f"Added dynamic dependency: {step_id} -> {dependency.step_id}")
    
    def remove_dependency(self, step_id: str, dependency_step_id: str):
        """Remove a dependency relationship"""
        if step_id not in self.dependency_graph:
            return
        
        node = self.dependency_graph[step_id]
        
        # Remove from dependencies list
        node.dependencies = [dep for dep in node.dependencies if dep.step_id != dependency_step_id]
        
        # Remove from blocked_by set
        node.blocked_by.discard(dependency_step_id)
        
        # Remove from dependent's dependents
        if dependency_step_id in self.dependency_graph:
            self.dependency_graph[dependency_step_id].dependents.discard(step_id)
        
        logger.debug(f"Removed dependency: {step_id} -> {dependency_step_id}")
    
    def clear(self):
        """Clear all dependencies"""
        self.dependency_graph.clear()
        self.execution_order.clear()
        self.blocked_steps.clear()
        logger.debug("Cleared dependency graph")