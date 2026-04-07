"""
Pytest Configuration and Shared Fixtures
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
import sys
import os

# Add brain to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'brain'))

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_supabase():
    """Mock Supabase client"""
    mock = Mock()
    mock.table = Mock(return_value=mock)
    mock.select = Mock(return_value=mock)
    mock.insert = Mock(return_value=mock)
    mock.update = Mock(return_value=mock)
    mock.delete = Mock(return_value=mock)
    mock.upsert = Mock(return_value=mock)
    mock.eq = Mock(return_value=mock)
    mock.like = Mock(return_value=mock)
    mock.gte = Mock(return_value=mock)
    mock.order = Mock(return_value=mock)
    mock.limit = Mock(return_value=mock)
    mock.execute = Mock(return_value=Mock(data=[], count=0))
    return mock

@pytest.fixture
def mock_settings():
    """Mock application settings"""
    with patch('core.config.settings') as mock:
        mock.APP_NAME = "MagicLamp"
        mock.APP_VERSION = "1.0.0"
        mock.ENVIRONMENT = "test"
        mock.SUPABASE_URL = "https://test.supabase.co"
        mock.SUPABASE_KEY = "test_key"
        mock.JWT_SECRET = "test_secret_key_min_32_chars_long"
        mock.JWT_ALGORITHM = "HS256"
        mock.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        mock.REFRESH_TOKEN_EXPIRE_DAYS = 30
        mock.BRAIN_API_KEY = "test_brain_key"
        mock.OLLAMA_URL = "http://test-ollama:11434"
        mock.OLLAMA_MODEL = "test-model"
        mock.OLLAMA_TIMEOUT = 120
        mock.AUTO_MODE = False
        mock.CORS_ORIGINS = "*"
        yield mock

@pytest.fixture
def test_user():
    """Standard test user"""
    return {
        "id": "123",
        "email": "test@example.com",
        "name": "testuser",
        "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU7fVKgL.E2K",  # "password123"
        "role": "user",
        "created_at": datetime.now(timezone.utc).isoformat()
    }

@pytest.fixture
def test_admin():
    """Admin test user"""
    return {
        "id": "999",
        "email": "admin@example.com",
        "name": "admin",
        "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU7fVKgL.E2K",
        "role": "admin",
        "org_id": "org_123",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
