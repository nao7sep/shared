"""Tests for env_vars key loading."""

import pytest
from poly_chat.keys.env_vars import load_from_env


def test_load_from_env_success(monkeypatch):
    """Test loading API key from environment variable."""
    monkeypatch.setenv("TEST_API_KEY", "test-key-value")

    key = load_from_env("TEST_API_KEY")
    assert key == "test-key-value"


def test_load_from_env_missing(monkeypatch):
    """Test loading non-existent environment variable."""
    # Make sure it doesn't exist
    monkeypatch.delenv("MISSING_KEY", raising=False)

    with pytest.raises(ValueError, match="not set"):
        load_from_env("MISSING_KEY")


def test_load_from_env_empty(monkeypatch):
    """Test loading empty environment variable."""
    monkeypatch.setenv("EMPTY_KEY", "")

    with pytest.raises(ValueError, match="not set"):
        load_from_env("EMPTY_KEY")


def test_load_from_env_strips_whitespace(monkeypatch):
    """Test that whitespace is stripped from key."""
    monkeypatch.setenv("WHITESPACE_KEY", "  test-key  ")

    key = load_from_env("WHITESPACE_KEY")
    assert key == "test-key"
