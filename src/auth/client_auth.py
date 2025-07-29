from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
import uuid
import hashlib
import time
from datetime import datetime, timedelta
import orjson as json
import structlog

logger = structlog.get_logger()

class APIKeyManager:
    def __init__(self):
        self._api_keys: Dict[str, Dict[str, Any]] = {}
        self._load_default_keys()
    
    def _load_default_keys(self):
        """Load default API keys."""
        # Create a default admin key
        admin_key = self.generate_api_key("officeai-admin")
        self._api_keys[admin_key] = {
            "key_id": "default_admin",
            "description": "Default admin key - change in production",
            "permissions": ["admin", "chat", "completion", "embedding"],
            "created_at": datetime.now(),
            "expires_at": None,  # Never expires
            "last_used_at": None,
            "usage_count": 0,
            "is_active": True
        }
        
        logger.info("Default admin API key created", 
                   key_id="default_admin", 
                   api_key=admin_key[:20] + "...")
        
        # Store the default admin key for startup display
        self._default_admin_key = admin_key
    
    def generate_api_key(self, prefix: str = "officeai") -> str:
        """Generate a new API key with the specified prefix."""
        key_suffix = hashlib.sha256(
            f"{uuid.uuid4()}{time.time()}".encode()
        ).hexdigest()[:32]
        return f"{prefix}-{key_suffix}"
    
    def create_api_key(
        self,
        key_id: str,
        description: str = "",
        permissions: list = None,
        expires_at: Optional[datetime] = None
    ) -> str:
        """Create a new API key."""
        if permissions is None:
            permissions = ["chat", "completion", "embedding"]
        
        api_key = self.generate_api_key()
        
        self._api_keys[api_key] = {
            "key_id": key_id,
            "description": description,
            "permissions": permissions,
            "created_at": datetime.now(),
            "expires_at": expires_at,
            "last_used_at": None,
            "usage_count": 0,
            "is_active": True
        }
        
        logger.info("API key created", 
                   key_id=key_id, 
                   permissions=permissions,
                   expires_at=expires_at)
        
        return api_key
    
    def validate_api_key(self, api_key: str) -> tuple[bool, Optional[Dict[str, Any]]]:
        """Validate an API key and return its metadata."""
        if not api_key or api_key not in self._api_keys:
            return False, None
        
        key_data = self._api_keys[api_key]
        
        # Check if key is active
        if not key_data.get("is_active", True):
            return False, None
        
        # Check if key has expired
        if key_data.get("expires_at") and datetime.now() > key_data["expires_at"]:
            return False, None
        
        # Update usage statistics
        key_data["last_used_at"] = datetime.now()
        key_data["usage_count"] += 1
        
        return True, key_data
    
    def revoke_api_key(self, api_key: str) -> bool:
        """Revoke an API key."""
        if api_key in self._api_keys:
            self._api_keys[api_key]["is_active"] = False
            logger.info("API key revoked", key_id=self._api_keys[api_key]["key_id"])
            return True
        return False
    
    def list_api_keys(self) -> Dict[str, Dict[str, Any]]:
        """List all API keys (without exposing the actual keys)."""
        return {
            key[:12] + "..." + key[-4:]: {
                "key_id": data["key_id"],
                "description": data["description"],
                "permissions": data["permissions"],
                "created_at": data["created_at"],
                "expires_at": data["expires_at"],
                "last_used_at": data["last_used_at"],
                "usage_count": data["usage_count"],
                "is_active": data["is_active"]
            }
            for key, data in self._api_keys.items()
        }
    
    def has_permission(self, api_key: str, permission: str) -> bool:
        """Check if an API key has a specific permission."""
        is_valid, key_data = self.validate_api_key(api_key)
        if not is_valid or not key_data:
            return False
        
        permissions = key_data.get("permissions", [])
        return "admin" in permissions or permission in permissions
    
    def get_default_admin_key(self) -> str:
        """Get the default admin API key for startup display."""
        return getattr(self, '_default_admin_key', 'Not available')


# Global API key manager instance
api_key_manager = APIKeyManager()

# HTTP Bearer security scheme
security = HTTPBearer(auto_error=False)

async def get_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> str:
    """Extract API key from Authorization header."""
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Missing authorization header"
        )
    
    return credentials.credentials

async def verify_api_key(api_key: str = Depends(get_api_key)) -> Dict[str, Any]:
    """Verify API key and return key metadata."""
    from src.config.settings import settings
    
    # Skip authentication if disabled in settings
    if not settings.enable_client_auth:
        return {"key_id": "anonymous", "permissions": ["admin", "chat", "completion", "embedding"]}
    
    is_valid, key_data = api_key_manager.validate_api_key(api_key)
    
    if not is_valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired API key"
        )
    
    return key_data

def require_permission(permission: str):
    """Create a dependency that requires a specific permission."""
    async def permission_check(api_key: str = Depends(get_api_key)) -> Dict[str, Any]:
        from src.config.settings import settings
        
        # Skip authentication if disabled in settings
        if not settings.enable_client_auth:
            return {"key_id": "anonymous", "permissions": ["admin", "chat", "completion", "embedding"]}
        
        if not api_key_manager.has_permission(api_key, permission):
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required: {permission}"
            )
        
        is_valid, key_data = api_key_manager.validate_api_key(api_key)
        return key_data
    
    return permission_check

# Convenience dependencies for common permissions
require_chat_permission = require_permission("chat")
require_completion_permission = require_permission("completion")
require_embedding_permission = require_permission("embedding")
require_admin_permission = require_permission("admin")