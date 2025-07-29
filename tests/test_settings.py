"""
Test-specific settings configuration.
This module provides isolated test settings that don't interfere with production.
"""
import os
from pathlib import Path
from pydantic import ConfigDict
from src.config.settings import Settings, PlatformType


def get_test_env_file():
    """Get the path to the .env.test file."""
    project_root = Path(__file__).parent.parent
    return project_root / ".env.test"


class IsolatedTestSettings(Settings):
    """Test-specific settings that use .env.test file."""
    
    model_config = ConfigDict(
        env_file=str(get_test_env_file()),
        env_file_encoding='utf-8'
    )


def create_test_settings_dict():
    """Create a dictionary of test settings for mocking."""
    return {
        "host": "127.0.0.1",
        "port": 8001,
        "log_level": "debug",
        "type": PlatformType.OPENAI,
        "api_key": "test-api-key-12345",
        "base_url": "https://api.test-openai.com/v1",
        "enabled": True,
        "actual_name": "gpt-3.5-turbo-test",
        "max_tokens": 4096,
        "supports_streaming": True,
        "supports_function_calling": True,
        "database_url": "sqlite+aiosqlite:///:memory:",
        "log_file_path": "./tests/logs/test.log",
        "log_retention_days": 1,
        "timeout": 30,
        "default_headers": {},
        "display_name": "Test GPT Model",
        "description": "Test model for unit testing",
        "cost_per_1k_input_tokens": 0.001,
        "cost_per_1k_output_tokens": 0.002,
    }