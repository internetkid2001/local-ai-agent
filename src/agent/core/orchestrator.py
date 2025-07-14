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
from ..ai.memory_system import MemoryType
from ..ai.adaptation_engine import ModelMetric
from dataclasses import dataclass
from enum import Enum
import time

from ..llm.ollama_client import OllamaClient, OllamaConfig, ModelType
from ..llm.function_calling import FunctionCallHandler
from ...mcp_client.base_client import BaseMCPClient, MCPClientConfig
from ...mcp_client.client_manager import MCPClientManager
from .task_router import TaskRouter, TaskCategory
from ..workflows.workflow_engine import WorkflowEngine, WorkflowDefinition
from ..workflows.workflow_templates import WorkflowTemplates
from ...utils.logger import get_logger

# Phase 3: Advanced AI Capabilities
from ..ai.model_orchestrator import ModelOrchestrator as AIModelOrchestrator
from ..ai.conversation_manager import ConversationManager
from ..ai.reasoning_engine import ReasoningEngine
from ..ai.planning_engine import PlanningEngine
from ..ai.memory_system import MemorySystem
from ..ai.adaptation_engine import AdaptationEngine

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
    mcp_configs: Dict[str, MCPClientConfig] = None  # Multiple MCP client configs
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
        self.mcp_manager = MCPClientManager()
        self.task_router = TaskRouter()
        self.function_handler = FunctionCallHandler()
        self.workflow_engine = WorkflowEngine(self)
        self.workflow_templates = WorkflowTemplates()
        
        # Phase 3: Advanced AI Components
        self.ai_model_orchestrator: Optional[AIModelOrchestrator] = None
        self.conversation_manager: Optional[ConversationManager] = None
        self.reasoning_engine: Optional[ReasoningEngine] = None
        self.planning_engine: Optional[PlanningEngine] = None
        self.memory_system: Optional[MemorySystem] = None
        self.adaptation_engine: Optional[AdaptationEngine] = None
        self.ai_enabled = False
        
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
            
            # Initialize MCP client manager
            if not await self.mcp_manager.initialize(self.config.mcp_configs):
                logger.warning("No MCP clients initialized - some functionality may be limited")
            
            # Register core functions with Ollama
            await self._register_core_functions()
            
            # Initialize Phase 3 AI capabilities (optional)
            await self._initialize_ai_capabilities()
            
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
        
        await self.mcp_manager.shutdown()
        
        # Shutdown AI capabilities
        await self._shutdown_ai_capabilities()
        
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
        """Route task to appropriate execution method using intelligent routing"""
        
        # Use task router for intelligent routing
        routing_decision = await self.task_router.route_task(
            task.description, 
            task.context
        )
        
        # Check if AI-enhanced processing is available and beneficial
        if self.ai_enabled and self._should_use_ai_processing(task, routing_decision):
            return await self._handle_ai_enhanced_task(task, routing_decision)
        
        # Route based on category and strategy (existing logic)
        if routing_decision.category in [
            TaskCategory.FILE_OPERATIONS, 
            TaskCategory.DESKTOP_AUTOMATION, 
            TaskCategory.SYSTEM_MONITORING,
            TaskCategory.SYSTEM_INTERACTION
        ]:
            # Use MCP clients for these categories
            return await self._handle_mcp_task(task, routing_decision)
        
        elif routing_decision.category == TaskCategory.CODE_GENERATION:
            if routing_decision.strategy.value == "hybrid_llm_mcp":
                return await self._handle_hybrid_task(task, routing_decision)
            else:
                return await self._handle_llm_query(task)
        
        elif routing_decision.category == TaskCategory.WORKFLOW:
            return await self._handle_workflow_task(task, routing_decision)
        
        elif routing_decision.category == TaskCategory.HYBRID:
            return await self._handle_hybrid_task(task, routing_decision)
        
        else:
            # Default to LLM processing for research, analysis, etc.
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
    
    async def _handle_mcp_task(self, task: Task, routing_decision) -> Dict[str, Any]:
        """Handle tasks that should be executed via MCP clients"""
        
        # Use MCP manager to route and execute task
        result = await self.mcp_manager.route_and_execute_task(
            task.description,
            task.context
        )
        
        # Add task metadata
        result["task_id"] = task.id
        result["task_type"] = task.task_type
        
        return result
    
    async def _handle_analysis_task(self, task: Task) -> Dict[str, Any]:
        """Handle analysis tasks that may require multiple steps"""
        # Placeholder for complex analysis tasks
        # This would coordinate between LLM and MCP servers for multi-step analysis
        
        return {
            "analysis_type": task.requirements.get("analysis_type", "general"),
            "status": "analysis_complete",
            "placeholder": True
        }
    
    async def _handle_hybrid_task(self, task: Task, routing_decision = None) -> Dict[str, Any]:
        """Handle hybrid tasks requiring both LLM and MCP coordination"""
        
        try:
            # Step 1: Use LLM to analyze and plan the task
            llm_response = await self._handle_llm_query(task)
            
            # Step 2: If LLM suggests MCP operations, execute them
            mcp_results = []
            if routing_decision and routing_decision.suggested_tools:
                for tool in routing_decision.suggested_tools[:3]:  # Limit to prevent loops
                    try:
                        # Extract parameters from LLM response or task context
                        parameters = task.context.get("parameters", {})
                        
                        # Route through MCP manager
                        mcp_result = await self.mcp_manager.route_and_execute_task(
                            f"Execute {tool} operation: {task.description}",
                            parameters
                        )
                        mcp_results.append(mcp_result)
                    except Exception as e:
                        logger.warning(f"MCP operation {tool} failed: {e}")
            
            # Step 3: Combine results
            return {
                "task_type": "hybrid",
                "llm_response": llm_response,
                "mcp_results": mcp_results,
                "status": "hybrid_complete",
                "routing_decision": routing_decision.reasoning if routing_decision else None
            }
            
        except Exception as e:
            logger.error(f"Hybrid task execution failed: {e}")
            return {
                "task_type": "hybrid",
                "status": "hybrid_failed",
                "error": str(e)
            }
    
    async def _handle_workflow_task(self, task: Task, routing_decision = None) -> Dict[str, Any]:
        """Handle workflow execution tasks"""
        try:
            # Check if this is a workflow template request
            if "template" in task.description.lower():
                # Extract template name and parameters from task context
                template_id = task.context.get("template_id")
                parameters = task.context.get("parameters", {})
                
                if template_id:
                    workflow = await self.create_workflow_from_template(template_id, parameters)
                    return {
                        "task_type": "workflow_template",
                        "workflow_id": workflow.id,
                        "status": workflow.status.value,
                        "template_used": template_id
                    }
            
            # Check if this is a custom workflow definition
            elif "workflow_definition" in task.context:
                workflow_def = task.context["workflow_definition"]
                workflow = self.workflow_templates.parser.parse_from_dict(workflow_def)
                executed_workflow = await self.execute_workflow(workflow)
                
                return {
                    "task_type": "custom_workflow",
                    "workflow_id": executed_workflow.id,
                    "status": executed_workflow.status.value,
                    "execution_results": self._summarize_workflow_results(executed_workflow)
                }
            
            # Default: Try to create a simple workflow from the task description
            else:
                # Use LLM to break down the task into workflow steps
                llm_response = await self._handle_llm_query(task)
                
                # For now, return the LLM response with workflow metadata
                return {
                    "task_type": "workflow_analysis",
                    "llm_analysis": llm_response,
                    "suggestion": "Task analyzed for potential workflow automation",
                    "next_steps": ["Create workflow template", "Define workflow steps"]
                }
                
        except Exception as e:
            logger.error(f"Workflow task execution failed: {e}")
            return {
                "task_type": "workflow",
                "status": "workflow_failed",
                "error": str(e)
            }
    
    def _summarize_workflow_results(self, workflow: WorkflowDefinition) -> Dict[str, Any]:
        """Summarize workflow execution results"""
        completed_steps = [s for s in workflow.steps if s.status.value == "completed"]
        failed_steps = [s for s in workflow.steps if s.status.value == "failed"]
        
        return {
            "total_steps": len(workflow.steps),
            "completed_steps": len(completed_steps),
            "failed_steps": len(failed_steps),
            "execution_time": workflow.completed_at - workflow.started_at if workflow.completed_at else None,
            "final_status": workflow.status.value
        }
    
    async def _register_core_functions(self):
        """Register core functions with the function handler"""
        # This will be expanded with actual functions
        pass
    
    async def _initialize_ai_capabilities(self):
        """Initialize Phase 3 AI capabilities"""
        try:
            logger.info("Initializing Phase 3 AI capabilities...")
            
            # Initialize AI Model Orchestrator
            self.ai_model_orchestrator = AIModelOrchestrator()
            
            # Initialize Conversation Manager
            self.conversation_manager = ConversationManager(
                storage_path="./data/conversations"
            )
            
            # Initialize Memory System
            self.memory_system = MemorySystem(
                storage_path="./data/memory"
            )
            
            # Initialize Adaptation Engine
            self.adaptation_engine = AdaptationEngine(
                storage_path="./data/adaptation"
            )
            
            # Initialize Reasoning Engine (requires model orchestrator)
            self.reasoning_engine = ReasoningEngine(
                model_orchestrator=self.ai_model_orchestrator
            )
            
            # Initialize Planning Engine (requires model orchestrator)
            self.planning_engine = PlanningEngine(
                model_orchestrator=self.ai_model_orchestrator
            )
            
            self.ai_enabled = True
            logger.info("Phase 3 AI capabilities initialized successfully")
            
        except Exception as e:
            logger.warning(f"Failed to initialize AI capabilities: {e}")
            logger.info("Agent will continue with core functionality only")
            self.ai_enabled = False
    
    async def _shutdown_ai_capabilities(self):
        """Shutdown Phase 3 AI capabilities"""
        if not self.ai_enabled:
            return
            
        try:
            if self.conversation_manager:
                await self.conversation_manager.cleanup()
            
            if self.memory_system:
                await self.memory_system.cleanup()
            
            if self.adaptation_engine:
                await self.adaptation_engine.cleanup()
            
            logger.info("AI capabilities shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during AI capabilities shutdown: {e}")
    
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
    
    async def get_mcp_status(self) -> Dict[str, Any]:
        """Get MCP client status"""
        return {
            "clients": self.mcp_manager.get_client_status(),
            "available_tools": self.mcp_manager.get_available_tools(),
            "health": await self.mcp_manager.health_check()
        }
    
    async def execute_mcp_tool(self, client_type: str, tool_name: str, 
                              parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an MCP tool directly"""
        return await self.mcp_manager.execute_tool_directly(client_type, tool_name, parameters)
    
    # Workflow Management Methods
    
    async def execute_workflow(self, workflow: WorkflowDefinition) -> WorkflowDefinition:
        """Execute a complete workflow"""
        return await self.workflow_engine.execute_workflow(workflow)
    
    async def create_workflow_from_template(self, template_id: str, 
                                          parameters: Dict[str, Any]) -> WorkflowDefinition:
        """Create and execute workflow from template"""
        workflow = self.workflow_templates.create_workflow_from_template(template_id, parameters)
        return await self.execute_workflow(workflow)
    
    def get_workflow_templates(self) -> List[Dict[str, str]]:
        """Get list of available workflow templates"""
        return self.workflow_templates.get_template_list()
    
    def get_template_info(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get template information and parameters"""
        return self.workflow_templates.get_template_info(template_id)
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow execution status"""
        return self.workflow_engine.get_workflow_status(workflow_id)
    
    def get_running_workflows(self) -> List[Dict[str, Any]]:
        """Get all running workflows"""
        return self.workflow_engine.get_running_workflows()
    
    async def pause_workflow(self, workflow_id: str) -> bool:
        """Pause a running workflow"""
        return await self.workflow_engine.pause_workflow(workflow_id)
    
    async def resume_workflow(self, workflow_id: str) -> bool:
        """Resume a paused workflow"""
        return await self.workflow_engine.resume_workflow(workflow_id)
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow"""
        return await self.workflow_engine.cancel_workflow(workflow_id)
    
    # Phase 3: AI-Enhanced Task Processing
    
    def _should_use_ai_processing(self, task: Task, routing_decision) -> bool:
        """Determine if task should use AI-enhanced processing"""
        if not self.ai_enabled:
            return False
        
        # Use AI for complex reasoning, planning, or analysis tasks
        ai_keywords = [
            'analyze', 'plan', 'reason', 'think', 'strategy', 'approach',
            'solution', 'complex', 'multi-step', 'workflow', 'breakdown'
        ]
        
        task_text = task.description.lower()
        return any(keyword in task_text for keyword in ai_keywords)
    
    async def _handle_ai_enhanced_task(self, task: Task, routing_decision) -> Dict[str, Any]:
        """Handle tasks using AI-enhanced processing"""
        try:
            # Store task in memory
            if self.memory_system:
                await self.memory_system.store_memory(
                    content=f"Task: {task.description}",
                    memory_type=MemoryType.EPISODIC,
                    metadata={"task_id": task.id, "task_type": task.task_type}
                )
            
            # Use reasoning engine for complex analysis
            reasoning_result = None
            if self.reasoning_engine and self._requires_reasoning(task):
                reasoning_result = await self.reasoning_engine.reason(
                    query=task.description,
                    context=task.context
                )
            
            # Use planning engine for multi-step tasks
            plan_result = None
            if self.planning_engine and self._requires_planning(task):
                plan_result = await self.planning_engine.create_plan(
                    goal=task.description,
                    context=task.context
                )
            
            # Execute the core task logic
            core_result = await self._execute_core_task_logic(task, routing_decision)
            
            # Record performance metrics
            if self.adaptation_engine:
                await self.adaptation_engine.record_performance(
                    metric_type=ModelMetric.CONTEXT_RELEVANCE,
                    value=0.85,  # Would be calculated based on actual performance
                    task_type=task.task_type
                )
            
            # Combine results
            ai_enhanced_result = {
                "task_type": "ai_enhanced",
                "core_result": core_result,
                "ai_processing": {
                    "reasoning_used": reasoning_result is not None,
                    "planning_used": plan_result is not None,
                    "memory_stored": self.memory_system is not None
                }
            }
            
            if reasoning_result:
                ai_enhanced_result["reasoning_analysis"] = reasoning_result
            
            if plan_result:
                ai_enhanced_result["execution_plan"] = plan_result
            
            return ai_enhanced_result
            
        except Exception as e:
            logger.error(f"AI-enhanced task processing failed: {e}")
            # Fallback to standard processing
            return await self._execute_core_task_logic(task, routing_decision)
    
    def _requires_reasoning(self, task: Task) -> bool:
        """Check if task requires reasoning analysis"""
        reasoning_keywords = ['analyze', 'compare', 'evaluate', 'reason', 'logic']
        return any(keyword in task.description.lower() for keyword in reasoning_keywords)
    
    def _requires_planning(self, task: Task) -> bool:
        """Check if task requires planning"""
        planning_keywords = ['plan', 'strategy', 'approach', 'steps', 'workflow', 'process']
        return any(keyword in task.description.lower() for keyword in planning_keywords)
    
    async def _execute_core_task_logic(self, task: Task, routing_decision) -> Dict[str, Any]:
        """Execute core task logic (existing routing logic)"""
        if routing_decision.category in [
            TaskCategory.FILE_OPERATIONS, 
            TaskCategory.DESKTOP_AUTOMATION, 
            TaskCategory.SYSTEM_MONITORING,
            TaskCategory.SYSTEM_INTERACTION
        ]:
            return await self._handle_mcp_task(task, routing_decision)
        elif routing_decision.category == TaskCategory.CODE_GENERATION:
            if routing_decision.strategy.value == "hybrid_llm_mcp":
                return await self._handle_hybrid_task(task, routing_decision)
            else:
                return await self._handle_llm_query(task)
        elif routing_decision.category == TaskCategory.WORKFLOW:
            return await self._handle_workflow_task(task, routing_decision)
        elif routing_decision.category == TaskCategory.HYBRID:
            return await self._handle_hybrid_task(task, routing_decision)
        else:
            return await self._handle_llm_query(task)
    
    # AI Capability Access Methods
    
    async def query_memory(self, query: str, memory_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Query the memory system"""
        if not self.memory_system:
            return []
        
        try:
            if memory_type:
                from ..ai.memory_system import MemoryType
                mem_type = MemoryType(memory_type)
                results = await self.memory_system.get_recent_memories(memory_type=mem_type)
            else:
                results = await self.memory_system.search_by_content(query)
            
            return [{
                "id": mem.id,
                "content": mem.content,
                "type": mem.memory_type.value,
                "created_at": mem.created_at.isoformat() if mem.created_at else None
            } for mem in results]
            
        except Exception as e:
            logger.error(f"Memory query failed: {e}")
            return []
    
    async def get_ai_capabilities_status(self) -> Dict[str, Any]:
        """Get status of AI capabilities"""
        if not self.ai_enabled:
            return {"ai_enabled": False, "reason": "AI capabilities not initialized"}
        
        status = {"ai_enabled": True, "components": {}}
        
        try:
            if self.memory_system:
                memory_stats = await self.memory_system.get_memory_stats()
                status["components"]["memory_system"] = memory_stats
            
            if self.adaptation_engine:
                adaptation_stats = await self.adaptation_engine.get_adaptation_stats()
                status["components"]["adaptation_engine"] = adaptation_stats
            
            if self.ai_model_orchestrator:
                models = await self.ai_model_orchestrator.list_available_models()
                status["components"]["model_orchestrator"] = {
                    "available_models": len(models)
                }
            
            status["components"]["reasoning_engine"] = {
                "available": self.reasoning_engine is not None
            }
            
            status["components"]["planning_engine"] = {
                "available": self.planning_engine is not None
            }
            
            status["components"]["conversation_manager"] = {
                "available": self.conversation_manager is not None
            }
            
        except Exception as e:
            logger.error(f"Error getting AI status: {e}")
            status["error"] = str(e)
        
        return status