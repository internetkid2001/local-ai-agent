"""
API Router

REST API endpoints for the Local AI Agent.

Author: Claude Code
Date: 2025-07-13
Session: 4.4
"""

import logging
from typing import Dict, List, Any, Optional
from fastapi import APIRouter as FastAPIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from ..core.agent import Agent, AgentRequest, AgentMode, AgentCapability

logger = logging.getLogger(__name__)


# Request/Response models
class ChatRequest(BaseModel):
    content: str
    conversation_id: Optional[str] = None
    mode: str = "chat"
    stream: bool = False
    use_memory: bool = True
    use_reasoning: bool = False
    preferred_provider: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: float = 0.7


class ChatResponse(BaseModel):
    request_id: str
    content: str
    success: bool
    mode: str
    provider_used: Optional[str] = None
    execution_time: float
    tokens_used: Optional[Dict[str, int]] = None
    error: Optional[str] = None


class AgentStatus(BaseModel):
    agent_id: str
    name: str
    initialized: bool
    mode: str
    capabilities: List[str]
    active_conversations: int
    active_sessions: int
    functions_registered: int
    llm_providers: Optional[Dict[str, Any]] = None


class ToolInfo(BaseModel):
    name: str
    description: str
    input_schema: Dict[str, Any]


class SessionRequest(BaseModel):
    conversation_id: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class SessionResponse(BaseModel):
    session_id: str
    conversation_id: str
    created_at: float


class APIRouter:
    """API Router for Local AI Agent"""
    
    def __init__(self, agent: Optional[Agent] = None):
        self.agent = agent
        self.router = FastAPIRouter()
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup API routes"""
        
        @self.router.get("/status", response_model=AgentStatus)
        async def get_status():
            """Get agent status"""
            if not self.agent:
                raise HTTPException(status_code=503, detail="Agent not available")
            
            status = self.agent.get_status()
            return AgentStatus(**status)
        
        @self.router.post("/chat", response_model=ChatResponse)
        async def chat(request: ChatRequest):
            """Send chat message to agent"""
            if not self.agent or not self.agent._initialized:
                raise HTTPException(status_code=503, detail="Agent not initialized")
            
            try:
                # Convert mode string to enum
                mode = AgentMode.CHAT
                if request.mode.upper() in AgentMode.__members__:
                    mode = AgentMode[request.mode.upper()]
                
                # Create agent request
                agent_request = AgentRequest(
                    content=request.content,
                    mode=mode,
                    stream=request.stream,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    use_memory=request.use_memory,
                    use_reasoning=request.use_reasoning,
                    metadata={
                        "conversation_id": request.conversation_id or "api-default"
                    }
                )
                
                # Process request
                response = await self.agent.process(agent_request)
                
                return ChatResponse(
                    request_id=response.request_id,
                    content=response.content,
                    success=response.success,
                    mode=response.mode.value,
                    provider_used=response.provider_used.value if response.provider_used else None,
                    execution_time=response.execution_time,
                    tokens_used=response.tokens_used,
                    error=response.error
                )
                
            except Exception as e:
                logger.error(f"Chat API error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/capabilities", response_model=List[str])
        async def get_capabilities():
            """Get agent capabilities"""
            if not self.agent:
                raise HTTPException(status_code=503, detail="Agent not available")
            
            capabilities = self.agent.get_capabilities()
            return [cap.value for cap in capabilities]
        
        @self.router.get("/functions", response_model=List[ToolInfo])
        async def get_functions():
            """Get available functions"""
            if not self.agent:
                raise HTTPException(status_code=503, detail="Agent not available")
            
            functions = self.agent.get_available_functions()
            return [
                ToolInfo(
                    name=func.get("name", ""),
                    description=func.get("description", ""),
                    input_schema=func.get("inputSchema", {})
                )
                for func in functions
            ]
        
        @self.router.post("/sessions", response_model=SessionResponse)
        async def create_session(request: SessionRequest):
            """Create new agent session"""
            if not self.agent:
                raise HTTPException(status_code=503, detail="Agent not available")
            
            try:
                session_config = request.config or {}
                if request.conversation_id:
                    session_config["conversation_id"] = request.conversation_id
                
                session_id = await self.agent.create_session(session_config)
                session_info = self.agent.active_sessions[session_id]
                
                return SessionResponse(
                    session_id=session_id,
                    conversation_id=session_info["conversation_id"],
                    created_at=session_info["created_at"]
                )
                
            except Exception as e:
                logger.error(f"Session creation error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.delete("/sessions/{session_id}")
        async def end_session(session_id: str, background_tasks: BackgroundTasks):
            """End agent session"""
            if not self.agent:
                raise HTTPException(status_code=503, detail="Agent not available")
            
            if session_id not in self.agent.active_sessions:
                raise HTTPException(status_code=404, detail="Session not found")
            
            # End session in background
            background_tasks.add_task(self.agent.end_session, session_id)
            
            return {"message": "Session ended"}
        
        @self.router.get("/sessions")
        async def list_sessions():
            """List active sessions"""
            if not self.agent:
                raise HTTPException(status_code=503, detail="Agent not available")
            
            sessions = []
            for session_id, session_info in self.agent.active_sessions.items():
                sessions.append({
                    "session_id": session_id,
                    "conversation_id": session_info["conversation_id"],
                    "created_at": session_info["created_at"],
                    "config": session_info["config"]
                })
            
            return sessions
        
        @self.router.get("/conversations/{conversation_id}")
        async def get_conversation(conversation_id: str):
            """Get conversation history"""
            if not self.agent:
                raise HTTPException(status_code=503, detail="Agent not available")
            
            if conversation_id not in self.agent.conversations:
                raise HTTPException(status_code=404, detail="Conversation not found")
            
            messages = self.agent.conversations[conversation_id]
            
            return {
                "conversation_id": conversation_id,
                "message_count": len(messages),
                "messages": [
                    {
                        "role": msg.role.value,
                        "content": msg.content,
                        "metadata": msg.metadata
                    }
                    for msg in messages
                ]
            }
        
        @self.router.get("/conversations")
        async def list_conversations():
            """List active conversations"""
            if not self.agent:
                raise HTTPException(status_code=503, detail="Agent not available")
            
            conversations = []
            for conv_id, messages in self.agent.conversations.items():
                conversations.append({
                    "conversation_id": conv_id,
                    "message_count": len(messages),
                    "last_message": messages[-1].content[:100] + "..." if messages else None
                })
            
            return conversations
        
        @self.router.post("/reset")
        async def reset_agent():
            """Reset agent state"""
            if not self.agent:
                raise HTTPException(status_code=503, detail="Agent not available")
            
            try:
                # Clear conversations and sessions
                self.agent.conversations.clear()
                
                # End all sessions
                session_ids = list(self.agent.active_sessions.keys())
                for session_id in session_ids:
                    await self.agent.end_session(session_id)
                
                return {"message": "Agent reset complete"}
                
            except Exception as e:
                logger.error(f"Agent reset error: {e}")
                raise HTTPException(status_code=500, detail=str(e))