#!/usr/bin/env python3
"""
MCP Orchestration System

Coordinates complex workflows across multiple MCP servers (filesystem, desktop, system).
Enables sophisticated automation by combining tools from different servers.

Author: Claude Code
Date: 2025-07-14
Phase: 4.6
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
from ...mcp_client.filesystem_client import FilesystemMCPClient
from ...mcp_client.desktop_client import DesktopMCPClient
from ...mcp_client.system_client import SystemMCPClient

logger = logging.getLogger(__name__)


class OrchestrationStatus(Enum):
    """Orchestration workflow status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class OrchestrationStep:
    """Single step in orchestration workflow"""
    id: str
    name: str
    server: str  # filesystem, desktop, or system
    tool: str
    arguments: Dict[str, Any]
    depends_on: List[str] = None  # List of step IDs this depends on
    retry_count: int = 0
    max_retries: int = 3
    timeout: float = 30.0
    
    def __post_init__(self):
        if self.depends_on is None:
            self.depends_on = []


@dataclass
class OrchestrationResult:
    """Result of orchestration step"""
    step_id: str
    status: OrchestrationStatus
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    timestamp: float = 0.0


@dataclass
class OrchestrationWorkflow:
    """Complete orchestration workflow"""
    id: str
    name: str
    description: str
    steps: List[OrchestrationStep]
    status: OrchestrationStatus = OrchestrationStatus.PENDING
    results: Dict[str, OrchestrationResult] = None
    start_time: float = 0.0
    end_time: float = 0.0
    
    def __post_init__(self):
        if self.results is None:
            self.results = {}


