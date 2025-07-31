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
        # For testing, we'll manually load a fallback key since database may not be available
        self.manager._api_keys = {}
        self.manager._default_admin_key = None
    
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
        
        # Should have exactly our 2 keys (no default admin key in test environment)
        assert len(keys) == 2
        
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
    
    def test_default_admin_key_not_loaded_by_default(self):
        """Test that default admin key is not loaded in test environment."""
        keys = self.manager.list_api_keys()
        
        # Should have no keys initially in test environment
        assert len(keys) == 0
    
    def test_get_default_admin_key_not_available_initially(self):
        """Test getting the default admin key when not loaded."""
        default_key = self.manager.get_default_admin_key()
        # Since we set _default_admin_key to None in setup, it should return 'Not available'
        assert default_key == 'Not available' or default_key is None
    
    @pytest.mark.asyncio
    async def test_load_default_keys_from_database(self):
        """Test loading default keys from database."""
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        from src.models.client import Client
        from src.models.request_log import Base
        
        # Create in-memory database
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        AsyncSessionLocal = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        # Create a default client
        async with AsyncSessionLocal() as session:
            default_client = Client(
                name="default_client",
                api_key="test-default-key-123",
                is_default=True,
                is_active=True
            )
            session.add(default_client)
            await session.commit()
        
        # Mock the database connection
        with patch('src.database.connection.AsyncSessionLocal', AsyncSessionLocal):
            # Load keys from database
            await self.manager._load_default_keys()
            
            # Verify key was loaded
            assert "test-default-key-123" in self.manager._api_keys
            key_data = self.manager._api_keys["test-default-key-123"]
            assert key_data["key_id"] == "default_admin"
            assert key_data["description"] == "Default admin key from database"
            assert "admin" in key_data["permissions"]
            
            # Verify default admin key is set
            assert self.manager.get_default_admin_key() == "test-default-key-123"
        
        await engine.dispose()
    
    @pytest.mark.asyncio
    async def test_load_default_keys_fallback_when_no_database(self):
        """Test fallback behavior when database is not available."""
        # Mock database connection to raise an exception
        with patch('src.database.connection.AsyncSessionLocal', side_effect=Exception("Database not available")):
            # Load keys should fall back to creating a temporary key
            await self.manager._load_default_keys()
            
            # Verify fallback key was created
            assert len(self.manager._api_keys) == 1
            fallback_key = self.manager.get_default_admin_key()
            assert fallback_key.startswith("officeai-admin-")
            
            key_data = self.manager._api_keys[fallback_key]
            assert key_data["key_id"] == "default_admin"
            assert key_data["description"] == "Temporary admin key - database unavailable"


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