from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel
import uuid
from datetime import datetime
import logging

from ..models.base import APIResponse, WorkflowInfo, WorkflowStatus
from ...enterprise.auth import User, Resource, Permission

logger = logging.getLogger(__name__)


class WorkflowCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    steps: List[Dict[str, Any]] = []
    config: Optional[Dict[str, Any]] = {}
    auto_start: bool = False


class WorkflowUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    steps: Optional[List[Dict[str, Any]]] = None
    config: Optional[Dict[str, Any]] = None


class WorkflowExecuteRequest(BaseModel):
    parameters: Optional[Dict[str, Any]] = {}
    context: Optional[Dict[str, Any]] = {}


class WorkflowRegistry:
    def __init__(self):
        self.workflows: Dict[str, Dict[str, Any]] = {}
        self.executions: Dict[str, Dict[str, Any]] = {}
    
    def create_workflow(self, request: WorkflowCreateRequest, tenant_id: Optional[str], created_by: str) -> str:
        workflow_id = str(uuid.uuid4())
        
        workflow_data = {
            "id": workflow_id,
            "name": request.name,
            "description": request.description,
            "status": WorkflowStatus.PENDING,
            "steps": request.steps,
            "config": request.config or {},
            "created_at": datetime.utcnow(),
            "started_at": None,
            "completed_at": None,
            "tenant_id": tenant_id,
            "created_by": created_by
        }
        
        self.workflows[workflow_id] = workflow_data
        
        if request.auto_start:
            self.start_workflow(workflow_id)
        
        logger.info(f"Created workflow {workflow_id} for tenant {tenant_id}")
        return workflow_id
    
    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        return self.workflows.get(workflow_id)
    
    def list_workflows(self, tenant_id: Optional[str] = None, status_filter: Optional[WorkflowStatus] = None) -> List[Dict[str, Any]]:
        workflows = list(self.workflows.values())
        
        if tenant_id:
            workflows = [w for w in workflows if w.get("tenant_id") == tenant_id]
        
        if status_filter:
            workflows = [w for w in workflows if w["status"] == status_filter]
        
        return workflows
    
    def update_workflow(self, workflow_id: str, updates: Dict[str, Any]) -> bool:
        if workflow_id not in self.workflows:
            return False
        
        workflow = self.workflows[workflow_id]
        if workflow["status"] == WorkflowStatus.RUNNING:
            raise ValueError("Cannot update running workflow")
        
        self.workflows[workflow_id].update(updates)
        return True
    
    def delete_workflow(self, workflow_id: str) -> bool:
        if workflow_id in self.workflows:
            workflow = self.workflows[workflow_id]
            if workflow["status"] == WorkflowStatus.RUNNING:
                raise ValueError("Cannot delete running workflow")
            
            del self.workflows[workflow_id]
            return True
        return False
    
    def start_workflow(self, workflow_id: str) -> bool:
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return False
        
        if workflow["status"] in [WorkflowStatus.RUNNING]:
            raise ValueError("Workflow is already running")
        
        workflow["status"] = WorkflowStatus.RUNNING
        workflow["started_at"] = datetime.utcnow()
        
        return True
    
    def stop_workflow(self, workflow_id: str) -> bool:
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return False
        
        if workflow["status"] != WorkflowStatus.RUNNING:
            raise ValueError("Workflow is not running")
        
        workflow["status"] = WorkflowStatus.CANCELLED
        workflow["completed_at"] = datetime.utcnow()
        
        return True
    
    def complete_workflow(self, workflow_id: str, success: bool = True) -> bool:
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return False
        
        workflow["status"] = WorkflowStatus.COMPLETED if success else WorkflowStatus.FAILED
        workflow["completed_at"] = datetime.utcnow()
        
        return True


