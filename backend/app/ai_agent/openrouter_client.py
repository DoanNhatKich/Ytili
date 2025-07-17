"""
OpenRouter API Client for Ytili AI Agent
Handles communication with OpenRouter API using qwen/qwen-2.5-72b-instruct model
"""
import asyncio
import json
import time
from typing import Dict, List, Optional, AsyncGenerator, Any
import aiohttp
import structlog
from openai import AsyncOpenAI

from ..core.config import settings

logger = structlog.get_logger()


class OpenRouterClient:
    """
    Client for OpenRouter API with conversation management and error handling
    """
    
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.base_url = settings.OPENROUTER_BASE_URL
        self.primary_model = settings.PRIMARY_MODEL
        self.fallback_model = settings.FALLBACK_MODEL
        
        # Initialize OpenAI client for OpenRouter
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )
        
        # Rate limiting
        self.max_requests_per_minute = 60
        self.request_timestamps = []
        
        # Conversation context management
        self.max_context_tokens = 8000  # Conservative limit for context window
        self.max_response_tokens = 2000
        
    async def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits"""
        current_time = time.time()
        
        # Remove timestamps older than 1 minute
        self.request_timestamps = [
            ts for ts in self.request_timestamps 
            if current_time - ts < 60
        ]
        
        if len(self.request_timestamps) >= self.max_requests_per_minute:
            return False
            
        self.request_timestamps.append(current_time)
        return True
    
    async def _count_tokens(self, text: str) -> int:
        """Estimate token count for text (rough approximation)"""
        # Rough estimation: 1 token ≈ 4 characters for English, 2-3 for Vietnamese
        return len(text) // 3
    
    async def _trim_conversation_history(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Trim conversation history to fit within context window"""
        if not messages:
            return messages
            
        # Always keep system message if present
        system_messages = [msg for msg in messages if msg.get("role") == "system"]
        other_messages = [msg for msg in messages if msg.get("role") != "system"]
        
        # Calculate tokens for system messages
        system_tokens = sum([await self._count_tokens(msg["content"]) for msg in system_messages])
        
        # Reserve tokens for response
        available_tokens = self.max_context_tokens - system_tokens - self.max_response_tokens
        
        # Trim from the beginning, keeping recent messages
        trimmed_messages = []
        current_tokens = 0
        
        for message in reversed(other_messages):
            message_tokens = await self._count_tokens(message["content"])
            if current_tokens + message_tokens <= available_tokens:
                trimmed_messages.insert(0, message)
                current_tokens += message_tokens
            else:
                break
        
        return system_messages + trimmed_messages
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Get chat completion from OpenRouter API
        
        Args:
            messages: List of conversation messages
            model: Model to use (defaults to primary model)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response
            stream: Whether to stream the response
            
        Returns:
            API response or error information
        """
        if not await self._check_rate_limit():
            logger.warning("Rate limit exceeded, waiting...")
            await asyncio.sleep(1)
            
        model = model or self.primary_model
        max_tokens = max_tokens or self.max_response_tokens
        
        # Trim conversation history
        trimmed_messages = await self._trim_conversation_history(messages)
        
        try:
            start_time = time.time()
            
            if stream:
                return await self._stream_completion(
                    trimmed_messages, model, temperature, max_tokens
                )
            else:
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=trimmed_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=False
                )
                
                response_time = time.time() - start_time
                
                result = {
                    "success": True,
                    "response": response.choices[0].message.content,
                    "model_used": model,
                    "tokens_used": response.usage.total_tokens if response.usage else 0,
                    "response_time": response_time,
                    "finish_reason": response.choices[0].finish_reason
                }
                
                logger.info(
                    "OpenRouter API call successful",
                    model=model,
                    tokens=result["tokens_used"],
                    response_time=response_time
                )
                
                return result
                
        except Exception as e:
            logger.error(f"OpenRouter API error with {model}: {str(e)}")
            
            # Try fallback model if primary failed
            if model == self.primary_model and self.fallback_model:
                logger.info(f"Trying fallback model: {self.fallback_model}")
                return await self.chat_completion(
                    messages, self.fallback_model, temperature, max_tokens, stream
                )
            
            return {
                "success": False,
                "error": str(e),
                "model_used": model,
                "response_time": time.time() - start_time if 'start_time' in locals() else 0
            }
    
    async def _stream_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream chat completion response"""
        try:
            start_time = time.time()
            
            stream = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            
            full_response = ""
            
            async for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    
                    yield {
                        "success": True,
                        "content": content,
                        "full_response": full_response,
                        "model_used": model,
                        "is_complete": False
                    }
            
            # Final chunk with complete response
            response_time = time.time() - start_time
            yield {
                "success": True,
                "content": "",
                "full_response": full_response,
                "model_used": model,
                "response_time": response_time,
                "is_complete": True
            }
            
        except Exception as e:
            logger.error(f"Streaming error: {str(e)}")
            yield {
                "success": False,
                "error": str(e),
                "model_used": model,
                "is_complete": True
            }
    
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Get text embedding (if supported by OpenRouter)
        Note: This is a placeholder - OpenRouter may not support embeddings
        """
        try:
            # This would need to be implemented based on available embedding models
            # For now, return None as embeddings might not be available
            logger.warning("Embeddings not implemented for OpenRouter")
            return None
            
        except Exception as e:
            logger.error(f"Embedding error: {str(e)}")
            return None
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if OpenRouter API is accessible"""
        try:
            test_messages = [
                {"role": "user", "content": "Hello, this is a health check."}
            ]
            
            result = await self.chat_completion(
                messages=test_messages,
                max_tokens=10
            )
            
            return {
                "status": "healthy" if result["success"] else "unhealthy",
                "model": self.primary_model,
                "response_time": result.get("response_time", 0),
                "error": result.get("error")
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# Global client instance
openrouter_client = OpenRouterClient()
