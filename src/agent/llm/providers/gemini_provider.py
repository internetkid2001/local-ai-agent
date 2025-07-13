"""
Google Gemini AI Provider Implementation

Support for Gemini models with function calling and streaming.
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


class GeminiProvider(BaseLLMProvider):
    """Google Gemini AI provider implementation"""
    
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
    
    # Model context windows
    CONTEXT_WINDOWS = {
        "gemini-pro": 32768,
        "gemini-pro-vision": 16384,
        "gemini-1.5-pro": 1048576,  # 1M tokens
        "gemini-1.5-flash": 1048576,  # 1M tokens
        "gemini-ultra": 32768,
    }
    
    # Models that support vision
    VISION_MODELS = {
        "gemini-pro-vision",
        "gemini-1.5-pro",
        "gemini-1.5-flash"
    }
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        if not config.api_key:
            raise ValueError("Google AI API key is required")
        
        self.api_key = config.api_key
        self.base_url = config.base_url or self.BASE_URL
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self) -> bool:
        """Initialize the Gemini provider"""
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout)
        )
        
        # Test connection by trying to list models
        try:
            url = f"{self.base_url}/models?key={self.api_key}"
            async with self._session.get(url) as response:
                if response.status == 200:
                    self._initialized = True
                    logger.info("Gemini provider initialized successfully")
                    return True
                elif response.status == 401:
                    raise LLMProviderAuthenticationError("Invalid Google AI API key")
                else:
                    raise LLMProviderConnectionError(f"Gemini API error: {response.status}")
        except aiohttp.ClientError as e:
            raise LLMProviderConnectionError(f"Failed to connect to Gemini: {e}")
    
    async def shutdown(self):
        """Shutdown the provider"""
        if self._session:
            await self._session.close()
            self._session = None
        self._initialized = False
        logger.info("Gemini provider shutdown")
    
    async def generate(
        self,
        messages: List[Message],
        functions: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
        **kwargs
    ) -> LLMResponse:
        """Generate response from Gemini"""
        if not self._initialized:
            raise LLMProviderError("Provider not initialized")
        
        # Convert messages to Gemini format
        gemini_contents = self._convert_messages_to_gemini_format(messages)
        
        # Prepare request data
        request_data = {
            "contents": gemini_contents,
            "generationConfig": {
                "temperature": self.config.temperature,
            }
        }
        
        # Add max tokens
        if self.config.max_tokens:
            request_data["generationConfig"]["maxOutputTokens"] = self.config.max_tokens
        
        # Add top_p
        if self.config.top_p is not None:
            request_data["generationConfig"]["topP"] = self.config.top_p
        
        # Add tools (functions) if provided
        if functions:
            request_data["tools"] = self._convert_functions_to_gemini_tools(functions)
        
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
                raise LLMProviderRateLimitError("Gemini rate limit exceeded")
            elif e.status == 401:
                raise LLMProviderAuthenticationError("Gemini authentication failed")
            else:
                raise LLMProviderError(f"Gemini API error: {e}")
    
    async def generate_stream(
        self,
        messages: List[Message],
        functions: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Generate streaming response from Gemini"""
        response = await self.generate(messages, functions, stream=True, **kwargs)
        yield response.content
    
    async def count_tokens(self, text: str) -> int:
        """Count tokens using Gemini's token counting endpoint"""
        if not self._initialized:
            # Fallback approximation
            return len(text.split()) * 1.3
        
        try:
            url = f"{self.base_url}/models/{self.config.model}:countTokens?key={self.api_key}"
            request_data = {
                "contents": [{"parts": [{"text": text}]}]
            }
            
            async with self._session.post(url, json=request_data) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("totalTokens", 0)
                else:
                    # Fallback approximation
                    return len(text.split()) * 1.3
        except Exception:
            # Fallback approximation
            return len(text.split()) * 1.3
    
    async def get_available_models(self) -> List[str]:
        """Get list of available Gemini models"""
        if not self._initialized:
            return []
        
        try:
            url = f"{self.base_url}/models?key={self.api_key}"
            async with self._session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    models = []
                    for model in data.get("models", []):
                        model_name = model.get("name", "").replace("models/", "")
                        if "generateContent" in model.get("supportedGenerationMethods", []):
                            models.append(model_name)
                    return models
                else:
                    logger.error(f"Failed to get Gemini models: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Error getting Gemini models: {e}")
            return []
    
    def supports_vision(self) -> bool:
        """Check if current model supports vision"""
        return self.config.model in self.VISION_MODELS
    
    def get_context_window(self) -> int:
        """Get context window for current model"""
        return self.CONTEXT_WINDOWS.get(self.config.model, 32768)
    
    async def _generate_complete(self, request_data: Dict[str, Any]) -> LLMResponse:
        """Generate complete response (non-streaming)"""
        url = f"{self.base_url}/models/{self.config.model}:generateContent?key={self.api_key}"
        
        async with self._session.post(url, json=request_data) as response:
            if response.status != 200:
                error_text = await response.text()
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message=error_text
                )
            
            data = await response.json()
            return self._convert_gemini_response(data)
    
    async def _generate_streaming(self, request_data: Dict[str, Any]) -> LLMResponse:
        """Generate streaming response"""
        url = f"{self.base_url}/models/{self.config.model}:streamGenerateContent?key={self.api_key}"
        
        full_content = ""
        function_calls = []
        finish_reason = None
        usage = None
        
        async with self._session.post(url, json=request_data) as response:
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
                        try:
                            chunk = json.loads(data_text)
                            
                            # Process candidates
                            for candidate in chunk.get('candidates', []):
                                content = candidate.get('content', {})
                                
                                # Extract text content
                                for part in content.get('parts', []):
                                    if 'text' in part:
                                        full_content += part['text']
                                    elif 'functionCall' in part:
                                        func_call = FunctionCall(
                                            name=part['functionCall']['name'],
                                            arguments=part['functionCall'].get('args', {}),
                                            call_id=part['functionCall'].get('id')
                                        )
                                        function_calls.append(func_call)
                                
                                # Get finish reason
                                if 'finishReason' in candidate:
                                    finish_reason = candidate['finishReason']
                            
                            # Get usage metadata
                            if 'usageMetadata' in chunk:
                                usage = chunk['usageMetadata']
                        
                        except json.JSONDecodeError:
                            continue
        
        return LLMResponse(
            content=full_content,
            provider=LLMProvider.GEMINI,
            model=self.config.model,
            finish_reason=finish_reason,
            function_calls=function_calls,
            usage=usage
        )
    
    def _convert_messages_to_gemini_format(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """Convert universal messages to Gemini format"""
        gemini_contents = []
        
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                # Gemini doesn't have explicit system messages, prepend to first user message
                continue
            
            role = "user" if msg.role == MessageRole.USER else "model"
            
            content = {
                "role": role,
                "parts": [{"text": msg.content}]
            }
            
            # Handle function call results
            if msg.function_call:
                content["parts"].append({
                    "functionResponse": {
                        "name": msg.function_call.get("name"),
                        "response": msg.function_call.get("result", {})
                    }
                })
            
            gemini_contents.append(content)
        
        # If we have system messages, prepend them to the first user message
        system_messages = [msg for msg in messages if msg.role == MessageRole.SYSTEM]
        if system_messages and gemini_contents:
            system_text = "\n".join(msg.content for msg in system_messages)
            first_user_content = gemini_contents[0]
            if first_user_content["role"] == "user":
                # Prepend system message to first user message
                original_text = first_user_content["parts"][0]["text"]
                first_user_content["parts"][0]["text"] = f"{system_text}\n\n{original_text}"
        
        return gemini_contents
    
    def _convert_functions_to_gemini_tools(self, functions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert function schemas to Gemini tools format"""
        tools = []
        
        function_declarations = []
        for func in functions:
            declaration = {
                "name": func["name"],
                "description": func.get("description", ""),
                "parameters": func.get("parameters", {})
            }
            function_declarations.append(declaration)
        
        if function_declarations:
            tools.append({
                "functionDeclarations": function_declarations
            })
        
        return tools
    
    def _convert_gemini_response(self, response_data: Dict[str, Any]) -> LLMResponse:
        """Convert Gemini response to universal format"""
        content = ""
        function_calls = []
        finish_reason = None
        
        # Process candidates
        candidates = response_data.get("candidates", [])
        if candidates:
            candidate = candidates[0]  # Use first candidate
            
            # Extract content
            content_parts = candidate.get("content", {}).get("parts", [])
            for part in content_parts:
                if "text" in part:
                    content += part["text"]
                elif "functionCall" in part:
                    func_call = FunctionCall(
                        name=part["functionCall"]["name"],
                        arguments=part["functionCall"].get("args", {}),
                        call_id=part["functionCall"].get("id")
                    )
                    function_calls.append(func_call)
            
            # Get finish reason
            finish_reason = candidate.get("finishReason")
        
        return LLMResponse(
            content=content,
            provider=LLMProvider.GEMINI,
            model=self.config.model,
            finish_reason=finish_reason,
            function_calls=function_calls,
            usage=response_data.get("usageMetadata"),
            metadata={"response_id": response_data.get("id")}
        )