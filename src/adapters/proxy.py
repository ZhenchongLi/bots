"""
Adapter proxy for seamless integration with existing code.
"""
from typing import Dict, Any, Optional
import structlog
from .manager import adapter_manager

logger = structlog.get_logger()


class AdapterProxy:
    """
    Proxy class that provides backward compatibility with existing platform client interface.
    
    This allows the new adapter system to work with existing code without modifications.
    """
    
    def __init__(self, platform_config: Dict[str, Any]):
        """
        Initialize adapter proxy.
        
        Args:
            platform_config: Platform configuration
        """
        self.config = platform_config
        self.platform_type = platform_config.get("type", "unknown")
        
        # Initialize adapter if supported
        if adapter_manager.is_platform_supported(self.platform_type):
            success = adapter_manager.initialize_adapter(self.platform_type, platform_config)
            if not success:
                logger.warning("Failed to initialize adapter, using fallback", 
                              platform=self.platform_type)
                self._fallback_mode = True
            else:
                self._fallback_mode = False
        else:
            logger.warning("Platform not supported by adapter system, using fallback", 
                          platform=self.platform_type)
            self._fallback_mode = True
    
    async def make_request(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make request through adapter system or fallback.
        
        This method maintains compatibility with the existing BasePlatformClient interface.
        """
        if self._fallback_mode:
            return await self._fallback_request(method, path, headers, json_data, params)
        
        try:
            # Use adapter system for supported platforms
            response = await adapter_manager.process_request(
                endpoint=path,
                method=method,
                openai_request=json_data or {},
                headers=headers
            )
            
            # Convert to expected format for backward compatibility
            return {
                "status_code": 200,
                "headers": {"content-type": "application/json"},
                "content": b"",  # Not used in adapter system
                "json": response
            }
            
        except Exception as e:
            logger.error("Adapter request failed, using fallback", 
                        platform=self.platform_type, 
                        error=str(e))
            return await self._fallback_request(method, path, headers, json_data, params)
    
    async def _fallback_request(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Fallback to original platform client system.
        
        This is used when adapter system is not available or fails.
        """
        # Import here to avoid circular imports
        from src.core.platform_clients import PlatformClientFactory
        
        # Create original client
        original_client = PlatformClientFactory.create_client(self.platform_type, self.config)
        
        # Use original client
        return await original_client.make_request(method, path, headers, json_data, params)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        if not self._fallback_mode:
            info = adapter_manager.get_model_info()
            if info:
                return info
        
        # Fallback to basic info from config
        return {
            "platform": self.platform_type,
            "enabled": self.config.get("enabled", True),
            "actual_name": self.config.get("actual_name", "unknown"),
            "display_name": self.config.get("display_name", self.platform_type),
            "description": self.config.get("description", f"{self.platform_type} model"),
            "max_tokens": self.config.get("max_tokens", 4096),
            "supports_streaming": self.config.get("supports_streaming", False),
            "supports_function_calling": self.config.get("supports_function_calling", False)
        }