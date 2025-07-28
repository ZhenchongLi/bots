from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional

from src.core.model_manager import model_manager

router = APIRouter(prefix="/admin")


class ModelInfo(BaseModel):
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None


class ModelMapping(BaseModel):
    alias: str
    actual_model: str


@router.get("/models")
async def get_available_models():
    """Get list of available models."""
    return {
        "available_models": model_manager.available_models,
        "model_mappings": model_manager.model_mappings,
        "validation_enabled": model_manager.validate_models,
        "allow_unknown_models": model_manager.allow_unknown_models
    }


@router.post("/models")
async def add_model(model: ModelInfo):
    """Add a new model to the available models list."""
    try:
        model_manager.add_model(model.name)
        return {"message": f"Model '{model.name}' added successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/models/{model_name}")
async def remove_model(model_name: str):
    """Remove a model from the available models list."""
    try:
        if model_name not in model_manager.available_models:
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")
        
        model_manager.remove_model(model_name)
        return {"message": f"Model '{model_name}' removed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/model-mappings")
async def add_model_mapping(mapping: ModelMapping):
    """Add a model mapping (alias -> actual model)."""
    try:
        model_manager.add_model_mapping(mapping.alias, mapping.actual_model)
        return {"message": f"Model mapping '{mapping.alias}' -> '{mapping.actual_model}' added successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/model-mappings/{alias}")
async def remove_model_mapping(alias: str):
    """Remove a model mapping."""
    try:
        if alias not in model_manager.model_mappings:
            raise HTTPException(status_code=404, detail=f"Model mapping '{alias}' not found")
        
        model_manager.remove_model_mapping(alias)
        return {"message": f"Model mapping '{alias}' removed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/model-mappings")
async def get_model_mappings():
    """Get all model mappings."""
    return model_manager.model_mappings


@router.post("/reload-config")
async def reload_model_config():
    """Reload model configuration from settings."""
    try:
        # Reinitialize model manager with current settings
        from src.config.settings import settings
        model_manager.available_models = settings.available_models
        model_manager.model_mappings = settings.model_mappings
        model_manager.validate_models = settings.validate_models
        model_manager.allow_unknown_models = settings.allow_unknown_models
        
        return {"message": "Model configuration reloaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))