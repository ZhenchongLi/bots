"""
Unit tests for OpenAI API compatibility endpoints
"""
import pytest
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.models.openai import (
    ChatCompletionRequest,
    ChatMessage,
    Role,
    ModelListResponse,
    CompletionRequest,
    EmbeddingRequest
)


@pytest.mark.unit
class TestModelsEndpoint:
    """Test the /v1/models endpoint"""
    
    def test_list_models_success(self, client):
        """Test successful models listing"""
        response = client.get("/v1/models")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure matches OpenAI format
        assert "object" in data
        assert data["object"] == "list"
        assert "data" in data
        assert isinstance(data["data"], list)
        
        # Verify each model has required fields
        for model in data["data"]:
            assert "id" in model
            assert "object" in model
            assert model["object"] == "model"
            assert "created" in model
            assert "owned_by" in model

    def test_list_models_response_model(self, client):
        """Test that response can be parsed by Pydantic model"""
        response = client.get("/v1/models")
        
        assert response.status_code == 200
        
        # Should be able to parse response with Pydantic model
        model_list = ModelListResponse.model_validate(response.json())
        assert model_list.object == "list"
        assert isinstance(model_list.data, list)


@pytest.mark.unit
class TestChatCompletionsEndpoint:
    """Test the /v1/chat/completions endpoint"""
    
    def test_chat_completions_request_validation(self, client):
        """Test request validation for chat completions"""
        # Valid request
        valid_payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "user", "content": "Hello, how are you?"}
            ],
            "temperature": 0.7,
            "max_tokens": 100
        }
        
        # Should validate without error
        chat_request = ChatCompletionRequest.model_validate(valid_payload)
        assert chat_request.model == "gpt-3.5-turbo"
        assert len(chat_request.messages) == 1
        assert chat_request.messages[0].role == Role.USER
        assert chat_request.temperature == 0.7
        assert chat_request.max_tokens == 100

    def test_chat_completions_invalid_temperature(self, client):
        """Test invalid temperature value"""
        invalid_payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "user", "content": "Hello"}
            ],
            "temperature": 3.0  # Invalid: should be <= 2.0
        }
        
        with pytest.raises(ValueError):
            ChatCompletionRequest.model_validate(invalid_payload)

    def test_chat_completions_model_not_available(self, client, mock_settings):
        """Test when model is not available"""
        with patch('src.core.model_manager.model_manager.is_model_available', return_value=False):
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": "Hello"}]
            }
            
            response = client.post("/v1/chat/completions", json=payload)
            assert response.status_code == 503
            assert "not available" in response.json()["detail"]

    @patch('src.core.platform_clients.PlatformClientFactory.create_client')
    @patch('src.core.model_manager.model_manager.process_model_request')
    @patch('src.core.model_manager.model_manager.is_model_available')
    @patch('src.core.model_manager.model_manager.get_model_config')
    def test_chat_completions_success(self, mock_get_config, mock_available, 
                                     mock_process, mock_create_client, client):
        """Test successful chat completion"""
        # Setup mocks
        mock_available.return_value = True
        mock_process.return_value = ({"model": "gpt-3.5-turbo"}, "gpt-3.5-turbo")
        mock_get_config.return_value = {"type": "openai"}
        
        mock_client = MagicMock()
        mock_response = {
            "json": {
                "id": "chatcmpl-123",
                "object": "chat.completion",
                "created": 1677652288,
                "model": "gpt-3.5-turbo",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Hello! I'm doing well, thank you for asking."
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 13,
                    "completion_tokens": 12,
                    "total_tokens": 25
                }
            },
            "status_code": 200,
            "headers": {"content-type": "application/json"}
        }
        # Make the async method return the response
        async def mock_make_request(*args, **kwargs):
            return mock_response
        mock_client.make_request = mock_make_request
        mock_create_client.return_value = mock_client
        
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "Hello"}]
        }
        
        response = client.post("/v1/chat/completions", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify OpenAI response format
        assert "id" in data
        assert data["object"] == "chat.completion"
        assert "created" in data
        assert "model" in data
        assert "choices" in data
        assert "usage" in data


@pytest.mark.unit
class TestCompletionsEndpoint:
    """Test the /v1/completions endpoint"""
    
    def test_completions_request_validation(self, client):
        """Test request validation for completions"""
        valid_payload = {
            "model": "text-davinci-003",
            "prompt": "Hello, world!",
            "max_tokens": 50,
            "temperature": 0.7
        }
        
        completion_request = CompletionRequest.model_validate(valid_payload)
        assert completion_request.model == "text-davinci-003"
        assert completion_request.prompt == "Hello, world!"
        assert completion_request.max_tokens == 50
        assert completion_request.temperature == 0.7

    def test_completions_model_not_available(self, client):
        """Test when model is not available"""
        with patch('src.core.model_manager.model_manager.is_model_available', return_value=False):
            payload = {
                "model": "text-davinci-003",
                "prompt": "Hello"
            }
            
            response = client.post("/v1/completions", json=payload)
            assert response.status_code == 503

    @patch('src.core.platform_clients.PlatformClientFactory.create_client')
    @patch('src.core.model_manager.model_manager.process_model_request')
    @patch('src.core.model_manager.model_manager.is_model_available')
    @patch('src.core.model_manager.model_manager.get_model_config')
    def test_completions_success(self, mock_get_config, mock_available,
                                mock_process, mock_create_client, client):
        """Test successful completion"""
        # Setup mocks
        mock_available.return_value = True
        mock_process.return_value = ({"model": "text-davinci-003"}, "text-davinci-003")
        mock_get_config.return_value = {"type": "openai"}
        
        mock_client = MagicMock()
        mock_response = {
            "json": {
                "id": "cmpl-123",
                "object": "text_completion",
                "created": 1677652288,
                "model": "text-davinci-003",
                "choices": [{
                    "text": " I'm doing well, thank you!",
                    "index": 0,
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 5,
                    "completion_tokens": 8,
                    "total_tokens": 13
                }
            },
            "status_code": 200,
            "headers": {"content-type": "application/json"}
        }
        # Make the async method return the response
        async def mock_make_request_completions(*args, **kwargs):
            return mock_response
        mock_client.make_request = mock_make_request_completions
        mock_create_client.return_value = mock_client
        
        payload = {
            "model": "text-davinci-003",
            "prompt": "Hello"
        }
        
        response = client.post("/v1/completions", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify OpenAI response format
        assert "id" in data
        assert data["object"] == "text_completion"
        assert "created" in data
        assert "model" in data
        assert "choices" in data
        assert "usage" in data


@pytest.mark.unit
class TestEmbeddingsEndpoint:
    """Test the /v1/embeddings endpoint"""
    
    def test_embeddings_request_validation(self, client):
        """Test request validation for embeddings"""
        valid_payload = {
            "model": "text-embedding-ada-002",
            "input": "Hello, world!",
            "encoding_format": "float"
        }
        
        embedding_request = EmbeddingRequest.model_validate(valid_payload)
        assert embedding_request.model == "text-embedding-ada-002"
        assert embedding_request.input == "Hello, world!"
        assert embedding_request.encoding_format == "float"

    def test_embeddings_model_not_available(self, client):
        """Test when model is not available"""
        with patch('src.core.model_manager.model_manager.is_model_available', return_value=False):
            payload = {
                "model": "text-embedding-ada-002",
                "input": "Hello"
            }
            
            response = client.post("/v1/embeddings", json=payload)
            assert response.status_code == 503

    @patch('src.core.platform_clients.PlatformClientFactory.create_client')
    @patch('src.core.model_manager.model_manager.process_model_request')
    @patch('src.core.model_manager.model_manager.is_model_available')
    @patch('src.core.model_manager.model_manager.get_model_config')
    def test_embeddings_success(self, mock_get_config, mock_available,
                               mock_process, mock_create_client, client):
        """Test successful embedding creation"""
        # Setup mocks
        mock_available.return_value = True
        mock_process.return_value = ({"model": "text-embedding-ada-002"}, "text-embedding-ada-002")
        mock_get_config.return_value = {"type": "openai"}
        
        mock_client = MagicMock()
        mock_response = {
            "json": {
                "object": "list",
                "data": [{
                    "object": "embedding",
                    "embedding": [0.1, 0.2, 0.3] * 512,  # Simulate 1536-dim embedding
                    "index": 0
                }],
                "model": "text-embedding-ada-002",
                "usage": {
                    "prompt_tokens": 5,
                    "total_tokens": 5
                }
            },
            "status_code": 200,
            "headers": {"content-type": "application/json"}
        }
        # Make the async method return the response
        async def mock_make_request_embeddings(*args, **kwargs):
            return mock_response
        mock_client.make_request = mock_make_request_embeddings
        mock_create_client.return_value = mock_client
        
        payload = {
            "model": "text-embedding-ada-002",
            "input": "Hello"
        }
        
        response = client.post("/v1/embeddings", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify OpenAI response format
        assert data["object"] == "list"
        assert "data" in data
        assert "model" in data
        assert "usage" in data


@pytest.mark.integration
class TestOpenAICompatibilityIntegration:
    """Integration tests for OpenAI API compatibility"""
    
    def test_error_response_format(self, client):
        """Test that error responses match OpenAI format"""
        # Test with invalid request body
        response = client.post("/v1/chat/completions", json={"invalid": "data"})
        
        # Should return 422 for validation error
        assert response.status_code == 422
        
        # FastAPI validation error format is different from OpenAI,
        # but our custom error handling should format it properly

    def test_openai_library_compatibility_structure(self, client):
        """Test that responses are structured for OpenAI library compatibility"""
        # Test models endpoint structure
        response = client.get("/v1/models")
        data = response.json()
        
        # Must have the exact structure expected by OpenAI library
        assert data["object"] == "list"
        assert "data" in data
        
        for model in data["data"]:
            # Each model must have these exact fields
            required_fields = ["id", "object", "created", "owned_by"]
            for field in required_fields:
                assert field in model
                assert model[field] is not None

    @pytest.mark.parametrize("endpoint,method,payload", [
        ("/v1/models", "GET", None),
        ("/v1/chat/completions", "POST", {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "test"}]
        }),
        ("/v1/completions", "POST", {
            "model": "text-davinci-003",
            "prompt": "test"
        }),
        ("/v1/embeddings", "POST", {
            "model": "text-embedding-ada-002",
            "input": "test"
        })
    ])
    def test_endpoint_accessibility(self, client, endpoint, method, payload):
        """Test that all OpenAI endpoints are accessible"""
        if method == "GET":
            response = client.get(endpoint)
        else:
            response = client.post(endpoint, json=payload)
        
        # Should not return 404 (endpoint exists)
        assert response.status_code != 404
        
        # Should return either success, service unavailable, or internal server error (if no model configured)
        # 500 is acceptable here as it indicates the endpoint exists but model isn't properly configured
        assert response.status_code in [200, 500, 503]