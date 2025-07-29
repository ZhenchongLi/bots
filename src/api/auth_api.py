from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from src.auth.client_auth import api_key_manager, require_admin_permission

router = APIRouter(prefix="/admin")

class CreateAPIKeyRequest(BaseModel):
    key_id: str = Field(..., description="Unique identifier for the API key")
    description: str = Field(default="", description="Description of the API key")
    permissions: List[str] = Field(
        default=["chat", "completion", "embedding"], 
        description="List of permissions for the API key"
    )
    expires_days: Optional[int] = Field(
        default=None, 
        description="Number of days until the key expires (null for never)"
    )

class APIKeyResponse(BaseModel):
    api_key: str
    key_id: str
    description: str
    permissions: List[str]
    created_at: datetime
    expires_at: Optional[datetime]

class APIKeyListResponse(BaseModel):
    keys: Dict[str, Dict[str, Any]]

class RevokeAPIKeyRequest(BaseModel):
    api_key: str = Field(..., description="The API key to revoke")

@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    request: CreateAPIKeyRequest,
    key_data: Dict[str, Any] = Depends(require_admin_permission)
):
    """Create a new API key (admin only)."""
    try:
        # Calculate expiration date
        expires_at = None
        if request.expires_days is not None:
            expires_at = datetime.now() + timedelta(days=request.expires_days)
        
        # Create the API key
        api_key = api_key_manager.create_api_key(
            key_id=request.key_id,
            description=request.description,
            permissions=request.permissions,
            expires_at=expires_at
        )
        
        return APIKeyResponse(
            api_key=api_key,
            key_id=request.key_id,
            description=request.description,
            permissions=request.permissions,
            created_at=datetime.now(),
            expires_at=expires_at
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create API key: {str(e)}")

@router.get("/api-keys", response_model=APIKeyListResponse)
async def list_api_keys(key_data: Dict[str, Any] = Depends(require_admin_permission)):
    """List all API keys (admin only)."""
    try:
        keys = api_key_manager.list_api_keys()
        return APIKeyListResponse(keys=keys)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list API keys: {str(e)}")

@router.delete("/api-keys")
async def revoke_api_key(
    request: RevokeAPIKeyRequest,
    key_data: Dict[str, Any] = Depends(require_admin_permission)
):
    """Revoke an API key (admin only)."""
    try:
        success = api_key_manager.revoke_api_key(request.api_key)
        if success:
            return {"message": "API key revoked successfully"}
        else:
            raise HTTPException(status_code=404, detail="API key not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to revoke API key: {str(e)}")

@router.get("/generate-default-admin-key")
async def generate_default_admin_key():
    """Generate and return the default admin API key for initial setup."""
    try:
        # This is a special endpoint that only works when no admin keys exist
        keys = api_key_manager.list_api_keys()
        admin_keys = [k for k, v in keys.items() if "admin" in v.get("permissions", [])]
        
        if admin_keys:
            raise HTTPException(
                status_code=403, 
                detail="Admin keys already exist. Use existing admin key to manage keys."
            )
        
        # Generate a new admin key
        admin_key = api_key_manager.create_api_key(
            key_id="bootstrap_admin",
            description="Bootstrap admin key for initial setup",
            permissions=["admin", "chat", "completion", "embedding"],
            expires_at=datetime.now() + timedelta(days=30)  # Expires in 30 days
        )
        
        return {
            "admin_key": admin_key,
            "expires_at": datetime.now() + timedelta(days=30),
            "message": "Bootstrap admin key created. Use this to create permanent admin keys, then revoke this one."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate admin key: {str(e)}")