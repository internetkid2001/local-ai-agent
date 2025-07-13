from typing import Optional, List, Callable, Any
from functools import wraps
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

from .jwt_manager import JWTManager
from .rbac import RBACManager, Resource, Permission
from .tenant_manager import TenantManager

logger = logging.getLogger(__name__)

class AuthenticationMiddleware:
    def __init__(self, jwt_manager: JWTManager, rbac_manager: RBACManager, tenant_manager: TenantManager):
        self.jwt_manager = jwt_manager
        self.rbac_manager = rbac_manager
        self.tenant_manager = tenant_manager
        self.security = HTTPBearer()

    async def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
        try:
            token = credentials.credentials
            payload = self.jwt_manager.verify_token(token)
            username = payload.get("sub")
            
            if not username:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: no subject found"
                )
            
            user = self.rbac_manager.get_user(username)
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive"
                )
            
            return user
        
        except ValueError as e:
            logger.warning(f"Token validation failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )

    async def get_current_active_user(self, user = Depends(get_current_user)):
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        return user

    def require_permission(self, resource: Resource, permission: Permission):
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                user = kwargs.get('current_user')
                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication required"
                    )
                
                has_permission = self.rbac_manager.check_permission(
                    user.username, resource, permission, user.tenant_id
                )
                
                if not has_permission:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Insufficient permissions for {resource.value}:{permission.value}"
                    )
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator

    def require_roles(self, required_roles: List[str]):
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                user = kwargs.get('current_user')
                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication required"
                    )
                
                user_roles = set(user.roles)
                required_roles_set = set(required_roles)
                
                if not user_roles.intersection(required_roles_set):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Required roles: {required_roles}"
                    )
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator

    def require_tenant_access(self, func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get('current_user')
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if not user.tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User not assigned to any tenant"
                )
            
            tenant = self.tenant_manager.get_tenant(user.tenant_id)
            if not tenant or not tenant.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Tenant not found or inactive"
                )
            
            kwargs['tenant'] = tenant
            return await func(*args, **kwargs)
        return wrapper

    def require_feature_access(self, feature: str):
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                user = kwargs.get('current_user')
                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication required"
                    )
                
                if user.tenant_id:
                    has_access = self.tenant_manager.check_feature_access(user.tenant_id, feature)
                    if not has_access:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Feature '{feature}' not available for this tenant"
                        )
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator

    async def extract_tenant_from_request(self, request: Request) -> Optional[str]:
        tenant_id = None
        
        if hasattr(request.headers, 'x-tenant-id'):
            tenant_id = request.headers.get('x-tenant-id')
        
        if not tenant_id and hasattr(request, 'path_params'):
            tenant_id = request.path_params.get('tenant_id')
        
        if not tenant_id and hasattr(request, 'query_params'):
            tenant_id = request.query_params.get('tenant_id')
        
        if tenant_id:
            tenant = self.tenant_manager.get_tenant(tenant_id)
            if tenant and tenant.is_active:
                return tenant_id
        
        return None


def create_auth_dependencies(
    jwt_manager: JWTManager,
    rbac_manager: RBACManager,
    tenant_manager: TenantManager
):
    middleware = AuthenticationMiddleware(jwt_manager, rbac_manager, tenant_manager)
    
    return {
        'get_current_user': middleware.get_current_user,
        'get_current_active_user': middleware.get_current_active_user,
        'require_permission': middleware.require_permission,
        'require_roles': middleware.require_roles,
        'require_tenant_access': middleware.require_tenant_access,
        'require_feature_access': middleware.require_feature_access
    }