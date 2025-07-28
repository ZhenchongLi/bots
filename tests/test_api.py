import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from src.config.settings import PlatformType


class TestAPIEndpoints:
    """Test API endpoints."""
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "openai-proxy"
    
    def test_models_endpoint_enabled(self, client, mock_settings):
        """Test models endpoint when model is enabled."""
        response = client.get("/models")
        
        assert response.status_code == 200
        data = response.json()
        assert data["object"] == "list"
        assert len(data["data"]) == 1
        
        model = data["data"][0]
        assert model["id"] == "gpt-3.5-turbo"
        assert model["object"] == "model"
        assert model["owned_by"] == "openai"
    
    def test_models_endpoint_disabled(self, client):
        """Test models endpoint when model is disabled."""
        disabled_settings = MagicMock()
        disabled_settings.enabled = False
        disabled_settings.api_key = ""
        
        with patch('src.core.model_manager.model_manager.config', {
            'enabled': False,
            'api_key': ''
        }):
            response = client.get("/models")
            
            assert response.status_code == 200
            data = response.json()
            assert data["object"] == "list"
            assert len(data["data"]) == 0
    
    @patch('src.core.platform_clients.PlatformClientFactory.create_client')
    def test_proxy_chat_completions_success(self, mock_factory, client, mock_settings):
        """Test successful chat completions proxy request."""
        # Mock platform client
        mock_client = MagicMock()
        mock_client.make_request = AsyncMock(return_value={
            "json": {
                "choices": [{"message": {"content": "Hello! How can I help you?"}}],
                "model": "gpt-3.5-turbo"
            },
            "status_code": 200,
            "headers": {"content-type": "application/json"},
            "content": None
        })
        mock_factory.return_value = mock_client
        
        request_data = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Hello"}]
        }
        
        response = client.post("/chat/completions", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "choices" in data
        assert data["choices"][0]["message"]["content"] == "Hello! How can I help you?"
        
        # Verify the client was called with the correct parameters
        mock_client.make_request.assert_called_once()
        call_args = mock_client.make_request.call_args
        assert call_args[1]["method"] == "POST"
        assert call_args[1]["path"] == "/chat/completions"
        assert call_args[1]["json_data"]["model"] == "gpt-3.5-turbo"  # Should be mapped
    
    @patch('src.core.platform_clients.PlatformClientFactory.create_client')
    def test_proxy_embeddings_success(self, mock_factory, client, mock_settings):
        """Test successful embeddings proxy request."""
        mock_client = MagicMock()
        mock_client.make_request = AsyncMock(return_value={
            "json": {
                "data": [{"embedding": [0.1, 0.2, 0.3]}],
                "model": "text-embedding-ada-002"
            },
            "status_code": 200,
            "headers": {"content-type": "application/json"},
            "content": None
        })
        mock_factory.return_value = mock_client
        
        request_data = {
            "model": "text-embedding-ada-002",
            "input": "Hello world"
        }
        
        response = client.post("/embeddings", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"][0]["embedding"]) == 3
    
    def test_proxy_model_unavailable(self, client):
        """Test proxy request when model is unavailable."""
        with patch('src.core.model_manager.model_manager.is_model_available', return_value=False):
            request_data = {
                "model": "gpt-4",
                "messages": [{"role": "user", "content": "Hello"}]
            }
            
            response = client.post("/chat/completions", json=request_data)
            
            assert response.status_code == 503
            data = response.json()
            assert "Model is not available" in data["detail"]
    
    def test_proxy_invalid_model_request(self, client, mock_settings):
        """Test proxy request with invalid model configuration."""
        with patch('src.core.model_manager.model_manager.process_model_request') as mock_process:
            mock_process.side_effect = ValueError("Invalid model configuration")
            
            request_data = {
                "model": "invalid-model",
                "messages": [{"role": "user", "content": "Hello"}]
            }
            
            response = client.post("/chat/completions", json=request_data)
            
            assert response.status_code == 400
            data = response.json()
            assert "Invalid model configuration" in data["detail"]
    
    @patch('src.core.platform_clients.PlatformClientFactory.create_client')
    def test_proxy_platform_error(self, mock_factory, client, mock_settings):
        """Test proxy request when platform client raises error."""
        mock_client = MagicMock()
        mock_client.make_request = AsyncMock(side_effect=Exception("Platform API error"))
        mock_factory.return_value = mock_client
        
        request_data = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Hello"}]
        }
        
        response = client.post("/chat/completions", json=request_data)
        
        assert response.status_code == 500
        data = response.json()
        assert "Proxy error" in data["detail"]
        assert "Platform API error" in data["detail"]
    
    def test_proxy_non_json_request(self, client, mock_settings):
        """Test proxy request with non-JSON body."""
        response = client.post("/chat/completions", data="not json")
        
        assert response.status_code == 503  # Model unavailable due to no valid request
    
    @patch('src.core.platform_clients.PlatformClientFactory.create_client')
    def test_proxy_streaming_response(self, mock_factory, client, mock_settings):
        """Test proxy request with streaming response."""
        mock_client = MagicMock()
        mock_client.make_request = AsyncMock(return_value={
            "json": None,
            "content": b"data: {\"choices\": [{\"delta\": {\"content\": \"Hello\"}}]}\\n\\n",
            "status_code": 200,
            "headers": {"content-type": "text/event-stream"}
        })
        mock_factory.return_value = mock_client
        
        request_data = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": True
        }
        
        response = client.post("/chat/completions", json=request_data)
        
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
    
    def test_proxy_get_request(self, client, mock_settings):
        """Test GET request to proxy endpoint."""
        with patch('src.core.platform_clients.PlatformClientFactory.create_client') as mock_factory:
            mock_client = MagicMock()
            mock_client.make_request = AsyncMock(return_value={
                "json": {"models": []},
                "status_code": 200,
                "headers": {"content-type": "application/json"},
                "content": None
            })
            mock_factory.return_value = mock_client
            
            response = client.get("/v1/models")
            
            assert response.status_code == 200
            mock_client.make_request.assert_called_once()
            call_args = mock_client.make_request.call_args
            assert call_args[1]["method"] == "GET"
            assert call_args[1]["path"] == "/v1/models"
    
    def test_proxy_put_request(self, client, mock_settings):
        """Test PUT request to proxy endpoint."""
        with patch('src.core.platform_clients.PlatformClientFactory.create_client') as mock_factory:
            mock_client = MagicMock()
            mock_client.make_request = AsyncMock(return_value={
                "json": {"success": True},
                "status_code": 200,
                "headers": {"content-type": "application/json"},
                "content": None
            })
            mock_factory.return_value = mock_client
            
            response = client.put("/custom/endpoint", json={"data": "test"})
            
            assert response.status_code == 200
            mock_client.make_request.assert_called_once()
            call_args = mock_client.make_request.call_args
            assert call_args[1]["method"] == "PUT"
            assert call_args[1]["path"] == "/custom/endpoint"
    
    def test_proxy_query_parameters(self, client, mock_settings):
        """Test proxy request with query parameters."""
        with patch('src.core.platform_clients.PlatformClientFactory.create_client') as mock_factory:
            mock_client = MagicMock()
            mock_client.make_request = AsyncMock(return_value={
                "json": {"result": "success"},
                "status_code": 200,
                "headers": {"content-type": "application/json"},
                "content": None
            })
            mock_factory.return_value = mock_client
            
            response = client.get("/test?param1=value1&param2=value2")
            
            assert response.status_code == 200
            mock_client.make_request.assert_called_once()
            call_args = mock_client.make_request.call_args
            assert call_args[1]["params"] == {"param1": "value1", "param2": "value2"}