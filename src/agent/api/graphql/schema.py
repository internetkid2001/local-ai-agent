import strawberry
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio

from ..models.base import AgentStatus, WorkflowStatus


@strawberry.type
class Agent:
    id: str
    name: str
    description: Optional[str]
    status: AgentStatus
    capabilities: List[str]
    created_at: datetime
    last_activity: Optional[datetime]
    tenant_id: Optional[str]


@strawberry.type
class Workflow:
    id: str
    name: str
    description: Optional[str]
    status: WorkflowStatus
    steps: List[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_by: str
    tenant_id: Optional[str]


@strawberry.type
class Execution:
    id: str
    agent_id: str
    command: str
    status: str
    result: Optional[str]
    error: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
    execution_time: Optional[float]


@strawberry.input
class AgentInput:
    name: str
    description: Optional[str] = None
    capabilities: List[str] = strawberry.field(default_factory=list)


@strawberry.input
class WorkflowInput:
    name: str
    description: Optional[str] = None
    steps: List[str] = strawberry.field(default_factory=list)


@strawberry.input
class ExecuteCommandInput:
    agent_id: str
    command: str
    parameters: Optional[str] = None


class GraphQLContext:
    def __init__(self, user=None, tenant_id=None, agent_registry=None, workflow_registry=None):
        self.user = user
        self.tenant_id = tenant_id
        self.agent_registry = agent_registry
        self.workflow_registry = workflow_registry


@strawberry.type
class Query:
    @strawberry.field
    async def agents(self, info: strawberry.Info, status: Optional[AgentStatus] = None) -> List[Agent]:
        context: GraphQLContext = info.context
        if not context.agent_registry:
            return []
        
        agents = context.agent_registry.list_agents(context.tenant_id)
        
        if status:
            agents = [a for a in agents if a["status"] == status]
        
        return [
            Agent(
                id=a["id"],
                name=a["name"],
                description=a.get("description"),
                status=a["status"],
                capabilities=a.get("capabilities", []),
                created_at=a["created_at"],
                last_activity=a.get("last_activity"),
                tenant_id=a.get("tenant_id")
            )
            for a in agents
        ]
    
    @strawberry.field
    async def agent(self, info: strawberry.Info, id: str) -> Optional[Agent]:
        context: GraphQLContext = info.context
        if not context.agent_registry:
            return None
        
        agent_data = context.agent_registry.get_agent(id)
        if not agent_data:
            return None
        
        if context.tenant_id and agent_data.get("tenant_id") != context.tenant_id:
            return None
        
        return Agent(
            id=agent_data["id"],
            name=agent_data["name"],
            description=agent_data.get("description"),
            status=agent_data["status"],
            capabilities=agent_data.get("capabilities", []),
            created_at=agent_data["created_at"],
            last_activity=agent_data.get("last_activity"),
            tenant_id=agent_data.get("tenant_id")
        )
    
    @strawberry.field
    async def workflows(self, info: strawberry.Info, status: Optional[WorkflowStatus] = None) -> List[Workflow]:
        context: GraphQLContext = info.context
        if not context.workflow_registry:
            return []
        
        workflows = context.workflow_registry.list_workflows(context.tenant_id, status)
        
        return [
            Workflow(
                id=w["id"],
                name=w["name"],
                description=w.get("description"),
                status=w["status"],
                steps=[str(step) for step in w.get("steps", [])],
                created_at=w["created_at"],
                started_at=w.get("started_at"),
                completed_at=w.get("completed_at"),
                created_by=w["created_by"],
                tenant_id=w.get("tenant_id")
            )
            for w in workflows
        ]
    
    @strawberry.field
    async def workflow(self, info: strawberry.Info, id: str) -> Optional[Workflow]:
        context: GraphQLContext = info.context
        if not context.workflow_registry:
            return None
        
        workflow_data = context.workflow_registry.get_workflow(id)
        if not workflow_data:
            return None
        
        if context.tenant_id and workflow_data.get("tenant_id") != context.tenant_id:
            return None
        
        return Workflow(
            id=workflow_data["id"],
            name=workflow_data["name"],
            description=workflow_data.get("description"),
            status=workflow_data["status"],
            steps=[str(step) for step in workflow_data.get("steps", [])],
            created_at=workflow_data["created_at"],
            started_at=workflow_data.get("started_at"),
            completed_at=workflow_data.get("completed_at"),
            created_by=workflow_data["created_by"],
            tenant_id=workflow_data.get("tenant_id")
        )
    
    @strawberry.field
    async def executions(self, info: strawberry.Info, agent_id: Optional[str] = None) -> List[Execution]:
        context: GraphQLContext = info.context
        if not context.agent_registry:
            return []
        
        executions = context.agent_registry.list_executions(agent_id)
        
        agent_executions = []
        for e in executions:
            if agent_id:
                agent_data = context.agent_registry.get_agent(e["agent_id"])
                if context.tenant_id and agent_data and agent_data.get("tenant_id") != context.tenant_id:
                    continue
            
            agent_executions.append(
                Execution(
                    id=e["id"],
                    agent_id=e["agent_id"],
                    command=e["command"],
                    status=e["status"],
                    result=str(e.get("result")) if e.get("result") else None,
                    error=e.get("error"),
                    started_at=e["started_at"],
                    completed_at=e.get("completed_at"),
                    execution_time=e.get("execution_time")
                )
            )
        
        return agent_executions


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_agent(self, info: strawberry.Info, input: AgentInput) -> Optional[Agent]:
        context: GraphQLContext = info.context
        if not context.agent_registry or not context.user:
            return None
        
        from ..rest.agents import AgentCreateRequest
        request = AgentCreateRequest(
            name=input.name,
            description=input.description,
            capabilities=input.capabilities
        )
        
        agent_id = context.agent_registry.create_agent(
            request, context.tenant_id, context.user.username
        )
        
        agent_data = context.agent_registry.get_agent(agent_id)
        return Agent(
            id=agent_data["id"],
            name=agent_data["name"],
            description=agent_data.get("description"),
            status=agent_data["status"],
            capabilities=agent_data.get("capabilities", []),
            created_at=agent_data["created_at"],
            last_activity=agent_data.get("last_activity"),
            tenant_id=agent_data.get("tenant_id")
        )
    
    @strawberry.mutation
    async def create_workflow(self, info: strawberry.Info, input: WorkflowInput) -> Optional[Workflow]:
        context: GraphQLContext = info.context
        if not context.workflow_registry or not context.user:
            return None
        
        from ..rest.workflows import WorkflowCreateRequest
        request = WorkflowCreateRequest(
            name=input.name,
            description=input.description,
            steps=[{"step": step} for step in input.steps]
        )
        
        workflow_id = context.workflow_registry.create_workflow(
            request, context.tenant_id, context.user.username
        )
        
        workflow_data = context.workflow_registry.get_workflow(workflow_id)
        return Workflow(
            id=workflow_data["id"],
            name=workflow_data["name"],
            description=workflow_data.get("description"),
            status=workflow_data["status"],
            steps=[str(step) for step in workflow_data.get("steps", [])],
            created_at=workflow_data["created_at"],
            started_at=workflow_data.get("started_at"),
            completed_at=workflow_data.get("completed_at"),
            created_by=workflow_data["created_by"],
            tenant_id=workflow_data.get("tenant_id")
        )
    
    @strawberry.mutation
    async def execute_command(self, info: strawberry.Info, input: ExecuteCommandInput) -> Optional[Execution]:
        context: GraphQLContext = info.context
        if not context.agent_registry:
            return None
        
        agent_data = context.agent_registry.get_agent(input.agent_id)
        if not agent_data:
            return None
        
        if context.tenant_id and agent_data.get("tenant_id") != context.tenant_id:
            return None
        
        from ..rest.agents import ExecutionRequest
        import json
        
        parameters = {}
        if input.parameters:
            try:
                parameters = json.loads(input.parameters)
            except json.JSONDecodeError:
                parameters = {"raw": input.parameters}
        
        request = ExecutionRequest(
            agent_id=input.agent_id,
            command=input.command,
            parameters=parameters
        )
        
        execution_id = await context.agent_registry.execute_command(input.agent_id, request)
        
        await asyncio.sleep(0.1)
        
        execution_data = context.agent_registry.get_execution(execution_id)
        return Execution(
            id=execution_data["id"],
            agent_id=execution_data["agent_id"],
            command=execution_data["command"],
            status=execution_data["status"],
            result=str(execution_data.get("result")) if execution_data.get("result") else None,
            error=execution_data.get("error"),
            started_at=execution_data["started_at"],
            completed_at=execution_data.get("completed_at"),
            execution_time=execution_data.get("execution_time")
        )
    
    @strawberry.mutation
    async def start_workflow(self, info: strawberry.Info, workflow_id: str) -> Optional[Workflow]:
        context: GraphQLContext = info.context
        if not context.workflow_registry:
            return None
        
        workflow_data = context.workflow_registry.get_workflow(workflow_id)
        if not workflow_data:
            return None
        
        if context.tenant_id and workflow_data.get("tenant_id") != context.tenant_id:
            return None
        
        context.workflow_registry.start_workflow(workflow_id)
        
        updated_workflow = context.workflow_registry.get_workflow(workflow_id)
        return Workflow(
            id=updated_workflow["id"],
            name=updated_workflow["name"],
            description=updated_workflow.get("description"),
            status=updated_workflow["status"],
            steps=[str(step) for step in updated_workflow.get("steps", [])],
            created_at=updated_workflow["created_at"],
            started_at=updated_workflow.get("started_at"),
            completed_at=updated_workflow.get("completed_at"),
            created_by=updated_workflow["created_by"],
            tenant_id=updated_workflow.get("tenant_id")
        )


schema = strawberry.Schema(query=Query, mutation=Mutation)