"""
Pytest-based tests for core functionality, converted from test_simple.py
"""
import os
from unittest.mock import patch
from pydantic import ConfigDict

from src.config.settings import Settings, PlatformType
from src.core.model_manager import ModelManager
from src.core.platform_clients import PlatformClientFactory

def test_settings_default_values():
    """Test that default settings are loaded correctly."""
    class SettingsWithoutEnvFile(Settings):
        model_config = ConfigDict(env_file=None, extra='ignore')

    with patch.dict(os.environ, {}, clear=True):
        settings = SettingsWithoutEnvFile()
        assert settings.type == PlatformType.OPENAI
        assert settings.base_url == "https://api.openai.com/v1"
        assert settings.actual_name == "gpt-3.5-turbo"

def test_model_manager_functions():
    """Test core ModelManager functionality."""
    # Mock configuration for the manager
    mock_config = {
        "type": PlatformType.OPENAI,
        "api_key": "test-key",
        "base_url": "https://api.openai.com/v1",
        "actual_name": "gpt-4",
        "enabled": True,
        "default_headers": {},
        "timeout": 300,
        "display_name": None,
        "description": None,
        "max_tokens": 4096,
        "supports_streaming": True,
        "supports_function_calling": True,
        "cost_per_1k_input_tokens": None,
        "cost_per_1k_output_tokens": None,
    }

    manager = ModelManager()
    manager.config = mock_config

    # Test model availability
    assert manager.is_model_available() is True

    # Test model request processing
    request_data = {"model": "gpt-3.5-turbo", "messages": []}
    processed_data, actual_model = manager.process_model_request(request_data)
    assert processed_data["model"] == "gpt-4"
    assert actual_model == "gpt-4"

def test_platform_client_factory():
    """Test the PlatformClientFactory."""
    mock_config = {
        "type": PlatformType.OPENAI,
        "api_key": "test-key",
        "base_url": "https://api.openai.com/v1",
        "timeout": 300
    }

    # Test client factory for all supported platforms
    platforms = [
        PlatformType.OPENAI,
        PlatformType.ANTHROPIC,
        PlatformType.GOOGLE,
        PlatformType.AZURE_OPENAI,
        PlatformType.CUSTOM
    ]
    for platform in platforms:
        client = PlatformClientFactory.create_client(platform, mock_config)
        assert client is not None
        assert hasattr(client, 'make_request')
