#!/usr/bin/env python3
"""
Unified API Gateway - Standardizes responses across all AI models
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import aiohttp

from model_selector import ModelSelector, ModelType
from gemini_integration import GeminiIntegration

logger = logging.getLogger(__name__)

class ResponseStatus(Enum):
    """Response status types"""
    SUCCESS = "success"
    ERROR = "error"
    FALLBACK = "fallback"
    TIMEOUT = "timeout"

@dataclass
class AIResponse:
    """Standardized AI response structure"""
    status: ResponseStatus
    message: str
    model_used: str
    timestamp: str
    processing_time: float
    metadata: Optional[Dict[str, Any]] = None
    error_details: Optional[str] = None
    fallback_reason: Optional[str] = None

class APIGateway:
    """Unified API gateway for all AI models"""
    
    def __init__(self):
        self.model_selector = ModelSelector()
        self.gemini = GeminiIntegration()
        self.fallback_chain = [ModelType.GEMINI, ModelType.OLLAMA_LLAMA]
        self.max_retries = 3
        self.timeout_seconds = 30
        
    async def process_message(self, 
                            message: str,
                            context: Optional[List[Dict[str, str]]] = None,
                            force_model: Optional[ModelType] = None,
                            include_metadata: bool = True) -> AIResponse:
        """
        Process a message through the appropriate AI model
        
        Args:
            message: User's message
            context: Conversation history
            force_model: Force a specific model (bypass selector)
            include_metadata: Include processing metadata
            
        Returns:
            Standardized AIResponse
        """
        start_time = datetime.now()
        
        try:
            # Select model
            if force_model:
                selected_model = force_model
                logger.info(f"Forced model selection: {selected_model.value}")
            else:
                selected_model = self.model_selector.select_model(message, context)
                logger.info(f"Auto-selected model: {selected_model.value}")
            
            # Process with selected model
            response_text = await self._process_with_model(selected_model, message, context)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Build metadata
            metadata = None
            if include_metadata:
                metadata = {
                    "model_selection_reason": self.model_selector.explain_selection(message, selected_model),
                    "message_length": len(message),
                    "context_length": len(context) if context else 0
                }
            
            return AIResponse(
                status=ResponseStatus.SUCCESS,
                message=response_text,
                model_used=selected_model.value,
                timestamp=datetime.now().isoformat(),
                processing_time=processing_time,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            
            # Try fallback
            fallback_response = await self._try_fallback(message, context, selected_model, str(e))
            if fallback_response:
                return fallback_response
            
            # If all fails, return error
            return AIResponse(
                status=ResponseStatus.ERROR,
                message="I'm having trouble processing your request. Please try again later.",
                model_used="none",
                timestamp=datetime.now().isoformat(),
                processing_time=(datetime.now() - start_time).total_seconds(),
                error_details=str(e)
            )
    
    async def _process_with_model(self, 
                                model_type: ModelType, 
                                message: str,
                                context: Optional[List[Dict[str, str]]]) -> str:
        """Process message with specific model"""
        
        if model_type == ModelType.GEMINI:
            return await self.gemini.chat(message)
        elif model_type == ModelType.OLLAMA_LLAMA:
            # This will be implemented when we have proper Ollama integration
            # For now, return a placeholder
            return await self._process_with_ollama(message, context)
        else:
            raise ValueError(f"Model {model_type.value} not implemented yet")
    
    async def _process_with_ollama(self, message: str, context: Optional[List[Dict[str, str]]]) -> str:
        """Process with Ollama"""
        try:
            # Prepare messages for Ollama
            messages = context[-10:] if context else []  # Keep last 10 messages
            messages.append({"role": "user", "content": message})
            
            payload = {
                "model": "llama3:8b",
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 100,  # More tokens for better responses
                    "num_ctx": 2048,     # Larger context window
                    "top_k": 40,
                    "top_p": 0.9
                }
            }
            
            # Add timeout to prevent hanging
            timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post("http://localhost:11434/api/chat", json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("message", {}).get("content", "Sorry, I couldn't generate a response.")
                    else:
                        raise Exception(f"Ollama responded with status {response.status}")
        
        except Exception as e:
            logger.error(f"Error with Ollama: {e}")
            raise
    
    async def _try_fallback(self, 
                          message: str, 
                          context: Optional[List[Dict[str, str]]],
                          failed_model: ModelType,
                          error_reason: str) -> Optional[AIResponse]:
        """Try fallback models if primary fails"""
        
        logger.info(f"Attempting fallback from {failed_model.value} due to: {error_reason}")
        
        for fallback_model in self.fallback_chain:
            if fallback_model == failed_model:
                continue
                
            try:
                logger.info(f"Trying fallback model: {fallback_model.value}")
                response_text = await self._process_with_model(fallback_model, message, context)
                
                return AIResponse(
                    status=ResponseStatus.FALLBACK,
                    message=response_text,
                    model_used=fallback_model.value,
                    timestamp=datetime.now().isoformat(),
                    processing_time=0.0,  # Not tracking for fallback
                    fallback_reason=f"Primary model {failed_model.value} failed: {error_reason}"
                )
            except Exception as e:
                logger.error(f"Fallback model {fallback_model.value} also failed: {e}")
                continue
        
        return None
    
    async def process_batch(self, 
                          messages: List[str],
                          parallel: bool = True) -> List[AIResponse]:
        """Process multiple messages"""
        
        if parallel:
            tasks = [self.process_message(msg) for msg in messages]
            return await asyncio.gather(*tasks)
        else:
            responses = []
            for msg in messages:
                response = await self.process_message(msg)
                responses.append(response)
            return responses
    
    def get_model_status(self) -> Dict[str, Any]:
        """Get status of all available models"""
        
        status = {}
        
        # Check Gemini
        try:
            gemini_info = self.gemini.get_model_info()
            status["gemini"] = {
                "available": gemini_info.get("api_key_configured", False),
                "info": gemini_info
            }
        except Exception as e:
            status["gemini"] = {"available": False, "error": str(e)}
        
        # Check Ollama (placeholder)
        status["ollama"] = {
            "available": True,  # Assume available for now
            "info": {"model": "llama3:8b", "local": True}
        }
        
        return status
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all models"""
        
        health = {
            "timestamp": datetime.now().isoformat(),
            "models": {}
        }
        
        # Test Gemini
        try:
            test_response = await self.gemini.chat("Hello, are you working?")
            health["models"]["gemini"] = {
                "status": "healthy",
                "response_received": bool(test_response)
            }
        except Exception as e:
            health["models"]["gemini"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Test Ollama (placeholder)
        health["models"]["ollama"] = {
            "status": "assumed_healthy",
            "note": "Actual health check not implemented"
        }
        
        return health


# Test function
async def test_gateway():
    """Test the API gateway"""
    gateway = APIGateway()
    
    # Test messages
    test_messages = [
        "Hello, how are you?",
        "Write a function to calculate fibonacci numbers",
        "What's the meaning of life?"
    ]
    
    for msg in test_messages:
        print(f"\nProcessing: {msg}")
        response = await gateway.process_message(msg)
        print(f"Status: {response.status.value}")
        print(f"Model: {response.model_used}")
        print(f"Response: {response.message[:100]}...")
        print(f"Processing time: {response.processing_time:.2f}s")
    
    # Test model status
    print("\nModel Status:")
    status = gateway.get_model_status()
    for model, info in status.items():
        print(f"{model}: {info}")
    
    # Test health check
    print("\nHealth Check:")
    health = await gateway.health_check()
    print(health)


if __name__ == "__main__":
    asyncio.run(test_gateway())
