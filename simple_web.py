#!/usr/bin/env python3
"""
Simple Web UI for Local AI Agent
Basic chat interface without complex imports
"""

import sys
import os
from pathlib import Path
import asyncio
import json
import logging

# Add src directory to Python path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import aiohttp
import uvicorn

app = FastAPI(title="Local AI Agent - Simple UI", version="1.0.0")

# Simple in-memory chat history
chat_history = []

@app.get("/", response_class=HTMLResponse)
async def home():
    """Simple chat interface"""
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Local AI Agent - Simple Chat</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            background: #2563eb;
            color: white;
            padding: 20px;
            border-radius: 10px 10px 0 0;
            text-align: center;
        }
        .chat-container {
            height: 400px;
            overflow-y: auto;
            padding: 20px;
            border-bottom: 1px solid #eee;
        }
        .message {
            margin: 10px 0;
            padding: 10px;
            border-radius: 5px;
        }
        .user-message {
            background: #e3f2fd;
            text-align: right;
        }
        .ai-message {
            background: #f3e5f5;
        }
        .input-container {
            padding: 20px;
            display: flex;
            gap: 10px;
        }
        .message-input {
            flex: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
        }
        .send-button {
            padding: 10px 20px;
            background: #2563eb;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }
        .send-button:hover {
            background: #1d4ed8;
        }
        .send-button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .status {
            text-align: center;
            padding: 10px;
            font-size: 14px;
            color: #666;
        }
        .loading {
            color: #2563eb;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Local AI Agent</h1>
            <p>Simple Chat Interface</p>
        </div>
        
        <div id="chat-container" class="chat-container">
            <div class="message ai-message">
                <strong>AI Agent:</strong> Hello! I'm your Local AI Agent. Ask me anything!
            </div>
        </div>
        
        <div class="status" id="status">Ready</div>
        
        <div class="input-container">
            <input type="text" id="message-input" class="message-input" placeholder="Type your message..." maxlength="500">
            <button id="send-button" class="send-button">Send</button>
        </div>
    </div>

    <script>
        const chatContainer = document.getElementById('chat-container');
        const messageInput = document.getElementById('message-input');
        const sendButton = document.getElementById('send-button');
        const status = document.getElementById('status');

        function addMessage(content, isUser) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${isUser ? 'user-message' : 'ai-message'}`;
            messageDiv.innerHTML = `<strong>${isUser ? 'You' : 'AI Agent'}:</strong> ${content}`;
            chatContainer.appendChild(messageDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        async function sendMessage() {
            const message = messageInput.value.trim();
            if (!message) return;

            // Add user message
            addMessage(message, true);
            messageInput.value = '';
            sendButton.disabled = true;
            status.textContent = 'Thinking...';
            status.className = 'status loading';

            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ message: message })
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const data = await response.json();
                addMessage(data.response, false);
                status.textContent = 'Ready';
                status.className = 'status';

            } catch (error) {
                addMessage(`Error: ${error.message}`, false);
                status.textContent = 'Error occurred';
                status.className = 'status';
            }

            sendButton.disabled = false;
        }

        sendButton.addEventListener('click', sendMessage);
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });

        // Focus on input
        messageInput.focus();
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)

@app.post("/chat")
async def chat(request: Request):
    """Handle chat messages"""
    try:
        data = await request.json()
        user_message = data.get("message", "").strip()
        
        if not user_message:
            raise HTTPException(status_code=400, detail="Empty message")
        
        # Store user message
        chat_history.append({"role": "user", "content": user_message})
        
        # Prepare Ollama request
        ollama_request = {
            "model": "deepseek-r1:latest",
            "messages": chat_history[-10:],  # Keep last 10 messages for context
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 150  # Limit response length
            }
        }
        
        # Send to Ollama
        async with aiohttp.ClientSession() as session:
            async with session.post("http://localhost:11434/api/chat", json=ollama_request) as response:
                if response.status == 200:
                    result = await response.json()
                    ai_response = result.get("message", {}).get("content", "Sorry, I couldn't generate a response.")
                    
                    # Store AI response
                    chat_history.append({"role": "assistant", "content": ai_response})
                    
                    return {"response": ai_response}
                else:
                    error_text = await response.text()
                    raise HTTPException(status_code=500, detail=f"Ollama error: {error_text}")
                    
    except Exception as e:
        logging.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        # Test Ollama connection
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:11434/api/version") as response:
                if response.status == 200:
                    version_data = await response.json()
                    return {
                        "status": "healthy",
                        "ollama_version": version_data.get("version"),
                        "chat_history_length": len(chat_history)
                    }
                else:
                    return {"status": "unhealthy", "error": "Ollama not responding"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.get("/clear")
async def clear_history():
    """Clear chat history"""
    global chat_history
    chat_history = []
    return {"message": "Chat history cleared"}

if __name__ == "__main__":
    print("🌐 Starting Local AI Agent Simple Web UI...")
    print("📡 Server will be available at: http://localhost:8080")
    print("🔄 Make sure Ollama is running on port 11434")
    print("👋 Press Ctrl+C to stop")
    
    uvicorn.run(
        app,
        host="localhost",
        port=8080,
        log_level="info"
    )