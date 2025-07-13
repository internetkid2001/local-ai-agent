from enum import Enum
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field
from abc import ABC, abstractmethod


class Permission(Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"
    ADMIN = "admin"


class Resource(Enum):
    AGENT = "agent"
    MCP_SERVER = "mcp_server"
    WORKFLOW = "workflow"
    USER = "user"
    TENANT = "tenant"
    SYSTEM = "system"
    API = "api"


@dataclass
class Role:
    name: str
    permissions: Dict[Resource, Set[Permission]] = field(default_factory=dict)
    description: Optional[str] = None
    is_system_role: bool = False

    def add_permission(self, resource: Resource, permission: Permission):
        if resource not in self.permissions:
            self.permissions[resource] = set()
        self.permissions[resource].add(permission)

    def remove_permission(self, resource: Resource, permission: Permission):
        if resource in self.permissions:
            self.permissions[resource].discard(permission)
            if not self.permissions[resource]:
                del self.permissions[resource]

    def has_permission(self, resource: Resource, permission: Permission) -> bool:
        return resource in self.permissions and permission in self.permissions[resource]

    def has_admin_permission(self, resource: Resource) -> bool:
        return self.has_permission(resource, Permission.ADMIN)


@dataclass
class User:
    username: str
    email: str
    tenant_id: Optional[str] = None
    roles: List[str] = field(default_factory=list)
    is_active: bool = True
    is_superuser: bool = False
    created_at: Optional[str] = None
    last_login: Optional[str] = None


class RBACManager:
    def __init__(self):
        self.roles: Dict[str, Role] = {}
        self.users: Dict[str, User] = {}
        self._initialize_default_roles()

    def _initialize_default_roles(self):
        superadmin = Role(
            name="superadmin",
            description="Full system access across all tenants",
            is_system_role=True
        )
        for resource in Resource:
            superadmin.add_permission(resource, Permission.ADMIN)
        
        tenant_admin = Role(
            name="tenant_admin",
            description="Full access within tenant scope"
        )
        for resource in [Resource.AGENT, Resource.MCP_SERVER, Resource.WORKFLOW, Resource.USER]:
            tenant_admin.add_permission(resource, Permission.ADMIN)
        
        agent_operator = Role(
            name="agent_operator",
            description="Can operate and configure agents"
        )
        agent_operator.add_permission(Resource.AGENT, Permission.READ)
        agent_operator.add_permission(Resource.AGENT, Permission.WRITE)
        agent_operator.add_permission(Resource.AGENT, Permission.EXECUTE)
        agent_operator.add_permission(Resource.MCP_SERVER, Permission.READ)
        agent_operator.add_permission(Resource.WORKFLOW, Permission.READ)
        agent_operator.add_permission(Resource.WORKFLOW, Permission.EXECUTE)
        
        readonly_user = Role(
            name="readonly_user",
            description="Read-only access to resources"
        )
        for resource in [Resource.AGENT, Resource.MCP_SERVER, Resource.WORKFLOW]:
            readonly_user.add_permission(resource, Permission.READ)
        
        workflow_designer = Role(
            name="workflow_designer",
            description="Can design and manage workflows"
        )
        workflow_designer.add_permission(Resource.WORKFLOW, Permission.READ)
        workflow_designer.add_permission(Resource.WORKFLOW, Permission.WRITE)
        workflow_designer.add_permission(Resource.WORKFLOW, Permission.EXECUTE)
        workflow_designer.add_permission(Resource.AGENT, Permission.READ)
        workflow_designer.add_permission(Resource.MCP_SERVER, Permission.READ)
        
        self.roles.update({
            "superadmin": superadmin,
            "tenant_admin": tenant_admin,
            "agent_operator": agent_operator,
            "readonly_user": readonly_user,
            "workflow_designer": workflow_designer
        })

    def create_role(self, role: Role) -> bool:
        if role.name in self.roles:
            return False
        self.roles[role.name] = role
        return True

    def get_role(self, role_name: str) -> Optional[Role]:
        return self.roles.get(role_name)

    def delete_role(self, role_name: str) -> bool:
        if role_name in self.roles and not self.roles[role_name].is_system_role:
            del self.roles[role_name]
            return True
        return False

    def create_user(self, user: User) -> bool:
        if user.username in self.users:
            return False
        self.users[user.username] = user
        return True

    def get_user(self, username: str) -> Optional[User]:
        return self.users.get(username)

    def assign_role_to_user(self, username: str, role_name: str) -> bool:
        user = self.get_user(username)
        role = self.get_role(role_name)
        
        if user and role and role_name not in user.roles:
            user.roles.append(role_name)
            return True
        return False

    def remove_role_from_user(self, username: str, role_name: str) -> bool:
        user = self.get_user(username)
        if user and role_name in user.roles:
            user.roles.remove(role_name)
            return True
        return False

    def check_permission(
        self, 
        username: str, 
        resource: Resource, 
        permission: Permission,
        tenant_id: Optional[str] = None
    ) -> bool:
        user = self.get_user(username)
        if not user or not user.is_active:
            return False
        
        if user.is_superuser:
            return True
        
        if tenant_id and user.tenant_id and user.tenant_id != tenant_id:
            return False
        
        for role_name in user.roles:
            role = self.get_role(role_name)
            if role and role.has_permission(resource, permission):
                return True
            if role and role.has_admin_permission(resource):
                return True
        
        return False

    def get_user_permissions(self, username: str) -> Dict[Resource, Set[Permission]]:
        user = self.get_user(username)
        if not user:
            return {}
        
        all_permissions: Dict[Resource, Set[Permission]] = {}
        
        for role_name in user.roles:
            role = self.get_role(role_name)
            if role:
                for resource, permissions in role.permissions.items():
                    if resource not in all_permissions:
                        all_permissions[resource] = set()
                    all_permissions[resource].update(permissions)
        
        return all_permissions

    def list_roles(self, include_system: bool = True) -> List[Role]:
        if include_system:
            return list(self.roles.values())
        return [role for role in self.roles.values() if not role.is_system_role]

    def list_users(self, tenant_id: Optional[str] = None) -> List[User]:
        if tenant_id:
            return [user for user in self.users.values() if user.tenant_id == tenant_id]
        return list(self.users.values())