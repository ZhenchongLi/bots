"""
Coze Bot platform adapter.
"""
from typing import Dict, Any, Optional, List
import httpx
import structlog
from .base import BasePlatformAdapter

logger = structlog.get_logger()


class CozeAdapter(BasePlatformAdapter):
    """Adapter for Coze Bot platform."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Coze adapter."""
        super().__init__(config)
        
        # Coze-specific configuration
        self.bot_id = config.get("bot_id")
        self.conversation_id = config.get("conversation_id", "")
        
        if not self.bot_id:
            raise ValueError("bot_id is required for Coze Bot adapter")
    
    def get_platform_name(self) -> str:
        """Return the platform name."""
        return "coze"
    
    def get_supported_endpoints(self) -> List[str]:
        """Return list of supported endpoints."""
        return ["/chat/completions"]
    
    async def transform_request(self, endpoint: str, openai_request: Dict[str, Any]) -> Dict[str, Any]:
        """Transform OpenAI request to Coze format."""
        if endpoint == "/chat/completions" and "messages" in openai_request:
            # Extract the user's message (last user message in the conversation)
            messages = openai_request["messages"]
            user_message = ""
            
            # Find the last user message
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    user_message = msg.get("content", "")
                    break
            
            coze_request = {
                "bot_id": self.bot_id,
                "user": user_message,
                "conversation_id": self.conversation_id,
                "stream": openai_request.get("stream", False)
            }
            
            # Add optional parameters
            if "max_tokens" in openai_request:
                coze_request["max_tokens"] = openai_request["max_tokens"]
            if "temperature" in openai_request:
                coze_request["temperature"] = openai_request["temperature"]
            
            logger.debug("Transformed OpenAI request to Coze format", 
                        user_message=user_message[:50] + "..." if len(user_message) > 50 else user_message)
            
            return coze_request
        
        # For unsupported endpoints, return as-is
        return openai_request
    
    async def transform_response(self, endpoint: str, platform_response: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Coze response to OpenAI format."""
        if endpoint == "/chat/completions":
            return self._transform_chat_response(platform_response)
        
        # For unsupported endpoints, return as-is
        return platform_response
    
    def _transform_chat_response(self, coze_response: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Coze chat response to OpenAI format."""
        # Handle different Coze response formats
        if "messages" in coze_response:
            # Format 1: Messages array
            messages = coze_response["messages"]
            if messages:
                last_message = messages[-1] if messages else {}
                content = last_message.get("content", "")
                
                return {
                    "id": coze_response.get("conversation_id", f"coze-{hash(content) % 10000:04d}"),
                    "object": "chat.completion",
                    "created": coze_response.get("created_at", 1677652288),
                    "model": self.config.get("actual_name", "coze-bot"),
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": content
                        },
                        "finish_reason": "stop"
                    }],
                    "usage": {
                        "prompt_tokens": 0,  # Coze doesn't provide token usage
                        "completion_tokens": 0,
                        "total_tokens": 0
                    }
                }
        
        elif "answer" in coze_response:
            # Format 2: Direct answer
            content = coze_response.get("answer", "")
            return {
                "id": f"coze-{hash(content) % 10000:04d}",
                "object": "chat.completion",
                "created": 1677652288,
                "model": self.config.get("actual_name", "coze-bot"),
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
            }
        
        elif "content" in coze_response:
            # Format 3: Direct content
            content = coze_response.get("content", "")
            return {
                "id": f"coze-{hash(content) % 10000:04d}",
                "object": "chat.completion",
                "created": 1677652288,
                "model": self.config.get("actual_name", "coze-bot"),
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
            }
        
        # If none of the expected formats, return error response
        logger.warning("Unexpected Coze response format", response_keys=list(coze_response.keys()))
        return {
            "id": "coze-error",
            "object": "chat.completion",
            "created": 1677652288,
            "model": self.config.get("actual_name", "coze-bot"),
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Sorry, I encountered an error processing your request."
                },
                "finish_reason": "stop"
            }],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        }
    
    async def make_request(
        self, 
        method: str, 
        url: str, 
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to Coze API."""
        request_headers = self.prepare_headers(headers)
        request_headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })
        
        logger.debug("Making request to Coze API", 
                    method=method, 
                    url=url,
                    has_json_data=json_data is not None)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    json=json_data,
                    params=params,
                )
                
                result = {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "content": response.content,
                    "json": None
                }
                
                # Parse JSON response if possible
                try:
                    if response.content:
                        result["json"] = response.json()
                except Exception as e:
                    logger.warning("Failed to parse JSON response", error=str(e))
                
                logger.debug("Received response from Coze API", 
                           status_code=response.status_code,
                           has_json=result["json"] is not None)
                
                return result
                
        except httpx.TimeoutException:
            logger.error("Timeout making request to Coze API", url=url)
            raise
        except Exception as e:
            logger.error("Error making request to Coze API", url=url, error=str(e))
            raise
    
    def validate_config(self) -> bool:
        """Validate Coze adapter configuration."""
        if not super().validate_config():
            return False
        
        if not self.bot_id:
            logger.error("bot_id is required for Coze adapter")
            return False
        
        return True
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get Coze model information."""
        info = super().get_model_info()
        info.update({
            "bot_id": self.bot_id,
            "conversation_id": self.conversation_id,
            "supports_streaming": self.config.get("supports_streaming", True),
            "supports_function_calling": False  # Coze doesn't support function calling in OpenAI format
        })
        return info