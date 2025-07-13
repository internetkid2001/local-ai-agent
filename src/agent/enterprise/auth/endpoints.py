from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
import logging

from .jwt_manager import JWTManager
from .rbac import RBACManager, User, Resource, Permission
from .tenant_manager import TenantManager
from .middleware import create_auth_dependencies

logger = logging.getLogger(__name__)


class LoginRequest(BaseModel):
    username: str
    password: str
    tenant_id: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class UserCreateRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    tenant_id: Optional[str] = None
    roles: List[str] = []
    is_active: bool = True


class UserResponse(BaseModel):
    username: str
    email: str
    tenant_id: Optional[str]
    roles: List[str]
    is_active: bool
    is_superuser: bool
    created_at: Optional[str]
    last_login: Optional[str]


class UserUpdateRequest(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    tenant_id: Optional[str] = None
    roles: Optional[List[str]] = None
    is_active: Optional[bool] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


def create_auth_router(
    jwt_manager: JWTManager,
    rbac_manager: RBACManager,
    tenant_manager: TenantManager
) -> APIRouter:
    
    router = APIRouter(prefix="/auth", tags=["authentication"])
    auth_deps = create_auth_dependencies(jwt_manager, rbac_manager, tenant_manager)
    
    @router.post("/login", response_model=LoginResponse)
    async def login(request: LoginRequest):
        user = rbac_manager.get_user(request.username)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        stored_password = getattr(user, 'password_hash', None)
        if not stored_password or not jwt_manager.verify_password(request.password, stored_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        if request.tenant_id and user.tenant_id and user.tenant_id != request.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not authorized for this tenant"
            )
        
        tenant_id = request.tenant_id or user.tenant_id
        if tenant_id:
            tenant = tenant_manager.get_tenant(tenant_id)
            if not tenant or not tenant.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Tenant not found or inactive"
                )
        
        access_token = jwt_manager.create_access_token(
            subject=user.username,
            roles=user.roles,
            tenant_id=tenant_id
        )
        refresh_token = jwt_manager.create_refresh_token(
            subject=user.username,
            tenant_id=tenant_id
        )
        
        user.last_login = datetime.utcnow().isoformat()
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=86400,
            user={
                "username": user.username,
                "email": user.email,
                "roles": user.roles,
                "tenant_id": user.tenant_id
            }
        )

    @router.post("/refresh", response_model=LoginResponse)
    async def refresh_token(request: RefreshTokenRequest):
        try:
            payload = jwt_manager.verify_token(request.refresh_token)
            if payload.get("type") != "refresh":
                raise ValueError("Invalid token type")
            
            username = payload.get("sub")
            tenant_id = payload.get("tenant_id")
            
            user = rbac_manager.get_user(username)
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive"
                )
            
            access_token = jwt_manager.create_access_token(
                subject=user.username,
                roles=user.roles,
                tenant_id=tenant_id
            )
            
            new_refresh_token = jwt_manager.create_refresh_token(
                subject=user.username,
                tenant_id=tenant_id
            )
            
            return LoginResponse(
                access_token=access_token,
                refresh_token=new_refresh_token,
                expires_in=86400,
                user={
                    "username": user.username,
                    "email": user.email,
                    "roles": user.roles,
                    "tenant_id": user.tenant_id
                }
            )
        
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

    @router.post("/users", response_model=UserResponse)
    async def create_user(
        request: UserCreateRequest,
        current_user: User = Depends(auth_deps['get_current_active_user'])
    ):
        if not rbac_manager.check_permission(
            current_user.username, Resource.USER, Permission.WRITE, current_user.tenant_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to create users"
            )
        
        if rbac_manager.get_user(request.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        
        if request.tenant_id:
            tenant = tenant_manager.get_tenant(request.tenant_id)
            if not tenant or not tenant.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or inactive tenant"
                )
        
        password_hash = jwt_manager.hash_password(request.password)
        
        user = User(
            username=request.username,
            email=request.email,
            tenant_id=request.tenant_id,
            roles=request.roles,
            is_active=request.is_active,
            created_at=datetime.utcnow().isoformat()
        )
        
        setattr(user, 'password_hash', password_hash)
        
        if not rbac_manager.create_user(user):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user"
            )
        
        if request.tenant_id:
            tenant_manager.assign_user_to_tenant(request.username, request.tenant_id)
        
        return UserResponse(**user.__dict__)

    @router.get("/users/me", response_model=UserResponse)
    async def get_current_user_info(
        current_user: User = Depends(auth_deps['get_current_active_user'])
    ):
        return UserResponse(**current_user.__dict__)

    @router.get("/users", response_model=List[UserResponse])
    async def list_users(
        current_user: User = Depends(auth_deps['get_current_active_user'])
    ):
        if not rbac_manager.check_permission(
            current_user.username, Resource.USER, Permission.READ, current_user.tenant_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to list users"
            )
        
        users = rbac_manager.list_users(current_user.tenant_id)
        return [UserResponse(**user.__dict__) for user in users]

    @router.get("/users/{username}", response_model=UserResponse)
    async def get_user(
        username: str,
        current_user: User = Depends(auth_deps['get_current_active_user'])
    ):
        if not rbac_manager.check_permission(
            current_user.username, Resource.USER, Permission.READ, current_user.tenant_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to view users"
            )
        
        user = rbac_manager.get_user(username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if current_user.tenant_id and user.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access user from different tenant"
            )
        
        return UserResponse(**user.__dict__)

    @router.put("/users/{username}", response_model=UserResponse)
    async def update_user(
        username: str,
        request: UserUpdateRequest,
        current_user: User = Depends(auth_deps['get_current_active_user'])
    ):
        if not rbac_manager.check_permission(
            current_user.username, Resource.USER, Permission.WRITE, current_user.tenant_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to update users"
            )
        
        user = rbac_manager.get_user(username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if current_user.tenant_id and user.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot update user from different tenant"
            )
        
        update_data = request.dict(exclude_unset=True)
        
        if 'password' in update_data:
            update_data['password_hash'] = jwt_manager.hash_password(update_data.pop('password'))
        
        for key, value in update_data.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        return UserResponse(**user.__dict__)

    @router.delete("/users/{username}")
    async def delete_user(
        username: str,
        current_user: User = Depends(auth_deps['get_current_active_user'])
    ):
        if not rbac_manager.check_permission(
            current_user.username, Resource.USER, Permission.DELETE, current_user.tenant_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to delete users"
            )
        
        user = rbac_manager.get_user(username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if current_user.tenant_id and user.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete user from different tenant"
            )
        
        if username == current_user.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )
        
        del rbac_manager.users[username]
        tenant_manager.remove_user_from_tenant(username)
        
        return {"message": "User deleted successfully"}

    return router