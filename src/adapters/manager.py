"""
Adapter manager for handling platform adapters.
"""
from typing import Dict, Any, Optional
import structlog
from .base import BasePlatformAdapter, adapter_registry
from .coze_adapter import CozeAdapter

logger = structlog.get_logger()


class AdapterManager:
    """Manager for platform adapters."""
    
    def __init__(self):
        """Initialize adapter manager."""
        self._register_builtin_adapters()
        self._current_adapter: Optional[BasePlatformAdapter] = None
        
    def _register_builtin_adapters(self):
        """Register built-in adapters."""
        # Register Coze adapter
        adapter_registry.register("coze", CozeAdapter)
        
        logger.info("Registered built-in adapters", 
                   platforms=adapter_registry.list_platforms())
    
    def initialize_adapter(self, platform_type: str, config: Dict[str, Any]) -> bool:
        """
        Initialize adapter for the specified platform.
        
        Args:
            platform_type: Platform type (e.g., 'coze', 'openai')
            config: Platform configuration
            
        Returns:
            True if initialization successful
        """
        try:
            adapter = adapter_registry.get_adapter(platform_type, config)
            if not adapter:
                logger.error("Failed to get adapter", platform=platform_type)
                return False
            
            self._current_adapter = adapter
            logger.info("Initialized adapter", 
                       platform=platform_type,
                       enabled=adapter.enabled)
            return True
            
        except Exception as e:
            logger.error("Failed to initialize adapter", 
                        platform=platform_type, 
                        error=str(e))
            return False
    
    def get_current_adapter(self) -> Optional[BasePlatformAdapter]:
        """Get the currently active adapter."""
        return self._current_adapter
    
    def is_platform_supported(self, platform_type: str) -> bool:
        """Check if platform is supported."""
        return adapter_registry.is_supported(platform_type)
    
    def get_supported_platforms(self) -> list:
        """Get list of supported platforms."""
        return adapter_registry.list_platforms()
    
    async def process_request(
        self, 
        endpoint: str, 
        method: str,
        openai_request: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Process request through the current adapter.
        
        Args:
            endpoint: API endpoint (e.g., '/chat/completions')
            method: HTTP method
            openai_request: Request in OpenAI format
            headers: HTTP headers
            
        Returns:
            Response in OpenAI format
        """
        if not self._current_adapter:
            raise RuntimeError("No adapter initialized")
        
        if not self._current_adapter.enabled:
            raise RuntimeError(f"Adapter {self._current_adapter.platform_name} is disabled")
        
        # Check if endpoint is supported and map to platform-specific endpoint
        if endpoint not in self._current_adapter.get_supported_endpoints():
            raise ValueError(f"Endpoint {endpoint} not supported by {self._current_adapter.platform_name}")
        
        try:
            # Transform request to platform format
            platform_request = await self._current_adapter.transform_request(endpoint, openai_request)
            
            # Map endpoint to platform-specific endpoint
            platform_endpoint = self._map_endpoint_to_platform(endpoint)
            
            # Construct URL
            url = f"{self._current_adapter.base_url.rstrip('/')}{platform_endpoint}"
            
            # Make request to platform
            platform_response = await self._current_adapter.make_request(
                method=method,
                url=url,
                headers=headers,
                json_data=platform_request
            )
            
            # Handle HTTP errors
            if platform_response["status_code"] >= 400:
                logger.error("Platform API error", 
                           platform=self._current_adapter.platform_name,
                           status_code=platform_response["status_code"])
                
                # Return error in OpenAI format
                return {
                    "error": {
                        "message": f"Platform API error: {platform_response['status_code']}",
                        "type": "platform_error",
                        "code": platform_response["status_code"]
                    }
                }
            
            # Transform response to OpenAI format
            if platform_response["json"]:
                openai_response = await self._current_adapter.transform_response(
                    endpoint, platform_response["json"]
                )
            else:
                # Handle non-JSON responses
                openai_response = {
                    "error": {
                        "message": "Invalid response from platform",
                        "type": "invalid_response",
                        "code": "no_json"
                    }
                }
            
            return openai_response
            
        except Exception as e:
            logger.error("Error processing request", 
                        platform=self._current_adapter.platform_name,
                        endpoint=endpoint,
                        error=str(e))
            
            return {
                "error": {
                    "message": f"Internal error: {str(e)}",
                    "type": "internal_error",
                    "code": "processing_error"
                }
            }
    
    def _map_endpoint_to_platform(self, endpoint: str) -> str:
        """Map OpenAI endpoint to platform-specific endpoint."""
        if not self._current_adapter:
            return endpoint
            
        platform_name = self._current_adapter.platform_name
        
        # Map endpoints for different platforms
        if platform_name == "coze":
            if endpoint == "/chat/completions":
                return "/v3/chat"
        
        # Default: return original endpoint
        return endpoint
    
    async def process_stream_request(
        self, 
        endpoint: str, 
        method: str,
        openai_request: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None
    ):
        """
        Process streaming request through the current adapter.
        
        Args:
            endpoint: API endpoint (e.g., '/chat/completions')
            method: HTTP method
            openai_request: Request in OpenAI format
            headers: HTTP headers
            
        Yields:
            Response chunks in OpenAI format
        """
        if not self._current_adapter:
            raise RuntimeError("No adapter initialized")
        
        if not self._current_adapter.enabled:
            raise RuntimeError(f"Adapter {self._current_adapter.platform_name} is disabled")
        
        # Check if endpoint is supported and map to platform-specific endpoint
        if endpoint not in self._current_adapter.get_supported_endpoints():
            raise ValueError(f"Endpoint {endpoint} not supported by {self._current_adapter.platform_name}")
        
        try:
            # Transform request to platform format
            platform_request = await self._current_adapter.transform_request(endpoint, openai_request)
            
            # Map endpoint to platform-specific endpoint
            platform_endpoint = self._map_endpoint_to_platform(endpoint)
            
            # Construct URL
            url = f"{self._current_adapter.base_url.rstrip('/')}{platform_endpoint}"
            
            # Check if adapter supports streaming
            if hasattr(self._current_adapter, 'make_stream_request'):
                # Make streaming request to platform
                async for chunk in self._current_adapter.make_stream_request(
                    method=method,
                    url=url,
                    headers=headers,
                    json_data=platform_request
                ):
                    if chunk:  # Skip None chunks
                        # Transform each chunk to OpenAI format if needed
                        if "error" not in chunk:
                            yield chunk
                        else:
                            # Error handling
                            yield chunk
                            return
            else:
                # Fallback to non-streaming for adapters without streaming support
                logger.warning("Adapter doesn't support streaming, using non-streaming fallback",
                              platform=self._current_adapter.platform_name)
                
                # Make regular request and yield as single chunk
                platform_response = await self._current_adapter.make_request(
                    method=method,
                    url=url,
                    headers=headers,
                    json_data=platform_request
                )
                
                if platform_response["status_code"] >= 400:
                    yield {
                        "error": {
                            "message": f"Platform API error: {platform_response['status_code']}",
                            "type": "platform_error",
                            "code": platform_response["status_code"]
                        }
                    }
                    return
                
                # Transform response to OpenAI streaming format
                if platform_response["json"]:
                    openai_response = await self._current_adapter.transform_response(
                        endpoint, platform_response["json"]
                    )
                    
                    # Convert to streaming format
                    if "choices" in openai_response and openai_response["choices"]:
                        content = openai_response["choices"][0].get("message", {}).get("content", "")
                        
                        # Start chunk
                        yield {
                            "id": openai_response.get("id", "fallback-stream"),
                            "object": "chat.completion.chunk",
                            "created": openai_response.get("created", 1677652288),
                            "model": openai_response.get("model", "unknown"),
                            "choices": [{
                                "index": 0,
                                "delta": {"role": "assistant"},
                                "finish_reason": None
                            }]
                        }
                        
                        # Content chunk
                        if content:
                            yield {
                                "id": openai_response.get("id", "fallback-stream"),
                                "object": "chat.completion.chunk",
                                "created": openai_response.get("created", 1677652288),
                                "model": openai_response.get("model", "unknown"),
                                "choices": [{
                                    "index": 0,
                                    "delta": {"content": content},
                                    "finish_reason": None
                                }]
                            }
                        
                        # End chunk
                        yield {
                            "id": openai_response.get("id", "fallback-stream"),
                            "object": "chat.completion.chunk",
                            "created": openai_response.get("created", 1677652288),
                            "model": openai_response.get("model", "unknown"),
                            "choices": [{
                                "index": 0,
                                "delta": {},
                                "finish_reason": "stop"
                            }],
                            "usage": openai_response.get("usage", {
                                "prompt_tokens": 0,
                                "completion_tokens": 0,
                                "total_tokens": 0
                            })
                        }
                else:
                    yield {
                        "error": {
                            "message": "Invalid response from platform",
                            "type": "invalid_response",
                            "code": "no_json"
                        }
                    }
                    
        except Exception as e:
            logger.error("Error processing streaming request", 
                        platform=self._current_adapter.platform_name,
                        endpoint=endpoint,
                        error=str(e))
            
            yield {
                "error": {
                    "message": f"Internal error: {str(e)}",
                    "type": "internal_error",
                    "code": "processing_error"
                }
            }
    
    def get_model_info(self) -> Optional[Dict[str, Any]]:
        """Get model information from current adapter."""
        if not self._current_adapter:
            return None
        
        return self._current_adapter.get_model_info()


# Global adapter manager instance
adapter_manager = AdapterManager()