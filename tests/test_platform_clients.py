import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock

from src.core.platform_clients import (
    PlatformClientFactory,
    OpenAIClient,
    AnthropicClient,
    GoogleClient,
    BasePlatformClient
)
from src.config.settings import PlatformType


class TestPlatformClientFactory:
    """Test platform client factory."""
    
    def test_create_openai_client(self):
        """Test creating OpenAI client."""
        config = {
            "type": PlatformType.OPENAI,
            "api_key": "sk-test",
            "base_url": "https://api.openai.com/v1"
        }
        
        client = PlatformClientFactory.create_client(PlatformType.OPENAI, config)
        assert isinstance(client, OpenAIClient)
    
    def test_create_anthropic_client(self):
        """Test creating Anthropic client."""
        config = {
            "type": PlatformType.ANTHROPIC,
            "api_key": "sk-ant-test",
            "base_url": "https://api.anthropic.com/v1"
        }
        
        client = PlatformClientFactory.create_client(PlatformType.ANTHROPIC, config)
        assert isinstance(client, AnthropicClient)
    
    def test_create_google_client(self):
        """Test creating Google client."""
        config = {
            "type": PlatformType.GOOGLE,
            "api_key": "google-key",
            "base_url": "https://generativelanguage.googleapis.com/v1"
        }
        
        client = PlatformClientFactory.create_client(PlatformType.GOOGLE, config)
        assert isinstance(client, GoogleClient)
    
    def test_create_azure_openai_client(self):
        """Test creating Azure OpenAI client."""
        config = {
            "type": PlatformType.AZURE_OPENAI,
            "api_key": "azure-key",
            "base_url": "https://test.openai.azure.com/openai/deployments/test"
        }
        
        client = PlatformClientFactory.create_client(PlatformType.AZURE_OPENAI, config)
        assert isinstance(client, OpenAIClient)  # Azure uses OpenAI client
    
    def test_create_custom_client(self):
        """Test creating custom client."""
        config = {
            "type": PlatformType.CUSTOM,
            "api_key": "custom-key",
            "base_url": "http://localhost:11434/v1"
        }
        
        client = PlatformClientFactory.create_client(PlatformType.CUSTOM, config)
        assert isinstance(client, OpenAIClient)  # Custom defaults to OpenAI client
    
    def test_create_client_invalid_type(self):
        """Test creating client with invalid type."""
        config = {"type": "invalid", "api_key": "test", "base_url": "http://test.com"}
        
        # Invalid types default to OpenAI client
        client = PlatformClientFactory.create_client("invalid", config)
        assert isinstance(client, OpenAIClient)


class TestOpenAIClient:
    """Test OpenAI client."""
    
    @pytest.fixture
    def openai_config(self):
        return {
            "type": PlatformType.OPENAI,
            "api_key": "sk-test-key",
            "base_url": "https://api.openai.com/v1",
            "timeout": 300
        }
    
    @pytest.fixture
    def openai_client(self, openai_config):
        return OpenAIClient(openai_config)
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_make_request_success(self, mock_httpx, openai_client):
        """Test successful OpenAI API request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello!"}}]
        }
        mock_response.content = None
        
        mock_client = MagicMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_httpx.return_value = mock_client
        
        result = await openai_client.make_request(
            method="POST",
            path="/chat/completions",
            headers={"content-type": "application/json"},
            json_data={"model": "gpt-4", "messages": []},
            params={}
        )
        
        assert result["status_code"] == 200
        assert result["json"]["choices"][0]["message"]["content"] == "Hello!"
        
        # Verify the request was made with correct headers
        mock_client.request.assert_called_once()
        call_args = mock_client.request.call_args
        assert call_args[1]["headers"]["Authorization"] == "Bearer sk-test-key"
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_make_request_streaming(self, mock_httpx, openai_client):
        """Test streaming OpenAI API request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/event-stream"}
        mock_response.content = b"data: {\"choices\": [{\"delta\": {\"content\": \"Hi\"}}]}\\n\\n"
        mock_response.json.side_effect = json.JSONDecodeError("Not JSON", "", 0)
        
        mock_client = MagicMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_httpx.return_value = mock_client
        
        result = await openai_client.make_request(
            method="POST",
            path="/chat/completions",
            headers={"content-type": "application/json"},
            json_data={"model": "gpt-4", "messages": [], "stream": True},
            params={}
        )
        
        assert result["status_code"] == 200
        assert result["json"] is None
        assert result["content"] == b"data: {\"choices\": [{\"delta\": {\"content\": \"Hi\"}}]}\\n\\n"