class MCPOrchestrator:
    """MCP Multi-server Orchestrator"""
    
    def __init__(self, client_manager: MCPClientManager):
        self.client_manager = client_manager
        self.context_manager = ContextManager()
        self.active_workflows: Dict[str, OrchestrationWorkflow] = {}
        self.execution_history: List[OrchestrationWorkflow] = []
        
    async def initialize(self):
        """Initialize orchestrator"""
        await self.context_manager.initialize()
        logger.info("MCP Orchestrator initialized")
    
    def create_workflow(self, name: str, description: str, steps: List[OrchestrationStep]) -> str:
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
            if step.server not in ["filesystem", "desktop", "system"]:
                raise ValueError(f"Invalid server: {step.server}")
    
    async def execute_workflow(self, workflow_id: str) -> OrchestrationWorkflow:
        """Execute orchestration workflow"""
        if workflow_id not in self.active_workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow = self.active_workflows[workflow_id]
        workflow.status = OrchestrationStatus.RUNNING
        workflow.start_time = time.time()
        
        logger.info(f"Starting workflow execution: {workflow.name}")
        
        try:
            # Execute steps in dependency order
            await self._execute_steps(workflow)
            
            workflow.status = OrchestrationStatus.COMPLETED
            logger.info(f"Workflow completed: {workflow.name}")
            
        except Exception as e:
            workflow.status = OrchestrationStatus.FAILED
            logger.error(f"Workflow failed: {workflow.name} - {e}")
            raise
        
        finally:
            workflow.end_time = time.time()
            self.execution_history.append(workflow)
            if workflow_id in self.active_workflows:
                del self.active_workflows[workflow_id]
        
        return workflow
    
    async def _execute_steps(self, workflow: OrchestrationWorkflow):
        """Execute workflow steps in dependency order"""
        executed_steps = set()
        pending_steps = {step.id: step for step in workflow.steps}
        
        while pending_steps:
            # Find steps ready to execute (dependencies satisfied)
            ready_steps = []
            for step in pending_steps.values():
                if all(dep_id in executed_steps for dep_id in step.depends_on):
                    ready_steps.append(step)
            
            if not ready_steps:
                raise RuntimeError("Circular dependency detected in workflow")
            
            # Execute ready steps in parallel
            tasks = []
            for step in ready_steps:
                task = asyncio.create_task(self._execute_step(step))
                tasks.append((step, task))
            
            # Wait for all tasks to complete
            for step, task in tasks:
                result = await task
                workflow.results[step.id] = result
                executed_steps.add(step.id)
                del pending_steps[step.id]
                
                if result.status == OrchestrationStatus.FAILED:
                    raise RuntimeError(f"Step {step.id} failed: {result.error}")
    
    async def _execute_step(self, step: OrchestrationStep) -> OrchestrationResult:
        """Execute single orchestration step"""
        start_time = time.time()
        
        logger.info(f"Executing step: {step.name} on {step.server}")
        
        try:
            # Get appropriate client
            client = self._get_client(step.server)
            
            # Execute tool with timeout
            result = await asyncio.wait_for(
                client.call_tool(step.tool, step.arguments),
                timeout=step.timeout
            )
            
            execution_time = time.time() - start_time
            
            return OrchestrationResult(
                step_id=step.id,
                status=OrchestrationStatus.COMPLETED,
                result=result,
                execution_time=execution_time,
                timestamp=time.time()
            )
            
        except asyncio.TimeoutError:
            error = f"Step {step.id} timed out after {step.timeout} seconds"
            logger.error(error)
            
            return OrchestrationResult(
                step_id=step.id,
                status=OrchestrationStatus.FAILED,
                error=error,
                execution_time=time.time() - start_time,
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
    
    def _get_client(self, server: str):
        """Get MCP client for server"""
        if server == "filesystem":
            return self.client_manager.filesystem_client
        elif server == "desktop":
            return self.client_manager.desktop_client
        elif server == "system":
            return self.client_manager.system_client
        else:
            raise ValueError(f"Unknown server: {server}")
    
    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get workflow status"""
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
        
        return {
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
            "execution_time": workflow.end_time - workflow.start_time if workflow.end_time > 0 else 0,
            "results": {step_id: {
                "status": result.status.value,
                "execution_time": result.execution_time,
                "error": result.error
            } for step_id, result in workflow.results.items()}
        }
    
    def create_system_health_workflow(self) -> str:
        """Create system health monitoring workflow"""
        steps = [
            OrchestrationStep(
                id="get_system_metrics",
                name="Get System Metrics",
                server="system",
                tool="get_system_metrics",
                arguments={"detailed": True}
            ),
            OrchestrationStep(
                id="get_processes",
                name="Get Running Processes",
                server="system",
                tool="list_processes",
                arguments={"limit": 20, "sort_by": "cpu_percent"}
            ),
            OrchestrationStep(
                id="take_screenshot",
                name="Take Screenshot",
                server="desktop",
                tool="take_screenshot",
                arguments={"path": "/tmp/system_health_screenshot.png"}
            ),
            OrchestrationStep(
                id="create_report",
                name="Create Health Report",
                server="filesystem",
                tool="write_file",
                arguments={
                    "path": "/tmp/system_health_report.json",
                    "content": "{{SYSTEM_METRICS}}"  # Will be populated
                },
                depends_on=["get_system_metrics", "get_processes", "take_screenshot"]
            )
        ]
        
        return self.create_workflow(
            name="System Health Check",
            description="Comprehensive system health monitoring with screenshot and reporting",
            steps=steps
        )
    
    def create_desktop_automation_workflow(self) -> str:
        """Create desktop automation workflow"""
        steps = [
            OrchestrationStep(
                id="get_screen_info",
                name="Get Screen Information",
                server="desktop",
                tool="get_screen_info",
                arguments={}
            ),
            OrchestrationStep(
                id="list_windows",
                name="List Windows",
                server="desktop",
                tool="list_windows",
                arguments={}
            ),
            OrchestrationStep(
                id="take_screenshot",
                name="Take Screenshot",
                server="desktop",
                tool="take_screenshot",
                arguments={"path": "/tmp/desktop_automation_screenshot.png"}
            ),
            OrchestrationStep(
                id="save_desktop_info",
                name="Save Desktop Information",
                server="filesystem",
                tool="write_file",
                arguments={
                    "path": "/tmp/desktop_info.json",
                    "content": "{{DESKTOP_INFO}}"  # Will be populated
                },
                depends_on=["get_screen_info", "list_windows"]
            )
        ]
        
        return self.create_workflow(
            name="Desktop Automation",
            description="Automated desktop information gathering and documentation",
            steps=steps
        )
    
    def create_file_management_workflow(self, source_dir: str, backup_dir: str) -> str:
        """Create file management workflow"""
        steps = [
            OrchestrationStep(
                id="list_source_files",
                name="List Source Files",
                server="filesystem",
                tool="list_directory",
                arguments={"path": source_dir}
            ),
            OrchestrationStep(
                id="create_backup_dir",
                name="Create Backup Directory",
                server="filesystem",
                tool="create_directory",
                arguments={"path": backup_dir}
            ),
            OrchestrationStep(
                id="get_disk_usage",
                name="Check Disk Usage",
                server="system",
                tool="get_disk_usage",
                arguments={"human_readable": True}
            ),
            OrchestrationStep(
                id="backup_files",
                name="Backup Files",
                server="filesystem",
                tool="copy_file",
                arguments={
                    "source": source_dir,
                    "destination": backup_dir
                },
                depends_on=["list_source_files", "create_backup_dir", "get_disk_usage"]
            )
        ]
        
        return self.create_workflow(
            name="File Management",
            description=f"Automated file backup from {source_dir} to {backup_dir}",
            steps=steps
        )
    
    async def shutdown(self):
        """Shutdown orchestrator"""
        # Cancel active workflows
        for workflow in self.active_workflows.values():
            workflow.status = OrchestrationStatus.CANCELLED
        
        self.active_workflows.clear()
        logger.info("MCP Orchestrator shutdown complete")