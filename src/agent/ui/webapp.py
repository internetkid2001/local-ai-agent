"""
Web Application

FastAPI-based web application for the Local AI Agent UI.

Author: Claude Code
Date: 2025-07-13
Session: 4.4
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from ..core.agent import Agent, AgentConfig, AgentRequest, AgentMode, AgentCapability
from .api import APIRouter

logger = logging.getLogger(__name__)


@dataclass
class WebUIConfig:
    """Configuration for web UI"""
    host: str = "localhost"
    port: int = 8080
    debug: bool = False
    agent_config: Optional[AgentConfig] = None
    static_dir: Optional[str] = None
    templates_dir: Optional[str] = None


class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connection established. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket connection closed. Total: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")


def create_app(config: WebUIConfig) -> FastAPI:
    """Create FastAPI application"""
    
    app = FastAPI(
        title="Local AI Agent",
        description="Web interface for Local AI Agent",
        version="1.0.0",
        debug=config.debug
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify exact origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize agent
    agent = None
    connection_manager = ConnectionManager()
    
    @app.on_event("startup")
    async def startup_event():
        nonlocal agent
        if config.agent_config:
            from ..core.agent import Agent
            agent = Agent(config.agent_config)
            await agent.initialize()
            logger.info("Agent initialized for web UI")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        nonlocal agent
        if agent:
            await agent.shutdown()
            logger.info("Agent shutdown complete")
    
    @app.get("/health")
    async def health_check():
        status = {
            "status": "healthy",
            "agent_initialized": agent is not None and agent._initialized if agent else False
        }
        
        if agent:
            status.update(agent.get_status())
        
        return status
    
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await connection_manager.connect(websocket)
        
        try:
            while True:
                # Receive message from client
                data = await websocket.receive_json()
                message_type = data.get("type")
                
                if message_type == "chat":
                    await handle_chat_message(websocket, data, agent, connection_manager)
                elif message_type == "ping":
                    await websocket.send_json({"type": "pong"})
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown message type: {message_type}"
                    })
                    
        except WebSocketDisconnect:
            connection_manager.disconnect(websocket)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            connection_manager.disconnect(websocket)
    
    async def handle_chat_message(websocket: WebSocket, data: Dict[str, Any], agent: Agent, manager: ConnectionManager):
        """Handle chat message from client"""
        try:
            if not agent or not agent._initialized:
                await websocket.send_json({
                    "type": "error",
                    "message": "Agent not available"
                })
                return
            
            content = data.get("content", "")
            if not content:
                await websocket.send_json({
                    "type": "error",
                    "message": "Empty message"
                })
                return
            
            # Create agent request
            agent_request = AgentRequest(
                content=content,
                mode=AgentMode.CHAT,
                stream=data.get("stream", False),
                use_memory=data.get("use_memory", True),
                use_reasoning=data.get("use_reasoning", False),
                metadata={
                    "conversation_id": data.get("conversation_id", "web-ui"),
                    "user_id": data.get("user_id", "web-user")
                }
            )
            
            if agent_request.stream:
                # Handle streaming response
                await websocket.send_json({
                    "type": "stream_start",
                    "request_id": agent_request.request_id
                })
                
                try:
                    async for chunk in agent.process_stream(agent_request):
                        await websocket.send_json({
                            "type": "stream_chunk",
                            "request_id": agent_request.request_id,
                            "content": chunk
                        })
                    
                    await websocket.send_json({
                        "type": "stream_end",
                        "request_id": agent_request.request_id
                    })
                    
                except Exception as e:
                    await websocket.send_json({
                        "type": "stream_error",
                        "request_id": agent_request.request_id,
                        "error": str(e)
                    })
            else:
                # Handle regular response
                response = await agent.process(agent_request)
                
                await websocket.send_json({
                    "type": "response",
                    "request_id": response.request_id,
                    "content": response.content,
                    "success": response.success,
                    "provider_used": response.provider_used.value if response.provider_used else None,
                    "execution_time": response.execution_time,
                    "tokens_used": response.tokens_used,
                    "error": response.error
                })
                
        except Exception as e:
            logger.error(f"Error handling chat message: {e}")
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
    
    # Include API router
    api_router = APIRouter(agent)
    app.include_router(api_router.router, prefix="/api/v1")
    
    # Setup static files and templates - MUST be last to avoid route conflicts
    current_dir = Path(__file__).parent
    
    # Point to the React build directory
    react_build_dir = current_dir / "frontend" / "build"
    
    # Ensure the build directory exists
    if not react_build_dir.exists():
        logger.error(f"React build directory not found: {react_build_dir}")
        raise RuntimeError("React build not found. Please run 'npm run build' in src/agent/ui/frontend.")

    # Serve the entire React build directory as static files
    app.mount("/", StaticFiles(directory=react_build_dir, html=True), name="react_app")
    
    return app


async def run_server(config: WebUIConfig):
    """Run the web server"""
    app = create_app(config)
    
    server_config = uvicorn.Config(
        app,
        host=config.host,
        port=config.port,
        log_level="info" if not config.debug else "debug"
    )
    
    server = uvicorn.Server(server_config)
    
    logger.info(f"Starting web server on http://{config.host}:{config.port}")
    await server.serve()


# CLI entry point
async def main():
    """Main entry point for web UI"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Local AI Agent Web UI")
    parser.add_argument("--host", default="localhost", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind to")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Create basic agent config
    from ..core.agent import create_basic_agent_config
    agent_config = create_basic_agent_config()
    
    # Create web UI config
    config = WebUIConfig(
        host=args.host,
        port=args.port,
        debug=args.debug,
        agent_config=agent_config
    )
    
    await run_server(config)


if __name__ == "__main__":
    asyncio.run(main())