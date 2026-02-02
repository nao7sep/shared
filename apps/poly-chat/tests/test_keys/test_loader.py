"""Tests for unified key loader."""

import pytest
from poly_chat.keys.loader import load_api_key, validate_api_key


def test_load_api_key_env(monkeypatch):
    """Test loading API key from environment."""
    monkeypatch.setenv("TEST_KEY", "sk-1234567890abcdef1234567890abcdef")

    config = {"type": "env", "key": "TEST_KEY"}
    key = load_api_key("test_provider", config)

    assert key == "sk-1234567890abcdef1234567890abcdef"


def test_load_api_key_invalid_type():
    """Test loading with invalid type."""
    config = {"type": "invalid_type"}

    with pytest.raises(ValueError, match="Unknown key type"):
        load_api_key("test_provider", config)


def test_validate_api_key_valid():
    """Test validating valid API key."""
    key = "sk-1234567890abcdef1234567890abcdef"
    assert validate_api_key(key, "openai") is True


def test_validate_api_key_empty():
    """Test validating empty key."""
    assert validate_api_key("", "openai") is False
    assert validate_api_key("   ", "openai") is False


def test_validate_api_key_too_short():
    """Test validating too short key."""
    assert validate_api_key("short", "openai") is False


def test_validate_api_key_minimum_length():
    """Test validating key at minimum length."""
    key = "a" * 20
    assert validate_api_key(key, "openai") is True
