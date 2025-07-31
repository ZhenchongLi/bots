"""
Base adapter for AI platform integration.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import structlog

logger = structlog.get_logger()


class BasePlatformAdapter(ABC):
    """Base class for AI platform adapters."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the adapter with configuration.
        
        Args:
            config: Platform-specific configuration dictionary
        """
        self.config = config
        self.platform_name = self.get_platform_name()
        
        # Common configuration
        self.api_key = config.get("api_key")
        self.base_url = config.get("base_url")
        self.timeout = config.get("timeout", 300)
        self.enabled = config.get("enabled", True)
        
        logger.info("Initialized platform adapter", 
                   platform=self.platform_name, 
                   enabled=self.enabled)
    
    @abstractmethod
    def get_platform_name(self) -> str:
        """Return the platform name."""
        pass
    
    @abstractmethod
    def get_supported_endpoints(self) -> List[str]:
        """Return list of supported endpoints for this platform."""
        pass
    
    @abstractmethod
    async def transform_request(self, endpoint: str, openai_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform OpenAI-compatible request to platform-specific format.
        
        Args:
            endpoint: The API endpoint being called (e.g., '/chat/completions')
            openai_request: Request in OpenAI format
            
        Returns:
            Platform-specific request format
        """
        pass
    
    @abstractmethod
    async def transform_response(self, endpoint: str, platform_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform platform-specific response to OpenAI-compatible format.
        
        Args:
            endpoint: The API endpoint that was called
            platform_response: Response from platform API
            
        Returns:
            OpenAI-compatible response format
        """
        pass
    
    @abstractmethod
    async def make_request(
        self, 
        method: str, 
        url: str, 
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to the platform API.
        
        Args:
            method: HTTP method
            url: Full URL for the request
            headers: HTTP headers
            json_data: JSON request body
            params: URL parameters
            
        Returns:
            Raw response from platform
        """
        pass
    
    def prepare_headers(self, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Prepare headers for the request."""
        request_headers = {}
        if headers:
            # Filter out potentially conflicting headers
            filtered_headers = {k: v for k, v in headers.items() 
                              if k.lower() not in ['authorization', 'host', 'content-length']}
            request_headers.update(filtered_headers)
        return request_headers
    
    def validate_config(self) -> bool:
        """
        Validate adapter configuration.
        
        Returns:
            True if configuration is valid
        """
        if not self.api_key:
            logger.error("API key is required", platform=self.platform_name)
            return False
        
        if not self.base_url:
            logger.error("Base URL is required", platform=self.platform_name)
            return False
            
        return True
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get model information for this platform.
        
        Returns:
            Model information dict
        """
        return {
            "platform": self.platform_name,
            "enabled": self.enabled,
            "actual_name": self.config.get("actual_name", "unknown"),
            "display_name": self.config.get("display_name", self.platform_name),
            "description": self.config.get("description", f"{self.platform_name} model"),
            "max_tokens": self.config.get("max_tokens", 4096),
            "supports_streaming": self.config.get("supports_streaming", False),
            "supports_function_calling": self.config.get("supports_function_calling", False)
        }


class AdapterRegistry:
    """Registry for managing platform adapters."""
    
    def __init__(self):
        self._adapters: Dict[str, type] = {}
        self._instances: Dict[str, BasePlatformAdapter] = {}
    
    def register(self, platform_name: str, adapter_class: type):
        """
        Register an adapter class for a platform.
        
        Args:
            platform_name: Name of the platform
            adapter_class: Adapter class to register
        """
        if not issubclass(adapter_class, BasePlatformAdapter):
            raise ValueError(f"Adapter class must inherit from BasePlatformAdapter")
        
        self._adapters[platform_name] = adapter_class
        logger.info("Registered platform adapter", platform=platform_name)
    
    def get_adapter(self, platform_name: str, config: Dict[str, Any]) -> Optional[BasePlatformAdapter]:
        """
        Get adapter instance for a platform.
        
        Args:
            platform_name: Name of the platform
            config: Platform configuration
            
        Returns:
            Adapter instance or None if not found
        """
        adapter_class = self._adapters.get(platform_name)
        if not adapter_class:
            logger.warning("No adapter found for platform", platform=platform_name)
            return None
        
        # Create new instance each time to ensure fresh config
        try:
            adapter = adapter_class(config)
            if not adapter.validate_config():
                logger.error("Invalid adapter configuration", platform=platform_name)
                return None
            return adapter
        except Exception as e:
            logger.error("Failed to create adapter", platform=platform_name, error=str(e))
            return None
    
    def list_platforms(self) -> List[str]:
        """Get list of registered platforms."""
        return list(self._adapters.keys())
    
    def is_supported(self, platform_name: str) -> bool:
        """Check if platform is supported."""
        return platform_name in self._adapters


# Global registry instance
adapter_registry = AdapterRegistry()