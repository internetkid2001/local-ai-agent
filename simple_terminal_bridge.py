#!/usr/bin/env python3
"""
Simple Terminal Bridge - Direct terminal-like interface for the floating UI
This provides a simple chat interface without complex MCP WebSocket connections
"""

import asyncio
import json
import logging
import subprocess
import sys
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import uvicorn
import aiohttp
from typing import Dict, List, Any

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Simple Terminal Bridge", version="1.0.0")

# Connected WebSocket clients
connected_clients: List[WebSocket] = []

class TerminalBridge:
    def __init__(self):
        self.ollama_url = "http://localhost:11434"
        self.conversation_history = []
    
    async def chat_with_ollama(self, message: str) -> str:
        """Send message to Ollama for AI response"""
        try:
            # Add user message to history
            self.conversation_history.append({"role": "user", "content": message})
            
            # Keep only last 10 messages for context
            messages = self.conversation_history[-10:]
            
            payload = {
                "model": "llama3:8b",
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 50,  # Reduced for faster responses
                    "num_ctx": 512,     # Smaller context for lower overhead
                    "num_batch": 256,   # Adjusted batch size for compatibility
                    "num_gpu": 1,        # Use GPU if available
                    "num_thread": 2,     # Lessen thread use for smaller model
                    "repeat_penalty": 1.1,
                    "top_k": 40,
                    "top_p": 0.9
                }
            }
            
            # Add timeout to prevent hanging
            timeout = aiohttp.ClientTimeout(total=15)  # 15 second timeout
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(f"{self.ollama_url}/api/chat", json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        ai_response = result.get("message", {}).get("content", "Sorry, I couldn't generate a response.")
                        
                        # Add AI response to history
                        self.conversation_history.append({"role": "assistant", "content": ai_response})
                        
                        return ai_response
                    else:
                        return f"Error: Ollama responded with status {response.status}"
        
        except Exception as e:
            logger.error(f"Error chatting with Ollama: {e}")
            return f"Error connecting to Ollama: {e}"
    
    def handle_nlp_command(self, message: str) -> str:
        """Interpret natural language commands with fuzzy matching"""
        import re
        
        # Normalize the message
        normalized_message = message.lower().strip()
        
        # Define keyword patterns for different commands
        patterns = {
            # System information patterns
            r'(system|computer|machine).*(info|information|details|specs|about)': '/mcp system get_system_info',
            r'(show|get|tell me).*(system|computer|machine).*(info|information|details|specs)': '/mcp system get_system_info',
            r'^(system info|system information|computer info|machine info)': '/mcp system get_system_info',
            
            # Process patterns (also covers CPU usage)
            r'(show|list|get|see).*(process|running|tasks?)': '/mcp system get_processes',
            r'(what|which).*(process|running|tasks?)': '/mcp system get_processes',
            r'^(processes|running processes|tasks)': '/mcp system get_processes',
            r'(cpu|processor).*(usage|load|utilization)': '/mcp system get_processes',
            r'(show|get|check).*(cpu|processor)': '/mcp system get_processes',
            r'^(cpu|processor|cpu usage|processor usage)': '/mcp system get_processes',
            
            # Memory patterns
            r'(memory|ram).*(usage|info|information|status)': '/mcp system get_memory_info',
            r'(show|get|check).*(memory|ram)': '/mcp system get_memory_info',
            r'^(memory|ram|memory usage|ram usage)': '/mcp system get_memory_info',
            
            # Disk patterns
            r'(disk|storage|drive).*(usage|space|info|information)': '/mcp system get_disk_usage',
            r'(show|get|check).*(disk|storage|drive)': '/mcp system get_disk_usage',
            r'^(disk|storage|disk usage|storage usage)': '/mcp system get_disk_usage',
            
            # Screenshot patterns
            r'(take|capture|grab|make).*(screenshot|screen shot|picture|image)': '/mcp desktop take_screenshot',
            r'(screenshot|screen shot|capture screen)': '/mcp desktop take_screenshot',
            r'^screenshot': '/mcp desktop take_screenshot',
            
            # File listing patterns
            r'(list|show|see).*(files?|directory|folder)': '/mcp filesystem list_files .',
            r'(what|which).*(files?|directory|folder)': '/mcp filesystem list_files .',
            r'^(files|ls|dir)': '/mcp filesystem list_files .',
            
            # Network patterns (map to system info for now)
            r'(network|net).*(info|information|status)': '/mcp system get_system_info',
            r'(show|get|check).*(network|net)': '/mcp system get_system_info',
            r'^(network|net|network info)': '/mcp system get_system_info'
        }
        
        # Try to match patterns
        for pattern, command in patterns.items():
            if re.search(pattern, normalized_message):
                return self.handle_mcp_command(command)
        
        # If no pattern matches, return None to trigger AI chat
        return None

    def execute_command(self, command: str) -> str:
        """Execute a simple system command"""
        try:
            if command.startswith("/"):
                # Handle special commands
                if command == "/status":
                    return self.get_system_status()
                elif command == "/help":
                    return self.get_help()
                elif command == "/clear":
                    self.conversation_history = []
                    return "Conversation history cleared."
                elif command == "/system_info":
                    return self.get_system_info()
                elif command == "/processes":
                    return self.get_processes()
                elif command == "/memory":
                    return self.get_memory_info()
                elif command == "/disk":
                    return self.get_disk_usage()
                elif command == "/screenshot":
                    return self.take_screenshot()
                elif command == "/files":
                    return self.list_files(".")
                elif command.startswith("/mcp"):
                    return self.handle_mcp_command(command)
                else:
                    return f"Unknown command: {command}"
            else:
                # Try to interpret as natural language command first
                nlp_result = self.handle_nlp_command(command)
                if nlp_result is not None:
                    return nlp_result
                else:
                    # If no command matched, return None to trigger AI chat
                    return None
        except Exception as e:
            return f"Error executing command: {e}"
    
    def get_system_status(self) -> str:
        """Get current system status"""
        try:
            # Check MCP servers
            mcp_status = []
            ports = [8765, 8766, 8767, 8005]
            for port in ports:
                result = subprocess.run(['netstat', '-tuln'], capture_output=True, text=True)
                if f":{port}" in result.stdout:
                    mcp_status.append(f"✅ Port {port}: Running")
                else:
                    mcp_status.append(f"❌ Port {port}: Not running")
            
            # Check Ollama
            try:
                result = subprocess.run(['curl', '-s', 'http://localhost:11434/api/version'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    ollama_status = "✅ Ollama: Running"
                else:
                    ollama_status = "❌ Ollama: Not responding"
            except:
                ollama_status = "❌ Ollama: Not available"
            
            status = "📊 System Status:\n\n"
            status += "MCP Servers:\n"
            status += "\n".join([f"  {s}" for s in mcp_status])
            status += f"\n\nAI Backend:\n  {ollama_status}"
            status += f"\n\nConversation: {len(self.conversation_history)} messages"
            
            return status
        except Exception as e:
            return f"Error getting system status: {e}"
    
    def handle_mcp_command(self, command: str) -> str:
        """Handle MCP-style commands (simulated)"""
        parts = command.split()
        if len(parts) < 3:
            return "Usage: /mcp <server> <command> [args...]"
        
        server = parts[1]
        cmd = parts[2]
        
        if server == "desktop" and cmd == "take_screenshot":
            return self.take_screenshot()
        elif server == "filesystem" and cmd == "list_files":
            path = parts[3] if len(parts) > 3 else "."
            return self.list_files(path)
        elif server == "system" and cmd == "get_info":
            return self.get_system_info()
        elif server == "system" and cmd == "get_system_info":
            return self.get_system_info()
        elif server == "system" and cmd == "get_processes":
            return self.get_processes()
        elif server == "system" and cmd == "get_memory_info":
            return self.get_memory_info()
        elif server == "system" and cmd == "get_disk_usage":
            return self.get_disk_usage()
        else:
            return f"MCP command not implemented: {server} {cmd}"
    
    def take_screenshot(self) -> str:
        """Take a screenshot using system tools"""
        try:
            # Save to user's Desktop or Pictures folder
            import os
            home_dir = os.path.expanduser("~")
            desktop_path = os.path.join(home_dir, "Desktop")
            if not os.path.exists(desktop_path):
                desktop_path = os.path.join(home_dir, "Pictures")
            if not os.path.exists(desktop_path):
                desktop_path = home_dir
            
            screenshot_path = os.path.join(desktop_path, "local_ai_agent_screenshot.png")
            result = subprocess.run(['gnome-screenshot', '-f', screenshot_path], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                return f"📸 Screenshot saved to: {screenshot_path}"
            else:
                # Try alternative screenshot methods
                result = subprocess.run(['scrot', screenshot_path], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    return f"📸 Screenshot saved to: {screenshot_path}"
                else:
                    return "❌ Failed to take screenshot. Install gnome-screenshot or scrot."
        except Exception as e:
            return f"❌ Screenshot error: {e}"
    
    def list_files(self, path: str) -> str:
        """List files in a directory"""
        try:
            result = subprocess.run(['ls', '-la', path], capture_output=True, text=True)
            if result.returncode == 0:
                return f"📁 Files in {path}:\n{result.stdout}"
            else:
                return f"❌ Error listing files: {result.stderr}"
        except Exception as e:
            return f"❌ File listing error: {e}"
    
    def get_system_info(self) -> str:
        """Get basic system information"""
        try:
            info = []
            
            # System uptime
            result = subprocess.run(['uptime'], capture_output=True, text=True)
            if result.returncode == 0:
                info.append(f"Uptime: {result.stdout.strip()}")
            
            # Memory usage
            result = subprocess.run(['free', '-h'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    info.append(f"Memory: {lines[1]}")
            
            # Disk usage
            result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    info.append(f"Disk: {lines[1]}")
            
            return "🖥️ System Info:\n" + "\n".join(info)
        except Exception as e:
            return f"❌ System info error: {e}"
    
    def get_processes(self) -> str:
        """Get running processes"""
        try:
            result = subprocess.run(['ps', 'aux', '--sort=-%cpu'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                # Get top 10 processes
                if len(lines) > 11:
                    header = lines[0]
                    processes = lines[1:11]
                    return f"⚙️ Top 10 Processes:\n{header}\n" + "\n".join(processes)
                else:
                    return f"⚙️ Processes:\n{result.stdout}"
            else:
                return f"❌ Error getting processes: {result.stderr}"
        except Exception as e:
            return f"❌ Process error: {e}"
    
    def get_memory_info(self) -> str:
        """Get detailed memory information"""
        try:
            result = subprocess.run(['free', '-h'], capture_output=True, text=True)
            if result.returncode == 0:
                return f"💾 Memory Information:\n{result.stdout}"
            else:
                return f"❌ Error getting memory info: {result.stderr}"
        except Exception as e:
            return f"❌ Memory info error: {e}"
    
    def get_disk_usage(self) -> str:
        """Get disk usage information"""
        try:
            result = subprocess.run(['df', '-h'], capture_output=True, text=True)
            if result.returncode == 0:
                return f"💿 Disk Usage:\n{result.stdout}"
            else:
                return f"❌ Error getting disk usage: {result.stderr}"
        except Exception as e:
            return f"❌ Disk usage error: {e}"
    
    def get_help(self) -> str:
        """Get help information"""
        return """🤖 Local AI Agent Terminal Help

Natural Language Commands:
• "take a screenshot" - Capture screen
• "show system info" - Display system information
• "list processes" - Show running processes
• "memory usage" - Display memory information
• "disk usage" - Show disk space
• "show files" - List current directory files

Traditional Commands:
• /status - Show system status
• /help - Show this help
• /clear - Clear conversation history
• /mcp desktop take_screenshot - Take a screenshot
• /mcp filesystem list_files [path] - List files
• /mcp system get_info - Get system information

Examples of Natural Language:
• "What processes are running?"
• "Show me the system information"
• "How much memory is being used?"
• "Take a screenshot of the desktop"
• "Check disk space"
• "List the files in this directory"

Regular messages will be sent to the AI for response.

MCP Servers:
• Filesystem (Port 8765) - File operations
• Desktop (Port 8766) - UI automation
• System (Port 8767) - System monitoring
• AI Bridge (Port 8005) - External AI integration"""

# Initialize the bridge
bridge = TerminalBridge()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    logger.info("🔌 Client connected to Terminal Bridge")
    
    try:
        # Send welcome message
        await websocket.send_text(json.dumps({
            "type": "connection_status",
            "connected": True,
            "message": "Connected to Local AI Agent Terminal Bridge",
            "help": "Type /help for available commands"
        }))
        
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data.get("type") == "chat_message":
                user_message = message_data.get("message", "").strip()
                
                if not user_message:
                    continue
                
                # Check if it's a command
                command_result = bridge.execute_command(user_message)
                
                if command_result is not None:
                    # It was a command
                    await websocket.send_text(json.dumps({
                        "type": "command_result",
                        "message": command_result
                    }))
                else:
                    # Regular AI chat
                    ai_response = await bridge.chat_with_ollama(user_message)
                    await websocket.send_text(json.dumps({
                        "type": "ai_response",
                        "message": ai_response,
                        "role": "assistant"
                    }))
    
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        logger.info("🔌 Client disconnected from Terminal Bridge")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in connected_clients:
            connected_clients.remove(websocket)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Terminal Bridge",
        "connected_clients": len(connected_clients)
    }

@app.get("/")
async def root():
    """Root endpoint info"""
    return {
        "service": "Simple Terminal Bridge",
        "version": "1.0.0",
        "websocket": "/ws",
        "health": "/health",
        "description": "Direct terminal-like interface for Local AI Agent"
    }

if __name__ == "__main__":
    print("🤖 Starting Simple Terminal Bridge...")
    print("💬 This provides a direct terminal-like chat interface")
    print("🔄 WebSocket endpoint: ws://localhost:8090/ws")
    print("❌ Press Ctrl+C to stop")
    
    uvicorn.run(
        app,
        host="localhost", 
        port=8090,
        log_level="info"
    )