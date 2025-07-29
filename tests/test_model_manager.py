import pytest
from unittest.mock import patch, MagicMock

from src.core.model_manager import ModelManager
from src.config.settings import Settings, PlatformType


def create_test_manager_config(api_key="sk-test-key", actual_name="gpt-4", enabled=True):
    """Helper function to create test manager configuration."""
    return {
        "type": PlatformType.OPENAI,
        "api_key": api_key,
        "base_url": "https://api.openai.com/v1",
        "actual_name": actual_name,
        "enabled": enabled,
        "default_headers": {},
        "timeout": 300,
        "display_name": None,
        "description": None,
        "max_tokens": 8192,
        "supports_streaming": True,
        "supports_function_calling": True,
        "cost_per_1k_input_tokens": None,
        "cost_per_1k_output_tokens": None,
    }


class TestModelManager:
    """Test model manager functionality."""
    
    @pytest.fixture
    def openai_settings(self):
        """OpenAI settings fixture."""
        return Settings(
            type=PlatformType.OPENAI,
            api_key="sk-test-key",
            base_url="https://api.openai.com/v1",
            actual_name="gpt-4",
            enabled=True,
            max_tokens=8192,
            supports_streaming=True,
            supports_function_calling=True
        )
    
    @pytest.fixture
    def anthropic_settings(self):
        """Anthropic settings fixture."""
        return Settings(
            type=PlatformType.ANTHROPIC,
            api_key="sk-ant-test-key",
            base_url="https://api.anthropic.com/v1",
            actual_name="claude-3-sonnet-20240229",
            enabled=True,
            max_tokens=4096,
            supports_streaming=False,
            supports_function_calling=False
        )
    
    @pytest.fixture
    def disabled_settings(self):
        """Disabled model settings fixture."""
        return Settings(
            type=PlatformType.OPENAI,
            api_key="",
            enabled=False
        )
    
    def test_model_manager_initialization(self, openai_settings):
        """Test model manager initialization."""
        test_config = create_test_manager_config()
        manager = ModelManager()
        manager.config = test_config  # Override with test config
        
        config = manager.get_model_config()
        assert config["type"] == PlatformType.OPENAI
        assert config["api_key"] == "sk-test-key"
        assert config["actual_name"] == "gpt-4"
        assert config["enabled"] is True
    
    def test_is_model_available_enabled(self, openai_settings):
        """Test model availability when enabled with API key."""
        test_config = create_test_manager_config()
        manager = ModelManager()
        manager.config = test_config
        assert manager.is_model_available() is True
    
    def test_is_model_available_disabled(self, disabled_settings):
        """Test model availability when disabled."""
        test_config = create_test_manager_config(enabled=False)
        manager = ModelManager()
        manager.config = test_config
        assert manager.is_model_available() is False
    
    def test_is_model_available_no_api_key(self):
        """Test model availability without API key."""
        test_config = create_test_manager_config(api_key="")
        manager = ModelManager()
        manager.config = test_config
        assert manager.is_model_available() is False
    
    def test_validate_model_request_success(self, openai_settings):
        """Test successful model request validation."""
        test_config = create_test_manager_config()
        manager = ModelManager()
        manager.config = test_config
        
        is_valid, error = manager.validate_model_request("gpt-4")
        assert is_valid is True
        assert error is None
    
    def test_validate_model_request_disabled(self, disabled_settings):
        """Test model request validation when disabled."""
        test_config = create_test_manager_config(api_key="", enabled=False)
        manager = ModelManager()
        manager.config = test_config
        
        is_valid, error = manager.validate_model_request("gpt-4")
        assert is_valid is False
        assert error == "Model is disabled"
    
    def test_validate_model_request_no_api_key(self):
        """Test model request validation when enabled but no API key."""
        test_config = create_test_manager_config(api_key="", enabled=True)
        manager = ModelManager()
        manager.config = test_config
        
        is_valid, error = manager.validate_model_request("gpt-4")
        assert is_valid is False
        assert error == "API key not configured"
    
    def test_process_model_request_success(self, openai_settings):
        """Test successful model request processing."""
        test_config = create_test_manager_config()
        manager = ModelManager()
        manager.config = test_config
        
        request_data = {"model": "gpt-3.5-turbo", "messages": []}
        processed_data, actual_model = manager.process_model_request(request_data)
        
        assert processed_data["model"] == "gpt-4"  # Should be replaced with actual_name
        assert actual_model == "gpt-4"
        assert processed_data["messages"] == []
    
    def test_process_model_request_no_model(self, openai_settings):
        """Test model request processing without model field."""
        test_config = create_test_manager_config()
        manager = ModelManager()
        manager.config = test_config
        
        request_data = {"messages": []}
        
        with pytest.raises(ValueError, match="No model specified in request"):
            manager.process_model_request(request_data)
    
    def test_process_model_request_disabled_model(self, disabled_settings):
        """Test model request processing with disabled model."""
        test_config = create_test_manager_config(api_key="", enabled=False)
        manager = ModelManager()
        manager.config = test_config
        
        request_data = {"model": "gpt-4", "messages": []}
        
        with pytest.raises(ValueError, match="Model is disabled"):
            manager.process_model_request(request_data)
    
    def test_get_models_list_enabled(self, openai_settings):
        """Test getting models list when enabled."""
        test_config = create_test_manager_config()
        manager = ModelManager()
        manager.config = test_config
        
        models = manager.get_models_list()
        
        assert len(models) == 1
        model = models[0]
        assert model["id"] == "gpt-4"
        assert model["object"] == "model"
        assert model["owned_by"] == "openai"
        assert model["root"] == "gpt-4"
    
    def test_get_models_list_disabled(self, disabled_settings):
        """Test getting models list when disabled."""
        test_config = create_test_manager_config(enabled=False)
        manager = ModelManager()
        manager.config = test_config
        
        models = manager.get_models_list()
        assert len(models) == 0
    
    def test_get_available_models_enabled(self, openai_settings):
        """Test getting available models when enabled."""
        test_config = create_test_manager_config()
        manager = ModelManager()
        manager.config = test_config
        
        models = manager.get_available_models()
        assert models == ["gpt-4"]
    
    def test_get_available_models_disabled(self, disabled_settings):
        """Test getting available models when disabled."""
        test_config = create_test_manager_config(enabled=False)
        manager = ModelManager()
        manager.config = test_config
        
        models = manager.get_available_models()
        assert models == []
    
    def test_get_platform_type(self, anthropic_settings):
        """Test getting platform type."""
        test_config = create_test_manager_config()
        test_config["type"] = PlatformType.ANTHROPIC
        manager = ModelManager()
        manager.config = test_config
        
        platform_type = manager.get_platform_type()
        assert platform_type == PlatformType.ANTHROPIC
    
    def test_reload_config(self, openai_settings):
        """Test configuration reload."""
        test_config = create_test_manager_config()
        manager = ModelManager()
        manager.config = test_config
        
        # Change settings
        new_config = create_test_manager_config(
            api_key="new-key",
            actual_name="claude-3"
        )
        new_config["type"] = PlatformType.ANTHROPIC
        
        with patch('src.config.settings.settings') as mock_settings:
            mock_settings.type = PlatformType.ANTHROPIC
            mock_settings.api_key = "new-key"
            mock_settings.actual_name = "claude-3"
            
            manager.reload_config()
            manager.config = new_config  # Override with new test config
            
            config = manager.get_model_config()
            assert config["type"] == PlatformType.ANTHROPIC
            assert config["api_key"] == "new-key"
            assert config["actual_name"] == "claude-3"
    
    def test_model_request_with_different_names(self, openai_settings):
        """Test processing requests with different model names."""
        test_config = create_test_manager_config()
        manager = ModelManager()
        manager.config = test_config
        
        # Test different input model names
        test_cases = ["gpt-3.5-turbo", "gpt-4", "custom-model"]
        
        for input_model in test_cases:
            request_data = {"model": input_model, "messages": []}
            processed_data, actual_model = manager.process_model_request(request_data)
            
            # All should be mapped to the configured actual_name
            assert processed_data["model"] == "gpt-4"
            assert actual_model == "gpt-4"