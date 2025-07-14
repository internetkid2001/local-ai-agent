"""
Core Agent Implementation

The main AI agent that coordinates all subsystems including LLM providers,
reasoning engine, memory, and MCP protocol integration.

Author: Claude Code
Date: 2025-07-13
Session: 4.4
"""

import asyncio
import time
import uuid
from typing import Dict, List, Any, Optional, Union, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
import logging

from ..llm.manager import LLMManager, LLMManagerConfig
from ..llm.providers.base import LLMProvider, LLMConfig, Message, MessageRole, LLMResponse
from ..ai.reasoning_engine import ReasoningEngine, ReasoningTask, ReasoningMode, ReasoningResult
from ..context.context_manager import ContextManager
from ..context.memory_store import MemoryStore
from ...mcp_client.client_manager import MCPClientManager
from ...mcp_client.base_client import MCPClientConfig, MCPServerConfig
try:
    from utils.logger import get_logger
except ImportError:
    # Fallback for relative imports
    import logging
    def get_logger(name):
        return logging.getLogger(name)

logger = get_logger(__name__)


class AgentMode(Enum):
    """Agent operation modes"""
    CHAT = "chat"
    TASK_EXECUTION = "task_execution"
    REASONING = "reasoning"
    ANALYSIS = "analysis"
    AUTOMATION = "automation"
    DEBUG = "debug"


class AgentCapability(Enum):
    """Agent capabilities"""
    NATURAL_LANGUAGE = "natural_language"
    CODE_GENERATION = "code_generation"
    REASONING = "reasoning"
    MEMORY = "memory"
    FUNCTION_CALLING = "function_calling"
    WEB_SEARCH = "web_search"
    FILE_OPERATIONS = "file_operations"
    SYSTEM_COMMANDS = "system_commands"
    VISION = "vision"
    MCP_INTEGRATION = "mcp_integration"
    ORCHESTRATION = "orchestration"


