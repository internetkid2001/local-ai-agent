"""
Agent Orchestrator

Main orchestration engine that coordinates between local LLMs (Ollama) 
and MCP servers to execute complex tasks.

Author: Claude Code
Date: 2025-07-13
Session: 1.3
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import time

from ..llm.ollama_client import OllamaClient, OllamaConfig, ModelType
from ..llm.function_calling import FunctionCallHandler
from ...mcp_client.base_client import BaseMCPClient, MCPClientConfig
from ...utils.logger import get_logger

logger = get_logger(__name__)


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Task:
    """Task definition for agent execution"""
    id: str
    description: str
    task_type: str
    priority: TaskPriority = TaskPriority.MEDIUM
    context: Dict[str, Any] = None
    requirements: Dict[str, Any] = None
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.context is None:
            self.context = {}
        if self.requirements is None:
            self.requirements = {}
        if self.created_at is None:
            self.created_at = time.time()


@dataclass
class AgentConfig:
    """Configuration for agent orchestrator"""
    ollama_config: OllamaConfig
    mcp_config: MCPClientConfig
    max_concurrent_tasks: int = 5
    task_timeout: float = 300.0  # 5 minutes
    enable_screenshots: bool = True
    screenshot_interval: float = 30.0
    context_retention_limit: int = 100


class AgentOrchestrator:
    """
    Main agent orchestrator that coordinates local LLM and MCP servers.
    
    Features:
    - Task queue management with priority scheduling
    - Coordination between Ollama and MCP servers
    - Context management and memory
    - Screenshot integration for visual context
    - Error handling and retry logic
    """
    
    def __init__(self, config: AgentConfig):
        """
        Initialize agent orchestrator.
        
        Args:
            config: Agent configuration
        """
        self.config = config
        
        # Core components
        self.ollama_client: Optional[OllamaClient] = None
        self.mcp_client: Optional[BaseMCPClient] = None
        self.function_handler = FunctionCallHandler()
        
        # Task management
        self.task_queue: List[Task] = []
        self.active_tasks: Dict[str, Task] = {}
        self.completed_tasks: List[Task] = []
        
        # Context and memory
        self.conversation_history: Dict[str, List[Dict[str, Any]]] = {}
        self.global_context: Dict[str, Any] = {}
        
        # Control flags
        self._running = False
        self._task_semaphore = asyncio.Semaphore(config.max_concurrent_tasks)
        
        logger.info("Agent orchestrator initialized")
    
    async def initialize(self) -> bool:
        """
        Initialize all agent components.
        
        Returns:
            True if initialization successful
        """
        logger.info("Initializing agent orchestrator...")
        
        try:
            # Initialize Ollama client
            self.ollama_client = OllamaClient(self.config.ollama_config)
            if not await self.ollama_client.initialize():
                logger.error("Failed to initialize Ollama client")
                return False
            
            # Initialize MCP client (placeholder - will be implemented with concrete client)
            # self.mcp_client = ConcreteMCPClient(self.config.mcp_config)
            # if not await self.mcp_client.initialize():
            #     logger.error("Failed to initialize MCP client")
            #     return False
            
            # Register core functions with Ollama
            await self._register_core_functions()
            
            logger.info("Agent orchestrator initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize agent orchestrator: {e}")
            return False
    
    async def shutdown(self):
        """Gracefully shutdown the orchestrator"""
        logger.info("Shutting down agent orchestrator...")
        
        self._running = False
        
        # Cancel active tasks
        for task_id, task in self.active_tasks.items():
            task.status = TaskStatus.CANCELLED
            logger.info(f"Cancelled task: {task_id}")
        
        # Shutdown components
        if self.ollama_client:
            await self.ollama_client.shutdown()
        
        if self.mcp_client:
            await self.mcp_client.shutdown()
        
        logger.info("Agent orchestrator shutdown complete")
    
    async def submit_task(self, task: Task) -> str:
        """
        Submit a task for execution.
        
        Args:
            task: Task to execute
            
        Returns:
            Task ID
        """
        # Add to queue sorted by priority
        self.task_queue.append(task)
        self.task_queue.sort(key=lambda t: t.priority.value, reverse=True)
        
        logger.info(f"Task submitted: {task.id} - {task.description}")
        return task.id
    
    async def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get status of a specific task"""
        # Check active tasks
        if task_id in self.active_tasks:
            return self.active_tasks[task_id].status
        
        # Check completed tasks
        for task in self.completed_tasks:
            if task.id == task_id:
                return task.status
        
        # Check pending tasks
        for task in self.task_queue:
            if task.id == task_id:
                return task.status
        
        return None
    
    async def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get result of a completed task"""
        for task in self.completed_tasks:
            if task.id == task_id:
                return task.result
        
        return None
    
    async def start_processing(self):
        """Start processing tasks from the queue"""
        self._running = True
        logger.info("Started task processing")
        
        while self._running:
            if self.task_queue:
                # Get highest priority task
                task = self.task_queue.pop(0)
                
                # Execute task in background
                asyncio.create_task(self._execute_task(task))
            
            # Brief pause to prevent tight loop
            await asyncio.sleep(0.1)
    
    async def stop_processing(self):
        """Stop processing new tasks"""
        self._running = False
        logger.info("Stopped task processing")
    
    async def _execute_task(self, task: Task):
        """Execute a single task"""
        async with self._task_semaphore:
            task_id = task.id
            self.active_tasks[task_id] = task
            
            try:
                logger.info(f"Starting task execution: {task_id}")
                task.status = TaskStatus.IN_PROGRESS
                task.started_at = time.time()
                
                # Route task to appropriate handler
                result = await self._route_task(task)
                
                # Mark as completed
                task.status = TaskStatus.COMPLETED
                task.completed_at = time.time()
                task.result = result
                
                logger.info(f"Task completed: {task_id}")
                
            except Exception as e:
                logger.error(f"Task failed: {task_id} - {e}")
                task.status = TaskStatus.FAILED
                task.error = str(e)
                task.completed_at = time.time()
            
            finally:
                # Move to completed tasks
                self.active_tasks.pop(task_id, None)
                self.completed_tasks.append(task)
                
                # Cleanup old completed tasks
                if len(self.completed_tasks) > self.config.context_retention_limit:
                    self.completed_tasks = self.completed_tasks[-self.config.context_retention_limit:]
    
    async def _route_task(self, task: Task) -> Dict[str, Any]:
        """Route task to appropriate execution method"""
        task_type = task.task_type.lower()
        
        if task_type == "llm_query":
            return await self._handle_llm_query(task)
        elif task_type == "file_operation":
            return await self._handle_file_operation(task)
        elif task_type == "analysis":
            return await self._handle_analysis_task(task)
        elif task_type == "hybrid":
            return await self._handle_hybrid_task(task)
        else:
            # Default to LLM processing
            return await self._handle_llm_query(task)
    
    async def _handle_llm_query(self, task: Task) -> Dict[str, Any]:
        """Handle pure LLM query tasks"""
        if not self.ollama_client:
            raise RuntimeError("Ollama client not initialized")
        
        prompt = task.description
        model_type = ModelType.PRIMARY
        
        # Check if this is a code-related task
        if any(keyword in prompt.lower() for keyword in ['code', 'programming', 'script', 'function']):
            model_type = ModelType.CODE
        
        # Execute LLM query
        response = await self.ollama_client.generate(
            prompt=prompt,
            model_type=model_type,
            conversation_id=task.id,
            functions=self.function_handler.get_function_schemas()
        )
        
        # Handle function calls if present
        if response.function_calls:
            function_results = []
            for func_call in response.function_calls:
                if 'result' in func_call:
                    function_results.append(func_call)
            
            return {
                "response": response.content,
                "function_calls": function_results,
                "model": response.model
            }
        
        return {
            "response": response.content,
            "model": response.model
        }
    
    async def _handle_file_operation(self, task: Task) -> Dict[str, Any]:
        """Handle file operation tasks via MCP servers"""
        if not self.mcp_client:
            raise RuntimeError("MCP client not initialized")
        
        operation = task.requirements.get("operation")
        parameters = task.requirements.get("parameters", {})
        
        if not operation:
            raise ValueError("File operation not specified")
        
        # Execute MCP tool
        result = await self.mcp_client.execute_tool(operation, parameters)
        
        return {
            "operation": operation,
            "parameters": parameters,
            "result": result
        }
    
    async def _handle_analysis_task(self, task: Task) -> Dict[str, Any]:
        """Handle analysis tasks that may require multiple steps"""
        # Placeholder for complex analysis tasks
        # This would coordinate between LLM and MCP servers for multi-step analysis
        
        return {
            "analysis_type": task.requirements.get("analysis_type", "general"),
            "status": "analysis_complete",
            "placeholder": True
        }
    
    async def _handle_hybrid_task(self, task: Task) -> Dict[str, Any]:
        """Handle hybrid tasks requiring both LLM and MCP coordination"""
        # Placeholder for hybrid task execution
        # This would orchestrate complex workflows between multiple components
        
        return {
            "task_type": "hybrid",
            "status": "hybrid_complete", 
            "placeholder": True
        }
    
    async def _register_core_functions(self):
        """Register core functions with the function handler"""
        # This will be expanded with actual functions
        pass
    
    def get_active_tasks(self) -> List[Task]:
        """Get list of currently active tasks"""
        return list(self.active_tasks.values())
    
    def get_completed_tasks(self, limit: int = 10) -> List[Task]:
        """Get list of recently completed tasks"""
        return self.completed_tasks[-limit:]
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        return {
            "pending_tasks": len(self.task_queue),
            "active_tasks": len(self.active_tasks),
            "completed_tasks": len(self.completed_tasks),
            "running": self._running
        }