"""
Model Orchestrator

Multi-model orchestration system for routing tasks to appropriate AI models
based on capabilities, performance, and availability.

Author: Claude Code
Date: 2025-07-13
Session: 3.1
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

from ...utils.logger import get_logger

logger = get_logger(__name__)


class ModelCapability(Enum):
    """AI model capabilities"""
    TEXT_GENERATION = "text_generation"
    CODE_GENERATION = "code_generation"
    REASONING = "reasoning"
    MATHEMATICS = "mathematics"
    ANALYSIS = "analysis"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    CREATIVE_WRITING = "creative_writing"
    QUESTION_ANSWERING = "question_answering"
    FUNCTION_CALLING = "function_calling"
    VISION = "vision"
    MULTIMODAL = "multimodal"


class ModelType(Enum):
    """Types of AI models"""
    LOCAL_OLLAMA = "local_ollama"
    OPENAI_API = "openai_api"
    ANTHROPIC_API = "anthropic_api"
    HUGGINGFACE = "huggingface"
    CUSTOM = "custom"


@dataclass
class ModelConfig:
    """AI model configuration"""
    model_id: str
    model_type: ModelType
    name: str
    capabilities: List[ModelCapability]
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 0.9
    context_window: int = 8192
    cost_per_token: float = 0.0
    priority: int = 1  # Higher = more preferred
    max_concurrent: int = 5
    timeout: float = 60.0
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelPerformance:
    """Model performance metrics"""
    model_id: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    total_tokens_generated: int = 0
    total_cost: float = 0.0
    last_used: Optional[float] = None
    availability_score: float = 1.0
    quality_score: float = 1.0


@dataclass
class ModelRequest:
    """Request for model execution"""
    prompt: str
    capabilities_required: List[ModelCapability]
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    context: Optional[Dict[str, Any]] = None
    priority: int = 1
    timeout: Optional[float] = None
    preferred_models: Optional[List[str]] = None
    excluded_models: Optional[List[str]] = None


@dataclass 
class ModelResponse:
    """Response from model execution"""
    content: str
    model_id: str
    model_name: str
    tokens_used: int
    response_time: float
    cost: float
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ModelOrchestrator:
    """
    Multi-model orchestration system.
    
    Features:
    - Intelligent model selection based on capabilities and performance
    - Load balancing and failover
    - Performance monitoring and optimization
    - Cost tracking and budget management
    - Quality assessment and model ranking
    - Concurrent request handling
    - Adaptive routing based on historical performance
    """
    
    def __init__(self, default_config: Optional[Dict[str, Any]] = None):
        """
        Initialize model orchestrator.
        
        Args:
            default_config: Default configuration settings
        """
        self.models: Dict[str, ModelConfig] = {}
        self.performance: Dict[str, ModelPerformance] = {}
        self.active_requests: Dict[str, int] = {}  # Model ID -> active request count
        self.request_queue: List[ModelRequest] = []
        
        # Configuration
        self.config = default_config or {
            "max_retries": 3,
            "retry_delay": 1.0,
            "quality_weight": 0.4,
            "performance_weight": 0.3,
            "cost_weight": 0.2,
            "availability_weight": 0.1,
            "enable_failover": True,
            "enable_load_balancing": True,
            "cost_budget_limit": None,
            "performance_history_size": 1000
        }
        
        logger.info("Model orchestrator initialized")
    
    def register_model(self, config: ModelConfig):
        """
        Register a new AI model.
        
        Args:
            config: Model configuration
        """
        self.models[config.model_id] = config
        self.performance[config.model_id] = ModelPerformance(model_id=config.model_id)
        self.active_requests[config.model_id] = 0
        
        logger.info(f"Registered model: {config.name} ({config.model_id})")
    
    def unregister_model(self, model_id: str):
        """Remove a model from the orchestrator"""
        if model_id in self.models:
            del self.models[model_id]
            del self.performance[model_id]
            del self.active_requests[model_id]
            logger.info(f"Unregistered model: {model_id}")
    
    def get_available_models(self, capabilities: Optional[List[ModelCapability]] = None) -> List[ModelConfig]:
        """
        Get list of available models, optionally filtered by capabilities.
        
        Args:
            capabilities: Required capabilities
            
        Returns:
            List of available model configurations
        """
        available = []
        
        for model in self.models.values():
            if not model.enabled:
                continue
                
            if capabilities:
                if not all(cap in model.capabilities for cap in capabilities):
                    continue
            
            # Check if model is not overloaded
            if self.active_requests[model.model_id] >= model.max_concurrent:
                continue
                
            available.append(model)
        
        return available
    
    def select_best_model(self, request: ModelRequest) -> Optional[ModelConfig]:
        """
        Select the best model for a request based on multiple criteria.
        
        Args:
            request: Model request
            
        Returns:
            Best model configuration or None
        """
        available_models = self.get_available_models(request.capabilities_required)
        
        if not available_models:
            return None
        
        # Filter by preferred/excluded models
        if request.preferred_models:
            available_models = [m for m in available_models if m.model_id in request.preferred_models]
        
        if request.excluded_models:
            available_models = [m for m in available_models if m.model_id not in request.excluded_models]
        
        if not available_models:
            return None
        
        # Score each model
        scored_models = []
        for model in available_models:
            score = self._calculate_model_score(model, request)
            scored_models.append((model, score))
        
        # Sort by score (descending) and return best
        scored_models.sort(key=lambda x: x[1], reverse=True)
        best_model = scored_models[0][0]
        
        logger.debug(f"Selected model {best_model.name} with score {scored_models[0][1]:.3f}")
        return best_model
    
    def _calculate_model_score(self, model: ModelConfig, request: ModelRequest) -> float:
        """Calculate composite score for model selection"""
        perf = self.performance[model.model_id]
        
        # Quality score (success rate)
        if perf.total_requests > 0:
            quality_score = perf.successful_requests / perf.total_requests
        else:
            quality_score = 1.0  # No history, assume good
        
        # Performance score (inverse of response time)
        if perf.average_response_time > 0:
            performance_score = 1.0 / (1.0 + perf.average_response_time)
        else:
            performance_score = 1.0
        
        # Cost score (inverse of cost, prefer cheaper)
        if model.cost_per_token > 0:
            cost_score = 1.0 / (1.0 + model.cost_per_token * 1000)  # Scale for readability
        else:
            cost_score = 1.0  # Free model
        
        # Availability score (based on current load)
        load_ratio = self.active_requests[model.model_id] / model.max_concurrent
        availability_score = 1.0 - load_ratio
        
        # Priority boost
        priority_score = model.priority / 10.0
        
        # Weighted composite score
        weights = self.config
        total_score = (
            quality_score * weights["quality_weight"] +
            performance_score * weights["performance_weight"] +
            cost_score * weights["cost_weight"] +
            availability_score * weights["availability_weight"] +
            priority_score * 0.1
        )
        
        return total_score
    
    async def generate(self, request: ModelRequest) -> ModelResponse:
        """
        Generate response using best available model.
        
        Args:
            request: Model request
            
        Returns:
            Model response
        """
        start_time = time.time()
        retries = 0
        max_retries = self.config["max_retries"]
        last_error = None
        
        while retries <= max_retries:
            try:
                # Select best model
                model = self.select_best_model(request)
                if not model:
                    return ModelResponse(
                        content="",
                        model_id="none",
                        model_name="none",
                        tokens_used=0,
                        response_time=time.time() - start_time,
                        cost=0.0,
                        success=False,
                        error="No suitable model available"
                    )
                
                # Execute request
                response = await self._execute_model_request(model, request)
                
                # Update performance metrics
                self._update_performance_metrics(model.model_id, response, time.time() - start_time)
                
                return response
                
            except Exception as e:
                last_error = str(e)
                retries += 1
                
                if retries <= max_retries:
                    await asyncio.sleep(self.config["retry_delay"] * retries)
                    logger.warning(f"Model request failed, retrying ({retries}/{max_retries}): {e}")
                else:
                    logger.error(f"Model request failed after {max_retries} retries: {e}")
        
        return ModelResponse(
            content="",
            model_id="error",
            model_name="error",
            tokens_used=0,
            response_time=time.time() - start_time,
            cost=0.0,
            success=False,
            error=f"Request failed after {max_retries} retries: {last_error}"
        )
    
    async def _execute_model_request(self, model: ModelConfig, request: ModelRequest) -> ModelResponse:
        """
        Execute request on specific model.
        
        Args:
            model: Model configuration
            request: Model request
            
        Returns:
            Model response
        """
        # Track active request
        self.active_requests[model.model_id] += 1
        
        try:
            start_time = time.time()
            
            if model.model_type == ModelType.LOCAL_OLLAMA:
                response = await self._execute_ollama_request(model, request)
            elif model.model_type == ModelType.OPENAI_API:
                response = await self._execute_openai_request(model, request)
            elif model.model_type == ModelType.ANTHROPIC_API:
                response = await self._execute_anthropic_request(model, request)
            else:
                raise ValueError(f"Unsupported model type: {model.model_type}")
            
            response.response_time = time.time() - start_time
            response.model_id = model.model_id
            response.model_name = model.name
            
            return response
            
        finally:
            # Release active request slot
            self.active_requests[model.model_id] -= 1
    
    async def _execute_ollama_request(self, model: ModelConfig, request: ModelRequest) -> ModelResponse:
        """Execute request using Ollama local model"""
        # Import here to avoid circular dependency
        from ..llm.ollama_client import OllamaClient
        
        # Use existing Ollama client if available, otherwise create new one
        if not hasattr(self, '_ollama_client'):
            self._ollama_client = OllamaClient()
        
        try:
            # Map model_id to Ollama model name
            ollama_model = model.model_id.replace("ollama:", "")
            
            response = await self._ollama_client.generate(
                prompt=request.prompt,
                model=ollama_model,
                max_tokens=request.max_tokens or model.max_tokens,
                temperature=request.temperature or model.temperature,
                timeout=request.timeout or model.timeout
            )
            
            # Calculate cost (usually 0 for local models)
            cost = model.cost_per_token * response.tokens_used
            
            return ModelResponse(
                content=response.content,
                model_id=model.model_id,
                model_name=model.name,
                tokens_used=response.tokens_used,
                response_time=0.0,  # Will be set by caller
                cost=cost,
                success=True,
                metadata={"model_type": "ollama"}
            )
            
        except Exception as e:
            return ModelResponse(
                content="",
                model_id=model.model_id,
                model_name=model.name,
                tokens_used=0,
                response_time=0.0,
                cost=0.0,
                success=False,
                error=str(e)
            )
    
    async def _execute_openai_request(self, model: ModelConfig, request: ModelRequest) -> ModelResponse:
        """Execute request using OpenAI API"""
        # Placeholder for OpenAI API integration
        # In a real implementation, you would use the OpenAI SDK
        raise NotImplementedError("OpenAI API integration not implemented yet")
    
    async def _execute_anthropic_request(self, model: ModelConfig, request: ModelRequest) -> ModelResponse:
        """Execute request using Anthropic API"""
        # Placeholder for Anthropic API integration
        # In a real implementation, you would use the Anthropic SDK
        raise NotImplementedError("Anthropic API integration not implemented yet")
    
    def _update_performance_metrics(self, model_id: str, response: ModelResponse, execution_time: float):
        """Update performance metrics for a model"""
        perf = self.performance[model_id]
        
        perf.total_requests += 1
        perf.last_used = time.time()
        
        if response.success:
            perf.successful_requests += 1
            perf.total_tokens_generated += response.tokens_used
            perf.total_cost += response.cost
            
            # Update average response time
            if perf.average_response_time == 0:
                perf.average_response_time = execution_time
            else:
                # Exponential moving average
                alpha = 0.1
                perf.average_response_time = (
                    alpha * execution_time + 
                    (1 - alpha) * perf.average_response_time
                )
        else:
            perf.failed_requests += 1
            
        # Update availability score based on recent performance
        if perf.total_requests >= 10:
            perf.availability_score = perf.successful_requests / perf.total_requests
    
    def get_model_stats(self, model_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance statistics for models.
        
        Args:
            model_id: Specific model ID, or None for all models
            
        Returns:
            Model statistics
        """
        if model_id:
            if model_id not in self.performance:
                return {}
            
            perf = self.performance[model_id]
            model = self.models[model_id]
            
            return {
                "model_id": model_id,
                "model_name": model.name,
                "total_requests": perf.total_requests,
                "success_rate": perf.successful_requests / perf.total_requests if perf.total_requests > 0 else 0,
                "average_response_time": perf.average_response_time,
                "total_tokens": perf.total_tokens_generated,
                "total_cost": perf.total_cost,
                "availability_score": perf.availability_score,
                "active_requests": self.active_requests[model_id],
                "enabled": model.enabled
            }
        else:
            # Return stats for all models
            stats = {}
            for mid in self.models.keys():
                stats[mid] = self.get_model_stats(mid)
            return stats
    
    def optimize_model_selection(self):
        """Optimize model selection based on historical performance"""
        logger.info("Optimizing model selection based on performance history")
        
        for model_id, perf in self.performance.items():
            model = self.models[model_id]
            
            # Adjust priority based on performance
            if perf.total_requests >= 50:  # Enough data for optimization
                success_rate = perf.successful_requests / perf.total_requests
                
                # Increase priority for high-performing models
                if success_rate > 0.95 and perf.average_response_time < 5.0:
                    model.priority = min(10, model.priority + 1)
                # Decrease priority for poor-performing models
                elif success_rate < 0.8 or perf.average_response_time > 30.0:
                    model.priority = max(1, model.priority - 1)
        
        logger.info("Model selection optimization completed")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all registered models"""
        health_status = {}
        
        for model_id, model in self.models.items():
            try:
                # Simple health check request
                test_request = ModelRequest(
                    prompt="Hello",
                    capabilities_required=[ModelCapability.TEXT_GENERATION],
                    max_tokens=5,
                    timeout=10.0
                )
                
                start_time = time.time()
                response = await self._execute_model_request(model, test_request)
                health_time = time.time() - start_time
                
                health_status[model_id] = {
                    "status": "healthy" if response.success else "unhealthy",
                    "response_time": health_time,
                    "error": response.error,
                    "last_check": time.time()
                }
                
            except Exception as e:
                health_status[model_id] = {
                    "status": "error",
                    "error": str(e),
                    "last_check": time.time()
                }
        
        return health_status