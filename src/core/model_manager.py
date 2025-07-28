from typing import Dict, List, Optional, Any
from src.config.settings import settings, ModelConfig
import structlog

logger = structlog.get_logger()


class ModelManager:
    def __init__(self):
        self.available_models = settings.available_models
        self.model_mappings = settings.model_mappings
        self.validate_models = settings.validate_models
        self.allow_unknown_models = settings.allow_unknown_models
    
    def is_model_available(self, model_name: str) -> bool:
        """Check if a model is available in the configured list."""
        return model_name in self.available_models
    
    def get_mapped_model(self, requested_model: str) -> str:
        """Get the actual model name to use, applying any mappings."""
        return self.model_mappings.get(requested_model, requested_model)
    
    def validate_model_request(self, model_name: str) -> tuple[bool, Optional[str]]:
        """
        Validate a model request.
        Returns (is_valid, error_message)
        """
        if not self.validate_models:
            return True, None
        
        # Check if model is in available list
        if self.is_model_available(model_name):
            return True, None
        
        # Check if there's a mapping for this model
        mapped_model = self.get_mapped_model(model_name)
        if mapped_model != model_name and self.is_model_available(mapped_model):
            return True, None
        
        # Check if unknown models are allowed
        if self.allow_unknown_models:
            logger.warning("Unknown model requested but allowed", model=model_name)
            return True, None
        
        return False, f"Model '{model_name}' is not available. Available models: {', '.join(self.available_models)}"
    
    def process_model_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a request and apply model mappings if necessary.
        Returns the modified request data.
        """
        if "model" not in request_data:
            return request_data
        
        original_model = request_data["model"]
        
        # Validate the model
        is_valid, error_message = self.validate_model_request(original_model)
        if not is_valid:
            raise ValueError(error_message)
        
        # Apply model mapping
        mapped_model = self.get_mapped_model(original_model)
        if mapped_model != original_model:
            logger.info("Model mapping applied", 
                       original_model=original_model, 
                       mapped_model=mapped_model)
            request_data = request_data.copy()
            request_data["model"] = mapped_model
        
        return request_data
    
    def get_models_list(self) -> List[Dict[str, Any]]:
        """Get a list of available models in OpenAI API format."""
        models = []
        for model_name in self.available_models:
            models.append({
                "id": model_name,
                "object": "model",
                "created": 1677610602,  # Placeholder timestamp
                "owned_by": "openai",
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
    
    def add_model(self, model_name: str) -> None:
        """Add a model to the available models list."""
        if model_name not in self.available_models:
            self.available_models.append(model_name)
            logger.info("Model added", model=model_name)
    
    def remove_model(self, model_name: str) -> None:
        """Remove a model from the available models list."""
        if model_name in self.available_models:
            self.available_models.remove(model_name)
            logger.info("Model removed", model=model_name)
    
    def add_model_mapping(self, alias: str, actual_model: str) -> None:
        """Add a model mapping (alias -> actual model)."""
        self.model_mappings[alias] = actual_model
        logger.info("Model mapping added", alias=alias, actual_model=actual_model)
    
    def remove_model_mapping(self, alias: str) -> None:
        """Remove a model mapping."""
        if alias in self.model_mappings:
            del self.model_mappings[alias]
            logger.info("Model mapping removed", alias=alias)


# Global model manager instance
model_manager = ModelManager()