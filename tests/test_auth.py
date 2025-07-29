import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from fastapi import HTTPException

from src.auth.client_auth import APIKeyManager, api_key_manager, get_api_key, verify_api_key, require_permission
from fastapi.security import HTTPAuthorizationCredentials


class TestAPIKeyManager:
    """Test API key management functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = APIKeyManager()
    
    def test_generate_api_key_default_prefix(self):
        """Test API key generation with default prefix."""
        key = self.manager.generate_api_key()
        assert key.startswith("officeai-")
        assert len(key) > len("officeai-")
    
    def test_generate_api_key_custom_prefix(self):
        """Test API key generation with custom prefix."""
        key = self.manager.generate_api_key("test")
        assert key.startswith("test-")
        assert len(key) > len("test-")
    
    def test_create_api_key(self):
        """Test creating a new API key."""
        key = self.manager.create_api_key(
            key_id="test_key",
            description="Test key",
            permissions=["chat"],
            expires_at=None
        )
        
        assert key.startswith("officeai-")
        
        # Validate the key
        is_valid, key_data = self.manager.validate_api_key(key)
        assert is_valid
        assert key_data["key_id"] == "test_key"
        assert key_data["description"] == "Test key"
        assert key_data["permissions"] == ["chat"]
        assert key_data["expires_at"] is None
        assert key_data["is_active"] is True
    
    def test_create_api_key_with_expiration(self):
        """Test creating an API key with expiration."""
        expires_at = datetime.now() + timedelta(days=1)
        key = self.manager.create_api_key(
            key_id="expiring_key",
            expires_at=expires_at
        )
        
        is_valid, key_data = self.manager.validate_api_key(key)
        assert is_valid
        assert key_data["expires_at"] == expires_at
    
    def test_validate_api_key_invalid(self):
        """Test validating an invalid API key."""
        is_valid, key_data = self.manager.validate_api_key("invalid-key")
        assert not is_valid
        assert key_data is None
    
    def test_validate_api_key_expired(self):
        """Test validating an expired API key."""
        expires_at = datetime.now() - timedelta(days=1)  # Already expired
        key = self.manager.create_api_key(
            key_id="expired_key",
            expires_at=expires_at
        )
        
        is_valid, key_data = self.manager.validate_api_key(key)
        assert not is_valid
        assert key_data is None
    
    def test_validate_api_key_inactive(self):
        """Test validating an inactive API key."""
        key = self.manager.create_api_key(key_id="inactive_key")
        
        # Revoke the key
        self.manager.revoke_api_key(key)
        
        is_valid, key_data = self.manager.validate_api_key(key)
        assert not is_valid
        assert key_data is None
    
    def test_validate_api_key_updates_usage(self):
        """Test that validating updates usage statistics."""
        key = self.manager.create_api_key(key_id="usage_test")
        
        # First validation
        is_valid, key_data = self.manager.validate_api_key(key)
        assert is_valid
        assert key_data["usage_count"] == 1
        assert key_data["last_used_at"] is not None
        
        # Second validation
        is_valid, key_data = self.manager.validate_api_key(key)
        assert is_valid
        assert key_data["usage_count"] == 2
    
    def test_revoke_api_key(self):
        """Test revoking an API key."""
        key = self.manager.create_api_key(key_id="to_revoke")
        
        # Key should be valid initially
        is_valid, _ = self.manager.validate_api_key(key)
        assert is_valid
        
        # Revoke the key
        success = self.manager.revoke_api_key(key)
        assert success
        
        # Key should now be invalid
        is_valid, _ = self.manager.validate_api_key(key)
        assert not is_valid
    
    def test_revoke_nonexistent_api_key(self):
        """Test revoking a non-existent API key."""
        success = self.manager.revoke_api_key("nonexistent-key")
        assert not success
    
    def test_list_api_keys(self):
        """Test listing API keys."""
        # Create a few keys
        key1 = self.manager.create_api_key(key_id="key1", description="First key")
        key2 = self.manager.create_api_key(key_id="key2", description="Second key")
        
        keys = self.manager.list_api_keys()
        
        # Should have at least our 2 keys plus the default admin key
        assert len(keys) >= 3
        
        # Check that keys are masked
        for masked_key, data in keys.items():
            assert "..." in masked_key
            assert len(masked_key) < 32  # Original keys are longer
            assert "key_id" in data
            assert "description" in data
            assert "permissions" in data
    
    def test_has_permission_admin(self):
        """Test permission checking for admin users."""
        key = self.manager.create_api_key(
            key_id="admin_key",
            permissions=["admin"]
        )
        
        # Admin should have all permissions
        assert self.manager.has_permission(key, "admin")
        assert self.manager.has_permission(key, "chat")
        assert self.manager.has_permission(key, "completion")
        assert self.manager.has_permission(key, "embedding")
    
    def test_has_permission_specific(self):
        """Test permission checking for specific permissions."""
        key = self.manager.create_api_key(
            key_id="chat_key",
            permissions=["chat", "completion"]
        )
        
        assert self.manager.has_permission(key, "chat")
        assert self.manager.has_permission(key, "completion")
        assert not self.manager.has_permission(key, "embedding")
        assert not self.manager.has_permission(key, "admin")
    
    def test_has_permission_invalid_key(self):
        """Test permission checking with invalid key."""
        assert not self.manager.has_permission("invalid-key", "chat")
    
    def test_default_admin_key_created(self):
        """Test that default admin key is created."""
        keys = self.manager.list_api_keys()
        
        # Should have at least one key (the default admin)
        assert len(keys) >= 1
        
        # Check that there's an admin key
        admin_keys = [
            data for data in keys.values() 
            if "admin" in data.get("permissions", [])
        ]
        assert len(admin_keys) >= 1
    
    def test_get_default_admin_key(self):
        """Test getting the default admin key."""
        default_key = self.manager.get_default_admin_key()
        assert default_key != 'Not available'
        assert default_key.startswith("officeai-admin-")


class TestAuthDependencies:
    """Test FastAPI authentication dependencies."""
    
    @pytest.mark.asyncio
    async def test_get_api_key_valid(self):
        """Test extracting valid API key from credentials."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="test-api-key"
        )
        
        key = await get_api_key(credentials)
        assert key == "test-api-key"
    
    @pytest.mark.asyncio
    async def test_get_api_key_missing(self):
        """Test handling missing credentials."""
        with pytest.raises(HTTPException) as exc_info:
            await get_api_key(None)
        
        assert exc_info.value.status_code == 401
        assert "Missing authorization header" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_verify_api_key_valid(self):
        """Test verifying a valid API key."""
        # Create a test key
        manager = APIKeyManager()
        test_key = manager.create_api_key(key_id="verify_test")
        
        # Mock the global manager
        with patch('src.auth.client_auth.api_key_manager', manager):
            key_data = await verify_api_key(test_key)
            assert key_data["key_id"] == "verify_test"
    
    @pytest.mark.asyncio
    async def test_verify_api_key_invalid(self):
        """Test verifying an invalid API key."""
        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key("invalid-key")
        
        assert exc_info.value.status_code == 401
        assert "Invalid or expired API key" in str(exc_info.value.detail)
    
    def test_require_permission_function(self):
        """Test the require_permission function creates proper dependency."""
        permission_dep = require_permission("test_permission")
        assert callable(permission_dep)
        
        # The function should be a coroutine function
        import inspect
        assert inspect.iscoroutinefunction(permission_dep)