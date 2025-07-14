#!/usr/bin/env python3
"""
Simple UI test script that bypasses complex agent imports
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Simple mock agent for testing UI
class MockAgent:
    def __init__(self):
        self._initialized = True
    
    async def initialize(self):
        pass
    
    async def shutdown(self):
        pass
    
    def get_status(self):
        return {"status": "mock_agent_running", "version": "test"}
    
    async def process_stream(self, request):
        # Mock streaming response with pause instruction
        yield "I received your message: "
        await asyncio.sleep(0.5)
        yield f'"{request.content}". '
        await asyncio.sleep(0.5)
        yield "This is a mock AI agent for UI testing. "
        await asyncio.sleep(0.5)
        yield "The real agent will be available when you continue development. "
        await asyncio.sleep(0.5)
        yield "Please provide further instructions to continue building features."
    
    async def process(self, request):
        # Mock regular response
        await asyncio.sleep(1)
        return MockResponse(
            request_id=request.request_id,
            content=f'Mock AI: I received "{request.content}". This is a test environment. The real agent awaits your further development instructions.',
            success=True
        )

class MockResponse:
    def __init__(self, request_id, content, success, provider_used=None, execution_time=1.0, tokens_used=10, error=None):
        self.request_id = request_id
        self.content = content
        self.success = success
        self.provider_used = provider_used
        self.execution_time = execution_time
        self.tokens_used = tokens_used
        self.error = error

class MockRequest:
    def __init__(self, content, **kwargs):
        self.content = content
        self.request_id = f"req_{id(self)}"
        self.stream = kwargs.get('stream', False)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"WebSocket connection established. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"WebSocket connection closed. Total: {len(self.active_connections)}")

def create_app() -> FastAPI:
    """Create simple FastAPI app for UI testing"""
    
    app = FastAPI(
        title="Local AI Agent - UI Test",
        description="Simple UI test interface",
        version="1.0.0"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize mock agent and connection manager
    agent = MockAgent()
    connection_manager = ConnectionManager()
    
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "agent_initialized": True,
            "mode": "ui_test"
        }
    
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await connection_manager.connect(websocket)
        
        try:
            while True:
                data = await websocket.receive_json()
                message_type = data.get("type")
                
                if message_type == "chat":
                    await handle_chat_message(websocket, data, agent)
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
            print(f"WebSocket error: {e}")
            connection_manager.disconnect(websocket)
    
    async def handle_chat_message(websocket: WebSocket, data: Dict[str, Any], agent: MockAgent):
        """Handle chat message from client"""
        try:
            content = data.get("content", "")
            if not content:
                await websocket.send_json({
                    "type": "error",
                    "message": "Empty message"
                })
                return
            
            # Create mock request
            request = MockRequest(
                content=content,
                stream=data.get("stream", False)
            )
            
            if request.stream:
                # Handle streaming response
                await websocket.send_json({
                    "type": "stream_start",
                    "request_id": request.request_id
                })
                
                try:
                    async for chunk in agent.process_stream(request):
                        await websocket.send_json({
                            "type": "stream_chunk",
                            "request_id": request.request_id,
                            "content": chunk
                        })
                    
                    await websocket.send_json({
                        "type": "stream_end",
                        "request_id": request.request_id
                    })
                    
                except Exception as e:
                    await websocket.send_json({
                        "type": "stream_error",
                        "request_id": request.request_id,
                        "error": str(e)
                    })
            else:
                # Handle regular response
                response = await agent.process(request)
                
                await websocket.send_json({
                    "type": "response",
                    "request_id": response.request_id,
                    "content": response.content,
                    "success": response.success,
                    "execution_time": response.execution_time,
                    "tokens_used": response.tokens_used,
                    "error": response.error
                })
                
        except Exception as e:
            print(f"Error handling chat message: {e}")
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
    
    # Setup static files - React build directory
    current_dir = Path(__file__).parent
    react_build_dir = current_dir / "src" / "agent" / "ui" / "frontend" / "build"
    
    if react_build_dir.exists():
        app.mount("/", StaticFiles(directory=react_build_dir, html=True), name="react_app")
        print(f"Serving React app from: {react_build_dir}")
    else:
        print(f"React build directory not found: {react_build_dir}")
        print("Please run 'npm run build' in src/agent/ui/frontend/")
        
        # Serve a simple HTML page instead
        @app.get("/")
        async def root():
            return {
                "message": "React build not found",
                "instructions": "Run 'npm run build' in src/agent/ui/frontend/ directory",
                "websocket_test": "ws://localhost:8080/ws"
            }
    
    return app

async def main():
    """Main entry point"""
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    print("🚀 Starting Local AI Agent UI Test...")
    print("📱 Open http://localhost:8080 in your browser")
    print("🔌 WebSocket endpoint: ws://localhost:8080/ws")
    print("❤️  Health check: http://localhost:8080/health")
    print("⏹️  Press Ctrl+C to stop")
    print()
    
    app = create_app()
    
    config = uvicorn.Config(
        app,
        host="localhost",
        port=8080,
        log_level="info"
    )
    
    server = uvicorn.Server(config)
    
    try:
        await server.serve()
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")

if __name__ == "__main__":
    asyncio.run(main())