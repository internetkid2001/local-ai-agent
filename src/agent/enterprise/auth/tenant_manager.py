from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
import uuid


@dataclass
class TenantConfig:
    tenant_id: str
    name: str
    domain: Optional[str] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    max_users: Optional[int] = None
    max_agents: Optional[int] = None
    allowed_features: Set[str] = field(default_factory=set)
    custom_settings: Dict[str, any] = field(default_factory=dict)


@dataclass
class TenantIsolation:
    tenant_id: str
    database_prefix: Optional[str] = None
    storage_bucket: Optional[str] = None
    resource_limits: Dict[str, int] = field(default_factory=dict)
    network_policies: List[str] = field(default_factory=list)


class TenantManager:
    def __init__(self):
        self.tenants: Dict[str, TenantConfig] = {}
        self.tenant_isolation: Dict[str, TenantIsolation] = {}
        self.user_tenant_mapping: Dict[str, str] = {}

    def create_tenant(
        self,
        name: str,
        domain: Optional[str] = None,
        max_users: Optional[int] = None,
        max_agents: Optional[int] = None,
        allowed_features: Optional[Set[str]] = None
    ) -> str:
        tenant_id = str(uuid.uuid4())
        
        tenant_config = TenantConfig(
            tenant_id=tenant_id,
            name=name,
            domain=domain,
            max_users=max_users,
            max_agents=max_agents,
            allowed_features=allowed_features or set()
        )
        
        tenant_isolation = TenantIsolation(
            tenant_id=tenant_id,
            database_prefix=f"tenant_{tenant_id}",
            storage_bucket=f"tenant-{tenant_id}-storage"
        )
        
        self.tenants[tenant_id] = tenant_config
        self.tenant_isolation[tenant_id] = tenant_isolation
        
        return tenant_id

    def get_tenant(self, tenant_id: str) -> Optional[TenantConfig]:
        return self.tenants.get(tenant_id)

    def get_tenant_by_domain(self, domain: str) -> Optional[TenantConfig]:
        for tenant in self.tenants.values():
            if tenant.domain == domain:
                return tenant
        return None

    def update_tenant(self, tenant_id: str, **kwargs) -> bool:
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False
        
        for key, value in kwargs.items():
            if hasattr(tenant, key):
                setattr(tenant, key, value)
        
        return True

    def deactivate_tenant(self, tenant_id: str) -> bool:
        tenant = self.get_tenant(tenant_id)
        if tenant:
            tenant.is_active = False
            return True
        return False

    def assign_user_to_tenant(self, username: str, tenant_id: str) -> bool:
        tenant = self.get_tenant(tenant_id)
        if not tenant or not tenant.is_active:
            return False
        
        if tenant.max_users:
            current_users = len([u for u, t in self.user_tenant_mapping.items() if t == tenant_id])
            if current_users >= tenant.max_users:
                return False
        
        self.user_tenant_mapping[username] = tenant_id
        return True

    def get_user_tenant(self, username: str) -> Optional[str]:
        return self.user_tenant_mapping.get(username)

    def remove_user_from_tenant(self, username: str) -> bool:
        if username in self.user_tenant_mapping:
            del self.user_tenant_mapping[username]
            return True
        return False

    def get_tenant_users(self, tenant_id: str) -> List[str]:
        return [username for username, tid in self.user_tenant_mapping.items() if tid == tenant_id]

    def get_tenant_isolation(self, tenant_id: str) -> Optional[TenantIsolation]:
        return self.tenant_isolation.get(tenant_id)

    def set_resource_limit(self, tenant_id: str, resource: str, limit: int) -> bool:
        isolation = self.get_tenant_isolation(tenant_id)
        if isolation:
            isolation.resource_limits[resource] = limit
            return True
        return False

    def check_resource_limit(self, tenant_id: str, resource: str, current_usage: int) -> bool:
        isolation = self.get_tenant_isolation(tenant_id)
        if not isolation:
            return True
        
        limit = isolation.resource_limits.get(resource)
        if limit is None:
            return True
        
        return current_usage < limit

    def check_feature_access(self, tenant_id: str, feature: str) -> bool:
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False
        
        return feature in tenant.allowed_features or len(tenant.allowed_features) == 0

    def list_tenants(self, active_only: bool = True) -> List[TenantConfig]:
        tenants = list(self.tenants.values())
        if active_only:
            tenants = [t for t in tenants if t.is_active]
        return tenants

    def get_tenant_stats(self, tenant_id: str) -> Optional[Dict[str, any]]:
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return None
        
        users = self.get_tenant_users(tenant_id)
        
        return {
            "tenant_id": tenant_id,
            "name": tenant.name,
            "user_count": len(users),
            "max_users": tenant.max_users,
            "is_active": tenant.is_active,
            "created_at": tenant.created_at.isoformat(),
            "allowed_features": list(tenant.allowed_features)
        }