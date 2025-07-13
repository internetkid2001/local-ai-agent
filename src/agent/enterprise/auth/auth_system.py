from typing import Optional
from fastapi import FastAPI
import logging

from .jwt_manager import JWTManager
from .rbac import RBACManager, User
from .tenant_manager import TenantManager
from .endpoints import create_auth_router
from .middleware import create_auth_dependencies

logger = logging.getLogger(__name__)


class EnterpriseAuthSystem:
    def __init__(self, secret_key: Optional[str] = None):
        self.jwt_manager = JWTManager(secret_key)
        self.rbac_manager = RBACManager()
        self.tenant_manager = TenantManager()
        self.auth_dependencies = create_auth_dependencies(
            self.jwt_manager, self.rbac_manager, self.tenant_manager
        )
        
        self._setup_default_admin()

    def _setup_default_admin(self):
        admin_user = User(
            username="admin",
            email="admin@localhost",
            roles=["superadmin"],
            is_active=True,
            is_superuser=True
        )
        
        default_password = "admin123"
        password_hash = self.jwt_manager.hash_password(default_password)
        setattr(admin_user, 'password_hash', password_hash)
        
        if not self.rbac_manager.get_user("admin"):
            self.rbac_manager.create_user(admin_user)
            logger.info("Default admin user created with username 'admin' and password 'admin123'")
            logger.warning("SECURITY: Please change the default admin password in production!")

    def setup_fastapi_app(self, app: FastAPI):
        auth_router = create_auth_router(
            self.jwt_manager, self.rbac_manager, self.tenant_manager
        )
        app.include_router(auth_router)
        logger.info("Enterprise authentication system initialized")

    def create_tenant_admin(self, tenant_id: str, username: str, email: str, password: str) -> bool:
        try:
            tenant = self.tenant_manager.get_tenant(tenant_id)
            if not tenant:
                logger.error(f"Tenant {tenant_id} not found")
                return False
            
            if self.rbac_manager.get_user(username):
                logger.error(f"User {username} already exists")
                return False
            
            password_hash = self.jwt_manager.hash_password(password)
            
            user = User(
                username=username,
                email=email,
                tenant_id=tenant_id,
                roles=["tenant_admin"],
                is_active=True
            )
            setattr(user, 'password_hash', password_hash)
            
            if self.rbac_manager.create_user(user):
                self.tenant_manager.assign_user_to_tenant(username, tenant_id)
                logger.info(f"Tenant admin {username} created for tenant {tenant_id}")
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Failed to create tenant admin: {str(e)}")
            return False

    def get_managers(self):
        return {
            'jwt_manager': self.jwt_manager,
            'rbac_manager': self.rbac_manager,
            'tenant_manager': self.tenant_manager,
            'auth_dependencies': self.auth_dependencies
        }