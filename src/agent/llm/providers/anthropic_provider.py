"""
Anthropic Provider Implementation

Support for Claude models with function calling and streaming.
"""

import json
import logging
from typing import Dict, List, Any, Optional, AsyncIterator
import aiohttp

from .base import (
    BaseLLMProvider, LLMConfig, LLMProvider, Message, LLMResponse, 
    FunctionCall, MessageRole, LLMProviderError, LLMProviderConnectionError,
    LLMProviderRateLimitError, LLMProviderAuthenticationError
)

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider implementation"""
    
    BASE_URL = "https://api.anthropic.com/v1"
    
    # Model context windows
    CONTEXT_WINDOWS = {
        "claude-3-opus-20240229": 200000,
        "claude-3-sonnet-20240229": 200000,
        "claude-3-haiku-20240307": 200000,
        "claude-2.1": 200000,
        "claude-2.0": 100000,
        "claude-instant-1.2": 100000,
    }
    
    # Models that support vision
    VISION_MODELS = {
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307"
    }
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        if not config.api_key:
            raise ValueError("Anthropic API key is required")
        
        self.api_key = config.api_key
        self.base_url = config.base_url or self.BASE_URL
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self) -> bool:
        """Initialize the Anthropic provider"""
        self._session = aiohttp.ClientSession(
            headers={
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            },
            timeout=aiohttp.ClientTimeout(total=self.config.timeout)
        )
        
        # Test connection by trying to get model info
        try:
            # Anthropic doesn't have a models endpoint, so we'll test with a simple message
            test_data = {
                "model": self.config.model,
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "Hi"}]
            }
            
            async with self._session.post(f"{self.base_url}/messages", json=test_data) as response:
                if response.status in [200, 400]:  # 400 is also OK for testing
                    self._initialized = True
                    logger.info("Anthropic provider initialized successfully")
                    return True
                elif response.status == 401:
                    raise LLMProviderAuthenticationError("Invalid Anthropic API key")
                else:
                    raise LLMProviderConnectionError(f"Anthropic API error: {response.status}")
        except aiohttp.ClientError as e:
            raise LLMProviderConnectionError(f"Failed to connect to Anthropic: {e}")
    
    async def shutdown(self):
        """Shutdown the provider"""
        if self._session:
            await self._session.close()
            self._session = None
        self._initialized = False
        logger.info("Anthropic provider shutdown")
    
    async def generate(
        self,
        messages: List[Message],
        functions: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
        **kwargs
    ) -> LLMResponse:
        """Generate response from Anthropic Claude"""
        if not self._initialized:
            raise LLMProviderError("Provider not initialized")
        
        # Convert messages to Anthropic format
        anthropic_messages, system_prompt = self._convert_messages_to_anthropic_format(messages)
        
        # Prepare request data
        request_data = {
            "model": self.config.model,
            "messages": anthropic_messages,
            "max_tokens": self.config.max_tokens or 4096,
            "stream": stream
        }
        
        # Add system prompt if present
        if system_prompt:
            request_data["system"] = system_prompt
        
        # Add temperature
        if self.config.temperature is not None:
            request_data["temperature"] = self.config.temperature
        
        # Add top_p
        if self.config.top_p is not None:
            request_data["top_p"] = self.config.top_p
        
        # Add tools (functions) if provided
        if functions:
            request_data["tools"] = self._convert_functions_to_anthropic_tools(functions)
        
        # Add custom parameters
        if self.config.custom_params:
            request_data.update(self.config.custom_params)
        
        try:
            if stream:
                return await self._generate_streaming(request_data)
            else:
                return await self._generate_complete(request_data)
        
        except aiohttp.ClientResponseError as e:
            if e.status == 429:
                raise LLMProviderRateLimitError("Anthropic rate limit exceeded")
            elif e.status == 401:
                raise LLMProviderAuthenticationError("Anthropic authentication failed")
            else:
                raise LLMProviderError(f"Anthropic API error: {e}")
    
    async def generate_stream(
        self,
        messages: List[Message],
        functions: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Generate streaming response from Anthropic"""
        response = await self.generate(messages, functions, stream=True, **kwargs)
        yield response.content
    
    async def count_tokens(self, text: str) -> int:
        """Count tokens (rough approximation for Anthropic)"""
        # Anthropic doesn't provide a public tokenizer
        # Using rough approximation: ~4 characters per token
        return len(text) // 4
    
    async def get_available_models(self) -> List[str]:
        """Get list of available Anthropic models"""
        # Anthropic doesn't have a models endpoint, return known models
        return [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229", 
            "claude-3-haiku-20240307",
            "claude-2.1",
            "claude-2.0",
            "claude-instant-1.2"
        ]
    
    def supports_vision(self) -> bool:
        """Check if current model supports vision"""
        return self.config.model in self.VISION_MODELS
    
    def get_context_window(self) -> int:
        """Get context window for current model"""
        return self.CONTEXT_WINDOWS.get(self.config.model, 100000)
    
    async def _generate_complete(self, request_data: Dict[str, Any]) -> LLMResponse:
        """Generate complete response (non-streaming)"""
        async with self._session.post(f"{self.base_url}/messages", json=request_data) as response:
            if response.status != 200:
                error_text = await response.text()
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message=error_text
                )
            
            data = await response.json()
            return self._convert_anthropic_response(data)
    
    async def _generate_streaming(self, request_data: Dict[str, Any]) -> LLMResponse:
        """Generate streaming response"""
        full_content = ""
        function_calls = []
        finish_reason = None
        usage = None
        model = self.config.model
        
        async with self._session.post(f"{self.base_url}/messages", json=request_data) as response:
            if response.status != 200:
                error_text = await response.text()
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message=error_text
                )
            
            async for line in response.content:
                if line:
                    line_text = line.decode('utf-8').strip()
                    if line_text.startswith('data: '):
                        data_text = line_text[6:]
                        if data_text == '[DONE]':
                            break
                        
                        try:
                            chunk = json.loads(data_text)
                            
                            # Handle different event types
                            event_type = chunk.get('type')
                            
                            if event_type == 'content_block_delta':
                                delta = chunk.get('delta', {})
                                if delta.get('type') == 'text_delta':
                                    full_content += delta.get('text', '')
                            
                            elif event_type == 'message_start':
                                message = chunk.get('message', {})
                                model = message.get('model', model)
                                usage = message.get('usage', usage)
                            
                            elif event_type == 'message_delta':
                                delta = chunk.get('delta', {})
                                if 'stop_reason' in delta:
                                    finish_reason = delta['stop_reason']
                                if 'usage' in delta:
                                    usage = delta['usage']
                            
                            # Handle tool use (function calls)
                            elif event_type == 'content_block_start':
                                content_block = chunk.get('content_block', {})
                                if content_block.get('type') == 'tool_use':
                                    func_call = FunctionCall(
                                        name=content_block.get('name', ''),
                                        arguments=content_block.get('input', {}),
                                        call_id=content_block.get('id')
                                    )
                                    function_calls.append(func_call)
                        
                        except json.JSONDecodeError:
                            continue
        
        return LLMResponse(
            content=full_content,
            provider=LLMProvider.ANTHROPIC,
            model=model,
            finish_reason=finish_reason,
            function_calls=function_calls,
            usage=usage
        )
    
    def _convert_messages_to_anthropic_format(self, messages: List[Message]) -> tuple[List[Dict[str, Any]], Optional[str]]:
        """Convert universal messages to Anthropic format"""
        anthropic_messages = []
        system_prompt = None
        
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                # Anthropic handles system messages separately
                system_prompt = msg.content
            else:
                anthropic_msg = {
                    "role": msg.role.value,
                    "content": msg.content
                }
                anthropic_messages.append(anthropic_msg)
        
        return anthropic_messages, system_prompt
    
    def _convert_functions_to_anthropic_tools(self, functions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert function schemas to Anthropic tools format"""
        tools = []
        
        for func in functions:
            tool = {
                "name": func["name"],
                "description": func.get("description", ""),
                "input_schema": func.get("parameters", {})
            }
            tools.append(tool)
        
        return tools
    
    def _convert_anthropic_response(self, response_data: Dict[str, Any]) -> LLMResponse:
        """Convert Anthropic response to universal format"""
        content = ""
        function_calls = []
        
        # Extract content from content blocks
        for content_block in response_data.get("content", []):
            if content_block["type"] == "text":
                content += content_block["text"]
            elif content_block["type"] == "tool_use":
                func_call = FunctionCall(
                    name=content_block["name"],
                    arguments=content_block["input"],
                    call_id=content_block["id"]
                )
                function_calls.append(func_call)
        
        return LLMResponse(
            content=content,
            provider=LLMProvider.ANTHROPIC,
            model=response_data["model"],
            finish_reason=response_data.get("stop_reason"),
            function_calls=function_calls,
            usage=response_data.get("usage"),
            metadata={"response_id": response_data.get("id")}
        )