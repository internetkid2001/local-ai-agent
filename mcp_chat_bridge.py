#!/usr/bin/env python3
"""
MCP Chat Bridge - Direct connection to MCP servers for the floating UI
This replaces the OpenWebUI dependency and connects directly to MCP servers
"""

import asyncio
import json
import logging
import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import aiohttp
from pathlib import Path
from typing import Dict, List, Any

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MCP Chat Bridge", version="1.0.0")

# MCP Server configurations
MCP_SERVERS = {
    "filesystem": {"host": "localhost", "port": 8765},
    "desktop": {"host": "localhost", "port": 8766}, 
    "system": {"host": "localhost", "port": 8767},
    "ai_bridge": {"host": "localhost", "port": 8005}
}

# Connected WebSocket clients
connected_clients: List[WebSocket] = []

class MCPBridge:
    def __init__(self):
        self.mcp_connections = {}
        self.ollama_url = "http://localhost:11434"
    
    async def connect_to_mcp_servers(self):
        """Connect to all available MCP servers"""
        for server_name, config in MCP_SERVERS.items():
            try:
                # Test connection to MCP server
                uri = f"ws://{config['host']}:{config['port']}"
                async with websockets.connect(uri) as ws:
                    logger.info(f"✅ Connected to {server_name} MCP server at {uri}")
                    self.mcp_connections[server_name] = config
            except Exception as e:
                logger.warning(f"❌ Failed to connect to {server_name} MCP server: {e}")
    
    async def get_mcp_tools(self, server_name: str) -> List[Dict]:
        """Get available tools from an MCP server"""
        if server_name not in self.mcp_connections:
            return []
        
        try:
            config = self.mcp_connections[server_name]
            uri = f"ws://{config['host']}:{config['port']}"
            
            async with websockets.connect(uri) as ws:
                # Send tools list request
                request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list"
                }
                await ws.send(json.dumps(request))
                response = await ws.recv()
                data = json.loads(response)
                
                if "result" in data and "tools" in data["result"]:
                    return data["result"]["tools"]
                return []
        except Exception as e:
            logger.error(f"Error getting tools from {server_name}: {e}")
            return []
    
    async def execute_mcp_tool(self, server_name: str, tool_name: str, arguments: Dict = None) -> Dict:
        """Execute a tool on an MCP server"""
        if server_name not in self.mcp_connections:
            return {"error": f"Server {server_name} not connected"}
        
        try:
            config = self.mcp_connections[server_name]
            uri = f"ws://{config['host']}:{config['port']}"
            
            async with websockets.connect(uri) as ws:
                # Send tool execution request
                request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": arguments or {}
                    }
                }
                await ws.send(json.dumps(request))
                response = await ws.recv()
                data = json.loads(response)
                
                return data
        except Exception as e:
            logger.error(f"Error executing {tool_name} on {server_name}: {e}")
            return {"error": str(e)}
    
    async def chat_with_ollama(self, message: str, conversation_history: List[Dict] = None) -> str:
        """Send message to Ollama for AI response"""
        try:
            messages = conversation_history or []
            messages.append({"role": "user", "content": message})
            
            # Keep only last 10 messages for context
            messages = messages[-10:]
            
            payload = {
                "model": "deepseek-r1:latest",
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 500
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.ollama_url}/api/chat", json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("message", {}).get("content", "Sorry, I couldn't generate a response.")
                    else:
                        return f"Error: Ollama responded with status {response.status}"
        
        except Exception as e:
            logger.error(f"Error chatting with Ollama: {e}")
            return f"Error connecting to Ollama: {e}"

# Initialize the bridge
bridge = MCPBridge()

