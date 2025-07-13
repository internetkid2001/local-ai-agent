"""
OpenAI Provider Implementation

Support for OpenAI GPT models with function calling and streaming.
"""

import json
import logging
from typing import Dict, List, Any, Optional, AsyncIterator
import aiohttp
import tiktoken

from .base import (
    BaseLLMProvider, LLMConfig, LLMProvider, Message, LLMResponse, 
    FunctionCall, LLMProviderError, LLMProviderConnectionError,
    LLMProviderRateLimitError, LLMProviderAuthenticationError
)

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider implementation"""
    
    BASE_URL = "https://api.openai.com/v1"
    
    # Model context windows
    CONTEXT_WINDOWS = {
        "gpt-4": 8192,
        "gpt-4-32k": 32768,
        "gpt-4-1106-preview": 128000,
        "gpt-4-vision-preview": 128000,
        "gpt-3.5-turbo": 4096,
        "gpt-3.5-turbo-16k": 16384,
        "gpt-3.5-turbo-1106": 16385,
    }
    
    # Models that support vision
    VISION_MODELS = {
        "gpt-4-vision-preview",
        "gpt-4o",
        "gpt-4o-mini"
    }
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        if not config.api_key:
            raise ValueError("OpenAI API key is required")
        
        self.api_key = config.api_key
        self.base_url = config.base_url or self.BASE_URL
        self._session: Optional[aiohttp.ClientSession] = None
        self._tokenizer = None
        
        # Initialize tokenizer for token counting
        try:
            self._tokenizer = tiktoken.encoding_for_model(config.model)
        except KeyError:
            # Fallback to a default tokenizer
            self._tokenizer = tiktoken.get_encoding("cl100k_base")
    
    async def initialize(self) -> bool:
        """Initialize the OpenAI provider"""
        self._session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=aiohttp.ClientTimeout(total=self.config.timeout)
        )
        
        # Test connection
        try:
            async with self._session.get(f"{self.base_url}/models") as response:
                if response.status == 200:
                    self._initialized = True
                    logger.info("OpenAI provider initialized successfully")
                    return True
                elif response.status == 401:
                    raise LLMProviderAuthenticationError("Invalid OpenAI API key")
                else:
                    raise LLMProviderConnectionError(f"OpenAI API error: {response.status}")
        except aiohttp.ClientError as e:
            raise LLMProviderConnectionError(f"Failed to connect to OpenAI: {e}")
    
    async def shutdown(self):
        """Shutdown the provider"""
        if self._session:
            await self._session.close()
            self._session = None
        self._initialized = False
        logger.info("OpenAI provider shutdown")
    
    async def generate(
        self,
        messages: List[Message],
        functions: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
        **kwargs
    ) -> LLMResponse:
        """Generate response from OpenAI"""
        if not self._initialized:
            raise LLMProviderError("Provider not initialized")
        
        # Convert messages to OpenAI format
        openai_messages = self._convert_messages_to_openai_format(messages)
        
        # Prepare request data
        request_data = {
            "model": self.config.model,
            "messages": openai_messages,
            "temperature": self.config.temperature,
            "stream": stream
        }
        
        # Add optional parameters
        if self.config.max_tokens:
            request_data["max_tokens"] = self.config.max_tokens
        if self.config.top_p is not None:
            request_data["top_p"] = self.config.top_p
        if self.config.frequency_penalty is not None:
            request_data["frequency_penalty"] = self.config.frequency_penalty
        if self.config.presence_penalty is not None:
            request_data["presence_penalty"] = self.config.presence_penalty
        
        # Add functions if provided
        if functions:
            request_data["tools"] = [
                {"type": "function", "function": func} for func in functions
            ]
            request_data["tool_choice"] = "auto"
        
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
                raise LLMProviderRateLimitError("OpenAI rate limit exceeded")
            elif e.status == 401:
                raise LLMProviderAuthenticationError("OpenAI authentication failed")
            else:
                raise LLMProviderError(f"OpenAI API error: {e}")
    
    async def generate_stream(
        self,
        messages: List[Message],
        functions: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Generate streaming response from OpenAI"""
        response = await self.generate(messages, functions, stream=True, **kwargs)
        yield response.content
    
    async def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken"""
        if self._tokenizer:
            return len(self._tokenizer.encode(text))
        else:
            # Rough approximation if tokenizer not available
            return len(text.split()) * 1.3
    
    async def get_available_models(self) -> List[str]:
        """Get list of available OpenAI models"""
        if not self._initialized:
            return []
        
        try:
            async with self._session.get(f"{self.base_url}/models") as response:
                if response.status == 200:
                    data = await response.json()
                    return [model["id"] for model in data["data"]]
                else:
                    logger.error(f"Failed to get OpenAI models: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Error getting OpenAI models: {e}")
            return []
    
    def supports_vision(self) -> bool:
        """Check if current model supports vision"""
        return self.config.model in self.VISION_MODELS
    
    def get_context_window(self) -> int:
        """Get context window for current model"""
        return self.CONTEXT_WINDOWS.get(self.config.model, 4096)
    
    async def _generate_complete(self, request_data: Dict[str, Any]) -> LLMResponse:
        """Generate complete response (non-streaming)"""
        async with self._session.post(f"{self.base_url}/chat/completions", json=request_data) as response:
            if response.status != 200:
                error_text = await response.text()
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message=error_text
                )
            
            data = await response.json()
            return self._convert_openai_response(data)
    
    async def _generate_streaming(self, request_data: Dict[str, Any]) -> LLMResponse:
        """Generate streaming response"""
        full_content = ""
        function_calls = []
        finish_reason = None
        usage = None
        
        async with self._session.post(f"{self.base_url}/chat/completions", json=request_data) as response:
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
                            delta = chunk.get('choices', [{}])[0].get('delta', {})
                            
                            # Handle content
                            if 'content' in delta and delta['content']:
                                full_content += delta['content']
                            
                            # Handle function calls
                            if 'tool_calls' in delta:
                                for tool_call in delta['tool_calls']:
                                    if 'function' in tool_call:
                                        func_call = FunctionCall(
                                            name=tool_call['function']['name'],
                                            arguments=json.loads(tool_call['function']['arguments']),
                                            call_id=tool_call.get('id')
                                        )
                                        function_calls.append(func_call)
                            
                            # Handle finish reason
                            choice = chunk.get('choices', [{}])[0]
                            if 'finish_reason' in choice:
                                finish_reason = choice['finish_reason']
                            
                            # Handle usage (usually in last chunk)
                            if 'usage' in chunk:
                                usage = chunk['usage']
                        
                        except json.JSONDecodeError:
                            continue
        
        return LLMResponse(
            content=full_content,
            provider=LLMProvider.OPENAI,
            model=self.config.model,
            finish_reason=finish_reason,
            function_calls=function_calls,
            usage=usage
        )
    
    def _convert_messages_to_openai_format(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """Convert universal messages to OpenAI format"""
        openai_messages = []
        
        for msg in messages:
            openai_msg = {
                "role": msg.role.value,
                "content": msg.content
            }
            
            if msg.function_call:
                openai_msg["function_call"] = msg.function_call
            if msg.tool_calls:
                openai_msg["tool_calls"] = msg.tool_calls
            if msg.name:
                openai_msg["name"] = msg.name
            
            openai_messages.append(openai_msg)
        
        return openai_messages
    
    def _convert_openai_response(self, response_data: Dict[str, Any]) -> LLMResponse:
        """Convert OpenAI response to universal format"""
        choice = response_data["choices"][0]
        message = choice["message"]
        
        content = message.get("content", "")
        function_calls = []
        
        # Handle tool calls (function calls)
        tool_calls = message.get("tool_calls", [])
        for tool_call in tool_calls:
            if tool_call["type"] == "function":
                func_call = FunctionCall(
                    name=tool_call["function"]["name"],
                    arguments=json.loads(tool_call["function"]["arguments"]),
                    call_id=tool_call.get("id")
                )
                function_calls.append(func_call)
        
        return LLMResponse(
            content=content,
            provider=LLMProvider.OPENAI,
            model=response_data["model"],
            finish_reason=choice.get("finish_reason"),
            function_calls=function_calls,
            usage=response_data.get("usage"),
            metadata={"response_id": response_data.get("id")}
        )