@dataclass
class AgentRequest:
    """Request to the agent"""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    mode: AgentMode = AgentMode.CHAT
    context: Dict[str, Any] = field(default_factory=dict)
    capabilities_required: List[AgentCapability] = field(default_factory=list)
    preferred_provider: Optional[LLMProvider] = None
    stream: bool = False
    max_tokens: Optional[int] = None
    temperature: float = 0.7
    use_memory: bool = True
    use_reasoning: bool = False
    timeout: float = 60.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Response from the agent"""
    request_id: str
    content: str
    success: bool
    mode: AgentMode
    provider_used: Optional[LLMProvider] = None
    reasoning_result: Optional[ReasoningResult] = None
    function_calls: List[Dict[str, Any]] = field(default_factory=list)
    execution_time: float = 0.0
    tokens_used: Optional[Dict[str, int]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class AgentConfig:
    """Configuration for the agent"""
    name: str = "LocalAIAgent"
    description: str = "Local AI Agent with multi-provider LLM support"
    default_mode: AgentMode = AgentMode.CHAT
    default_provider: LLMProvider = LLMProvider.OLLAMA
    enable_reasoning: bool = True
    enable_memory: bool = True
    enable_function_calling: bool = True
    max_conversation_length: int = 50
    default_timeout: float = 60.0
    llm_manager_config: Optional[LLMManagerConfig] = None
    mcp_configs: Optional[Dict[str, Any]] = None  # MCP client configurations
    capabilities: List[AgentCapability] = field(default_factory=lambda: [
        AgentCapability.NATURAL_LANGUAGE,
        AgentCapability.REASONING,
        AgentCapability.MEMORY,
        AgentCapability.FUNCTION_CALLING,
        AgentCapability.MCP_INTEGRATION
    ])


class Agent:
    """
    Core AI Agent with multi-provider LLM support.
    
    Features:
    - Multi-provider LLM integration (Ollama, OpenAI, Anthropic, Gemini)
    - Advanced reasoning capabilities
    - Memory and context management
    - Function calling support
    - MCP protocol integration (planned)
    - Streaming responses
    - Conversation management
    """
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.agent_id = str(uuid.uuid4())
        
        # Core components
        self.llm_manager: Optional[LLMManager] = None
        self.reasoning_engine: Optional[ReasoningEngine] = None
        self.context_manager: Optional[ContextManager] = None
        self.memory_store: Optional[MemoryStore] = None
        self.mcp_manager: Optional[MCPClientManager] = None
        self.orchestrator: Optional['MCPOrchestrator'] = None
        
        # State management
        self.conversations: Dict[str, List[Message]] = {}
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self._initialized = False
        
        # Function registry
        self.functions: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"Agent {self.config.name} created with ID: {self.agent_id}")
    
    async def initialize(self) -> bool:
        """Initialize the agent and all its components"""
        try:
            # Initialize LLM Manager
            if self.config.llm_manager_config:
                self.llm_manager = LLMManager(self.config.llm_manager_config)
                if not await self.llm_manager.initialize():
                    logger.error("Failed to initialize LLM Manager")
                    return False
            else:
                logger.warning("No LLM Manager config provided")
            
            # Initialize reasoning engine
            if self.config.enable_reasoning:
                self.reasoning_engine = ReasoningEngine(
                    model_orchestrator=self.llm_manager,
                    memory_system=self.memory_store
                )
            
            # Initialize memory store
            if self.config.enable_memory:
                self.memory_store = MemoryStore()
                await self.memory_store.initialize()
            
            # Initialize context manager
            self.context_manager = ContextManager()
            await self.context_manager.initialize()
            
            # Initialize MCP client manager
            if self.config.mcp_configs:
                self.mcp_manager = MCPClientManager()
                if not await self.mcp_manager.initialize(self.config.mcp_configs):
                    logger.warning("No MCP clients initialized - some functionality may be limited")
                
                # Initialize orchestrator if MCP is available
                if self.mcp_manager:
                    from ..orchestration.mcp_orchestrator import MCPOrchestrator
                    self.orchestrator = MCPOrchestrator(self.mcp_manager)
                    await self.orchestrator.initialize()
                    logger.info("MCP Orchestrator initialized")
            else:
                logger.info("No MCP configs provided - MCP functionality disabled")
            
            self._initialized = True
            logger.info(f"Agent {self.config.name} initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the agent and cleanup resources"""
        try:
            if self.llm_manager:
                await self.llm_manager.shutdown()
            
            if self.memory_store:
                await self.memory_store.shutdown()
            
            if self.context_manager:
                await self.context_manager.shutdown()
            
            if self.orchestrator:
                await self.orchestrator.shutdown()
            
            if self.mcp_manager:
                await self.mcp_manager.shutdown()
            
            self.conversations.clear()
            self.active_sessions.clear()
            self._initialized = False
            
            logger.info(f"Agent {self.config.name} shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during agent shutdown: {e}")
    
    async def process(self, request: AgentRequest) -> AgentResponse:
        """Process a request and return response"""
        if not self._initialized:
            return AgentResponse(
                request_id=request.request_id,
                content="Agent not initialized",
                success=False,
                mode=request.mode,
                error="Agent not initialized"
            )
        
        start_time = time.time()
        
        try:
            # Handle different request modes
            if request.mode == AgentMode.REASONING:
                return await self._process_reasoning_request(request)
            elif request.mode == AgentMode.TASK_EXECUTION:
                return await self._process_task_request(request)
            elif request.mode == AgentMode.ANALYSIS:
                return await self._process_analysis_request(request)
            else:
                # Default chat mode
                return await self._process_chat_request(request)
                
        except Exception as e:
            logger.error(f"Error processing request {request.request_id}: {e}")
            return AgentResponse(
                request_id=request.request_id,
                content=f"Error processing request: {str(e)}",
                success=False,
                mode=request.mode,
                execution_time=time.time() - start_time,
                error=str(e)
            )
    
    async def process_stream(self, request: AgentRequest) -> AsyncIterator[str]:
        """Process a request with streaming response"""
        if not self._initialized:
            yield "Error: Agent not initialized"
            return
        
        if not self.llm_manager:
            yield "Error: No LLM Manager available"
            return
        
        try:
            # Build conversation context
            conversation_id = request.metadata.get('conversation_id', 'default')
            messages = self._build_conversation_context(request, conversation_id)
            
            # Stream response from LLM
            async for chunk in self.llm_manager.generate_stream(
                messages,
                preferred_provider=request.preferred_provider
            ):
                yield chunk
            
            # Update conversation history
            if request.use_memory:
                await self._update_conversation_history(conversation_id, messages)
                
        except Exception as e:
            yield f"Error: {str(e)}"
    
    async def _process_chat_request(self, request: AgentRequest) -> AgentResponse:
        """Process a chat request"""
        if not self.llm_manager:
            return AgentResponse(
                request_id=request.request_id,
                content="No LLM Manager available",
                success=False,
                mode=request.mode,
                error="No LLM Manager available"
            )
        
        # Build conversation context
        conversation_id = request.metadata.get('conversation_id', 'default')
        messages = self._build_conversation_context(request, conversation_id)
        
        # Generate response
        response = await self.llm_manager.generate(
            messages,
            preferred_provider=request.preferred_provider,
            stream=request.stream
        )
        
        # Update conversation history
        if request.use_memory:
            await self._update_conversation_history(conversation_id, messages, response)
        
        return AgentResponse(
            request_id=request.request_id,
            content=response.content,
            success=True,
            mode=request.mode,
            provider_used=response.provider,
            function_calls=[fc.__dict__ for fc in response.function_calls],
            tokens_used=response.usage,
            metadata=response.metadata or {}
        )
    
    async def _process_reasoning_request(self, request: AgentRequest) -> AgentResponse:
        """Process a reasoning request"""
        if not self.reasoning_engine:
            return AgentResponse(
                request_id=request.request_id,
                content="Reasoning engine not available",
                success=False,
                mode=request.mode,
                error="Reasoning engine not available"
            )
        
        # Create reasoning task
        reasoning_task = ReasoningTask(
            query=request.content,
            context=request.context,
            reasoning_modes=[ReasoningMode.CHAIN_OF_THOUGHT, ReasoningMode.LOGICAL_DEDUCTION],
            timeout=request.timeout,
            use_memory=request.use_memory
        )
        
        # Perform reasoning
        reasoning_result = await self.reasoning_engine.reason(reasoning_task)
        
        return AgentResponse(
            request_id=request.request_id,
            content=reasoning_result.conclusion,
            success=True,
            mode=request.mode,
            reasoning_result=reasoning_result,
            metadata={
                "reasoning_steps": len(reasoning_result.steps),
                "confidence": reasoning_result.confidence.value,
                "evidence_count": len(reasoning_result.evidence)
            }
        )
    
    async def _process_task_request(self, request: AgentRequest) -> AgentResponse:
        """Process a task execution request"""
        # For now, delegate to chat processing
        # In future, this could involve task planning and execution
        request.mode = AgentMode.CHAT
        return await self._process_chat_request(request)
    
    async def _process_analysis_request(self, request: AgentRequest) -> AgentResponse:
        """Process an analysis request"""
        # Combine chat processing with reasoning for analysis
        chat_response = await self._process_chat_request(request)
        
        if self.reasoning_engine and request.use_reasoning:
            reasoning_task = ReasoningTask(
                query=f"Analyze: {request.content}",
                context=request.context,
                reasoning_modes=[ReasoningMode.CAUSAL_ANALYSIS, ReasoningMode.LOGICAL_DEDUCTION],
                timeout=request.timeout,
                use_memory=request.use_memory
            )
            
            reasoning_result = await self.reasoning_engine.reason(reasoning_task)
            chat_response.reasoning_result = reasoning_result
            chat_response.content += f"\n\nAnalysis: {reasoning_result.conclusion}"
        
        return chat_response
    
    def _build_conversation_context(self, request: AgentRequest, conversation_id: str) -> List[Message]:
        """Build conversation context from request and history"""
        messages = []
        
        # Add system message if needed
        if request.mode != AgentMode.CHAT:
            system_content = self._get_system_prompt(request.mode)
            messages.append(Message(
                role=MessageRole.SYSTEM,
                content=system_content
            ))
        
        # Add conversation history
        if conversation_id in self.conversations:
            messages.extend(self.conversations[conversation_id][-self.config.max_conversation_length:])
        
        # Add current request
        messages.append(Message(
            role=MessageRole.USER,
            content=request.content,
            metadata=request.metadata
        ))
        
        return messages
    
    def _get_system_prompt(self, mode: AgentMode) -> str:
        """Get system prompt for different modes"""
        prompts = {
            AgentMode.REASONING: "You are an AI assistant focused on logical reasoning and analysis. Provide step-by-step reasoning for your conclusions.",
            AgentMode.TASK_EXECUTION: "You are an AI assistant that helps execute tasks efficiently. Break down complex tasks into actionable steps.",
            AgentMode.ANALYSIS: "You are an AI assistant specialized in analysis. Provide thorough, structured analysis of the given information.",
            AgentMode.AUTOMATION: "You are an AI assistant that helps automate workflows and processes. Focus on efficiency and automation solutions.",
            AgentMode.DEBUG: "You are an AI assistant that helps debug issues and problems. Provide systematic troubleshooting approaches."
        }
        return prompts.get(mode, "You are a helpful AI assistant.")
    
    async def _update_conversation_history(
        self, 
        conversation_id: str, 
        messages: List[Message],
        response: Optional[LLMResponse] = None
    ):
        """Update conversation history"""
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []
        
        # Add user message if not already in history
        user_message = messages[-1]  # Last message is the current request
        self.conversations[conversation_id].append(user_message)
        
        # Add assistant response if provided
        if response:
            assistant_message = Message(
                role=MessageRole.ASSISTANT,
                content=response.content,
                metadata={
                    "provider": response.provider.value,
                    "model": response.model,
                    "function_calls": [fc.__dict__ for fc in response.function_calls] if response.function_calls else []
                }
            )
            self.conversations[conversation_id].append(assistant_message)
        
        # Trim conversation if too long
        max_length = self.config.max_conversation_length * 2  # User + assistant pairs
        if len(self.conversations[conversation_id]) > max_length:
            # Keep recent messages and any system messages
            system_messages = [msg for msg in self.conversations[conversation_id] if msg.role == MessageRole.SYSTEM]
            recent_messages = self.conversations[conversation_id][-max_length:]
            self.conversations[conversation_id] = system_messages + recent_messages
    
    def register_function(self, name: str, function_def: Dict[str, Any]):
        """Register a function for function calling"""
        self.functions[name] = function_def
        logger.info(f"Registered function: {name}")
    
    def get_available_functions(self) -> List[Dict[str, Any]]:
        """Get list of available functions"""
        return list(self.functions.values())
    
    def get_capabilities(self) -> List[AgentCapability]:
        """Get agent capabilities"""
        return self.config.capabilities.copy()
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent status"""
        status = {
            "agent_id": self.agent_id,
            "name": self.config.name,
            "initialized": self._initialized,
            "mode": self.config.default_mode.value,
            "capabilities": [cap.value for cap in self.config.capabilities],
            "active_conversations": len(self.conversations),
            "active_sessions": len(self.active_sessions),
            "functions_registered": len(self.functions)
        }
        
        if self.llm_manager:
            status["llm_providers"] = self.llm_manager.get_provider_status()
        
        if self.orchestrator:
            status["orchestrator"] = {
                "initialized": True,
                "active_workflows": len(self.orchestrator.active_workflows),
                "completed_workflows": len(self.orchestrator.execution_history)
            }
        
        return status
    
    async def create_session(self, session_config: Optional[Dict[str, Any]] = None) -> str:
        """Create a new agent session"""
        session_id = str(uuid.uuid4())
        
        self.active_sessions[session_id] = {
            "created_at": time.time(),
            "config": session_config or {},
            "conversation_id": session_config.get('conversation_id', session_id) if session_config else session_id,
            "metadata": {}
        }
        
        logger.info(f"Created session: {session_id}")
        return session_id
    
    async def end_session(self, session_id: str):
        """End an agent session"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            conversation_id = session.get('conversation_id')
            
            # Optionally save conversation to memory
            if conversation_id in self.conversations and self.memory_store:
                await self._save_conversation_to_memory(conversation_id)
            
            del self.active_sessions[session_id]
            logger.info(f"Ended session: {session_id}")
    
    async def _save_conversation_to_memory(self, conversation_id: str):
        """Save conversation to long-term memory"""
        if not self.memory_store or conversation_id not in self.conversations:
            return
        
        try:
            conversation = self.conversations[conversation_id]
            conversation_summary = f"Conversation with {len(conversation)} messages"
            
            # Save to memory store
            await self.memory_store.store_memory(
                content=conversation_summary,
                memory_type="conversation",
                metadata={
                    "conversation_id": conversation_id,
                    "message_count": len(conversation),
                    "timestamp": time.time()
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to save conversation to memory: {e}")


# Utility functions for creating common configurations
def create_basic_agent_config(
    providers: List[LLMProvider] = None,
    enable_reasoning: bool = True,
    enable_memory: bool = True,
    enable_mcp: bool = True
) -> AgentConfig:
    """Create a basic agent configuration"""
    if providers is None:
        providers = [LLMProvider.OLLAMA]
    
    # Create LLM Manager config
    llm_manager_config = LLMManagerConfig()
    
    # Add basic provider configs (would need actual API keys in real usage)
    for provider in providers:
        if provider == LLMProvider.OLLAMA:
            llm_manager_config.provider_configs[provider] = LLMConfig(
                provider=provider,
                model="llama3.1:8b",
                base_url="http://localhost:11434"
            )
        # Add other providers as needed
    
    # Create MCP configurations
    mcp_configs = None
    if enable_mcp:
        mcp_configs = {
            "filesystem": MCPClientConfig(
                servers=[MCPServerConfig(
                    name="filesystem",
                    url="ws://localhost:8765",
                    enabled=True
                )]
            ),
            "desktop": MCPClientConfig(
                servers=[MCPServerConfig(
                    name="desktop",
                    url="ws://localhost:8766",
                    enabled=True
                )]
            ),
            "system": MCPClientConfig(
                servers=[MCPServerConfig(
                    name="system",
                    url="ws://localhost:8767",
                    enabled=True
                )]
            )
        }
    
    return AgentConfig(
        llm_manager_config=llm_manager_config,
        enable_reasoning=enable_reasoning,
        enable_memory=enable_memory,
        mcp_configs=mcp_configs
    )


async def create_agent(config: Optional[AgentConfig] = None) -> Agent:
    """Create and initialize an agent"""
    if config is None:
        config = create_basic_agent_config()
    
    agent = Agent(config)
    await agent.initialize()
    return agent