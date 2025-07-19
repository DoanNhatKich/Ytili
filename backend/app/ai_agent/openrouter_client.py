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
        stream: bool = False,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Get chat completion from OpenRouter API with enhanced error handling

        Args:
            messages: List of conversation messages
            model: Model to use (defaults to primary model)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response
            stream: Whether to stream the response
            retry_count: Current retry attempt

        Returns:
            API response or error information
        """
        # Input validation
        if not messages:
            return {
                "success": False,
                "error": "No messages provided",
                "model_used": model or self.primary_model,
                "response_time": 0
            }

        if not await self._check_rate_limit():
            logger.warning("Rate limit exceeded, waiting...")
            await asyncio.sleep(1)

        model = model or self.primary_model
        max_tokens = max_tokens or self.max_response_tokens

        # Trim conversation history
        trimmed_messages = await self._trim_conversation_history(messages)

        start_time = time.time()

        try:
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

                # Validate response
                if not response.choices or not response.choices[0].message:
                    raise ValueError("Invalid response structure from API")

                result = {
                    "success": True,
                    "response": response.choices[0].message.content or "",
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

        except asyncio.TimeoutError:
            logger.error(f"Timeout error with {model}")
            error_msg = "Request timed out"
        except aiohttp.ClientError as e:
            logger.error(f"Network error with {model}: {str(e)}")
            error_msg = f"Network error: {str(e)}"
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error with {model}: {str(e)}")
            error_msg = f"Invalid response format: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error with {model}: {str(e)}")
            error_msg = str(e)

        # Retry logic with exponential backoff
        if retry_count < 2:
            wait_time = (2 ** retry_count) * 1  # 1s, 2s, 4s
            logger.info(f"Retrying in {wait_time}s (attempt {retry_count + 1}/3)")
            await asyncio.sleep(wait_time)
            return await self.chat_completion(
                messages, model, temperature, max_tokens, stream, retry_count + 1
            )

        # Try fallback model if primary failed and we haven't tried it yet
        if model == self.primary_model and self.fallback_model and retry_count == 0:
            logger.info(f"Trying fallback model: {self.fallback_model}")
            return await self.chat_completion(
                messages, self.fallback_model, temperature, max_tokens, stream, 0
            )

        return {
            "success": False,
            "error": error_msg,
            "model_used": model,
            "response_time": time.time() - start_time,
            "retry_count": retry_count
        }
    
    async def _stream_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream chat completion response with enhanced error handling"""
        start_time = time.time()
        full_response = ""
        chunk_count = 0

        try:
            stream = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )

            async for chunk in stream:
                chunk_count += 1

                # Handle different chunk types
                if hasattr(chunk, 'choices') and chunk.choices:
                    choice = chunk.choices[0]

                    # Check for content
                    if hasattr(choice, 'delta') and choice.delta and choice.delta.content:
                        content = choice.delta.content
                        full_response += content

                        yield {
                            "success": True,
                            "content": content,
                            "full_response": full_response,
                            "model_used": model,
                            "is_complete": False,
                            "chunk_count": chunk_count
                        }

                    # Check for finish reason
                    if hasattr(choice, 'finish_reason') and choice.finish_reason:
                        break

                # Timeout protection for streaming
                if time.time() - start_time > 30:  # 30 second timeout
                    logger.warning("Streaming timeout reached")
                    break

            # Final chunk with complete response
            response_time = time.time() - start_time
            yield {
                "success": True,
                "content": "",
                "full_response": full_response,
                "model_used": model,
                "response_time": response_time,
                "is_complete": True,
                "chunk_count": chunk_count,
                "total_tokens": await self._count_tokens(full_response)
            }

            logger.info(
                "Streaming completed successfully",
                model=model,
                chunks=chunk_count,
                response_time=response_time,
                response_length=len(full_response)
            )

        except asyncio.TimeoutError:
            logger.error("Streaming timeout error")
            yield {
                "success": False,
                "error": "Streaming timeout",
                "model_used": model,
                "is_complete": True,
                "response_time": time.time() - start_time
            }
        except Exception as e:
            logger.error(f"Streaming error: {str(e)}")
            yield {
                "success": False,
                "error": str(e),
                "model_used": model,
                "is_complete": True,
                "response_time": time.time() - start_time,
                "partial_response": full_response if full_response else None
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
