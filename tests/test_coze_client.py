import pytest
from unittest.mock import patch, MagicMock
import httpx

from src.adapters.coze_adapter import CozeAdapter
from src.adapters.manager import adapter_manager
from src.core.platform_clients import PlatformClientFactory
from src.config.settings import PlatformType


class TestCozeAdapter:
    """Test Coze Bot adapter functionality."""
    
    @pytest.fixture
    def coze_config(self):
        """Create test configuration for Coze Bot."""
        return {
            "api_key": "test-coze-api-key",
            "base_url": "https://api.coze.com/v1",
            "bot_id": "test-bot-123",
            "conversation_id": "test-conv-456",
            "timeout": 300,
            "default_headers": {}
        }
    
    @pytest.fixture
    def coze_adapter(self, coze_config):
        """Create CozeAdapter instance for testing."""
        return CozeAdapter(coze_config)
    
    def test_coze_adapter_initialization(self, coze_config):
        """Test CozeAdapter initialization."""
        adapter = CozeAdapter(coze_config)
        
        assert adapter.api_key == "test-coze-api-key"
        assert adapter.base_url == "https://api.coze.com/v1"
        assert adapter.timeout == 300
        # bot_id is now extracted from model name at runtime, not during init
        assert adapter.bot_id is None  # Initially None until model is processed
    
    @pytest.mark.asyncio
    async def test_transform_request(self, coze_adapter):
        """Test request transformation from OpenAI format to Coze format."""
        openai_data = {
            "model": "bot-test-bot-123",  # Use proper bot-{id} format
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, how are you?"}
            ],
            "stream": False
        }
        
        coze_data = await coze_adapter.transform_request("/chat/completions", openai_data)
        
        assert coze_data["bot_id"] == "test-bot-123"
        assert coze_data["user_id"] == "default_user"
        assert coze_data["additional_messages"][-1]["content"] == "Hello, how are you?"
        assert coze_data["stream"] is False
    
    def test_adapter_initialization_missing_bot_id(self):
        """Test adapter initialization no longer requires bot_id during init."""
        config = {
            "api_key": "test-api-key",
            "base_url": "https://api.coze.com/v1"
            # bot_id is now extracted from model name, not required during init
        }
        
        # Should not fail - bot_id is extracted from model at runtime
        adapter = CozeAdapter(config)
        assert adapter.bot_id is None  # Initially None
    
    @pytest.mark.asyncio
    async def test_transform_response_with_messages(self, coze_adapter):
        """Test response transformation from Coze format to OpenAI format (messages format)."""
        coze_response = {
            "conversation_id": "test-conv-456",
            "created_at": 1677652288,
            "messages": [
                {
                    "role": "assistant",
                    "content": "Hello! I'm doing well, thank you for asking.",
                    "content_type": "text"
                }
            ]
        }
        
        openai_response = await coze_adapter.transform_response("/chat/completions", coze_response)
        
        assert openai_response["id"] == "chatcmpl-test-conv-456"
        assert openai_response["object"] == "chat.completion"
        assert openai_response["created"] == 1677652288
        assert len(openai_response["choices"]) == 1
        
        choice = openai_response["choices"][0]
        assert choice["index"] == 0
        assert choice["message"]["role"] == "assistant"
        assert choice["message"]["content"] == "Hello! I'm doing well, thank you for asking."
        assert choice["finish_reason"] == "stop"
        
        assert openai_response["usage"]["prompt_tokens"] == 0
        assert openai_response["usage"]["completion_tokens"] == 0
        assert openai_response["usage"]["total_tokens"] == 0
    
    @pytest.mark.asyncio
    async def test_transform_response_with_answer(self, coze_adapter):
        """Test response transformation from Coze format to OpenAI format (answer format)."""
        coze_response = {
            "answer": "This is the bot's response.",
            "status": "success"
        }
        
        openai_response = await coze_adapter.transform_response("/chat/completions", coze_response)
        
        assert openai_response["id"] == "chatcmpl-unknown"
        assert openai_response["object"] == "chat.completion"
        assert len(openai_response["choices"]) == 1
        
        choice = openai_response["choices"][0]
        assert choice["message"]["content"] == "This is the bot's response."
        assert choice["finish_reason"] == "stop"
    
    @pytest.mark.asyncio
    async def test_make_request_success(self, coze_adapter):
        """Test successful API request to Coze Bot."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.content = b'{"messages": [{"role": "assistant", "content": "Test response"}]}'
        mock_response.json.return_value = {
            "messages": [{"role": "assistant", "content": "Test response"}]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.request.return_value = mock_response
            
            result = await coze_adapter.make_request(
                method="POST",
                url="https://api.coze.com/v1/chat/completions",
                json_data={
                    "bot_id": "test-bot-123",
                    "user": "Hello",
                    "conversation_id": "test-conv-456"
                }
            )
            
            assert result["status_code"] == 200
            assert "json" in result
            assert result["json"]["messages"][0]["content"] == "Test response"
    
    def test_platform_factory_uses_adapter(self, coze_config):
        """Test that PlatformClientFactory uses adapter for COZE platform."""
        coze_config["type"] = "coze"
        client = PlatformClientFactory.create_client("coze", coze_config)
        
        # Should return AdapterProxy when adapter system is available
        from src.adapters.proxy import AdapterProxy
        assert isinstance(client, AdapterProxy)
        assert client.platform_type == "coze"
    
    def test_prepare_headers(self, coze_adapter):
        """Test header preparation for Coze requests."""
        headers = coze_adapter.prepare_headers({"Custom-Header": "value"})
        
        assert "Custom-Header" in headers
        assert headers["Custom-Header"] == "value"
        
        # Test header filtering
        headers_with_auth = coze_adapter.prepare_headers({
            "Authorization": "should-be-filtered",
            "Custom-Header": "should-be-kept"
        })
        
        assert "Authorization" not in headers_with_auth
        assert "Custom-Header" in headers_with_auth
    
    def test_get_supported_endpoints(self, coze_adapter):
        """Test supported endpoints list."""
        endpoints = coze_adapter.get_supported_endpoints()
        assert "/chat/completions" in endpoints
        assert isinstance(endpoints, list)


class TestCozeIntegration:
    """Test Coze Bot integration with the overall system."""
    
    def test_coze_platform_type_exists(self):
        """Test that COZE platform type is available."""
        assert PlatformType.COZE == "coze"
        assert hasattr(PlatformType, 'COZE')
    
    def test_coze_adapter_in_registry(self):
        """Test that CozeAdapter is registered in the adapter registry."""
        assert adapter_manager.is_platform_supported("coze")
        assert "coze" in adapter_manager.get_supported_platforms()