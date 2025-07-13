#!/usr/bin/env python3

import asyncio
import uvicorn
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent.enterprise.auth import EnterpriseAuthSystem
from src.agent.api.gateway import create_api_gateway


def create_demo_gateway():
    auth_system = EnterpriseAuthSystem()
    
    tenant_id = auth_system.tenant_manager.create_tenant(
        name="Demo Enterprise",
        domain="demo.enterprise.com",
        max_users=1000,
        allowed_features={"agents", "workflows", "mcp_servers", "graphql", "websockets"}
    )
    
    auth_system.create_tenant_admin(
        tenant_id=tenant_id,
        username="enterprise_admin",
        email="admin@demo.enterprise.com",
        password="enterprise123"
    )
    
    from src.agent.enterprise.auth.rbac import User
    
    demo_user = User(
        username="demo_user",
        email="user@demo.enterprise.com",
        tenant_id=tenant_id,
        roles=["agent_operator", "workflow_designer"],
        is_active=True
    )
    
    password_hash = auth_system.jwt_manager.hash_password("demo123")
    setattr(demo_user, 'password_hash', password_hash)
    
    auth_system.rbac_manager.create_user(demo_user)
    auth_system.tenant_manager.assign_user_to_tenant("demo_user", tenant_id)
    
    app = create_api_gateway(auth_system)
    
    return app, tenant_id


if __name__ == "__main__":
    app, demo_tenant_id = create_demo_gateway()
    
    print("🚀 Starting Enterprise API Gateway Demo")
    print("=" * 60)
    print("")
    print("📖 API Documentation:")
    print("   • OpenAPI Docs: http://localhost:8000/docs")
    print("   • ReDoc: http://localhost:8000/redoc")
    print("")
    print("🔐 Demo Credentials:")
    print("   • Superadmin: admin / admin123")
    print("   • Enterprise Admin: enterprise_admin / enterprise123")
    print("   • Demo User: demo_user / demo123")
    print(f"   • Demo Tenant ID: {demo_tenant_id}")
    print("")
    print("🌐 Available Endpoints:")
    print("   • REST API: http://localhost:8000/api/v1/")
    print("     - Agents: /api/v1/agents")
    print("     - Workflows: /api/v1/workflows")
    print("     - MCP Servers: /api/v1/mcp-servers")
    print("   • GraphQL: http://localhost:8000/graphql")
    print("   • WebSocket: ws://localhost:8000/ws?token=<jwt_token>")
    print("   • Authentication: http://localhost:8000/auth/")
    print("")
    print("📝 Example Usage:")
    print("1. Login: POST /auth/login")
    print("   {\"username\": \"demo_user\", \"password\": \"demo123\"}")
    print("")
    print("2. Create Agent: POST /api/v1/agents")
    print("   Authorization: Bearer <token>")
    print("   {\"name\": \"Demo Agent\", \"capabilities\": [\"text_processing\"]}")
    print("")
    print("3. GraphQL Query: POST /graphql")
    print("   query { agents { id name status } }")
    print("")
    print("4. WebSocket Connection:")
    print("   ws://localhost:8000/ws?token=<jwt_token>")
    print("   Send: {\"type\": \"subscribe\", \"topic\": \"agent_updates\"}")
    print("")
    print("🔧 Features Included:")
    print("   ✅ JWT Authentication with RBAC")
    print("   ✅ Multi-tenant isolation")
    print("   ✅ REST API with OpenAPI docs")
    print("   ✅ GraphQL API with GraphiQL")
    print("   ✅ Real-time WebSocket connections")
    print("   ✅ Rate limiting and throttling")
    print("   ✅ CORS support")
    print("   ✅ Error handling")
    print("   ✅ Request/response validation")
    print("")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")