class TestAnthropicClient:
    """Test Anthropic client."""
    
    @pytest.fixture
    def anthropic_config(self):
        return {
            "type": PlatformType.ANTHROPIC,
            "api_key": "sk-ant-test-key",
            "base_url": "https://api.anthropic.com/v1",
            "timeout": 300
        }
    
    @pytest.fixture
    def anthropic_client(self, anthropic_config):
        return AnthropicClient(anthropic_config)
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_make_request_success(self, mock_httpx, anthropic_client):
        """Test successful Anthropic API request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "content": [{"text": "Hello from Claude!"}]
        }
        
        mock_client = MagicMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_httpx.return_value = mock_client
        
        result = await anthropic_client.make_request(
            method="POST",
            path="/messages",
            headers={"content-type": "application/json"},
            json_data={"model": "claude-3-sonnet", "messages": []},
            params={}
        )
        
        assert result["status_code"] == 200
        assert result["json"]["content"][0]["text"] == "Hello from Claude!"
        
        # Verify the request was made with correct headers
        mock_client.request.assert_called_once()
        call_args = mock_client.request.call_args
        assert call_args[1]["headers"]["x-api-key"] == "sk-ant-test-key"
        assert call_args[1]["headers"]["anthropic-version"] == "2023-06-01"


class TestGoogleClient:
    """Test Google client."""
    
    @pytest.fixture
    def google_config(self):
        return {
            "type": PlatformType.GOOGLE,
            "api_key": "google-test-key",
            "base_url": "https://generativelanguage.googleapis.com/v1",
            "timeout": 300
        }
    
    @pytest.fixture
    def google_client(self, google_config):
        return GoogleClient(google_config)
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_make_request_success(self, mock_httpx, google_client):
        """Test successful Google API request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Hello from Gemini!"}]}}]
        }
        
        mock_client = MagicMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_httpx.return_value = mock_client
        
        result = await google_client.make_request(
            method="POST",
            path="/models/gemini-pro:generateContent",
            headers={"content-type": "application/json"},
            json_data={"contents": []},
            params={"key": "google-test-key"}
        )
        
        assert result["status_code"] == 200
        assert result["json"]["candidates"][0]["content"]["parts"][0]["text"] == "Hello from Gemini!"


class TestAzureAndCustomClients:
    """Test Azure OpenAI and Custom clients (both use OpenAI client implementation)."""
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_azure_openai_client_behavior(self, mock_httpx):
        """Test Azure OpenAI client behavior."""
        config = {
            "type": PlatformType.AZURE_OPENAI,
            "api_key": "azure-test-key",
            "base_url": "https://test.openai.azure.com/openai/deployments/test",
            "timeout": 300
        }
        
        client = PlatformClientFactory.create_client(PlatformType.AZURE_OPENAI, config)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello from Azure!"}}]
        }
        
        mock_client = MagicMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_httpx.return_value = mock_client
        
        result = await client.make_request(
            method="POST",
            path="/chat/completions",
            headers={"content-type": "application/json"},
            json_data={"model": "gpt-4", "messages": []},
            params={}
        )
        
        assert result["status_code"] == 200
        assert result["json"]["choices"][0]["message"]["content"] == "Hello from Azure!"
        
        # Verify the request was made with Bearer auth (OpenAI style)
        mock_client.request.assert_called_once()
        call_args = mock_client.request.call_args
        assert call_args[1]["headers"]["Authorization"] == "Bearer azure-test-key"
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_custom_client_behavior(self, mock_httpx):
        """Test custom client behavior."""
        config = {
            "type": PlatformType.CUSTOM,
            "api_key": "custom-key",
            "base_url": "http://localhost:11434/v1",
            "timeout": 300
        }
        
        client = PlatformClientFactory.create_client(PlatformType.CUSTOM, config)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "response": "Hello from custom API!"
        }
        
        mock_client = MagicMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_httpx.return_value = mock_client
        
        result = await client.make_request(
            method="POST",
            path="/generate",
            headers={"content-type": "application/json"},
            json_data={"model": "llama2", "prompt": "Hello"},
            params={}
        )
        
        assert result["status_code"] == 200
        assert result["json"]["response"] == "Hello from custom API!"