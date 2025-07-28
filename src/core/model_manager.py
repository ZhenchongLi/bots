from typing import Dict, List, Optional, Any, Tuple
from src.config.settings import settings
import structlog

logger = structlog.get_logger()


class ModelManager:
    def __init__(self):
        self.config = self._get_model_config()
    
    def _get_model_config(self) -> Dict[str, Any]:
        """Get the single model configuration from settings."""
        return {
            "type": settings.type,
            "api_key": settings.api_key,
            "base_url": settings.base_url,
            "enabled": settings.enabled,
            "default_headers": settings.default_headers,
            "timeout": settings.timeout,
            "actual_name": settings.actual_name,
            "display_name": settings.display_name,
            "description": settings.description,
            "max_tokens": settings.max_tokens,
            "supports_streaming": settings.supports_streaming,
            "supports_function_calling": settings.supports_function_calling,
            "cost_per_1k_input_tokens": settings.cost_per_1k_input_tokens,
            "cost_per_1k_output_tokens": settings.cost_per_1k_output_tokens,
        }
    
    def is_model_available(self) -> bool:
        """Check if the model is available and enabled."""
        return self.config.get("enabled", False) and self.config.get("api_key", "")
    
    def get_model_config(self) -> Dict[str, Any]:
        """Get model configuration."""
        return self.config
    
    def validate_model_request(self, model_name: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a model request.
        Returns (is_valid, error_message)
        """
        # Check if model is enabled and has API key
        if not self.config.get("enabled", False):
            return False, "Model is disabled"
        
        if not self.config.get("api_key"):
            return False, "API key not configured"
        
        return True, None
    
    def process_model_request(self, request_data: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """
        Process a request and determine actual model name.
        Returns (request_data, actual_model_name)
        """
        if "model" not in request_data:
            raise ValueError("No model specified in request")
        
        requested_model = request_data["model"]
        
        # Validate the model configuration
        is_valid, error_message = self.validate_model_request(requested_model)
        if not is_valid:
            raise ValueError(error_message)
        
        # Get actual model name from configuration
        actual_model_name = self.config.get("actual_name", requested_model)
        
        # Update request data with actual model name
        modified_request = request_data.copy()
        modified_request["model"] = actual_model_name
        
        logger.info("Model request processed", 
                   requested_model=requested_model,
                   actual_model=actual_model_name,
                   platform_type=self.config.get("type"))
        
        return modified_request, actual_model_name
    
    def get_models_list(self) -> List[Dict[str, Any]]:
        """Get a list of available models in OpenAI API format."""
        models = []
        
        # Only include model if it's enabled and has api_key
        if self.config.get("enabled", False) and self.config.get("api_key"):
            model_name = self.config.get("actual_name", "model")
            platform_type = self.config.get("type", "unknown")
            
            models.append({
                "id": model_name,
                "object": "model",
                "created": 1677610602,  # Placeholder timestamp
                "owned_by": platform_type,
                "root": model_name,
                "parent": None,
                "permission": [{
                    "id": f"modelperm-{model_name}",
                    "object": "model_permission",
                    "created": 1677610602,
                    "allow_create_engine": False,
                    "allow_sampling": True,
                    "allow_logprobs": True,
                    "allow_search_indices": False,
                    "allow_view": True,
                    "allow_fine_tuning": False,
                    "organization": "*",
                    "group": None,
                    "is_blocking": False
                }]
            })
        
        return models
    
    def reload_config(self) -> None:
        """Reload configuration from settings."""
        from src.config.settings import settings
        self.config = self._get_model_config()
        logger.info("Configuration reloaded")
            
    def get_available_models(self) -> List[str]:
        """Get list of available model names."""
        if self.config.get("enabled", False) and self.config.get("api_key"):
            return [self.config.get("actual_name", "model")]
        return []
        
    def get_platform_type(self) -> Optional[str]:
        """Get the platform type."""
        return self.config.get("type")


# Global model manager instance
model_manager = ModelManager()