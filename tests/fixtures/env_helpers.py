"""Environment and configuration helpers for testing."""

import os
from collections.abc import Generator
from unittest.mock import patch

import pytest


@pytest.fixture
def mock_env_vars() -> Generator[None, None, None]:
    """Mock environment variables for OpenAI."""
    with patch.dict(
        os.environ,
        {
            "API_KEY": "sk-test1234567890abcdef",
            "OPENAI_API_KEY": "sk-test1234567890abcdef",
            "OPENAI_MODEL": "gpt-4o-mini",
        },
    ):
        yield


@pytest.fixture
def empty_env() -> Generator[None, None, None]:
    """Empty environment variables."""
    with patch.dict(os.environ, {}, clear=True):
        yield


@pytest.fixture
def openai_api_key() -> str:
    """Test OpenAI API key."""
    return "test-key"


@pytest.fixture
def openai_model() -> str:
    """Test OpenAI model name."""
    return "gpt-4o-mini"
