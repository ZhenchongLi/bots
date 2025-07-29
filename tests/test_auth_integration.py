import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.auth.client_auth import APIKeyManager
from src.main import create_app


class TestAuthIntegration:
    """Test authentication integration with real auth enabled."""
    
    @pytest.fixture
    def auth_enabled_client(self):
        """Create a test client with authentication enabled."""
        # Create settings dict with auth enabled
        auth_settings = {
            "host": "127.0.0.1",
            "port": 8001,
            "log_level": "debug",
            "enable_client_auth": True,  # Enable auth for these tests
            "allow_anonymous_access": False,
            "type": "openai",
            "api_key": "test-api-key-12345",
            "base_url": "https://api.test-openai.com/v1",
            "enabled": True,
            "actual_name": "gpt-3.5-turbo-test",
            "display_name": "officeai",
            "max_tokens": 4096,
            "supports_streaming": True,
            "supports_function_calling": True,
            "database_url": "sqlite+aiosqlite:///:memory:",
            "log_file_path": "./tests/logs/test.log",
            "log_retention_days": 1,
            "timeout": 30,
            "default_headers": {},
            "description": "Test model for unit testing",
            "cost_per_1k_input_tokens": 0.001,
            "cost_per_1k_output_tokens": 0.002,
        }
        
        # Create mock settings object
        mock_settings_obj = MagicMock()
        for key, value in auth_settings.items():
            setattr(mock_settings_obj, key, value)
        
        with patch('src.config.settings.settings', mock_settings_obj), \
             patch('src.core.model_manager.settings', mock_settings_obj), \
             patch('src.database.connection.init_db'):
            
            # Also patch the model_manager's config directly
            from src.core.model_manager import model_manager
            original_config = model_manager.config
            model_manager.config = auth_settings
            
            try:
                app = create_app()
                with TestClient(app) as test_client:
                    yield test_client
            finally:
                model_manager.config = original_config
    
    @pytest.fixture
    def admin_key(self, auth_enabled_client):
        """Create an admin API key for testing."""
        # Use the global api_key_manager to ensure consistency
        from src.auth.client_auth import api_key_manager
        return api_key_manager.create_api_key(
            key_id="test_admin",
            permissions=["admin", "chat", "completion", "embedding"]
        )
    
    @pytest.fixture
    def regular_key(self, auth_enabled_client):
        """Create a regular API key for testing."""
        # Use the global api_key_manager to ensure consistency
        from src.auth.client_auth import api_key_manager
        return api_key_manager.create_api_key(
            key_id="test_regular",
            permissions=["chat"]
        )
    
    def test_unauthorized_access_denied(self, auth_enabled_client):
        """Test that unauthorized access is denied when auth is enabled."""
        response = auth_enabled_client.get("/v1/models")
        assert response.status_code == 401
        assert "Missing authorization header" in response.json()["detail"]
    
    def test_invalid_api_key_denied(self, auth_enabled_client):
        """Test that invalid API key is denied."""
        response = auth_enabled_client.get(
            "/v1/models",
            headers={"Authorization": "Bearer invalid-key"}
        )
        assert response.status_code == 401
        assert "Invalid or expired API key" in response.json()["detail"]
    
    def test_valid_api_key_allowed(self, auth_enabled_client):
        """Test that valid API key is allowed."""
        # Use the default admin key that's automatically created
        from src.auth.client_auth import api_key_manager
        default_admin_key = api_key_manager.get_default_admin_key()
        
        response = auth_enabled_client.get(
            "/v1/models",
            headers={"Authorization": f"Bearer {default_admin_key}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) > 0
        # Should have the configured actual model
        model_ids = [model["id"] for model in data["data"]]
        assert "gpt-3.5-turbo-test" in model_ids
    
    def test_insufficient_permissions_denied(self, auth_enabled_client, regular_key):
        """Test that insufficient permissions are denied."""
        # Regular key trying to access admin endpoint
        response = auth_enabled_client.get(
            "/admin/api-keys",
            headers={"Authorization": f"Bearer {regular_key}"}
        )
        assert response.status_code == 403
        assert "Insufficient permissions" in response.json()["detail"]
    
    def test_admin_permissions_allowed(self, auth_enabled_client, admin_key):
        """Test that admin permissions are allowed."""
        response = auth_enabled_client.get(
            "/admin/api-keys",
            headers={"Authorization": f"Bearer {admin_key}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "keys" in data
    
    def test_chat_completion_with_officeai_model(self, auth_enabled_client, admin_key):
        """Test chat completion using the officeai model name."""
        request_data = {
            "model": "officeai",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 10
        }
        
        # Mock the external API call
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "id": "test-response",
            "object": "chat.completion",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": "Hello there!"},
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15
            }
        }
        
        with patch('src.core.platform_clients.httpx.AsyncClient') as mock_client_class:
            from unittest.mock import AsyncMock
            mock_client = MagicMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_context_manager = MagicMock()
            mock_context_manager.__aenter__ = AsyncMock(return_value=mock_client)
            mock_context_manager.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_context_manager
            
            response = auth_enabled_client.post(
                "/v1/chat/completions",
                json=request_data,
                headers={"Authorization": f"Bearer {admin_key}"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "choices" in data
        assert len(data["choices"]) > 0
    
    def test_model_name_mapping(self, auth_enabled_client, admin_key):
        """Test that officeai model name is properly mapped to actual model."""
        # This test verifies that when we request "officeai", 
        # it gets mapped to the actual model name configured
        request_data = {
            "model": "officeai",
            "messages": [{"role": "user", "content": "Test"}]
        }
        
        with patch('src.core.platform_clients.httpx.AsyncClient') as mock_client_class:
            from unittest.mock import AsyncMock
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "application/json"}
            mock_response.json.return_value = {"test": "response"}
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_context_manager = MagicMock()
            mock_context_manager.__aenter__ = AsyncMock(return_value=mock_client)
            mock_context_manager.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_context_manager
            
            response = auth_enabled_client.post(
                "/v1/chat/completions",
                json=request_data,
                headers={"Authorization": f"Bearer {admin_key}"}
            )
            
            # Check that the actual request was made with the configured model name
            call_args = mock_client.request.call_args
            request_json = call_args[1]["json"]
            assert request_json["model"] == "gpt-3.5-turbo-test"  # The configured actual model name
    
    def test_model_name_replacement_forced(self, auth_enabled_client):
        """Test that all client model names are replaced with configured actual model."""
        from src.auth.client_auth import api_key_manager
        default_admin_key = api_key_manager.get_default_admin_key()
        
        # Test different client model names
        client_models = ["gpt-4", "claude-3-opus", "gemini-pro", "random-model-123"]
        
        for client_model in client_models:
            request_data = {
                "model": client_model,
                "messages": [{"role": "user", "content": f"Test with {client_model}"}]
            }
            
            with patch('src.core.platform_clients.httpx.AsyncClient') as mock_client_class:
                from unittest.mock import AsyncMock
                mock_client = MagicMock()
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.headers = {"content-type": "application/json"}
                mock_response.json.return_value = {
                    "id": "test-response",
                    "object": "chat.completion", 
                    "choices": [{"message": {"content": "Response"}}]
                }
                mock_client.request = AsyncMock(return_value=mock_response)
                mock_context_manager = MagicMock()
                mock_context_manager.__aenter__ = AsyncMock(return_value=mock_client)
                mock_context_manager.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_context_manager
                
                response = auth_enabled_client.post(
                    "/v1/chat/completions",
                    json=request_data,
                    headers={"Authorization": f"Bearer {default_admin_key}"}
                )
                
                # Verify request was successful
                assert response.status_code == 200
                
                # Verify that the backend call used the configured model, not client model
                call_args = mock_client.request.call_args
                backend_request = call_args[1]["json"]
                assert backend_request["model"] == "gpt-3.5-turbo-test", \
                    f"Client model '{client_model}' should be replaced with 'gpt-3.5-turbo-test'"