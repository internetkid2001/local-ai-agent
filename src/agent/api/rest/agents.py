from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel
import asyncio
import uuid
from datetime import datetime
import logging

from ..models.base import APIResponse, AgentInfo, AgentStatus, ExecutionRequest, ExecutionResult
from ...enterprise.auth import User, Resource, Permission

logger = logging.getLogger(__name__)


class AgentCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    capabilities: List[str] = []
    config: Optional[Dict[str, Any]] = {}


class AgentUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    capabilities: Optional[List[str]] = None
    config: Optional[Dict[str, Any]] = None


class AgentRegistry:
    def __init__(self):
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.executions: Dict[str, Dict[str, Any]] = {}
    
    def create_agent(self, request: AgentCreateRequest, tenant_id: Optional[str], created_by: str) -> str:
        agent_id = str(uuid.uuid4())
        
        agent_data = {
            "id": agent_id,
            "name": request.name,
            "description": request.description,
            "status": AgentStatus.IDLE,
            "capabilities": request.capabilities,
            "config": request.config or {},
            "created_at": datetime.utcnow(),
            "last_activity": None,
            "tenant_id": tenant_id,
            "created_by": created_by
        }
        
        self.agents[agent_id] = agent_data
        logger.info(f"Created agent {agent_id} for tenant {tenant_id}")
        return agent_id
    
    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        return self.agents.get(agent_id)
    
    def list_agents(self, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        agents = list(self.agents.values())
        if tenant_id:
            agents = [a for a in agents if a.get("tenant_id") == tenant_id]
        return agents
    
    def update_agent(self, agent_id: str, updates: Dict[str, Any]) -> bool:
        if agent_id not in self.agents:
            return False
        
        self.agents[agent_id].update(updates)
        return True
    
    def delete_agent(self, agent_id: str) -> bool:
        if agent_id in self.agents:
            del self.agents[agent_id]
            return True
        return False
    
    async def execute_command(self, agent_id: str, request: ExecutionRequest) -> str:
        agent = self.get_agent(agent_id)
        if not agent:
            raise ValueError("Agent not found")
        
        execution_id = str(uuid.uuid4())
        execution_data = {
            "id": execution_id,
            "agent_id": agent_id,
            "command": request.command,
            "parameters": request.parameters,
            "context": request.context,
            "status": "running",
            "result": None,
            "error": None,
            "started_at": datetime.utcnow(),
            "completed_at": None,
            "execution_time": None
        }
        
        self.executions[execution_id] = execution_data
        self.agents[agent_id]["status"] = AgentStatus.RUNNING
        self.agents[agent_id]["last_activity"] = datetime.utcnow()
        
        asyncio.create_task(self._simulate_execution(execution_id, request.timeout or 300))
        
        return execution_id
    
    async def _simulate_execution(self, execution_id: str, timeout: int):
        await asyncio.sleep(min(2, timeout))
        
        execution = self.executions.get(execution_id)
        if not execution:
            return
        
        agent_id = execution["agent_id"]
        
        execution["status"] = "completed"
        execution["result"] = {"message": f"Command '{execution['command']}' executed successfully"}
        execution["completed_at"] = datetime.utcnow()
        execution["execution_time"] = (execution["completed_at"] - execution["started_at"]).total_seconds()
        
        if agent_id in self.agents:
            self.agents[agent_id]["status"] = AgentStatus.IDLE
            self.agents[agent_id]["last_activity"] = datetime.utcnow()
    
    def get_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        return self.executions.get(execution_id)
    
    def list_executions(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        executions = list(self.executions.values())
        if agent_id:
            executions = [e for e in executions if e.get("agent_id") == agent_id]
        return executions


def create_agents_router(auth_deps: Dict[str, Any]) -> APIRouter:
    router = APIRouter(prefix="/agents", tags=["agents"])
    agent_registry = AgentRegistry()
    
    @router.post("/", response_model=APIResponse)
    async def create_agent(
        request: AgentCreateRequest,
        current_user: User = Depends(auth_deps['get_current_active_user'])
    ):
        try:
            agent_id = agent_registry.create_agent(
                request, current_user.tenant_id, current_user.username
            )
            
            agent_data = agent_registry.get_agent(agent_id)
            return APIResponse(
                data=AgentInfo(**agent_data),
                message="Agent created successfully"
            )
        
        except Exception as e:
            logger.error(f"Failed to create agent: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create agent"
            )
    
    @router.get("/", response_model=APIResponse)
    async def list_agents(
        current_user: User = Depends(auth_deps['get_current_active_user']),
        status_filter: Optional[AgentStatus] = Query(None, alias="status")
    ):
        agents = agent_registry.list_agents(current_user.tenant_id)
        
        if status_filter:
            agents = [a for a in agents if a["status"] == status_filter]
        
        agent_infos = [AgentInfo(**agent) for agent in agents]
        
        return APIResponse(
            data=agent_infos,
            message=f"Found {len(agent_infos)} agents"
        )
    
    @router.get("/{agent_id}", response_model=APIResponse)
    async def get_agent(
        agent_id: str,
        current_user: User = Depends(auth_deps['get_current_active_user'])
    ):
        agent = agent_registry.get_agent(agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )
        
        if current_user.tenant_id and agent.get("tenant_id") != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access agent from different tenant"
            )
        
        return APIResponse(
            data=AgentInfo(**agent),
            message="Agent retrieved successfully"
        )
    
    @router.put("/{agent_id}", response_model=APIResponse)
    async def update_agent(
        agent_id: str,
        request: AgentUpdateRequest,
        current_user: User = Depends(auth_deps['get_current_active_user'])
    ):
        agent = agent_registry.get_agent(agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )
        
        if current_user.tenant_id and agent.get("tenant_id") != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot update agent from different tenant"
            )
        
        updates = request.dict(exclude_unset=True)
        agent_registry.update_agent(agent_id, updates)
        
        updated_agent = agent_registry.get_agent(agent_id)
        return APIResponse(
            data=AgentInfo(**updated_agent),
            message="Agent updated successfully"
        )
    
    @router.delete("/{agent_id}", response_model=APIResponse)
    async def delete_agent(
        agent_id: str,
        current_user: User = Depends(auth_deps['get_current_active_user'])
    ):
        agent = agent_registry.get_agent(agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )
        
        if current_user.tenant_id and agent.get("tenant_id") != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete agent from different tenant"
            )
        
        agent_registry.delete_agent(agent_id)
        
        return APIResponse(
            message="Agent deleted successfully"
        )
    
    @router.post("/{agent_id}/execute", response_model=APIResponse)
    async def execute_command(
        agent_id: str,
        request: ExecutionRequest,
        current_user: User = Depends(auth_deps['get_current_active_user'])
    ):
        agent = agent_registry.get_agent(agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )
        
        if current_user.tenant_id and agent.get("tenant_id") != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot execute on agent from different tenant"
            )
        
        try:
            request.agent_id = agent_id
            execution_id = await agent_registry.execute_command(agent_id, request)
            
            return APIResponse(
                data={"execution_id": execution_id},
                message="Command execution started"
            )
        
        except Exception as e:
            logger.error(f"Failed to execute command: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to execute command"
            )
    
    @router.get("/{agent_id}/executions", response_model=APIResponse)
    async def get_agent_executions(
        agent_id: str,
        current_user: User = Depends(auth_deps['get_current_active_user'])
    ):
        agent = agent_registry.get_agent(agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found"
            )
        
        if current_user.tenant_id and agent.get("tenant_id") != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access executions from different tenant"
            )
        
        executions = agent_registry.list_executions(agent_id)
        execution_results = [ExecutionResult(**execution) for execution in executions]
        
        return APIResponse(
            data=execution_results,
            message=f"Found {len(execution_results)} executions"
        )
    
    @router.get("/executions/{execution_id}", response_model=APIResponse)
    async def get_execution_status(
        execution_id: str,
        current_user: User = Depends(auth_deps['get_current_active_user'])
    ):
        execution = agent_registry.get_execution(execution_id)
        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Execution not found"
            )
        
        agent = agent_registry.get_agent(execution["agent_id"])
        if current_user.tenant_id and agent and agent.get("tenant_id") != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access execution from different tenant"
            )
        
        return APIResponse(
            data=ExecutionResult(**execution),
            message="Execution status retrieved"
        )
    
    return router