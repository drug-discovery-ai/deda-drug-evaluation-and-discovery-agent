"""Environment and configuration helpers for testing."""

import pytest
from unittest.mock import patch
import os


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for OpenAI."""
    with patch.dict(os.environ, {
        "OPENAI_API_KEY": "test-key",
        "OPENAI_MODEL": "gpt-4o-mini"
    }):
        yield


@pytest.fixture
def empty_env():
    """Empty environment variables."""
    with patch.dict(os.environ, {}, clear=True):
        yield


@pytest.fixture
def openai_api_key():
    """Test OpenAI API key."""
    return "test-key"


@pytest.fixture
def openai_model():
    """Test OpenAI model name."""
    return "gpt-4o-mini"