def create_workflows_router(auth_deps: Dict[str, Any]) -> APIRouter:
    router = APIRouter(prefix="/workflows", tags=["workflows"])
    workflow_registry = WorkflowRegistry()
    
    @router.post("/", response_model=APIResponse)
    async def create_workflow(
        request: WorkflowCreateRequest,
        current_user: User = Depends(auth_deps['get_current_active_user'])
    ):
        try:
            workflow_id = workflow_registry.create_workflow(
                request, current_user.tenant_id, current_user.username
            )
            
            workflow_data = workflow_registry.get_workflow(workflow_id)
            return APIResponse(
                data=WorkflowInfo(**workflow_data),
                message="Workflow created successfully"
            )
        
        except Exception as e:
            logger.error(f"Failed to create workflow: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create workflow"
            )
    
    @router.get("/", response_model=APIResponse)
    async def list_workflows(
        current_user: User = Depends(auth_deps['get_current_active_user']),
        status_filter: Optional[WorkflowStatus] = Query(None, alias="status")
    ):
        workflows = workflow_registry.list_workflows(current_user.tenant_id, status_filter)
        workflow_infos = [WorkflowInfo(**workflow) for workflow in workflows]
        
        return APIResponse(
            data=workflow_infos,
            message=f"Found {len(workflow_infos)} workflows"
        )
    
    @router.get("/{workflow_id}", response_model=APIResponse)
    async def get_workflow(
        workflow_id: str,
        current_user: User = Depends(auth_deps['get_current_active_user'])
    ):
        workflow = workflow_registry.get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        
        if current_user.tenant_id and workflow.get("tenant_id") != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access workflow from different tenant"
            )
        
        return APIResponse(
            data=WorkflowInfo(**workflow),
            message="Workflow retrieved successfully"
        )
    
    @router.put("/{workflow_id}", response_model=APIResponse)
    async def update_workflow(
        workflow_id: str,
        request: WorkflowUpdateRequest,
        current_user: User = Depends(auth_deps['get_current_active_user'])
    ):
        workflow = workflow_registry.get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        
        if current_user.tenant_id and workflow.get("tenant_id") != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot update workflow from different tenant"
            )
        
        try:
            updates = request.dict(exclude_unset=True)
            workflow_registry.update_workflow(workflow_id, updates)
            
            updated_workflow = workflow_registry.get_workflow(workflow_id)
            return APIResponse(
                data=WorkflowInfo(**updated_workflow),
                message="Workflow updated successfully"
            )
        
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    
    @router.delete("/{workflow_id}", response_model=APIResponse)
    async def delete_workflow(
        workflow_id: str,
        current_user: User = Depends(auth_deps['get_current_active_user'])
    ):
        workflow = workflow_registry.get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        
        if current_user.tenant_id and workflow.get("tenant_id") != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete workflow from different tenant"
            )
        
        try:
            workflow_registry.delete_workflow(workflow_id)
            return APIResponse(
                message="Workflow deleted successfully"
            )
        
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    
    @router.post("/{workflow_id}/start", response_model=APIResponse)
    async def start_workflow(
        workflow_id: str,
        current_user: User = Depends(auth_deps['get_current_active_user'])
    ):
        workflow = workflow_registry.get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        
        if current_user.tenant_id and workflow.get("tenant_id") != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot start workflow from different tenant"
            )
        
        try:
            workflow_registry.start_workflow(workflow_id)
            updated_workflow = workflow_registry.get_workflow(workflow_id)
            
            return APIResponse(
                data=WorkflowInfo(**updated_workflow),
                message="Workflow started successfully"
            )
        
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    
    @router.post("/{workflow_id}/stop", response_model=APIResponse)
    async def stop_workflow(
        workflow_id: str,
        current_user: User = Depends(auth_deps['get_current_active_user'])
    ):
        workflow = workflow_registry.get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        
        if current_user.tenant_id and workflow.get("tenant_id") != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot stop workflow from different tenant"
            )
        
        try:
            workflow_registry.stop_workflow(workflow_id)
            updated_workflow = workflow_registry.get_workflow(workflow_id)
            
            return APIResponse(
                data=WorkflowInfo(**updated_workflow),
                message="Workflow stopped successfully"
            )
        
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    
    return router