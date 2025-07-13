"""
Ollama Provider Implementation

Implements the universal LLM provider interface for Ollama local models
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional, AsyncIterator
import aiohttp
import logging

from .base import (
    BaseLLMProvider, LLMProvider, LLMConfig, Message, MessageRole, 
    LLMResponse, FunctionCall, LLMProviderError, LLMProviderConnectionError
)

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    """Ollama provider implementation"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = config.base_url or "http://localhost:11434"
        self._session: Optional[aiohttp.ClientSession] = None
        self._model_health: Dict[str, bool] = {}
        
    async def initialize(self) -> bool:
        """Initialize the Ollama provider"""
        try:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout)
            )
            
            # Check if Ollama is running
            async with self._session.get(f"{self.base_url}/api/version") as response:
                if response.status != 200:
                    logger.error(f"Ollama not accessible: {response.status}")
                    return False
                
                version_info = await response.json()
                logger.info(f"Connected to Ollama version: {version_info.get('version', 'unknown')}")
            
            # Check if model is available
            await self._check_model_availability()
            
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Ollama provider: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the provider"""
        if self._session:
            await self._session.close()
            self._session = None
        self._initialized = False
    
    async def generate(
        self,
        messages: List[Message],
        functions: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
        **kwargs
    ) -> LLMResponse:
        """Generate response from Ollama"""
        if not self._initialized:
            raise LLMProviderConnectionError("Provider not initialized")
        
        try:
            # Convert messages to Ollama format
            ollama_messages = self._convert_messages_to_ollama_format(messages)
            
            # Prepare request
            request_data = {
                "model": self.config.model,
                "messages": ollama_messages,
                "options": {
                    "temperature": self.config.temperature,
                    "num_ctx": getattr(self.config, 'context_window', 8192),
                },
                "stream": False  # We handle streaming separately
            }
            
            if self.config.max_tokens:
                request_data["options"]["num_predict"] = self.config.max_tokens
            
            # Add function calling if supported and functions provided
            if functions and self.supports_function_calling():
                request_data["tools"] = self._convert_functions_to_ollama_format(functions)
            
            # Generate response
            url = f"{self.base_url}/api/chat"
            async with self._session.post(url, json=request_data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise LLMProviderConnectionError(f"Ollama API error {response.status}: {error_text}")
                
                result = await response.json()
                return self._convert_ollama_response(result)
                
        except Exception as e:
            if isinstance(e, LLMProviderError):
                raise
            raise LLMProviderConnectionError(f"Ollama generation failed: {e}")
    
    async def generate_stream(
        self,
        messages: List[Message],
        functions: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Generate streaming response from Ollama"""
        if not self._initialized:
            raise LLMProviderConnectionError("Provider not initialized")
        
        try:
            # Convert messages to Ollama format
            ollama_messages = self._convert_messages_to_ollama_format(messages)
            
            # Prepare request
            request_data = {
                "model": self.config.model,
                "messages": ollama_messages,
                "options": {
                    "temperature": self.config.temperature,
                    "num_ctx": getattr(self.config, 'context_window', 8192),
                },
                "stream": True
            }
            
            if self.config.max_tokens:
                request_data["options"]["num_predict"] = self.config.max_tokens
            
            if functions and self.supports_function_calling():
                request_data["tools"] = self._convert_functions_to_ollama_format(functions)
            
            # Generate streaming response
            url = f"{self.base_url}/api/chat"
            async with self._session.post(url, json=request_data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise LLMProviderConnectionError(f"Ollama API error {response.status}: {error_text}")
                
                async for line in response.content:
                    if line:
                        try:
                            chunk = json.loads(line.decode('utf-8'))
                            
                            if "message" in chunk:
                                content = chunk["message"].get("content", "")
                                if content:
                                    yield content
                            
                            if chunk.get("done", False):
                                break
                                
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            if isinstance(e, LLMProviderError):
                raise
            raise LLMProviderConnectionError(f"Ollama streaming failed: {e}")
    
    async def count_tokens(self, text: str) -> int:
        """Count tokens in text (approximation for Ollama)"""
        # Ollama doesn't have a direct token counting API
        # Use rough approximation: 1 token ≈ 4 characters
        return len(text) // 4
    
    async def get_available_models(self) -> List[str]:
        """Get list of available models"""
        if not self._initialized or not self._session:
            return []
        
        try:
            url = f"{self.base_url}/api/tags"
            async with self._session.get(url) as response:
                if response.status == 200:
                    result = await response.json()
                    models = result.get("models", [])
                    return [model["name"] for model in models]
                else:
                    logger.error(f"Failed to get models: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error getting available models: {e}")
            return []
    
    async def is_healthy(self) -> bool:
        """Check if provider is healthy"""
        if not self._initialized or not self._session:
            return False
        
        try:
            # Quick health check
            url = f"{self.base_url}/api/version"
            async with self._session.get(url) as response:
                return response.status == 200
                
        except Exception:
            return False
    
    def supports_function_calling(self) -> bool:
        """Check if provider supports function calling"""
        # Ollama supports function calling in newer versions
        # For now, we'll return True and handle gracefully if not supported
        return True
    
    def supports_streaming(self) -> bool:
        """Check if provider supports streaming"""
        return True
    
    def supports_vision(self) -> bool:
        """Check if provider supports vision"""
        # Some Ollama models support vision (like llava)
        vision_models = ["llava", "bakllava", "moondream"]
        return any(model in self.config.model.lower() for model in vision_models)
    
    def get_context_window(self) -> int:
        """Get model context window size"""
        # Default context window for Ollama models
        model_contexts = {
            "llama": 8192,
            "mistral": 8192,
            "codellama": 16384,
            "llava": 4096,
            "gemma": 8192,
            "qwen": 32768,
        }
        
        model_name = self.config.model.lower()
        for model_prefix, context_size in model_contexts.items():
            if model_prefix in model_name:
                return context_size
        
        # Default fallback
        return 8192
    
    def _convert_messages_to_ollama_format(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """Convert universal messages to Ollama format"""
        ollama_messages = []
        
        for msg in messages:
            ollama_msg = {
                "role": msg.role.value,
                "content": msg.content
            }
            
            # Handle function calls and tool calls
            if msg.function_call:
                ollama_msg["function_call"] = msg.function_call
            
            if msg.tool_calls:
                ollama_msg["tool_calls"] = msg.tool_calls
            
            ollama_messages.append(ollama_msg)
        
        return ollama_messages
    
    def _convert_functions_to_ollama_format(self, functions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert functions to Ollama tools format"""
        tools = []
        
        for func in functions:
            # Convert OpenAI-style function definition to Ollama format
            if "function" in func:
                # Already in tool format
                tools.append(func)
            else:
                # Convert from simple function format
                tool = {
                    "type": "function",
                    "function": func
                }
                tools.append(tool)
        
        return tools
    
    def _convert_ollama_response(self, response: Dict[str, Any]) -> LLMResponse:
        """Convert Ollama response to universal format"""
        message = response.get("message", {})
        content = message.get("content", "")
        
        # Extract function calls if present
        function_calls = []
        tool_calls = message.get("tool_calls", [])
        
        for tool_call in tool_calls:
            if tool_call.get("type") == "function":
                func_info = tool_call.get("function", {})
                function_calls.append(FunctionCall(
                    name=func_info.get("name", ""),
                    arguments=func_info.get("arguments", {}),
                    call_id=tool_call.get("id")
                ))
        
        # Extract usage information
        usage = {}
        if "prompt_eval_count" in response:
            usage["prompt_tokens"] = response["prompt_eval_count"]
        if "eval_count" in response:
            usage["completion_tokens"] = response["eval_count"]
        if usage:
            usage["total_tokens"] = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
        
        return LLMResponse(
            content=content,
            provider=LLMProvider.OLLAMA,
            model=response.get("model", self.config.model),
            finish_reason="stop" if response.get("done", False) else "length",
            function_calls=function_calls,
            usage=usage if usage else None,
            metadata={
                "total_duration": response.get("total_duration"),
                "load_duration": response.get("load_duration"),
                "eval_duration": response.get("eval_duration"),
            }
        )
    
    async def _check_model_availability(self):
        """Check if the configured model is available"""
        try:
            available_models = await self.get_available_models()
            
            if self.config.model not in available_models:
                logger.warning(f"Model {self.config.model} not found in available models: {available_models}")
                
                # Try to pull the model if it's not available
                await self._pull_model(self.config.model)
            else:
                logger.info(f"Model {self.config.model} is available")
                
        except Exception as e:
            logger.error(f"Error checking model availability: {e}")
    
    async def _pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama registry"""
        try:
            logger.info(f"Attempting to pull model: {model_name}")
            
            url = f"{self.base_url}/api/pull"
            request_data = {"name": model_name}
            
            async with self._session.post(url, json=request_data) as response:
                if response.status == 200:
                    # Monitor pull progress
                    async for line in response.content:
                        if line:
                            try:
                                chunk = json.loads(line.decode('utf-8'))
                                if chunk.get("status"):
                                    logger.debug(f"Pull status: {chunk['status']}")
                                if chunk.get("error"):
                                    logger.error(f"Pull error: {chunk['error']}")
                                    return False
                            except json.JSONDecodeError:
                                continue
                    
                    logger.info(f"Successfully pulled model: {model_name}")
                    return True
                else:
                    logger.error(f"Failed to pull model {model_name}: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error pulling model {model_name}: {e}")
            return False