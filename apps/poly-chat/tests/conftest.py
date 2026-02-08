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
        "timeout": 30,
        "input_mode": "quick",
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
            "system_prompt": None,
            "created_at": "2026-02-02T10:00:00.000000Z",
            "updated_at": "2026-02-02T10:00:00.000000Z"
        },
        "messages": [
            {
                "timestamp": "2026-02-02T10:00:00.000000Z",
                "role": "user",
                "content": [
                    "I need help with a project.",
                    "",
                    "What are the key steps to get started?"
                ]
            },
            {
                "timestamp": "2026-02-02T10:00:05.000000Z",
                "role": "assistant",
                "model": "claude-haiku-4-5",
                "content": [
                    "Here are the key steps:",
                    "",
                    "1. Define your goals",
                    "2. Create a timeline",
                    "3. Gather resources"
                ]
            }
        ]
    }


@pytest.fixture
def mock_api_key(monkeypatch):
    """Mock API key environment variable."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-1234567890abcdef1234567890abcdef")
    monkeypatch.setenv("CLAUDE_API_KEY", "sk-ant-test-key-1234567890abcdef1234567890abcdef")


@pytest.fixture
def mock_session_manager():
    """Create a mock SessionManager for testing commands."""
    from src.poly_chat.session_manager import SessionManager

    manager = SessionManager(
        profile={
            "default_ai": "claude",
            "input_mode": "quick",
            "models": {"claude": "claude-haiku-4-5", "openai": "gpt-5-mini"},
            "api_keys": {},
            "chats_dir": "/test/chats",
            "log_dir": "/test/logs",
            "timeout": 30,
        },
        current_ai="claude",
        current_model="claude-haiku-4-5",
        chat={"metadata": {}, "messages": []},
        chat_path="/test/chat.json",
        profile_path="/test/profile.json",
        log_file="/test/log.txt",
    )
    return manager


@pytest.fixture
def command_handler(mock_session_manager):
    """Create a CommandHandler with SessionManager state only."""
    from src.poly_chat.commands import CommandHandler
    return CommandHandler(mock_session_manager)
