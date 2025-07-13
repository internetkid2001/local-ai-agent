from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel
import uuid
from datetime import datetime
import logging

from ..models.base import APIResponse, MCPServerInfo
from ...enterprise.auth import User, Resource, Permission

logger = logging.getLogger(__name__)


class MCPServerCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    url: str
    capabilities: List[str] = []
    config: Optional[Dict[str, Any]] = {}


class MCPServerUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    capabilities: Optional[List[str]] = None
    config: Optional[Dict[str, Any]] = None


class MCPServerRegistry:
    def __init__(self):
        self.servers: Dict[str, Dict[str, Any]] = {}
    
    def create_server(self, request: MCPServerCreateRequest, tenant_id: Optional[str], created_by: str) -> str:
        server_id = str(uuid.uuid4())
        
        server_data = {
            "id": server_id,
            "name": request.name,
            "description": request.description,
            "url": request.url,
            "status": "inactive",
            "capabilities": request.capabilities,
            "config": request.config or {},
            "created_at": datetime.utcnow(),
            "tenant_id": tenant_id,
            "created_by": created_by
        }
        
        self.servers[server_id] = server_data
        logger.info(f"Created MCP server {server_id} for tenant {tenant_id}")
        return server_id
    
    def get_server(self, server_id: str) -> Optional[Dict[str, Any]]:
        return self.servers.get(server_id)
    
    def list_servers(self, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        servers = list(self.servers.values())
        if tenant_id:
            servers = [s for s in servers if s.get("tenant_id") == tenant_id]
        return servers
    
    def update_server(self, server_id: str, updates: Dict[str, Any]) -> bool:
        if server_id not in self.servers:
            return False
        
        self.servers[server_id].update(updates)
        return True
    
    def delete_server(self, server_id: str) -> bool:
        if server_id in self.servers:
            del self.servers[server_id]
            return True
        return False
    
    def activate_server(self, server_id: str) -> bool:
        server = self.get_server(server_id)
        if not server:
            return False
        
        server["status"] = "active"
        return True
    
    def deactivate_server(self, server_id: str) -> bool:
        server = self.get_server(server_id)
        if not server:
            return False
        
        server["status"] = "inactive"
        return True


def create_mcp_servers_router(auth_deps: Dict[str, Any]) -> APIRouter:
    router = APIRouter(prefix="/mcp-servers", tags=["mcp-servers"])
    server_registry = MCPServerRegistry()
    
    @router.post("/", response_model=APIResponse)
    async def create_mcp_server(
        request: MCPServerCreateRequest,
        current_user: User = Depends(auth_deps['get_current_active_user'])
    ):
        try:
            server_id = server_registry.create_server(
                request, current_user.tenant_id, current_user.username
            )
            
            server_data = server_registry.get_server(server_id)
            return APIResponse(
                data=MCPServerInfo(**server_data),
                message="MCP server created successfully"
            )
        
        except Exception as e:
            logger.error(f"Failed to create MCP server: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create MCP server"
            )
    
    @router.get("/", response_model=APIResponse)
    async def list_mcp_servers(
        current_user: User = Depends(auth_deps['get_current_active_user']),
        status_filter: Optional[str] = Query(None, alias="status")
    ):
        servers = server_registry.list_servers(current_user.tenant_id)
        
        if status_filter:
            servers = [s for s in servers if s["status"] == status_filter]
        
        server_infos = [MCPServerInfo(**server) for server in servers]
        
        return APIResponse(
            data=server_infos,
            message=f"Found {len(server_infos)} MCP servers"
        )
    
    @router.get("/{server_id}", response_model=APIResponse)
    async def get_mcp_server(
        server_id: str,
        current_user: User = Depends(auth_deps['get_current_active_user'])
    ):
        server = server_registry.get_server(server_id)
        if not server:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MCP server not found"
            )
        
        if current_user.tenant_id and server.get("tenant_id") != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access MCP server from different tenant"
            )
        
        return APIResponse(
            data=MCPServerInfo(**server),
            message="MCP server retrieved successfully"
        )
    
    @router.put("/{server_id}", response_model=APIResponse)
    async def update_mcp_server(
        server_id: str,
        request: MCPServerUpdateRequest,
        current_user: User = Depends(auth_deps['get_current_active_user'])
    ):
        server = server_registry.get_server(server_id)
        if not server:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MCP server not found"
            )
        
        if current_user.tenant_id and server.get("tenant_id") != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot update MCP server from different tenant"
            )
        
        updates = request.dict(exclude_unset=True)
        server_registry.update_server(server_id, updates)
        
        updated_server = server_registry.get_server(server_id)
        return APIResponse(
            data=MCPServerInfo(**updated_server),
            message="MCP server updated successfully"
        )
    
    @router.delete("/{server_id}", response_model=APIResponse)
    async def delete_mcp_server(
        server_id: str,
        current_user: User = Depends(auth_deps['get_current_active_user'])
    ):
        server = server_registry.get_server(server_id)
        if not server:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MCP server not found"
            )
        
        if current_user.tenant_id and server.get("tenant_id") != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete MCP server from different tenant"
            )
        
        server_registry.delete_server(server_id)
        
        return APIResponse(
            message="MCP server deleted successfully"
        )
    
    @router.post("/{server_id}/activate", response_model=APIResponse)
    async def activate_mcp_server(
        server_id: str,
        current_user: User = Depends(auth_deps['get_current_active_user'])
    ):
        server = server_registry.get_server(server_id)
        if not server:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MCP server not found"
            )
        
        if current_user.tenant_id and server.get("tenant_id") != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot activate MCP server from different tenant"
            )
        
        server_registry.activate_server(server_id)
        updated_server = server_registry.get_server(server_id)
        
        return APIResponse(
            data=MCPServerInfo(**updated_server),
            message="MCP server activated successfully"
        )
    
    @router.post("/{server_id}/deactivate", response_model=APIResponse)
    async def deactivate_mcp_server(
        server_id: str,
        current_user: User = Depends(auth_deps['get_current_active_user'])
    ):
        server = server_registry.get_server(server_id)
        if not server:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MCP server not found"
            )
        
        if current_user.tenant_id and server.get("tenant_id") != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot deactivate MCP server from different tenant"
            )
        
        server_registry.deactivate_server(server_id)
        updated_server = server_registry.get_server(server_id)
        
        return APIResponse(
            data=MCPServerInfo(**updated_server),
            message="MCP server deactivated successfully"
        )
    
    return router