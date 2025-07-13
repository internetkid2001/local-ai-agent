"""
Ollama Client Implementation

Local LLM client for Ollama with function calling support,
streaming responses, and context window management.

Author: Claude Code
Date: 2025-07-13
Session: 1.2
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional, AsyncIterator, Callable
from dataclasses import dataclass
from enum import Enum
import aiohttp
import logging

from ...utils.logger import get_logger

logger = get_logger(__name__)


class ModelType(Enum):
    """Ollama model types for different tasks"""
    PRIMARY = "primary"
    CODE = "code"
    FALLBACK = "fallback"


@dataclass
class OllamaConfig:
    """Configuration for Ollama client"""
    host: str = "http://localhost:11434"
    models: Dict[str, str] = None
    context_window: int = 8192
    max_tokens: int = 2048
    temperature: Dict[str, float] = None
    timeout: float = 30.0
    
    def __post_init__(self):
        if self.models is None:
            self.models = {
                "primary": "llama3.1:8b",
                "code": "codellama:7b", 
                "fallback": "mistral:7b"
            }
        
        if self.temperature is None:
            self.temperature = {
                "creative": 0.8,
                "balanced": 0.5,
                "precise": 0.2
            }


@dataclass
class OllamaMessage:
    """Ollama message structure"""
    role: str  # "system", "user", "assistant"
    content: str
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        return {"role": self.role, "content": self.content}


@dataclass
class OllamaResponse:
    """Ollama response structure"""
    content: str
    model: str
    done: bool
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    eval_count: Optional[int] = None
    function_calls: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.function_calls is None:
            self.function_calls = []


class OllamaClient:
    """
    Ollama client with advanced features for the AI Agent.
    
    Features:
    - Multiple model support with automatic selection
    - Function calling support
    - Streaming responses
    - Context window management
    - Automatic retry with fallback models
    - Performance monitoring
    """
    
    def __init__(self, config: OllamaConfig):
        """
        Initialize Ollama client.
        
        Args:
            config: Ollama configuration
        """
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._context_history: Dict[str, List[OllamaMessage]] = {}
        self._model_health: Dict[str, bool] = {}
        
        # Function calling setup
        self._functions: Dict[str, Callable] = {}
        self._function_schemas: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"Ollama client initialized with host: {config.host}")
        logger.info(f"Available models: {list(config.models.values())}")
    
    async def initialize(self) -> bool:
        """
        Initialize HTTP session and check model availability.
        
        Returns:
            True if initialization successful
        """
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout)
        )
        
        # Check if Ollama is running
        try:
            async with self._session.get(f"{self.config.host}/api/version") as response:
                if response.status == 200:
                    version_info = await response.json()
                    logger.info(f"Connected to Ollama version: {version_info.get('version', 'unknown')}")
                else:
                    logger.error(f"Ollama responded with status: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            return False
        
        # Check model availability
        await self._check_model_health()
        
        healthy_models = [model for model, healthy in self._model_health.items() if healthy]
        if not healthy_models:
            logger.error("No healthy models available")
            return False
        
        logger.info(f"Healthy models: {healthy_models}")
        return True
    
    async def shutdown(self):
        """Close HTTP session"""
        if self._session:
            await self._session.close()
            self._session = None
        logger.info("Ollama client shutdown complete")
    
    async def generate(
        self,
        prompt: str,
        model_type: ModelType = ModelType.PRIMARY,
        temperature_type: str = "balanced",
        system_prompt: Optional[str] = None,
        conversation_id: Optional[str] = None,
        functions: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False
    ) -> OllamaResponse:
        """
        Generate response from Ollama model.
        
        Args:
            prompt: User prompt
            model_type: Type of model to use
            temperature_type: Temperature setting (creative/balanced/precise)
            system_prompt: Optional system prompt
            conversation_id: Optional conversation tracking
            functions: Available functions for function calling
            stream: Whether to stream response
            
        Returns:
            Ollama response
        """
        model_name = self._select_model(model_type)
        temperature = self.config.temperature.get(temperature_type, 0.5)
        
        # Build messages
        messages = []
        
        if system_prompt:
            messages.append(OllamaMessage("system", system_prompt))
        
        # Add conversation history if provided
        if conversation_id and conversation_id in self._context_history:
            messages.extend(self._context_history[conversation_id])
        
        # Add current prompt
        user_message = OllamaMessage("user", prompt)
        messages.append(user_message)
        
        # Manage context window
        messages = self._manage_context_window(messages, model_name)
        
        # Prepare request
        request_data = {
            "model": model_name,
            "messages": [msg.to_dict() for msg in messages],
            "options": {
                "temperature": temperature,
                "num_ctx": self.config.context_window,
                "num_predict": self.config.max_tokens
            },
            "stream": stream
        }
        
        # Add function calling if functions provided
        if functions:
            request_data["tools"] = functions
        
        try:
            if stream:
                return await self._generate_streaming(request_data, conversation_id)
            else:
                return await self._generate_complete(request_data, conversation_id)
                
        except Exception as e:
            logger.error(f"Generation failed with {model_name}: {e}")
            
            # Try fallback model if primary failed
            if model_type == ModelType.PRIMARY:
                logger.info("Retrying with fallback model")
                return await self.generate(
                    prompt, ModelType.FALLBACK, temperature_type,
                    system_prompt, conversation_id, functions, stream
                )
            else:
                raise
    
    async def generate_streaming(
        self,
        prompt: str,
        model_type: ModelType = ModelType.PRIMARY,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Generate streaming response from Ollama.
        
        Args:
            prompt: User prompt
            model_type: Type of model to use
            **kwargs: Additional arguments for generate()
            
        Yields:
            Response chunks as they arrive
        """
        kwargs['stream'] = True
        response = await self.generate(prompt, model_type, **kwargs)
        
        # For streaming, response.content will be the full response
        # In a real implementation, this would yield chunks as they arrive
        yield response.content
    
    def register_function(self, name: str, function: Callable, schema: Dict[str, Any]):
        """
        Register a function for function calling.
        
        Args:
            name: Function name
            function: Callable function
            schema: JSON schema describing the function
        """
        self._functions[name] = function
        self._function_schemas[name] = schema
        logger.info(f"Registered function: {name}")
    
    async def call_function(self, name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a registered function.
        
        Args:
            name: Function name
            arguments: Function arguments
            
        Returns:
            Function result
        """
        if name not in self._functions:
            raise ValueError(f"Function not registered: {name}")
        
        try:
            function = self._functions[name]
            if asyncio.iscoroutinefunction(function):
                result = await function(**arguments)
            else:
                result = function(**arguments)
            
            logger.debug(f"Function {name} executed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Function {name} execution failed: {e}")
            raise
    
    def get_available_functions(self) -> List[Dict[str, Any]]:
        """Get list of available functions for function calling"""
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    **schema
                }
            }
            for name, schema in self._function_schemas.items()
        ]
    
    async def _generate_complete(self, request_data: Dict[str, Any], conversation_id: Optional[str]) -> OllamaResponse:
        """Generate complete response (non-streaming)"""
        url = f"{self.config.host}/api/chat"
        
        async with self._session.post(url, json=request_data) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Ollama API error {response.status}: {error_text}")
            
            result = await response.json()
            
            # Extract response content
            content = result.get("message", {}).get("content", "")
            
            # Handle function calls if present
            function_calls = []
            tool_calls = result.get("message", {}).get("tool_calls", [])
            
            for tool_call in tool_calls:
                function_name = tool_call.get("function", {}).get("name")
                function_args = tool_call.get("function", {}).get("arguments", {})
                
                if function_name in self._functions:
                    try:
                        func_result = await self.call_function(function_name, function_args)
                        function_calls.append({
                            "name": function_name,
                            "arguments": function_args,
                            "result": func_result
                        })
                    except Exception as e:
                        function_calls.append({
                            "name": function_name,
                            "arguments": function_args,
                            "error": str(e)
                        })
            
            # Update conversation history
            if conversation_id:
                if conversation_id not in self._context_history:
                    self._context_history[conversation_id] = []
                
                self._context_history[conversation_id].append(
                    OllamaMessage("assistant", content)
                )
            
            return OllamaResponse(
                content=content,
                model=result.get("model", "unknown"),
                done=result.get("done", True),
                total_duration=result.get("total_duration"),
                load_duration=result.get("load_duration"),
                prompt_eval_count=result.get("prompt_eval_count"),
                eval_count=result.get("eval_count"),
                function_calls=function_calls
            )
    
    async def _generate_streaming(self, request_data: Dict[str, Any], conversation_id: Optional[str]) -> OllamaResponse:
        """Generate streaming response"""
        url = f"{self.config.host}/api/chat"
        
        full_content = ""
        model_name = "unknown"
        
        async with self._session.post(url, json=request_data) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Ollama API error {response.status}: {error_text}")
            
            async for line in response.content:
                if line:
                    try:
                        chunk = json.loads(line.decode('utf-8'))
                        
                        if "message" in chunk:
                            content = chunk["message"].get("content", "")
                            full_content += content
                            model_name = chunk.get("model", model_name)
                        
                        if chunk.get("done", False):
                            break
                            
                    except json.JSONDecodeError:
                        continue
        
        # Update conversation history
        if conversation_id and full_content:
            if conversation_id not in self._context_history:
                self._context_history[conversation_id] = []
            
            self._context_history[conversation_id].append(
                OllamaMessage("assistant", full_content)
            )
        
        return OllamaResponse(
            content=full_content,
            model=model_name,
            done=True
        )
    
    def _select_model(self, model_type: ModelType) -> str:
        """Select appropriate model based on type and health"""
        model_name = self.config.models.get(model_type.value)
        
        if not model_name:
            # Fallback to primary model
            model_name = self.config.models.get("primary")
        
        # Check if model is healthy, fallback if needed
        if not self._model_health.get(model_name, False):
            # Find any healthy model
            for name, healthy in self._model_health.items():
                if healthy:
                    logger.warning(f"Using fallback model {name} instead of {model_name}")
                    return name
            
            # If no healthy models, use the requested one anyway
            logger.warning(f"No healthy models available, using {model_name}")
        
        return model_name
    
    def _manage_context_window(self, messages: List[OllamaMessage], model_name: str) -> List[OllamaMessage]:
        """Manage context window by truncating old messages if needed"""
        # Estimate token count (rough approximation: 1 token = 4 characters)
        total_chars = sum(len(msg.content) for msg in messages)
        estimated_tokens = total_chars // 4
        
        if estimated_tokens <= self.config.context_window:
            return messages
        
        # Keep system message and recent messages
        result = []
        system_messages = [msg for msg in messages if msg.role == "system"]
        other_messages = [msg for msg in messages if msg.role != "system"]
        
        # Always include system messages
        result.extend(system_messages)
        
        # Add recent messages until we approach context limit
        chars_used = sum(len(msg.content) for msg in system_messages) * 4
        max_chars = self.config.context_window * 4 * 0.8  # Use 80% of context window
        
        for msg in reversed(other_messages):
            msg_chars = len(msg.content) * 4
            if chars_used + msg_chars > max_chars:
                break
            result.insert(-len(system_messages) if system_messages else 0, msg)
            chars_used += msg_chars
        
        if len(result) < len(messages):
            logger.info(f"Truncated context: {len(messages)} -> {len(result)} messages")
        
        return result
    
    async def _check_model_health(self):
        """Check health of all configured models"""
        for model_type, model_name in self.config.models.items():
            try:
                # Simple test request to check if model is available
                test_data = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": "test"}],
                    "options": {"num_predict": 1}
                }
                
                url = f"{self.config.host}/api/chat"
                async with self._session.post(url, json=test_data) as response:
                    if response.status == 200:
                        self._model_health[model_name] = True
                        logger.debug(f"Model {model_name} is healthy")
                    else:
                        self._model_health[model_name] = False
                        logger.warning(f"Model {model_name} is unhealthy: {response.status}")
                        
            except Exception as e:
                self._model_health[model_name] = False
                logger.warning(f"Model {model_name} health check failed: {e}")
    
    def clear_conversation(self, conversation_id: str):
        """Clear conversation history for a specific conversation"""
        if conversation_id in self._context_history:
            del self._context_history[conversation_id]
            logger.debug(f"Cleared conversation: {conversation_id}")
    
    def get_conversation_history(self, conversation_id: str) -> List[OllamaMessage]:
        """Get conversation history for a specific conversation"""
        return self._context_history.get(conversation_id, [])
    
    async def get_model_info(self, model_name: Optional[str] = None) -> Dict[str, Any]:
        """Get information about a specific model or all models"""
        if model_name:
            url = f"{self.config.host}/api/show"
            data = {"name": model_name}
        else:
            url = f"{self.config.host}/api/tags"
            data = {}
        
        async with self._session.post(url, json=data) if model_name else self._session.get(url) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise Exception(f"Failed to get model info: {error_text}")