"""
Step Executor

Executes individual workflow steps by routing to appropriate execution engines
(LLM, MCP, hybrid) based on step type and requirements.

Author: Claude Code
Date: 2025-07-13
Session: 2.2
"""

import asyncio
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging

from ...utils.logger import get_logger

logger = get_logger(__name__)


class StepType(Enum):
    """Types of workflow steps"""
    LLM_QUERY = "llm_query"           # Pure LLM interaction
    MCP_TOOL = "mcp_tool"             # MCP tool execution
    FILE_OPERATION = "file_operation"  # File system operations
    SYSTEM_COMMAND = "system_command"  # System/shell commands
    DESKTOP_ACTION = "desktop_action"  # Desktop automation
    CONDITIONAL = "conditional"        # Conditional logic
    LOOP = "loop"                     # Loop operations
    WAIT = "wait"                     # Wait/delay operations
    VALIDATION = "validation"         # Data validation
    TRANSFORMATION = "transformation"  # Data transformation
    NOTIFICATION = "notification"     # Send notifications
    EXTERNAL_SERVICE = "external_service"  # External service calls
    CUSTOM = "custom"                 # Custom step types


@dataclass
class StepResult:
    """Result of step execution"""
    success: bool
    output_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    step_type: Optional[StepType] = None
    metadata: Optional[Dict[str, Any]] = None


