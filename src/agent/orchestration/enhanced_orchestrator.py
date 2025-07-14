#!/usr/bin/env python3
"""
Enhanced MCP Orchestrator

Advanced orchestration system with performance optimization, connection pooling,
caching, error handling, and comprehensive monitoring.

Author: Claude Code
Date: 2025-07-14
Phase: 4.6 - Performance Optimization
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import time
import uuid

# Add parent directory to path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from ..context.context_manager import ContextManager
from ...mcp_client.client_manager import MCPClientManager
from ..performance.connection_pool import MCPConnectionPool, PoolConfig
from ..performance.response_cache import ResponseCache, CacheConfig, CachedMCPClient
from ..performance.error_handler import EnhancedErrorHandler, ResilientMCPClient
from ..performance.monitoring import PerformanceMonitor, MonitoredMCPClient
from .mcp_orchestrator import (
    OrchestrationStatus, OrchestrationStep, 
    OrchestrationResult, OrchestrationWorkflow
)

logger = logging.getLogger(__name__)


@dataclass
class EnhancedOrchestrationConfig:
    """Configuration for enhanced orchestrator"""
    enable_connection_pooling: bool = True
    enable_response_caching: bool = True
    enable_error_handling: bool = True
    enable_monitoring: bool = True
    pool_config: Optional[PoolConfig] = None
    cache_config: Optional[CacheConfig] = None
    
    def __post_init__(self):
        if self.pool_config is None:
            self.pool_config = PoolConfig()
        if self.cache_config is None:
            self.cache_config = CacheConfig()


class EnhancedMCPOrchestrator:
    """
    Enhanced MCP orchestrator with comprehensive performance optimizations.
    
    Features:
    - Connection pooling for improved performance
    - Response caching to reduce redundant operations
    - Enhanced error handling with retry logic
    - Comprehensive performance monitoring
    - Intelligent workflow optimization
    - Resource utilization tracking
    """
    
    def __init__(self, 
                 client_manager: MCPClientManager, 
                 config: EnhancedOrchestrationConfig = None):
        self.client_manager = client_manager
        self.config = config or EnhancedOrchestrationConfig()
        self.context_manager = ContextManager()
        
        # Performance components
        self.connection_pool = None
        self.response_cache = None
        self.error_handler = None
        self.monitor = None
        
        # Orchestration state
        self.active_workflows: Dict[str, OrchestrationWorkflow] = {}
        self.execution_history: List[OrchestrationWorkflow] = []
        
        # Enhanced clients with performance wrappers
        self.enhanced_clients: Dict[str, Any] = {}
        
    async def initialize(self):
        """Initialize enhanced orchestrator"""
        logger.info("Initializing enhanced MCP orchestrator...")
        
        await self.context_manager.initialize()
        
        # Initialize performance components
        if self.config.enable_connection_pooling:
            self.connection_pool = MCPConnectionPool(self.config.pool_config)
            await self.connection_pool.initialize(self.client_manager)
        
        if self.config.enable_response_caching:
            self.response_cache = ResponseCache(self.config.cache_config)
            await self.response_cache.initialize()
        
        if self.config.enable_error_handling:
            self.error_handler = EnhancedErrorHandler()
        
        if self.config.enable_monitoring:
            self.monitor = PerformanceMonitor()
            await self.monitor.initialize()
        
        # Create enhanced clients
        await self._create_enhanced_clients()
        
        logger.info("Enhanced MCP orchestrator initialized")
    
    async def _create_enhanced_clients(self):
        """Create enhanced client wrappers"""
        for client_type, client in self.client_manager.clients.items():
            enhanced_client = client
            
            # Wrap with monitoring
            if self.monitor:
                enhanced_client = MonitoredMCPClient(enhanced_client, self.monitor)
            
            # Wrap with error handling
            if self.error_handler:
                enhanced_client = ResilientMCPClient(enhanced_client, self.error_handler)
            
            # Wrap with caching
            if self.response_cache:
                enhanced_client = CachedMCPClient(enhanced_client, self.response_cache)
            
            self.enhanced_clients[client_type.value] = enhanced_client
    
    def create_workflow(self, name: str, description: str, 
                       steps: List[OrchestrationStep]) -> str:
        """Create new orchestration workflow"""
        workflow_id = str(uuid.uuid4())
        workflow = OrchestrationWorkflow(
            id=workflow_id,
            name=name,
            description=description,
            steps=steps
        )
        
        # Validate workflow
        self._validate_workflow(workflow)
        
        # Optimize workflow if possible
        optimized_steps = self._optimize_workflow(workflow.steps)
        workflow.steps = optimized_steps
        
        self.active_workflows[workflow_id] = workflow
        logger.info(f"Created workflow: {name} ({workflow_id})")
        return workflow_id
    
    def _validate_workflow(self, workflow: OrchestrationWorkflow):
        """Validate workflow structure and dependencies"""
        step_ids = {step.id for step in workflow.steps}
        
        for step in workflow.steps:
            # Check dependencies exist
            for dep_id in step.depends_on:
                if dep_id not in step_ids:
                    raise ValueError(f"Step {step.id} depends on non-existent step {dep_id}")
            
            # Check server availability
            if step.server not in self.enhanced_clients:
                raise ValueError(f"Invalid server: {step.server}")
    
    def _optimize_workflow(self, steps: List[OrchestrationStep]) -> List[OrchestrationStep]:
        """Optimize workflow for better performance"""
        # Group steps by server to reduce context switching
        server_groups = {}
        for step in steps:
            if step.server not in server_groups:
                server_groups[step.server] = []
            server_groups[step.server].append(step)
        
        # Identify parallelizable steps
        optimized_steps = []
        processed_steps = set()
        
        while len(processed_steps) < len(steps):
            # Find steps that can be executed (dependencies satisfied)
            ready_steps = []
            for step in steps:
                if (step.id not in processed_steps and 
                    all(dep_id in processed_steps for dep_id in step.depends_on)):
                    ready_steps.append(step)
            
            if not ready_steps:
                raise RuntimeError("Circular dependency detected in workflow")
            
            # Group ready steps by server for batching
            server_batches = {}
            for step in ready_steps:
                if step.server not in server_batches:
                    server_batches[step.server] = []
                server_batches[step.server].append(step)
            
            # Add steps to optimized list
            for server, batch_steps in server_batches.items():
                optimized_steps.extend(batch_steps)
                for step in batch_steps:
                    processed_steps.add(step.id)
        
        return optimized_steps
    
    async def execute_workflow(self, workflow_id: str) -> OrchestrationWorkflow:
        """Execute orchestration workflow with performance optimizations"""
        if workflow_id not in self.active_workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow = self.active_workflows[workflow_id]
        workflow.status = OrchestrationStatus.RUNNING
        workflow.start_time = time.time()
        
        logger.info(f"Starting enhanced workflow execution: {workflow.name}")
        
        try:
            # Execute steps with performance monitoring
            if self.monitor:
                with self.monitor.time_operation("workflow_execution", 
                                                {"workflow_id": workflow_id}):
                    await self._execute_steps_enhanced(workflow)
            else:
                await self._execute_steps_enhanced(workflow)
            
            workflow.status = OrchestrationStatus.COMPLETED
            logger.info(f"Workflow completed: {workflow.name}")
            
        except Exception as e:
            workflow.status = OrchestrationStatus.FAILED
            logger.error(f"Workflow failed: {workflow.name} - {e}")
            
            # Record error in monitoring
            if self.monitor:
                self.monitor.increment_counter("workflow_errors", 
                                             {"workflow_id": workflow_id})
            
            raise
        
        finally:
            workflow.end_time = time.time()
            self.execution_history.append(workflow)
            if workflow_id in self.active_workflows:
                del self.active_workflows[workflow_id]
        
        return workflow
    
    async def _execute_steps_enhanced(self, workflow: OrchestrationWorkflow):
        """Execute workflow steps with performance enhancements"""
        executed_steps = set()
        pending_steps = {step.id: step for step in workflow.steps}
        
        # Track performance metrics
        batch_sizes = []
        execution_times = []
        
        while pending_steps:
            batch_start_time = time.time()
            
            # Find steps ready to execute (dependencies satisfied)
            ready_steps = []
            for step in pending_steps.values():
                if all(dep_id in executed_steps for dep_id in step.depends_on):
                    ready_steps.append(step)
            
            if not ready_steps:
                raise RuntimeError("Circular dependency detected in workflow")
            
            batch_sizes.append(len(ready_steps))
            
            # Group steps by server for batch execution
            server_batches = {}
            for step in ready_steps:
                if step.server not in server_batches:
                    server_batches[step.server] = []
                server_batches[step.server].append(step)
            
            # Execute batches in parallel
            batch_tasks = []
            for server, steps in server_batches.items():
                task = asyncio.create_task(
                    self._execute_batch(server, steps)
                )
                batch_tasks.append(task)
            
            # Wait for all batches to complete
            batch_results = await asyncio.gather(*batch_tasks)
            
            # Process results
            for batch_result in batch_results:
                for step_id, result in batch_result.items():
                    workflow.results[step_id] = result
                    executed_steps.add(step_id)
                    del pending_steps[step_id]
                    
                    if result.status == OrchestrationStatus.FAILED:
                        raise RuntimeError(f"Step {step_id} failed: {result.error}")
            
            batch_time = time.time() - batch_start_time
            execution_times.append(batch_time)
            
            # Update monitoring metrics
            if self.monitor:
                self.monitor.record_histogram("workflow_batch_size", len(ready_steps))
                self.monitor.record_histogram("workflow_batch_time", batch_time)
        
        # Record overall workflow metrics
        if self.monitor:
            total_time = sum(execution_times)
            avg_batch_size = sum(batch_sizes) / len(batch_sizes) if batch_sizes else 0
            
            self.monitor.record_histogram("workflow_total_time", total_time)
            self.monitor.record_histogram("workflow_avg_batch_size", avg_batch_size)
            self.monitor.increment_counter("workflow_completed")
    
    async def _execute_batch(self, server: str, steps: List[OrchestrationStep]) -> Dict[str, OrchestrationResult]:
        """Execute a batch of steps on the same server"""
        results = {}
        
        # Use connection pooling if available
        if self.connection_pool:
            # Execute steps using pooled connections
            tasks = []
            for step in steps:
                task = asyncio.create_task(
                    self._execute_step_with_pool(step, server)
                )
                tasks.append((step.id, task))
            
            # Wait for all tasks
            for step_id, task in tasks:
                try:
                    result = await task
                    results[step_id] = result
                except Exception as e:
                    results[step_id] = OrchestrationResult(
                        step_id=step_id,
                        status=OrchestrationStatus.FAILED,
                        error=str(e),
                        execution_time=0,
                        timestamp=time.time()
                    )
        else:
            # Fallback to sequential execution
            for step in steps:
                result = await self._execute_step_enhanced(step, server)
                results[step.id] = result
        
        return results
    
    async def _execute_step_with_pool(self, step: OrchestrationStep, server: str) -> OrchestrationResult:
        """Execute step using connection pool"""
        start_time = time.time()
        
        try:
            # Map server name to client type
            client_type_mapping = {
                "filesystem": "filesystem",
                "desktop": "desktop", 
                "system": "system"
            }
            
            client_type = client_type_mapping.get(server)
            if not client_type:
                raise ValueError(f"Unknown server: {server}")
            
            # Execute using connection pool
            result = await self.connection_pool.execute_with_pool(
                client_type, step.tool, step.arguments
            )
            
            execution_time = time.time() - start_time
            
            if result.get("success", False):
                return OrchestrationResult(
                    step_id=step.id,
                    status=OrchestrationStatus.COMPLETED,
                    result=result.get("result"),
                    execution_time=execution_time,
                    timestamp=time.time()
                )
            else:
                return OrchestrationResult(
                    step_id=step.id,
                    status=OrchestrationStatus.FAILED,
                    error=result.get("error", "Unknown error"),
                    execution_time=execution_time,
                    timestamp=time.time()
                )
                
        except Exception as e:
            return OrchestrationResult(
                step_id=step.id,
                status=OrchestrationStatus.FAILED,
                error=str(e),
                execution_time=time.time() - start_time,
                timestamp=time.time()
            )
    
    async def _execute_step_enhanced(self, step: OrchestrationStep, server: str) -> OrchestrationResult:
        """Execute step using enhanced client"""
        start_time = time.time()
        
        logger.info(f"Executing step: {step.name} on {server}")
        
        try:
            # Get enhanced client
            client = self.enhanced_clients.get(server)
            if not client:
                raise ValueError(f"No enhanced client available for {server}")
            
            # Execute tool with all enhancements
            result = await client.call_tool(step.tool, step.arguments)
            
            execution_time = time.time() - start_time
            
            return OrchestrationResult(
                step_id=step.id,
                status=OrchestrationStatus.COMPLETED,
                result=result,
                execution_time=execution_time,
                timestamp=time.time()
            )
            
        except Exception as e:
            error = f"Step {step.id} failed: {str(e)}"
            logger.error(error)
            
            return OrchestrationResult(
                step_id=step.id,
                status=OrchestrationStatus.FAILED,
                error=error,
                execution_time=time.time() - start_time,
                timestamp=time.time()
            )
    
    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get workflow status with performance metrics"""
        if workflow_id in self.active_workflows:
            workflow = self.active_workflows[workflow_id]
        else:
            # Check history
            for w in self.execution_history:
                if w.id == workflow_id:
                    workflow = w
                    break
            else:
                raise ValueError(f"Workflow {workflow_id} not found")
        
        # Base status
        status = {
            "id": workflow.id,
            "name": workflow.name,
            "description": workflow.description,
            "status": workflow.status.value,
            "steps_total": len(workflow.steps),
            "steps_completed": len([r for r in workflow.results.values() 
                                   if r.status == OrchestrationStatus.COMPLETED]),
            "steps_failed": len([r for r in workflow.results.values() 
                                if r.status == OrchestrationStatus.FAILED]),
            "start_time": workflow.start_time,
            "end_time": workflow.end_time,
            "execution_time": workflow.end_time - workflow.start_time if workflow.end_time > 0 else 0
        }
        
        # Add performance metrics
        if workflow.results:
            execution_times = [r.execution_time for r in workflow.results.values()]
            status["performance_metrics"] = {
                "avg_step_time": sum(execution_times) / len(execution_times),
                "max_step_time": max(execution_times),
                "min_step_time": min(execution_times),
                "total_step_time": sum(execution_times)
            }
        
        return status
    
    def get_performance_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive performance dashboard"""
        dashboard = {
            "timestamp": time.time(),
            "orchestrator_status": "running" if self.active_workflows else "idle",
            "active_workflows": len(self.active_workflows),
            "completed_workflows": len(self.execution_history)
        }
        
        # Connection pool metrics
        if self.connection_pool:
            dashboard["connection_pool"] = self.connection_pool.get_pool_stats()
        
        # Cache metrics
        if self.response_cache:
            dashboard["cache"] = self.response_cache.get_stats()
        
        # Error handling metrics
        if self.error_handler:
            dashboard["error_handling"] = self.error_handler.get_error_stats()
        
        # Monitoring metrics
        if self.monitor:
            dashboard["monitoring"] = self.monitor.get_dashboard_data()
        
        return dashboard
    
    async def shutdown(self):
        """Shutdown enhanced orchestrator"""
        logger.info("Shutting down enhanced MCP orchestrator...")
        
        # Cancel active workflows
        for workflow in self.active_workflows.values():
            workflow.status = OrchestrationStatus.CANCELLED
        
        # Shutdown performance components
        if self.connection_pool:
            await self.connection_pool.shutdown()
        
        if self.response_cache:
            await self.response_cache.shutdown()
        
        if self.monitor:
            await self.monitor.shutdown()
        
        self.active_workflows.clear()
        logger.info("Enhanced MCP orchestrator shutdown complete")