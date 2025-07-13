"""
LLM Manager - Orchestrates multiple LLM providers

Provides intelligent routing, load balancing, and fallback capabilities
across different LLM providers (Ollama, OpenAI, Anthropic, Gemini)
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Type, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
import time
import random

from .providers.base import (
    BaseLLMProvider, LLMProvider, LLMConfig, Message, LLMResponse,
    LLMProviderError, LLMProviderConnectionError, LLMProviderRateLimitError
)
from .providers.ollama_provider import OllamaProvider
from .providers.openai_provider import OpenAIProvider
from .providers.anthropic_provider import AnthropicProvider
from .providers.gemini_provider import GeminiProvider


logger = logging.getLogger(__name__)


class RoutingStrategy(Enum):
    """Strategies for routing requests to providers"""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    FASTEST_RESPONSE = "fastest_response"
    COST_OPTIMIZED = "cost_optimized"
    CAPABILITY_BASED = "capability_based"
    RANDOM = "random"


@dataclass
class ProviderMetrics:
    """Metrics for provider performance tracking"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    last_used: Optional[float] = None
    consecutive_failures: int = 0
    is_healthy: bool = True
    
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests
    
    def update_response_time(self, response_time: float):
        """Update average response time"""
        if self.average_response_time == 0:
            self.average_response_time = response_time
        else:
            # Exponential moving average
            self.average_response_time = (self.average_response_time * 0.8) + (response_time * 0.2)


@dataclass
class LLMManagerConfig:
    """Configuration for LLM Manager"""
    default_provider: LLMProvider = LLMProvider.OLLAMA
    routing_strategy: RoutingStrategy = RoutingStrategy.CAPABILITY_BASED
    enable_fallback: bool = True
    max_retries: int = 3
    retry_delay: float = 1.0
    health_check_interval: float = 60.0
    circuit_breaker_threshold: int = 5  # consecutive failures to trigger circuit breaker
    circuit_breaker_timeout: float = 300.0  # 5 minutes
    provider_configs: Dict[LLMProvider, LLMConfig] = field(default_factory=dict)


