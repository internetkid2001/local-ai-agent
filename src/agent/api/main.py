"""
Main FastAPI Application with Authentication Integration

This module creates the main FastAPI application that integrates
the enterprise authentication system with the agent API endpoints.

Author: Claude Code
Date: 2025-07-14
Session: 4.5
"""

import logging
from typing import Dict, Any
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..enterprise.auth.auth_system import AuthSystem
from ..enterprise.auth.endpoints import create_auth_router
from ..enterprise.auth.middleware import create_auth_dependencies
from ..core.agent import Agent, AgentConfig, create_basic_agent_config

logger = logging.getLogger(__name__)


def create_main_app(agent_config: AgentConfig = None) -> FastAPI:
    """Create the main FastAPI application with authentication"""
    
    app = FastAPI(
        title="Local AI Agent API",
        description="Enterprise-grade Local AI Agent with Authentication",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize authentication system
    auth_system = AuthSystem()
    
    # Create authentication dependencies
    auth_deps = create_auth_dependencies(
        auth_system.jwt_manager,
        auth_system.rbac_manager,
        auth_system.tenant_manager
    )
    
    # Initialize agent
    agent = None
    if agent_config is None:
        agent_config = create_basic_agent_config()
    
    @app.on_event("startup")
    async def startup_event():
        nonlocal agent
        # Initialize authentication system
        await auth_system.initialize()
        logger.info("Authentication system initialized")
        
        # Initialize agent
        if agent_config:
            agent = Agent(agent_config)
            await agent.initialize()
            logger.info("Agent initialized")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        nonlocal agent
        if agent:
            await agent.shutdown()
            logger.info("Agent shutdown complete")
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "auth_initialized": auth_system.is_initialized(),
            "agent_initialized": agent is not None and agent._initialized if agent else False,
            "timestamp": "2025-07-14"
        }
    
    # Protected agent endpoint for testing
    @app.get("/agent/status")
    async def get_agent_status(
        current_user: Dict[str, Any] = Depends(auth_deps.get_current_user)
    ):
        """Get agent status - requires authentication"""
        if not agent or not agent._initialized:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Agent not available"
            )
        
        status_info = agent.get_status()
        status_info["user"] = current_user["username"]
        return status_info
    
    # Include authentication router
    auth_router = create_auth_router(auth_system)
    app.include_router(auth_router, prefix="/auth", tags=["authentication"])
    
    return app


def create_app() -> FastAPI:
    """Factory function to create the application"""
    return create_main_app()


# For direct execution
if __name__ == "__main__":
    import uvicorn
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    app = create_app()
    
    logger.info("Starting Local AI Agent API Server...")
    logger.info("API Documentation: http://localhost:8000/docs")
    logger.info("Alternative Docs: http://localhost:8000/redoc")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )