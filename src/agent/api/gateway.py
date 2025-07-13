from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import logging
from typing import Optional

from ..enterprise.auth import EnterpriseAuthSystem
from .rest.agents import create_agents_router
from .rest.workflows import create_workflows_router
from .rest.mcp_servers import create_mcp_servers_router
from .graphql.endpoint import create_graphql_router
from .websocket.endpoint import create_websocket_route
from .middleware.rate_limiting import limiter, rate_limit_exceeded_handler

logger = logging.getLogger(__name__)


class APIGateway:
    def __init__(self, auth_system: Optional[EnterpriseAuthSystem] = None):
        self.app = FastAPI(
            title="Local AI Agent Enterprise API Gateway",
            description="Enterprise-grade API gateway for the Local AI Agent system",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        
        self.auth_system = auth_system or EnterpriseAuthSystem()
        self._setup_middleware()
        self._setup_routes()
        self._setup_error_handlers()
        
        logger.info("API Gateway initialized successfully")
    
    def _setup_middleware(self):
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        self.app.state.limiter = limiter
        self.app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    
    def _setup_routes(self):
        auth_deps = self.auth_system.get_managers()['auth_dependencies']
        
        @self.app.get("/")
        async def root():
            return {
                "name": "Local AI Agent Enterprise API Gateway",
                "version": "1.0.0",
                "status": "active",
                "endpoints": {
                    "authentication": "/auth/*",
                    "agents": "/api/v1/agents",
                    "workflows": "/api/v1/workflows",
                    "mcp_servers": "/api/v1/mcp-servers",
                    "graphql": "/graphql",
                    "websocket": "/ws",
                    "docs": "/docs"
                }
            }
        
        @self.app.get("/health")
        async def health_check():
            return {
                "status": "healthy",
                "timestamp": "2024-01-01T00:00:00Z"
            }
        
        self.auth_system.setup_fastapi_app(self.app)
        
        agents_router = create_agents_router(auth_deps)
        workflows_router = create_workflows_router(auth_deps)
        mcp_servers_router = create_mcp_servers_router(auth_deps)
        
        self.app.include_router(agents_router, prefix="/api/v1")
        self.app.include_router(workflows_router, prefix="/api/v1")
        self.app.include_router(mcp_servers_router, prefix="/api/v1")
        
        graphql_router = create_graphql_router(auth_deps, require_auth=True)
        self.app.include_router(graphql_router, prefix="/graphql")
        
        ws_route, ws_endpoint = create_websocket_route(
            self.auth_system.get_managers()['jwt_manager']
        )
        self.app.router.routes.append(ws_route)
        
        self.app.state.ws_endpoint = ws_endpoint
        self.app.state.agent_registry = getattr(agents_router, 'agent_registry', None)
        self.app.state.workflow_registry = getattr(workflows_router, 'workflow_registry', None)
    
    def _setup_error_handlers(self):
        @self.app.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException):
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "success": False,
                    "error": exc.detail,
                    "status_code": exc.status_code
                }
            )
        
        @self.app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            logger.error(f"Unhandled exception: {str(exc)}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "success": False,
                    "error": "Internal server error",
                    "status_code": 500
                }
            )
    
    def get_app(self) -> FastAPI:
        return self.app


def create_api_gateway(auth_system: Optional[EnterpriseAuthSystem] = None) -> FastAPI:
    gateway = APIGateway(auth_system)
    return gateway.get_app()