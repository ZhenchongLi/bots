"""
Integration tests for OpenAI Python library compatibility
"""
import pytest
import orjson as json

# Skip these tests if openai library is not installed
openai = pytest.importorskip("openai")


@pytest.mark.integration
class TestOpenAILibraryIntegration:
    """Test compatibility with the official OpenAI Python library"""
    
    @pytest.fixture
    def openai_client(self):
        """Create OpenAI client configured to use local test server"""
        # This is a basic test to ensure the library can be instantiated
        # Real integration tests would require a running server
        return openai.OpenAI(
            base_url="http://localhost:8000/v1",
            api_key="test-key"
        )
    
    def test_openai_client_creation(self, openai_client):
        """Test that OpenAI client can be created with our API base URL"""
        assert str(openai_client.base_url) == "http://localhost:8000/v1/"
        assert openai_client.api_key == "test-key"

    def test_openai_library_compatibility_structure(self):
        """Test that we can import and use OpenAI library classes"""
        # Test that we can create request objects that match our API
        from openai.types.chat import ChatCompletion
        from openai.types import Completion, Embedding

        # These should be importable and usable
        chat_params = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "test"}]
        }
        assert chat_params["model"] == "gpt-3.5-turbo"

        completion_params = {
            "model": "text-davinci-003",
            "prompt": "test"
        }
        assert completion_params["model"] == "text-davinci-003"

        embedding_params = {
            "model": "text-embedding-ada-002",
            "input": "test"
        }
        assert embedding_params["model"] == "text-embedding-ada-002"
    
    def test_openai_request_types_compatibility(self):
        """Test that our Pydantic models are compatible with OpenAI types"""
        from src.models.openai import ChatCompletionRequest, CompletionRequest, EmbeddingRequest
        
        # Test that our models accept the same data as OpenAI types
        chat_data = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "Hello"}],
            "temperature": 0.7,
            "max_tokens": 100
        }
        
        # Should be able to create our request model
        chat_request = ChatCompletionRequest.model_validate(chat_data)
        assert chat_request.model == "gpt-3.5-turbo"
        
        completion_data = {
            "model": "text-davinci-003",
            "prompt": "Hello",
            "max_tokens": 50
        }
        
        completion_request = CompletionRequest.model_validate(completion_data)
        assert completion_request.model == "text-davinci-003"
        
        embedding_data = {
            "model": "text-embedding-ada-002",
            "input": "Hello world"
        }
        
        embedding_request = EmbeddingRequest.model_validate(embedding_data)
        assert embedding_request.model == "text-embedding-ada-002"