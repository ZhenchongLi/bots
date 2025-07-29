import pytest
import asyncio
import os
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import tempfile

from src.main import create_app
from src.config.settings import Settings, PlatformType
from tests.test_settings import IsolatedTestSettings, create_test_settings_dict


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Setup test environment with .env.test file."""
    # Get the project root directory
    project_root = Path(__file__).parent.parent
    test_env_file = project_root / ".env.test"
    
    # Ensure .env.test exists
    if not test_env_file.exists():
        raise FileNotFoundError(f"Test environment file not found: {test_env_file}")
    
    # Set environment to use test configuration
    original_env_file = os.environ.get("ENV_FILE")
    os.environ["ENV_FILE"] = str(test_env_file)
    
    yield
    
    # Cleanup
    if original_env_file:
        os.environ["ENV_FILE"] = original_env_file
    else:
        os.environ.pop("ENV_FILE", None)


@pytest.fixture
def test_settings():
    """Create test settings from .env.test file."""
    return IsolatedTestSettings()


@pytest.fixture
def test_settings_dict():
    """Create test settings dictionary for mocking."""
    return create_test_settings_dict()


@pytest.fixture
def mock_settings(test_settings):
    """Mock the settings module with test configuration."""
    # Create a mock settings object with test values
    mock_settings_obj = MagicMock()
    test_dict = create_test_settings_dict()
    
    # Set all attributes on the mock
    for key, value in test_dict.items():
        setattr(mock_settings_obj, key, value)
    
    with patch('src.config.settings.settings', mock_settings_obj), \
         patch('src.core.model_manager.settings', mock_settings_obj):
        # Also patch the model_manager's config directly
        from src.core.model_manager import model_manager
        original_config = model_manager.config
        model_manager.config = test_dict
        
        try:
            yield mock_settings_obj
        finally:
            model_manager.config = original_config


@pytest.fixture
def client(mock_settings):
    """Create a test client."""
    with patch('src.database.connection.init_db'):
        app = create_app()
        with TestClient(app) as test_client:
            yield test_client


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient for testing external API calls."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Test response"}}]
    }
    
    mock_client = MagicMock()
    mock_client.request.return_value.__aenter__.return_value = mock_response
    
    with patch('httpx.AsyncClient', return_value=mock_client):
        yield mock_client


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    yield f"sqlite+aiosqlite:///{db_path}"
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)