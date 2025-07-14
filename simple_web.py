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
from fastapi.responses import HTMLResponse, FileResponse
import aiohttp
import uvicorn

app = FastAPI(title="Local AI Agent - Simple UI", version="1.0.0")

# Simple in-memory chat history
chat_history = []

# Mount the UI directory
ui_path = project_root / "src" / "ui"
app.mount("/", StaticFiles(directory=ui_path, html=True), name="ui")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return FileResponse(ui_path / "index.html")


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
                    ai_response_content = result.get("message", {}).get("content", "Sorry, I couldn't generate a response.")
                    
                    # For demonstration, let's try to structure a sample response
                    # In a real scenario, the LLM would generate this structured content
                    if "cluely" in ai_response_content.lower() or "features" in ai_response_content.lower():
                        structured_response = {
                            "question": "I can see you're currently viewing the Cluely website homepage. The AI assistant that monitors your screen and audio to provide contextual help before you even ask for it.",
                            "features": [
                                {"title": "Screen monitoring", "description": "Cluely can see what's on your screen and understand the content"},
                                {"title": "Audio listening", "description": "It processes your calls and conversations"},
                                {"title": "Proactive assistance", "description": "Rather than waiting for questions, it anticipates what you might need"},
                                {"title": "Real-time help", "description": "Provides instant responses during meetings, interviews, or exams"}
                            ]
                        }
                        ai_response = json.dumps(structured_response)
                    else:
                        ai_response = ai_response_content

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