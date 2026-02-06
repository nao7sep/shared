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
            "openai": "gpt-5-mini",
            "claude": "claude-haiku-4-5",
            "gemini": "gemini-3-flash-preview"
        },
        "system_prompt": "You are a helpful assistant.",
        "chats_dir": str(temp_dir / "chats"),
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
def sample_chat():
    """Create sample chat data."""
    return {
        "metadata": {
            "title": "Test Chat",
            "summary": None,
            "system_prompt_key": None,
            "default_model": "claude-haiku-4-5",
            "created_at": "2026-02-02T10:00:00.000000Z",
            "updated_at": "2026-02-02T10:00:00.000000Z"
        },
        "messages": [
            {
                "role": "user",
                "content": [
                    "I need help with a project.",
                    "",
                    "What are the key steps to get started?"
                ],
                "timestamp": "2026-02-02T10:00:00.000000Z"
            },
            {
                "role": "assistant",
                "content": [
                    "Here are the key steps:",
                    "",
                    "1. Define your goals",
                    "2. Create a timeline",
                    "3. Gather resources"
                ],
                "timestamp": "2026-02-02T10:00:05.000000Z",
                "model": "claude-haiku-4-5"
            }
        ]
    }


@pytest.fixture
def mock_api_key(monkeypatch):
    """Mock API key environment variable."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-1234567890abcdef1234567890abcdef")
    monkeypatch.setenv("CLAUDE_API_KEY", "sk-ant-test-key-1234567890abcdef1234567890abcdef")
