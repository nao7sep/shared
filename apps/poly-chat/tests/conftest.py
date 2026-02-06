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


# ============================================================================
# Integration test helpers (for loading real API keys)
# ============================================================================

from typing import Optional

_TEST_API_KEYS_FILENAME = ".TEST_API_KEYS.json"
_config_cache: Optional[dict] = None


def find_test_api_keys_file() -> Optional[Path]:
    """
    Search for .TEST_API_KEYS.json by recursively checking parent directories.

    Starts from the current file's directory and moves up until:
    - File is found (returns Path)
    - Filesystem root is reached (returns None)

    This allows placing the file outside the repo if needed.
    """
    current = Path(__file__).resolve().parent

    while True:
        candidate = current / _TEST_API_KEYS_FILENAME
        if candidate.exists():
            return candidate

        # Check if we've reached filesystem root
        parent = current.parent
        if parent == current:
            # Can't go higher
            return None

        current = parent


def load_test_config() -> dict:
    """
    Load test API keys configuration.

    Returns the full config dict. Caches result after first load.
    Raises FileNotFoundError if .TEST_API_KEYS.json is not found.
    """
    global _config_cache

    if _config_cache is not None:
        return _config_cache

    config_file = find_test_api_keys_file()
    if config_file is None:
        raise FileNotFoundError(
            f"{_TEST_API_KEYS_FILENAME} not found in current directory or any parent directory. "
            "Create this file at repo root with API keys for testing."
        )

    with open(config_file, 'r', encoding='utf-8') as f:
        _config_cache = json.load(f)

    return _config_cache


def is_ai_available(ai_name: str) -> bool:
    """
    Check if an AI provider is available for testing.

    Returns True if:
    - The AI exists in config
    - It has a non-empty api_key

    Args:
        ai_name: Provider name (e.g., "openai", "claude", "gemini")

    Returns:
        True if AI can be tested, False otherwise
    """
    try:
        config = load_test_config()
    except FileNotFoundError:
        return False

    if ai_name not in config:
        return False

    ai_config = config[ai_name]
    api_key = ai_config.get("api_key", "")

    return bool(api_key and api_key.strip())


def get_ai_config(ai_name: str) -> dict:
    """
    Get configuration for a specific AI provider.

    Args:
        ai_name: Provider name (e.g., "openai", "claude")

    Returns:
        Dict with api_key, model, and other parameters

    Raises:
        KeyError: If AI not found in config
        FileNotFoundError: If config file not found
    """
    config = load_test_config()
    return config[ai_name]