class LLMManager:
    """Manages multiple LLM providers with intelligent routing and fallback"""
    
    def __init__(self, config: LLMManagerConfig):
        self.config = config
        self.providers: Dict[LLMProvider, BaseLLMProvider] = {}
        self.metrics: Dict[LLMProvider, ProviderMetrics] = {}
        self.provider_classes: Dict[LLMProvider, Type[BaseLLMProvider]] = {
            LLMProvider.OLLAMA: OllamaProvider,
            LLMProvider.OPENAI: OpenAIProvider,
            LLMProvider.ANTHROPIC: AnthropicProvider,
            LLMProvider.GEMINI: GeminiProvider,
        }
        self._round_robin_index = 0
        self._health_check_task: Optional[asyncio.Task] = None
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize all configured providers"""
        try:
            # Initialize providers based on config
            for provider_type, provider_config in self.config.provider_configs.items():
                await self._add_provider(provider_type, provider_config)
            
            # Start health check task
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            
            self._initialized = True
            logger.info(f"LLM Manager initialized with {len(self.providers)} providers")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize LLM Manager: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown all providers and cleanup"""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        for provider in self.providers.values():
            try:
                await provider.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down provider: {e}")
        
        self.providers.clear()
        self.metrics.clear()
        self._initialized = False
    
    async def _add_provider(self, provider_type: LLMProvider, config: LLMConfig):
        """Add a provider to the manager"""
        try:
            provider_class = self.provider_classes[provider_type]
            provider = provider_class(config)
            
            # Initialize provider
            if await provider.initialize():
                self.providers[provider_type] = provider
                self.metrics[provider_type] = ProviderMetrics()
                logger.info(f"Added provider: {provider_type.value}")
            else:
                logger.error(f"Failed to initialize provider: {provider_type.value}")
                
        except Exception as e:
            logger.error(f"Error adding provider {provider_type.value}: {e}")
    
    async def generate(
        self,
        messages: List[Message],
        functions: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
        preferred_provider: Optional[LLMProvider] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response using optimal provider"""
        if not self._initialized:
            raise RuntimeError("LLM Manager not initialized")
        
        if not self.providers:
            raise RuntimeError("No providers available")
        
        # Select provider
        provider_type = await self._select_provider(
            messages, functions, preferred_provider, **kwargs
        )
        
        # Attempt generation with retries and fallback
        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                provider = self.providers[provider_type]
                metrics = self.metrics[provider_type]
                
                # Check circuit breaker
                if not metrics.is_healthy:
                    if time.time() - (metrics.last_used or 0) < self.config.circuit_breaker_timeout:
                        raise LLMProviderConnectionError(f"Provider {provider_type.value} circuit breaker active")
                    else:
                        # Reset circuit breaker
                        metrics.is_healthy = True
                        metrics.consecutive_failures = 0
                
                # Generate response
                start_time = time.time()
                response = await provider.generate(messages, functions, stream, **kwargs)
                response_time = time.time() - start_time
                
                # Update metrics
                self._update_metrics_success(provider_type, response_time)
                
                return response
                
            except Exception as e:
                last_error = e
                self._update_metrics_failure(provider_type)
                
                logger.warning(f"Provider {provider_type.value} failed (attempt {attempt + 1}): {e}")
                
                # Try fallback if enabled
                if self.config.enable_fallback and len(self.providers) > 1:
                    provider_type = await self._get_fallback_provider(provider_type, messages, functions, **kwargs)
                    if provider_type is None:
                        break
                
                # Wait before retry
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay * (2 ** attempt))  # Exponential backoff
        
        raise LLMProviderError(f"All providers failed. Last error: {last_error}")
    
    async def generate_stream(
        self,
        messages: List[Message],
        functions: Optional[List[Dict[str, Any]]] = None,
        preferred_provider: Optional[LLMProvider] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Generate streaming response using optimal provider"""
        if not self._initialized:
            raise RuntimeError("LLM Manager not initialized")
        
        provider_type = await self._select_provider(
            messages, functions, preferred_provider, **kwargs
        )
        
        provider = self.providers[provider_type]
        
        try:
            start_time = time.time()
            async for chunk in provider.generate_stream(messages, functions, **kwargs):
                yield chunk
            
            response_time = time.time() - start_time
            self._update_metrics_success(provider_type, response_time)
            
        except Exception as e:
            self._update_metrics_failure(provider_type)
            raise
    
    async def _select_provider(
        self,
        messages: List[Message],
        functions: Optional[List[Dict[str, Any]]] = None,
        preferred_provider: Optional[LLMProvider] = None,
        **kwargs
    ) -> LLMProvider:
        """Select optimal provider based on routing strategy"""
        
        # Use preferred provider if specified and available
        if preferred_provider and preferred_provider in self.providers:
            if self.metrics[preferred_provider].is_healthy:
                return preferred_provider
        
        # Filter healthy providers
        healthy_providers = [
            p for p in self.providers.keys()
            if self.metrics[p].is_healthy
        ]
        
        if not healthy_providers:
            # Use any available provider as last resort
            healthy_providers = list(self.providers.keys())
        
        if len(healthy_providers) == 1:
            return healthy_providers[0]
        
        # Apply routing strategy
        if self.config.routing_strategy == RoutingStrategy.ROUND_ROBIN:
            return self._round_robin_selection(healthy_providers)
        
        elif self.config.routing_strategy == RoutingStrategy.LEAST_LOADED:
            return self._least_loaded_selection(healthy_providers)
        
        elif self.config.routing_strategy == RoutingStrategy.FASTEST_RESPONSE:
            return self._fastest_response_selection(healthy_providers)
        
        elif self.config.routing_strategy == RoutingStrategy.CAPABILITY_BASED:
            return await self._capability_based_selection(healthy_providers, messages, functions, **kwargs)
        
        elif self.config.routing_strategy == RoutingStrategy.RANDOM:
            return random.choice(healthy_providers)
        
        else:
            # Default to first available
            return healthy_providers[0]
    
    def _round_robin_selection(self, providers: List[LLMProvider]) -> LLMProvider:
        """Round-robin provider selection"""
        provider = providers[self._round_robin_index % len(providers)]
        self._round_robin_index = (self._round_robin_index + 1) % len(providers)
        return provider
    
    def _least_loaded_selection(self, providers: List[LLMProvider]) -> LLMProvider:
        """Select provider with least current load"""
        return min(providers, key=lambda p: self.metrics[p].total_requests)
    
    def _fastest_response_selection(self, providers: List[LLMProvider]) -> LLMProvider:
        """Select provider with fastest average response time"""
        return min(providers, key=lambda p: self.metrics[p].average_response_time or float('inf'))
    
    async def _capability_based_selection(
        self,
        providers: List[LLMProvider],
        messages: List[Message],
        functions: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> LLMProvider:
        """Select provider based on capabilities needed"""
        
        # Check if function calling is needed
        if functions:
            function_providers = [p for p in providers if self.providers[p].supports_function_calling()]
            if function_providers:
                providers = function_providers
        
        # Check if vision is needed (look for image content)
        needs_vision = any(
            "image" in msg.content.lower() or "vision" in msg.content.lower()
            for msg in messages
        )
        if needs_vision:
            vision_providers = [p for p in providers if self.providers[p].supports_vision()]
            if vision_providers:
                providers = vision_providers
        
        # Prefer local models for simple tasks, cloud models for complex tasks
        message_length = sum(len(msg.content) for msg in messages)
        if message_length < 1000 and LLMProvider.OLLAMA in providers:
            return LLMProvider.OLLAMA
        
        # For complex tasks, prefer more capable cloud models
        if message_length > 5000:
            if LLMProvider.ANTHROPIC in providers:
                return LLMProvider.ANTHROPIC
            elif LLMProvider.OPENAI in providers:
                return LLMProvider.OPENAI
        
        # Default to fastest response
        return self._fastest_response_selection(providers)
    
    async def _get_fallback_provider(
        self,
        failed_provider: LLMProvider,
        messages: List[Message],
        functions: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Optional[LLMProvider]:
        """Get fallback provider when primary fails"""
        available_providers = [p for p in self.providers.keys() if p != failed_provider]
        
        if not available_providers:
            return None
        
        # Select best fallback based on capabilities
        return await self._select_provider(messages, functions, None, **kwargs)
    
    def _update_metrics_success(self, provider: LLMProvider, response_time: float):
        """Update metrics for successful request"""
        metrics = self.metrics[provider]
        metrics.total_requests += 1
        metrics.successful_requests += 1
        metrics.consecutive_failures = 0
        metrics.is_healthy = True
        metrics.last_used = time.time()
        metrics.update_response_time(response_time)
    
    def _update_metrics_failure(self, provider: LLMProvider):
        """Update metrics for failed request"""
        metrics = self.metrics[provider]
        metrics.total_requests += 1
        metrics.failed_requests += 1
        metrics.consecutive_failures += 1
        metrics.last_used = time.time()
        
        # Trigger circuit breaker if too many consecutive failures
        if metrics.consecutive_failures >= self.config.circuit_breaker_threshold:
            metrics.is_healthy = False
            logger.warning(f"Circuit breaker triggered for provider {provider.value}")
    
    async def _health_check_loop(self):
        """Periodic health check for all providers"""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                
                for provider_type, provider in self.providers.items():
                    try:
                        is_healthy = await provider.is_healthy()
                        
                        # Reset circuit breaker if provider is healthy again
                        if is_healthy and not self.metrics[provider_type].is_healthy:
                            self.metrics[provider_type].is_healthy = True
                            self.metrics[provider_type].consecutive_failures = 0
                            logger.info(f"Provider {provider_type.value} is healthy again")
                            
                    except Exception as e:
                        logger.warning(f"Health check failed for {provider_type.value}: {e}")
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all providers"""
        status = {}
        for provider_type, metrics in self.metrics.items():
            status[provider_type.value] = {
                "healthy": metrics.is_healthy,
                "total_requests": metrics.total_requests,
                "success_rate": metrics.success_rate(),
                "average_response_time": metrics.average_response_time,
                "consecutive_failures": metrics.consecutive_failures,
                "last_used": metrics.last_used
            }
        return status
    
    def get_available_providers(self) -> List[LLMProvider]:
        """Get list of available providers"""
        return list(self.providers.keys())
    
    async def count_tokens(self, text: str, provider: Optional[LLMProvider] = None) -> int:
        """Count tokens using specified or default provider"""
        if provider is None:
            provider = self.config.default_provider
        
        if provider not in self.providers:
            raise ValueError(f"Provider {provider.value} not available")
        
        return await self.providers[provider].count_tokens(text)