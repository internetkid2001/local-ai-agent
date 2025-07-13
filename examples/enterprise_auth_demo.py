#!/usr/bin/env python3

import asyncio
from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
import uvicorn
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent.enterprise.auth import EnterpriseAuthSystem, Resource, Permission


def create_demo_app():
    app = FastAPI(
        title="Enterprise Authentication Demo",
        description="Demo of the enterprise authentication system",
        version="1.0.0"
    )
    
    auth_system = EnterpriseAuthSystem()
    auth_system.setup_fastapi_app(app)
    
    managers = auth_system.get_managers()
    rbac_manager = managers['rbac_manager']
    tenant_manager = managers['tenant_manager']
    auth_deps = managers['auth_dependencies']
    
    tenant_id = tenant_manager.create_tenant(
        name="Demo Company",
        domain="demo.company.com",
        max_users=100
    )
    
    auth_system.create_tenant_admin(
        tenant_id=tenant_id,
        username="demo_admin",
        email="admin@demo.company.com",
        password="demo123"
    )
    
    @app.get("/")
    async def root():
        return {
            "message": "Enterprise Authentication Demo API",
            "endpoints": {
                "login": "POST /auth/login",
                "users": "GET /auth/users",
                "protected": "GET /protected",
                "admin_only": "GET /admin-only"
            },
            "demo_credentials": {
                "superadmin": {"username": "admin", "password": "admin123"},
                "tenant_admin": {"username": "demo_admin", "password": "demo123", "tenant_id": tenant_id}
            }
        }
    
    @app.get("/protected")
    async def protected_endpoint(
        current_user = Depends(auth_deps['get_current_active_user'])
    ):
        return {
            "message": "This is a protected endpoint",
            "user": {
                "username": current_user.username,
                "roles": current_user.roles,
                "tenant_id": current_user.tenant_id
            }
        }
    
    @app.get("/admin-only")
    async def admin_only_endpoint(
        current_user = Depends(auth_deps['get_current_active_user'])
    ):
        if not rbac_manager.check_permission(
            current_user.username, Resource.SYSTEM, Permission.ADMIN
        ):
            return JSONResponse(
                status_code=403,
                content={"detail": "Admin privileges required"}
            )
        
        return {
            "message": "This endpoint requires admin privileges",
            "user": current_user.username,
            "system_info": {
                "total_users": len(rbac_manager.list_users()),
                "total_tenants": len(tenant_manager.list_tenants())
            }
        }
    
    @app.get("/tenant-stats")
    async def tenant_stats(
        current_user = Depends(auth_deps['get_current_active_user'])
    ):
        if not current_user.tenant_id:
            return JSONResponse(
                status_code=400,
                content={"detail": "No tenant associated with user"}
            )
        
        stats = tenant_manager.get_tenant_stats(current_user.tenant_id)
        return {"tenant_stats": stats}
    
    return app


if __name__ == "__main__":
    app = create_demo_app()
    
    print("🚀 Starting Enterprise Authentication Demo")
    print("📖 API Documentation: http://localhost:8000/docs")
    print("🔐 Demo Credentials:")
    print("   Superadmin: admin / admin123")
    print("   Tenant Admin: demo_admin / demo123")
    print("")
    print("📝 Example Usage:")
    print("1. Login: POST /auth/login with credentials")
    print("2. Use returned token in Authorization header: Bearer <token>")
    print("3. Access protected endpoints")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)