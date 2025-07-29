import pytest
import os
import tempfile
from unittest.mock import patch
from pathlib import Path

from src.config.settings import Settings, PlatformType
from tests.test_settings import IsolatedTestSettings, create_test_settings_dict


class TestSettingsConfig:
    """Test settings configuration."""
    
    def test_test_environment_settings(self):
        """Test that test environment settings are loaded correctly."""
        settings = IsolatedTestSettings()
        
        assert settings.host == "127.0.0.1"
        assert settings.port == 8001
        assert settings.log_level == "debug"
        assert settings.type == PlatformType.OPENAI
        assert settings.api_key == "test-api-key-12345"
        assert settings.base_url == "https://api.test-openai.com/v1"
        assert settings.actual_name == "gpt-3.5-turbo-test"
        assert settings.enabled is True
        assert settings.max_tokens == 4096
        assert settings.supports_streaming is True
        assert settings.supports_function_calling is True
        assert settings.database_url == "sqlite+aiosqlite:///:memory:"
    
    def test_platform_type_enum(self):
        """Test platform type enum values."""
        assert PlatformType.OPENAI == "openai"
        assert PlatformType.ANTHROPIC == "anthropic"
        assert PlatformType.GOOGLE == "google"
        assert PlatformType.AZURE_OPENAI == "azure_openai"
        assert PlatformType.COHERE == "cohere"
        assert PlatformType.CUSTOM == "custom"
    
    def test_settings_with_env_vars(self):
        """Test settings loading from environment variables."""
        env_vars = {
            "HOST": "127.0.0.1",
            "PORT": "9000",
            "TYPE": "anthropic",
            "API_KEY": "test-key",
            "BASE_URL": "https://api.anthropic.com/v1",
            "ACTUAL_NAME": "claude-3-sonnet",
            "ENABLED": "false",
            "MAX_TOKENS": "8192",
            "SUPPORTS_STREAMING": "false",
            "SUPPORTS_FUNCTION_CALLING": "false"
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            
            assert settings.host == "127.0.0.1"
            assert settings.port == 9000
            assert settings.type == PlatformType.ANTHROPIC
            assert settings.api_key == "test-key"
            assert settings.base_url == "https://api.anthropic.com/v1"
            assert settings.actual_name == "claude-3-sonnet"
            assert settings.enabled is False
            assert settings.max_tokens == 8192
            assert settings.supports_streaming is False
            assert settings.supports_function_calling is False
    
    def test_cost_fields_validation(self):
        """Test cost fields validation with empty strings."""
        env_vars = {
            "COST_PER_1K_INPUT_TOKENS": "",
            "COST_PER_1K_OUTPUT_TOKENS": ""
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            
            assert settings.cost_per_1k_input_tokens is None
            assert settings.cost_per_1k_output_tokens is None
    
    def test_cost_fields_with_values(self):
        """Test cost fields with actual values."""
        env_vars = {
            "COST_PER_1K_INPUT_TOKENS": "0.0015",
            "COST_PER_1K_OUTPUT_TOKENS": "0.002"
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            
            assert settings.cost_per_1k_input_tokens == 0.0015
            assert settings.cost_per_1k_output_tokens == 0.002
    
    def test_invalid_platform_type(self):
        """Test invalid platform type raises validation error."""
        with patch.dict(os.environ, {"TYPE": "invalid"}):
            with pytest.raises(ValueError):
                Settings()
    
    def test_database_url_configuration(self):
        """Test database URL configuration."""
        with patch.dict(os.environ, {"DATABASE_URL": "sqlite:///test.db"}):
            settings = Settings()
            assert settings.database_url == "sqlite:///test.db"
    
    def test_logging_configuration(self):
        """Test logging configuration."""
        env_vars = {
            "LOG_FILE_PATH": "/custom/log/path.log",
            "LOG_RETENTION_DAYS": "60",
            "LOG_LEVEL": "debug"
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            
            assert settings.log_file_path == "/custom/log/path.log"
            assert settings.log_retention_days == 60
            assert settings.log_level == "debug"