@app.on_event("startup")
async def startup_event():
    """Initialize MCP connections on startup"""
    logger.info("🚀 Starting MCP Chat Bridge...")
    await bridge.connect_to_mcp_servers()
    logger.info(f"📡 Connected to {len(bridge.mcp_connections)} MCP servers")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    logger.info("🔌 Client connected to WebSocket")
    
    try:
        # Send initial connection status
        await websocket.send_text(json.dumps({
            "type": "connection_status",
            "connected": True,
            "mcp_servers": list(bridge.mcp_connections.keys()),
            "server_count": len(bridge.mcp_connections)
        }))
        
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data.get("type") == "chat_message":
                # Handle regular chat message
                user_message = message_data.get("message", "")
                conversation_history = message_data.get("history", [])
                
                # Check if this is an MCP command
                if user_message.lower().startswith("/mcp "):
                    await handle_mcp_command(websocket, user_message[5:])
                elif user_message.lower() == "/status":
                    await send_status(websocket)
                elif user_message.lower() == "/tools":
                    await send_available_tools(websocket)
                else:
                    # Regular AI chat
                    ai_response = await bridge.chat_with_ollama(user_message, conversation_history)
                    await websocket.send_text(json.dumps({
                        "type": "ai_response",
                        "message": ai_response,
                        "role": "assistant"
                    }))
            
            elif message_data.get("type") == "mcp_command":
                # Handle MCP tool execution
                await handle_mcp_tool_execution(websocket, message_data)
    
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        logger.info("🔌 Client disconnected from WebSocket")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in connected_clients:
            connected_clients.remove(websocket)

async def handle_mcp_command(websocket: WebSocket, command: str):
    """Handle MCP-specific commands"""
    parts = command.strip().split()
    if len(parts) < 2:
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": "Usage: /mcp <server> <tool> [arguments]"
        }))
        return
    
    server_name = parts[0]
    tool_name = parts[1]
    arguments = {}
    
    # Parse simple arguments (key=value)
    for part in parts[2:]:
        if "=" in part:
            key, value = part.split("=", 1)
            arguments[key] = value
    
    result = await bridge.execute_mcp_tool(server_name, tool_name, arguments)
    
    await websocket.send_text(json.dumps({
        "type": "mcp_result",
        "server": server_name,
        "tool": tool_name,
        "result": result
    }))

async def handle_mcp_tool_execution(websocket: WebSocket, message_data: Dict):
    """Handle direct MCP tool execution"""
    server_name = message_data.get("server")
    tool_name = message_data.get("tool")
    arguments = message_data.get("arguments", {})
    
    result = await bridge.execute_mcp_tool(server_name, tool_name, arguments)
    
    await websocket.send_text(json.dumps({
        "type": "mcp_result",
        "server": server_name,
        "tool": tool_name,
        "result": result
    }))

async def send_status(websocket: WebSocket):
    """Send current system status"""
    status = {
        "type": "system_status",
        "mcp_servers": bridge.mcp_connections,
        "connected_servers": len(bridge.mcp_connections),
        "available_commands": [
            "/status - Show system status",
            "/tools - List available tools",
            "/mcp <server> <tool> [args] - Execute MCP tool"
        ]
    }
    await websocket.send_text(json.dumps(status))

async def send_available_tools(websocket: WebSocket):
    """Send list of available tools from all servers"""
    all_tools = {}
    
    for server_name in bridge.mcp_connections.keys():
        tools = await bridge.get_mcp_tools(server_name)
        all_tools[server_name] = tools
    
    await websocket.send_text(json.dumps({
        "type": "available_tools",
        "tools": all_tools
    }))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "mcp_servers": len(bridge.mcp_connections),
        "connected_servers": list(bridge.mcp_connections.keys())
    }

@app.get("/")
async def root():
    """Root endpoint info"""
    return {
        "service": "MCP Chat Bridge",
        "version": "1.0.0",
        "websocket": "/ws",
        "health": "/health",
        "mcp_servers": list(bridge.mcp_connections.keys())
    }

if __name__ == "__main__":
    print("🤖 Starting MCP Chat Bridge Server...")
    print("📡 This service connects the floating UI directly to MCP servers")
    print("🔄 WebSocket endpoint: ws://localhost:8090/ws")
    print("❌ Press Ctrl+C to stop")
    
    uvicorn.run(
        app,
        host="localhost", 
        port=8090,
        log_level="info"
    )