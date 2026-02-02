"""Pytest configuration and fixtures for PolyChat tests."""

import pytest
import tempfile
import json
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_profile(temp_dir):
    """Create sample profile for testing."""
    profile = {
        "default_ai": "claude",
        "models": {
            "openai": "gpt-4o",
            "claude": "claude-sonnet-4",
            "gemini": "gemini-2.0-flash"
        },
        "system_prompt": "You are a helpful assistant.",
        "conversations_dir": str(temp_dir / "conversations"),
        "log_dir": str(temp_dir / "logs"),
        "api_keys": {
            "openai": {
                "type": "env",
                "key": "OPENAI_API_KEY"
            }
        }
    }

    profile_path = temp_dir / "test-profile.json"
    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)

    return profile_path


@pytest.fixture
def sample_conversation():
    """Create sample conversation data."""
    return {
        "metadata": {
            "title": "Test Conversation",
            "summary": None,
            "system_prompt_key": None,
            "default_model": "claude-sonnet-4",
            "created_at": "2026-02-02T10:00:00.000000Z",
            "updated_at": "2026-02-02T10:00:00.000000Z"
        },
        "messages": [
            {
                "role": "user",
                "content": ["Hello", "How are you?"],
                "timestamp": "2026-02-02T10:00:00.000000Z"
            },
            {
                "role": "assistant",
                "content": ["I'm doing well, thank you!"],
                "timestamp": "2026-02-02T10:00:05.000000Z",
                "model": "claude-sonnet-4"
            }
        ]
    }


@pytest.fixture
def mock_api_key(monkeypatch):
    """Mock API key environment variable."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-1234567890abcdef1234567890abcdef")
    monkeypatch.setenv("CLAUDE_API_KEY", "sk-ant-test-key-1234567890abcdef1234567890abcdef")
