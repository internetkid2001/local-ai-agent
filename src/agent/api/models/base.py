from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class APIResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None
    errors: Optional[List[str]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    BUSY = "busy"
    ERROR = "error"
    STOPPED = "stopped"


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentInfo(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    status: AgentStatus
    capabilities: List[str] = []
    created_at: datetime
    last_activity: Optional[datetime] = None
    tenant_id: Optional[str] = None


class WorkflowInfo(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    status: WorkflowStatus
    steps: List[Dict[str, Any]] = []
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_by: str
    tenant_id: Optional[str] = None


class MCPServerInfo(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    url: str
    status: str
    capabilities: List[str] = []
    config: Dict[str, Any] = {}
    created_at: datetime
    tenant_id: Optional[str] = None


class ExecutionRequest(BaseModel):
    agent_id: str
    command: str
    parameters: Optional[Dict[str, Any]] = {}
    context: Optional[Dict[str, Any]] = {}
    timeout: Optional[int] = 300


class ExecutionResult(BaseModel):
    id: str
    agent_id: str
    command: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    execution_time: Optional[float] = None