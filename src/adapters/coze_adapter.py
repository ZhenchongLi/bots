"""
Coze Bot platform adapter.
"""
from typing import Dict, Any, Optional, List
import time
import json
import httpx
import structlog
from .base import BasePlatformAdapter

logger = structlog.get_logger()


class CozeAdapter(BasePlatformAdapter):
    """Adapter for Coze Bot platform."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Coze adapter."""
        super().__init__(config)
        
        # Bot ID will be extracted from model name at runtime
        self.bot_id = None
        self._current_event_type = None  # Track current SSE event type
    
    def get_platform_name(self) -> str:
        """Return the platform name."""
        return "coze"
    
    def get_supported_endpoints(self) -> List[str]:
        """Return list of supported endpoints."""
        return ["/chat/completions"]
    
    async def transform_request(self, endpoint: str, openai_request: Dict[str, Any]) -> Dict[str, Any]:
        """Transform OpenAI request to Coze format according to documentation specs."""
        if endpoint == "/chat/completions" and "messages" in openai_request:
            # Extract bot_id from model name (bot-{COZE_BOT_ID} format)
            model = openai_request.get("model", "")
            if model.startswith("bot-"):
                self.bot_id = model[4:]  # Remove "bot-" prefix
            else:
                # If no bot- prefix, use the model name as bot_id
                self.bot_id = model
            
            if not self.bot_id:
                raise ValueError("Bot ID could not be extracted from model name")
            
            messages = openai_request["messages"]
            
            # Extract query (last user message) and chat_history (previous messages)
            query = ""
            chat_history = []
            
            for i, message in enumerate(messages):
                if i == len(messages) - 1:  # Last message becomes query
                    query = message.get("content", "")
                else:  # Previous messages become chat history
                    chat_history.append({
                        "role": message.get("role"),
                        "content": message.get("content", "")
                    })
            
            # Build Coze v3 API request format
            coze_request = {
                "bot_id": self.bot_id,
                "user_id": openai_request.get("user", "default_user"),
                "additional_messages": [{"role": "user", "content": query}],
                "stream": openai_request.get("stream", False)
            }
            
            # Add chat history as additional messages if present
            if chat_history:
                coze_request["additional_messages"] = chat_history + [{"role": "user", "content": query}]
            
            logger.info("Transformed OpenAI request to Coze format", 
                        bot_id=self.bot_id,
                        query=query[:50] + "..." if len(query) > 50 else query,
                        chat_history_length=len(chat_history),
                        request=coze_request)
            
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
        """Transform Coze non-streaming response to OpenAI format according to docs."""
        response_text = ""
        
        # Extract answer type messages according to documentation
        for message in coze_response.get("messages", []):
            if message.get("type") == "answer":
                response_text = message.get("content", "")
                break
        
        # Build OpenAI response according to docs
        return {
            "id": f"chatcmpl-{coze_response.get('conversation_id', 'unknown')}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": f"bot-{self.bot_id}" if self.bot_id else "coze-bot",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 0,  # Coze doesn't provide token statistics
                "completion_tokens": 0,
                "total_tokens": 0
            }
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
        
        # v3 API uses standard Bearer token authentication
        cookies = None
        
        logger.debug("Making request to Coze API", 
                    method=method, 
                    url=url,
                    has_json_data=json_data is not None)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if cookies:
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=request_headers,
                        json=json_data,
                        params=params,
                        cookies=cookies,
                    )
                else:
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
    
    async def make_stream_request(
        self, 
        method: str, 
        url: str, 
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None
    ):
        """Make streaming HTTP request to Coze API."""
        request_headers = self.prepare_headers(headers)
        request_headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        })
        
        logger.info("Making streaming request to Coze API", 
                    method=method, 
                    url=url,
                    has_json_data=json_data is not None,
                    request_data=json_data)
        
        conversation_id = None
        chat_id = None
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    method=method,
                    url=url,
                    headers=request_headers,
                    json=json_data,
                    params=params,
                ) as response:
                    
                    if response.status_code >= 400:
                        error_content = await response.aread()
                        logger.error("Coze API streaming error", 
                                   status_code=response.status_code,
                                   error_content=error_content.decode('utf-8') if error_content else "No content")
                        yield {
                            "error": {
                                "message": f"Coze API error: {response.status_code}",
                                "type": "platform_error",
                                "code": response.status_code
                            }
                        }
                        return
                    
                    # Track conversation info for content fetching
                    conversation_id = None
                    chat_id = None
                    has_yielded_start = False
                    
                    # SSE processing with proper event handling
                    current_event = None
                    buffer = ""
                    
                    async for chunk in response.aiter_text():
                        if not isinstance(chunk, str):
                            continue
                            
                        buffer += chunk
                        
                        # Process complete lines for SSE format
                        while '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                            line = line.strip()
                            
                            if not line:
                                continue
                                
                            try:
                                # Handle SSE event types
                                if line.startswith("event:"):
                                    current_event = line[6:].strip()
                                    logger.debug("SSE event received", event_type=current_event)
                                    continue
                                elif line.startswith("data:"):
                                    # Extract and process SSE data
                                    data_str = line[5:].strip()
                                    
                                    if not data_str or data_str == "":
                                        # Empty data, often follows event completion
                                        continue
                                        
                                    try:
                                        data = json.loads(data_str)
                                        
                                        # Extract conversation info for tracking
                                        if not conversation_id and "conversation_id" in data:
                                            conversation_id = data.get("conversation_id")
                                        if not chat_id and "id" in data:
                                            chat_id = data.get("id")
                                        
                                        # Transform to OpenAI format
                                        result = self._transform_coze_stream_data(data)
                                        if result:
                                            # Yield start chunk once
                                            if not has_yielded_start:
                                                start_chunk = {
                                                    "id": result.get("id", f"coze-{chat_id or 'stream'}"),
                                                    "object": "chat.completion.chunk",
                                                    "created": int(time.time()),
                                                    "model": f"bot-{self.bot_id}" if self.bot_id else "coze-bot",
                                                    "choices": [{
                                                        "index": 0,
                                                        "delta": {"role": "assistant"},
                                                        "finish_reason": None
                                                    }]
                                                }
                                                yield f"data: {json.dumps(start_chunk)}"
                                                has_yielded_start = True
                                            
                                            # Yield transformed result
                                            yield f"data: {json.dumps(result)}"
                                            
                                    except json.JSONDecodeError as e:
                                        logger.warning("Failed to parse SSE JSON data", 
                                                      data=data_str[:100], error=str(e))
                                        continue
                                else:
                                    # Non-SSE line, try direct parsing for fallback
                                    result = self._parse_stream_line(line)
                                    if result:
                                        yield f"data: {json.dumps(result)}"
                                        
                            except Exception as e:
                                logger.error("Error processing SSE stream", 
                                           line=line[:200], 
                                           error=str(e),
                                           current_event=current_event)
                                raise
                    
                    # After streaming is done, try to fetch the actual conversation content
                    if conversation_id and chat_id:
                        content = await self._fetch_conversation_content(
                            client, conversation_id, chat_id, request_headers
                        )
                        if content:
                            # Yield content chunk
                            content_chunk = {
                                "id": chat_id,
                                "object": "chat.completion.chunk",
                                "created": int(time.time()),
                                "model": f"bot-{self.bot_id}" if self.bot_id else "coze-bot",
                                "choices": [{
                                    "index": 0,
                                    "delta": {"content": content},
                                    "finish_reason": None
                                }]
                            }
                            yield f"data: {json.dumps(content_chunk)}"
                            
        except httpx.TimeoutException:
            logger.error("Timeout making streaming request to Coze API", url=url)
            error_chunk = {
                "error": {
                    "message": "Request timeout",
                    "type": "timeout_error",
                    "code": "timeout"
                }
            }
            yield f"data: {json.dumps(error_chunk)}"
        except Exception as e:
            logger.error("Error making streaming request to Coze API", url=url, error=str(e))
            error_chunk = {
                "error": {
                    "message": f"Internal error: {str(e)}",
                    "type": "internal_error",
                    "code": "streaming_error"
                }
            }
            yield f"data: {json.dumps(error_chunk)}"
    
    async def _fetch_conversation_content(
        self, 
        client: httpx.AsyncClient, 
        conversation_id: str, 
        chat_id: str,
        headers: Dict[str, str]
    ) -> Optional[str]:
        """Fetch the actual conversation content after streaming completes."""
        try:
            # Try multiple possible endpoints for getting conversation content
            endpoints = [
                f"/v3/chat/message/list",
                f"/v1/conversation/message/list"
            ]
            
            for endpoint in endpoints:
                try:
                    messages_url = f"{self.base_url.rstrip('/')}{endpoint}"
                    response = await client.get(
                        messages_url,
                        headers=headers,
                        params={
                            "conversation_id": conversation_id,
                            "chat_id": chat_id
                        }
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        # Extract the assistant's response
                        if "data" in data:
                            messages = data["data"]
                            for msg in reversed(messages):  # Get latest message
                                if msg.get("role") == "assistant" and msg.get("content"):
                                    return msg["content"]
                        elif "messages" in data:
                            messages = data["messages"]
                            for msg in reversed(messages):
                                if msg.get("role") == "assistant" and msg.get("content"):
                                    return msg["content"]
                except Exception as e:
                    logger.debug(f"Failed to fetch from {endpoint}", error=str(e))
                    continue
            
            logger.debug("Could not fetch conversation content from any endpoint", 
                        conversation_id=conversation_id,
                        chat_id=chat_id)
            return None
            
        except Exception as e:
            logger.warning("Failed to fetch conversation content", 
                          conversation_id=conversation_id, 
                          error=str(e))
            return None
    
    def _parse_stream_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a single line from Coze streaming response."""
        try:
            if not isinstance(line, str):
                logger.warning("Expected string line, got", type=type(line).__name__)
                return None
            
            line = line.strip()
            if not line:
                return None
            
            # Handle Server-Sent Events format: "event: type\ndata: json"
            if line.startswith("event:"):
                # Store event type for context
                event_type = line[6:].strip()
                self._current_event_type = event_type
                return None
            elif line.startswith("data:"):
                # Extract JSON data
                json_str = line[5:].strip()  # Remove "data:" prefix
                
                if json_str == "" or json_str == "null":
                    return None
                
                try:
                    data = json.loads(json_str)
                    return self._transform_coze_stream_data(data)
                except json.JSONDecodeError as e:
                    logger.warning("Failed to parse JSON from stream line", 
                                  json_str=json_str[:100], error=str(e))
                    return None
            else:
                # Try to parse as direct JSON (in case it's not SSE format)
                try:
                    data = json.loads(line)
                    return self._transform_coze_stream_data(data)
                except json.JSONDecodeError:
                    return None
                
        except Exception as e:
            logger.error("Unexpected error in _parse_stream_line", 
                        line=str(line)[:100] if line else "empty", 
                        error=str(e))
            raise
    
    def _transform_coze_stream_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transform Coze v3 SSE stream data to OpenAI format."""
        try:
            # Handle Coze v3 SSE streaming format
            conversation_id = data.get("conversation_id", "unknown")
            status = data.get("status", "")
            chat_id = data.get("id", conversation_id)
            created_at = data.get("created_at", int(time.time()))
            
            # Map status to OpenAI streaming format
            if status == "in_progress":
                # Progress - return empty delta to maintain connection
                return {
                    "id": f"coze-{chat_id}",
                    "object": "chat.completion.chunk",
                    "created": created_at,
                    "model": f"bot-{self.bot_id}" if self.bot_id else "coze-bot",
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": None
                    }]
                }
            elif status == "completed":
                # Completion - final chunk with stop reason
                return {
                    "id": f"coze-{chat_id}",
                    "object": "chat.completion.chunk",
                    "created": created_at,
                    "model": f"bot-{self.bot_id}" if self.bot_id else "coze-bot",
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }]
                }
            elif status == "failed":
                # Error case
                logger.error("Coze conversation failed", conversation_data=data)
                return {
                    "error": {
                        "message": "Coze conversation failed",
                        "type": "coze_error",
                        "code": "conversation_failed"
                    }
                }
            elif "message" in data:
                # Handle message content if present (for future message streaming)
                message = data.get("message", {})
                if isinstance(message, dict):
                    content = message.get("content", "")
                    if content:
                        return {
                            "id": f"coze-{chat_id}",
                            "object": "chat.completion.chunk", 
                            "created": created_at,
                            "model": f"bot-{self.bot_id}" if self.bot_id else "coze-bot",
                            "choices": [{
                                "index": 0,
                                "delta": {"content": content},
                                "finish_reason": None
                            }]
                        }
            
            # Handle other status types or log for debugging
            if status and status not in ["in_progress", "completed", "failed"]:
                logger.debug("Unknown Coze status", status=status, data=data)
            
            return None
                
        except Exception as e:
            logger.warning("Failed to transform Coze v3 SSE stream data", 
                          error=str(e), data=str(data)[:200])
            return None
    
    def validate_config(self) -> bool:
        """Validate Coze adapter configuration."""
        if not super().validate_config():
            return False
        
        # bot_id is now extracted from the model name at runtime
        # No need to validate it in config
        return True
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get Coze model information."""
        info = super().get_model_info()
        info.update({
            "bot_id": self.bot_id or "extracted_from_model_name",
            "supports_streaming": True,
            "supports_function_calling": False,  # Coze doesn't support function calling in OpenAI format
            "model_format": "bot-{COZE_BOT_ID}",
            "endpoint": "/v3/chat"
        })
        return info