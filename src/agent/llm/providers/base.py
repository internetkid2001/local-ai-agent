"""
Base LLM Provider Interface

Unified interface for all LLM providers (Ollama, OpenAI, Anthropic, Gemini AI)
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, AsyncIterator, Union
from dataclasses import dataclass
from enum import Enum
import asyncio


class LLMProvider(Enum):
    """Supported LLM providers"""
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"


class MessageRole(Enum):
    """Message roles for conversation"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TOOL = "tool"


@dataclass
class Message:
    """Universal message format for all providers"""
    role: MessageRole
    content: str
    function_call: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        result = {
            "role": self.role.value,
            "content": self.content
        }
        
        if self.function_call:
            result["function_call"] = self.function_call
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        if self.name:
            result["name"] = self.name
        if self.metadata:
            result["metadata"] = self.metadata
            
        return result


@dataclass
class FunctionCall:
    """Function call data structure"""
    name: str
    arguments: Dict[str, Any]
    call_id: Optional[str] = None


@dataclass
class LLMResponse:
    """Universal response format for all providers"""
    content: str
    provider: LLMProvider
    model: str
    finish_reason: Optional[str] = None
    function_calls: List[FunctionCall] = None
    usage: Optional[Dict[str, int]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.function_calls is None:
            self.function_calls = []


@dataclass
class LLMConfig:
    """Universal configuration for LLM providers"""
    provider: LLMProvider
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    timeout: float = 30.0
    custom_params: Optional[Dict[str, Any]] = None


class BaseLLMProvider(ABC):
    """Base class for all LLM providers"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.provider = config.provider
        self._initialized = False
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the provider"""
        pass
    
    @abstractmethod
    async def shutdown(self):
        """Shutdown the provider"""
        pass
    
    @abstractmethod
    async def generate(
        self,
        messages: List[Message],
        functions: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
        **kwargs
    ) -> LLMResponse:
        """Generate response from the LLM"""
        pass
    
    @abstractmethod
    async def generate_stream(
        self,
        messages: List[Message],
        functions: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Generate streaming response from the LLM"""
        pass
    
    @abstractmethod
    async def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        pass
    
    @abstractmethod
    async def get_available_models(self) -> List[str]:
        """Get list of available models"""
        pass
    
    async def is_healthy(self) -> bool:
        """Check if provider is healthy"""
        try:
            models = await self.get_available_models()
            return len(models) > 0
        except Exception:
            return False
    
    def supports_function_calling(self) -> bool:
        """Check if provider supports function calling"""
        return True  # Most modern providers do
    
    def supports_streaming(self) -> bool:
        """Check if provider supports streaming"""
        return True  # Most modern providers do
    
    def supports_vision(self) -> bool:
        """Check if provider supports vision/image understanding"""
        return False  # Override in providers that support it
    
    def get_context_window(self) -> int:
        """Get model context window size"""
        # Default context windows by provider
        context_windows = {
            LLMProvider.OLLAMA: 8192,
            LLMProvider.OPENAI: 4096,  # varies by model
            LLMProvider.ANTHROPIC: 100000,  # Claude
            LLMProvider.GEMINI: 32768,  # Gemini Pro
        }
        return context_windows.get(self.provider, 4096)
    
    def _convert_messages_to_provider_format(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """Convert universal messages to provider-specific format"""
        # Default implementation - override in providers if needed
        return [msg.to_dict() for msg in messages]
    
    def _convert_provider_response(self, response: Any) -> LLMResponse:
        """Convert provider response to universal format"""
        # Must be implemented by each provider
        raise NotImplementedError


class LLMProviderError(Exception):
    """Base exception for LLM provider errors"""
    pass


class LLMProviderConnectionError(LLMProviderError):
    """Connection error to LLM provider"""
    pass


class LLMProviderRateLimitError(LLMProviderError):
    """Rate limit error from LLM provider"""
    pass


class LLMProviderAuthenticationError(LLMProviderError):
    """Authentication error with LLM provider"""
    pass


class LLMProviderModelNotFoundError(LLMProviderError):
    """Model not found error"""
    pass