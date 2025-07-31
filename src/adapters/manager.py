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
        
        # Check if endpoint is supported
        if endpoint not in self._current_adapter.get_supported_endpoints():
            raise ValueError(f"Endpoint {endpoint} not supported by {self._current_adapter.platform_name}")
        
        try:
            # Transform request to platform format
            platform_request = await self._current_adapter.transform_request(endpoint, openai_request)
            
            # Construct URL
            url = f"{self._current_adapter.base_url.rstrip('/')}{endpoint}"
            
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
    
    def get_model_info(self) -> Optional[Dict[str, Any]]:
        """Get model information from current adapter."""
        if not self._current_adapter:
            return None
        
        return self._current_adapter.get_model_info()


# Global adapter manager instance
adapter_manager = AdapterManager()