class StepExecutor:
    """
    Executes individual workflow steps.
    
    Routes step execution to appropriate handlers based on step type.
    Provides standardized interface for all step types.
    """
    
    def __init__(self, orchestrator=None):
        """
        Initialize step executor.
        
        Args:
            orchestrator: Agent orchestrator for task execution
        """
        self.orchestrator = orchestrator
        logger.info("Step executor initialized")
    
    async def execute_step(self, step, context: Dict[str, Any]) -> StepResult:
        """
        Execute a workflow step.
        
        Args:
            step: WorkflowStep to execute
            context: Execution context
            
        Returns:
            Step execution result
        """
        start_time = time.time()
        logger.info(f"Executing step: {step.id} ({step.step_type.value})")
        
        try:
            # Route to appropriate handler based on step type
            if step.step_type == StepType.LLM_QUERY:
                result = await self._execute_llm_query(step, context)
            elif step.step_type == StepType.MCP_TOOL:
                result = await self._execute_mcp_tool(step, context)
            elif step.step_type == StepType.FILE_OPERATION:
                result = await self._execute_file_operation(step, context)
            elif step.step_type == StepType.SYSTEM_COMMAND:
                result = await self._execute_system_command(step, context)
            elif step.step_type == StepType.DESKTOP_ACTION:
                result = await self._execute_desktop_action(step, context)
            elif step.step_type == StepType.CONDITIONAL:
                result = await self._execute_conditional(step, context)
            elif step.step_type == StepType.LOOP:
                result = await self._execute_loop(step, context)
            elif step.step_type == StepType.WAIT:
                result = await self._execute_wait(step, context)
            elif step.step_type == StepType.VALIDATION:
                result = await self._execute_validation(step, context)
            elif step.step_type == StepType.TRANSFORMATION:
                result = await self._execute_transformation(step, context)
            elif step.step_type == StepType.NOTIFICATION:
                result = await self._execute_notification(step, context)
            elif step.step_type == StepType.EXTERNAL_SERVICE:
                result = await self._execute_external_service(step, context)
            elif step.step_type == StepType.CUSTOM:
                result = await self._execute_custom(step, context)
            else:
                result = StepResult(
                    success=False,
                    error=f"Unknown step type: {step.step_type}",
                    step_type=step.step_type
                )
            
            result.execution_time = time.time() - start_time
            result.step_type = step.step_type
            
            return result
            
        except Exception as e:
            logger.error(f"Step execution failed: {step.id} - {e}")
            return StepResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
                step_type=step.step_type
            )
    
    async def _execute_llm_query(self, step, context: Dict[str, Any]) -> StepResult:
        """Execute LLM query step"""
        if not self.orchestrator or not self.orchestrator.ollama_client:
            return StepResult(
                success=False,
                error="Ollama client not available"
            )
        
        # Prepare prompt with context substitution
        prompt = self._substitute_context_variables(step.action, context)
        model_type = step.parameters.get("model_type", "primary")
        
        try:
            response = await self.orchestrator.ollama_client.generate(
                prompt=prompt,
                model_type=model_type,
                conversation_id=step.id
            )
            
            return StepResult(
                success=True,
                output_data={
                    "response": response.content,
                    "model": response.model,
                    "tokens": response.tokens_used
                }
            )
            
        except Exception as e:
            return StepResult(success=False, error=str(e))
    
    async def _execute_mcp_tool(self, step, context: Dict[str, Any]) -> StepResult:
        """Execute MCP tool step"""
        if not self.orchestrator or not self.orchestrator.mcp_manager:
            return StepResult(
                success=False,
                error="MCP manager not available"
            )
        
        tool_name = step.action
        client_type = step.parameters.get("client_type", "auto")
        
        # Substitute context variables in parameters
        parameters = {}
        for key, value in step.parameters.items():
            if isinstance(value, str):
                parameters[key] = self._substitute_context_variables(value, context)
            else:
                parameters[key] = value
        
        try:
            if client_type == "auto":
                # Let MCP manager route automatically
                result = await self.orchestrator.mcp_manager.route_and_execute_task(
                    f"Execute {tool_name}",
                    parameters
                )
            else:
                # Use specific client
                result = await self.orchestrator.mcp_manager.execute_tool_directly(
                    client_type, tool_name, parameters
                )
            
            return StepResult(
                success=True,
                output_data=result
            )
            
        except Exception as e:
            return StepResult(success=False, error=str(e))
    
    async def _execute_file_operation(self, step, context: Dict[str, Any]) -> StepResult:
        """Execute file operation step"""
        operation = step.action  # read_file, write_file, etc.
        
        # Map to MCP file operations
        return await self._execute_mcp_tool(step, context)
    
    async def _execute_system_command(self, step, context: Dict[str, Any]) -> StepResult:
        """Execute system command step"""
        command = self._substitute_context_variables(step.action, context)
        shell = step.parameters.get("shell", True)
        timeout = step.parameters.get("timeout", 30)
        
        try:
            if shell:
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            else:
                process = await asyncio.create_subprocess_exec(
                    *command.split(),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
                
                return StepResult(
                    success=process.returncode == 0,
                    output_data={
                        "stdout": stdout.decode(),
                        "stderr": stderr.decode(),
                        "returncode": process.returncode
                    },
                    error=stderr.decode() if process.returncode != 0 else None
                )
                
            except asyncio.TimeoutError:
                process.kill()
                return StepResult(
                    success=False,
                    error=f"Command timed out after {timeout} seconds"
                )
                
        except Exception as e:
            return StepResult(success=False, error=str(e))
    
    async def _execute_desktop_action(self, step, context: Dict[str, Any]) -> StepResult:
        """Execute desktop automation step"""
        # Map to desktop MCP operations
        step.parameters["client_type"] = "desktop"
        return await self._execute_mcp_tool(step, context)
    
    async def _execute_conditional(self, step, context: Dict[str, Any]) -> StepResult:
        """Execute conditional logic step"""
        condition = self._substitute_context_variables(step.action, context)
        
        # Simple condition evaluation
        try:
            # Basic variable comparison
            if "==" in condition:
                left, right = condition.split("==", 1)
                left = left.strip()
                right = right.strip().strip('"\'')
                
                # Get value from context
                if left in context:
                    result = str(context[left]) == right
                else:
                    result = False
            elif "!=" in condition:
                left, right = condition.split("!=", 1)
                left = left.strip()
                right = right.strip().strip('"\'')
                
                if left in context:
                    result = str(context[left]) != right
                else:
                    result = True
            elif "exists" in condition:
                var_name = condition.replace("exists", "").strip()
                result = var_name in context
            else:
                # Try to evaluate as Python expression (limited safety)
                result = eval(condition, {"__builtins__": {}}, context)
            
            return StepResult(
                success=True,
                output_data={"condition_result": result}
            )
            
        except Exception as e:
            return StepResult(success=False, error=f"Condition evaluation failed: {e}")
    
    async def _execute_loop(self, step, context: Dict[str, Any]) -> StepResult:
        """Execute loop step"""
        loop_type = step.parameters.get("type", "count")
        
        if loop_type == "count":
            count = step.parameters.get("count", 1)
            results = []
            
            for i in range(count):
                loop_context = context.copy()
                loop_context["loop_index"] = i
                loop_context["loop_count"] = count
                
                # Execute loop action
                action_result = await self._execute_simple_action(
                    step.action, step.parameters, loop_context
                )
                results.append(action_result)
            
            return StepResult(
                success=True,
                output_data={"loop_results": results}
            )
        
        elif loop_type == "foreach":
            items = step.parameters.get("items", [])
            if isinstance(items, str) and items in context:
                items = context[items]
            
            results = []
            for item in items:
                loop_context = context.copy()
                loop_context["loop_item"] = item
                
                action_result = await self._execute_simple_action(
                    step.action, step.parameters, loop_context
                )
                results.append(action_result)
            
            return StepResult(
                success=True,
                output_data={"loop_results": results}
            )
        
        return StepResult(success=False, error=f"Unknown loop type: {loop_type}")
    
    async def _execute_wait(self, step, context: Dict[str, Any]) -> StepResult:
        """Execute wait/delay step"""
        duration = step.parameters.get("duration", 1.0)
        
        try:
            await asyncio.sleep(duration)
            return StepResult(
                success=True,
                output_data={"waited_seconds": duration}
            )
        except Exception as e:
            return StepResult(success=False, error=str(e))
    
    async def _execute_validation(self, step, context: Dict[str, Any]) -> StepResult:
        """Execute validation step"""
        validation_type = step.parameters.get("type", "exists")
        target = step.parameters.get("target")
        
        if validation_type == "exists":
            exists = target in context
            return StepResult(
                success=exists,
                output_data={"validation_result": exists},
                error=f"Variable '{target}' does not exist" if not exists else None
            )
        
        elif validation_type == "not_empty":
            if target in context:
                value = context[target]
                not_empty = value is not None and value != ""
                return StepResult(
                    success=not_empty,
                    output_data={"validation_result": not_empty},
                    error=f"Variable '{target}' is empty" if not not_empty else None
                )
            else:
                return StepResult(
                    success=False,
                    error=f"Variable '{target}' does not exist"
                )
        
        return StepResult(success=False, error=f"Unknown validation type: {validation_type}")
    
    async def _execute_transformation(self, step, context: Dict[str, Any]) -> StepResult:
        """Execute data transformation step"""
        transform_type = step.parameters.get("type", "copy")
        source = step.parameters.get("source")
        target = step.parameters.get("target")
        
        if transform_type == "copy":
            if source in context:
                return StepResult(
                    success=True,
                    output_data={target: context[source]}
                )
            else:
                return StepResult(
                    success=False,
                    error=f"Source variable '{source}' not found"
                )
        
        elif transform_type == "format":
            template = step.parameters.get("template", "{value}")
            if source in context:
                value = template.format(value=context[source])
                return StepResult(
                    success=True,
                    output_data={target: value}
                )
            else:
                return StepResult(
                    success=False,
                    error=f"Source variable '{source}' not found"
                )
        
        return StepResult(success=False, error=f"Unknown transformation type: {transform_type}")
    
    async def _execute_notification(self, step, context: Dict[str, Any]) -> StepResult:
        """Execute notification step"""
        message = self._substitute_context_variables(step.action, context)
        notification_type = step.parameters.get("type", "log")
        
        if notification_type == "log":
            logger.info(f"Workflow notification: {message}")
            return StepResult(
                success=True,
                output_data={"message": message}
            )
        
        # Future: Email, Slack, etc.
        return StepResult(success=False, error=f"Unknown notification type: {notification_type}")
    
    async def _execute_external_service(self, step, context: Dict[str, Any]) -> StepResult:
        """Execute external service step"""
        service_action = step.action  # web_search, api_request, database_query, etc.
        service_id = step.parameters.get("service_id")
        
        if not self.orchestrator:
            return StepResult(
                success=False,
                error="Orchestrator not available for external service calls"
            )
        
        try:
            # Import external service components
            from ..external import (
                WebSearchManager, APIClient, SQLClient, SQLConfig, SQLDialect,
                AuthManager, RateLimiter, ServiceRegistry
            )
            
            # Initialize service registry if not available
            if not hasattr(self.orchestrator, 'service_registry'):
                self.orchestrator.service_registry = ServiceRegistry()
            
            # Route to appropriate external service handler
            if service_action == "web_search":
                result = await self._handle_web_search(step, context)
            elif service_action == "api_request":
                result = await self._handle_api_request(step, context)
            elif service_action == "database_query":
                result = await self._handle_database_query(step, context)
            elif service_action == "data_fetch":
                result = await self._handle_data_fetch(step, context)
            else:
                result = StepResult(
                    success=False,
                    error=f"Unknown external service action: {service_action}"
                )
            
            return result
            
        except ImportError as e:
            return StepResult(
                success=False,
                error=f"External service dependencies not available: {e}"
            )
        except Exception as e:
            return StepResult(
                success=False,
                error=f"External service execution failed: {e}"
            )
    
    async def _handle_web_search(self, step, context: Dict[str, Any]) -> StepResult:
        """Handle web search operations"""
        from ..external import WebSearchManager
        
        query = self._substitute_context_variables(
            step.parameters.get("query", ""), context
        )
        provider = step.parameters.get("provider", "duckduckgo")
        max_results = step.parameters.get("max_results", 10)
        
        # Initialize web search manager
        if not hasattr(self.orchestrator, 'web_search_manager'):
            self.orchestrator.web_search_manager = WebSearchManager()
        
        try:
            results = await self.orchestrator.web_search_manager.search(
                query=query,
                providers=[provider],
                max_results=max_results
            )
            
            return StepResult(
                success=True,
                output_data={
                    "results": results,
                    "query": query,
                    "provider": provider,
                    "result_count": len(results)
                }
            )
            
        except Exception as e:
            return StepResult(
                success=False,
                error=f"Web search failed: {e}"
            )
    
    async def _handle_api_request(self, step, context: Dict[str, Any]) -> StepResult:
        """Handle API request operations"""
        from ..external import APIClient, AuthManager
        
        service_id = step.parameters.get("service_id")
        endpoint = self._substitute_context_variables(
            step.parameters.get("endpoint", ""), context
        )
        method = step.parameters.get("method", "GET")
        params = step.parameters.get("params", {})
        
        # Initialize API client
        if not hasattr(self.orchestrator, 'api_clients'):
            self.orchestrator.api_clients = {}
        
        if service_id not in self.orchestrator.api_clients:
            auth_manager = AuthManager()
            self.orchestrator.api_clients[service_id] = APIClient(
                base_url="",  # Will be set per request
                auth_manager=auth_manager
            )
        
        api_client = self.orchestrator.api_clients[service_id]
        
        try:
            response = await api_client.request(
                method=method,
                url=endpoint,
                params=params
            )
            
            return StepResult(
                success=True,
                output_data={
                    "data": response.data,
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "service_id": service_id
                }
            )
            
        except Exception as e:
            return StepResult(
                success=False,
                error=f"API request failed: {e}"
            )
    
    async def _handle_database_query(self, step, context: Dict[str, Any]) -> StepResult:
        """Handle database query operations"""
        from ..external import SQLClient, SQLConfig, SQLDialect
        
        service_id = step.parameters.get("service_id")
        query = self._substitute_context_variables(
            step.parameters.get("query", ""), context
        )
        timeout = step.parameters.get("timeout", 60)
        
        # Initialize database client
        if not hasattr(self.orchestrator, 'db_clients'):
            self.orchestrator.db_clients = {}
        
        if service_id not in self.orchestrator.db_clients:
            # Default to SQLite for demo purposes
            config = SQLConfig(
                dialect=SQLDialect.SQLITE,
                database=f"/tmp/{service_id}.db"
            )
            self.orchestrator.db_clients[service_id] = SQLClient(config)
        
        db_client = self.orchestrator.db_clients[service_id]
        
        try:
            result = await db_client.execute_query(query)
            
            return StepResult(
                success=result.success,
                output_data={
                    "rows": result.rows,
                    "row_count": result.row_count,
                    "columns": result.columns,
                    "execution_time": result.execution_time
                },
                error=result.error if not result.success else None
            )
            
        except Exception as e:
            return StepResult(
                success=False,
                error=f"Database query failed: {e}"
            )
    
    async def _handle_data_fetch(self, step, context: Dict[str, Any]) -> StepResult:
        """Handle generic data fetching operations"""
        source = step.parameters.get("source")
        params = step.parameters.get("params", {})
        
        # Route to appropriate handler based on source type
        if source == "api":
            # Convert to API request
            step.action = "api_request"
            return await self._handle_api_request(step, context)
        elif source == "database":
            # Convert to database query
            step.action = "database_query"
            return await self._handle_database_query(step, context)
        elif source == "file":
            # Use existing file operation handler
            step.step_type = StepType.FILE_OPERATION
            step.action = "read_file"
            return await self._execute_file_operation(step, context)
        else:
            return StepResult(
                success=False,
                error=f"Unknown data source: {source}"
            )
    
    async def _execute_custom(self, step, context: Dict[str, Any]) -> StepResult:
        """Execute custom step type"""
        # Placeholder for custom step implementations
        return StepResult(
            success=False,
            error="Custom step types not implemented yet"
        )
    
    async def _execute_simple_action(self, action: str, parameters: Dict[str, Any], 
                                   context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a simple action (for loops)"""
        # Simplified action execution for loop contexts
        return {"action": action, "parameters": parameters}
    
    def _substitute_context_variables(self, text: str, context: Dict[str, Any]) -> str:
        """Substitute context variables in text using {variable} syntax"""
        if not isinstance(text, str):
            return text
        
        for key, value in context.items():
            placeholder = f"{{{key}}}"
            if placeholder in text:
                text = text.replace(placeholder, str(value))
        
        return text
    
    async def rollback_step(self, step, context: Dict[str, Any]) -> bool:
        """Rollback a completed step (if possible)"""
        # Rollback logic depends on step type
        if step.step_type == StepType.FILE_OPERATION:
            # Could restore file backups
            pass
        elif step.step_type == StepType.SYSTEM_COMMAND:
            # Could execute reverse commands
            pass
        elif step.step_type == StepType.MCP_TOOL:
            # Could call rollback-specific tools
            pass
        
        logger.warning(f"Rollback not implemented for step type: {step.step_type}")
        return False