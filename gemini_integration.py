#!/usr/bin/env python3
"""
Gemini API Integration - Proper implementation using Google's generative AI
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
import google.generativeai as genai

logger = logging.getLogger(__name__)

class GeminiIntegration:
    """Handle Gemini API interactions"""
    
    def __init__(self, api_key: str = None):
        """Initialize Gemini with API key"""
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "AIzaSyAZkBKhhPqgycPQJFTvy3Yfbhl8Z-bP9RI")
        
        # Configure the API
        genai.configure(api_key=self.api_key)
        
        # Initialize model
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # System prompt for context
        self.system_prompt = """You are a helpful AI assistant integrated into a local system management platform. 
You can help with various tasks including system queries, code analysis, creative writing, and general conversation. 
Be concise but thorough in your responses."""
        
        # Conversation history
        self.conversation_history = []
    
    def format_conversation_history(self) -> str:
        """Format conversation history for context"""
        if not self.conversation_history:
            return ""
        
        formatted = "Previous conversation:\n"
        for entry in self.conversation_history[-5:]:  # Last 5 exchanges
            formatted += f"{entry['role']}: {entry['content']}\n"
        
        return formatted
    
    async def chat(self, message: str, include_history: bool = True) -> str:
        """
        Send a message to Gemini and get response
        
        Args:
            message: User's message
            include_history: Whether to include conversation history
            
        Returns:
            AI response as string
        """
        try:
            # Add to history
            self.conversation_history.append({"role": "user", "content": message})
            
            # Prepare prompt
            if include_history and len(self.conversation_history) > 1:
                context = self.format_conversation_history()
                full_prompt = f"{self.system_prompt}\n\n{context}\n\nUser: {message}\nAssistant:"
            else:
                full_prompt = f"{self.system_prompt}\n\nUser: {message}\nAssistant:"
            
            # Generate response
            response = self.model.generate_content(full_prompt)
            
            # Extract text response
            ai_response = response.text
            
            # Add to history
            self.conversation_history.append({"role": "assistant", "content": ai_response})
            
            # Keep history manageable
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return f"Error communicating with Gemini: {str(e)}"
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        return "Conversation history cleared."
    
    async def analyze_code(self, code: str, language: str = "python") -> str:
        """Analyze code for improvements, bugs, or explanations"""
        prompt = f"""Analyze this {language} code and provide:
1. A brief explanation of what it does
2. Any potential bugs or issues
3. Suggestions for improvements
4. Code quality assessment

Code:
```{language}
{code}
```
"""
        return await self.chat(prompt, include_history=False)
    
    async def generate_code(self, description: str, language: str = "python") -> str:
        """Generate code based on description"""
        prompt = f"""Generate {language} code for the following requirement:
{description}

Please provide:
1. Complete, working code
2. Comments explaining key parts
3. Any necessary imports or dependencies
4. Example usage if applicable
"""
        return await self.chat(prompt, include_history=False)
    
    async def explain_error(self, error_message: str, context: str = "") -> str:
        """Explain an error message and suggest fixes"""
        prompt = f"""Explain this error message and provide solutions:

Error: {error_message}

{"Context: " + context if context else ""}

Please provide:
1. What the error means
2. Common causes
3. Step-by-step solutions
4. How to prevent it in the future
"""
        return await self.chat(prompt, include_history=False)
    
    async def creative_task(self, task_description: str) -> str:
        """Handle creative writing or brainstorming tasks"""
        prompt = f"""Creative task: {task_description}

Please provide a creative, engaging response that fulfills this request."""
        return await self.chat(prompt, include_history=False)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current Gemini model"""
        return {
            "model": "gemini-2.0-flash-exp",
            "capabilities": [
                "text_generation",
                "code_analysis",
                "creative_writing",
                "problem_solving",
                "conversation"
            ],
            "context_length": "1M tokens",
            "multimodal": True,
            "api_key_configured": bool(self.api_key)
        }


# Test function
async def test_gemini():
    """Test Gemini integration"""
    gemini = GeminiIntegration()
    
    # Test basic chat
    response = await gemini.chat("Hello! Can you explain what you can help me with?")
    print("Basic chat response:", response)
    
    # Test code analysis
    code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
"""
    analysis = await gemini.analyze_code(code)
    print("\nCode analysis:", analysis)
    
    # Test model info
    info = gemini.get_model_info()
    print("\nModel info:", json.dumps(info, indent=2))


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_gemini())
