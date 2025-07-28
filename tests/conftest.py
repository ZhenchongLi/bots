import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import tempfile
import os

from src.main import create_app
from src.config.settings import Settings, PlatformType


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings():
    """Create test settings."""
    return Settings(
        host="127.0.0.1",
        port=8001,
        type=PlatformType.OPENAI,
        api_key="test-api-key",
        base_url="https://api.openai.com/v1",
        actual_name="gpt-3.5-turbo",
        enabled=True,
        database_url="sqlite+aiosqlite:///:memory:",
        log_file_path="/tmp/test.log"
    )


@pytest.fixture
def mock_settings(test_settings):
    """Mock the settings module."""
    with patch('src.config.settings.settings', test_settings), \
         patch('src.core.model_manager.settings', test_settings):
        yield test_settings


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