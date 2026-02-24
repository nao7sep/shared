"""Tests for direct value key loading."""

import pytest
from polychat.keys.loader import load_api_key


def test_load_direct_success():
    """Test loading API key from direct value."""
    config = {
        "type": "direct",
        "value": "sk-test-direct-key-12345"
    }

    key = load_api_key("test_provider", config)
    assert key == "sk-test-direct-key-12345"


def test_load_direct_empty_value():
    """Test loading direct value that is empty."""
    config = {
        "type": "direct",
        "value": ""
    }

    # Direct loader doesn't validate, just returns the value
    key = load_api_key("test_provider", config)
    assert key == ""


def test_load_direct_with_whitespace():
    """Test loading direct value with whitespace."""
    config = {
        "type": "direct",
        "value": "  sk-key-with-spaces  "
    }

    # Direct loader returns value as-is (validation happens later)
    key = load_api_key("test_provider", config)
    assert key == "  sk-key-with-spaces  "


def test_load_direct_missing_value():
    """Test loading when 'value' field is missing."""
    config = {
        "type": "direct"
        # Missing 'value' field
    }

    with pytest.raises(KeyError):
        load_api_key("test_provider", config)


def test_load_direct_special_characters():
    """Test loading direct value with special characters."""
    config = {
        "type": "direct",
        "value": "sk-test!@#$%^&*()_+-=[]{}|;':\",./<>?"
    }

    key = load_api_key("test_provider", config)
    assert key == "sk-test!@#$%^&*()_+-=[]{}|;':\",./<>?"


def test_load_direct_long_key():
    """Test loading very long direct value."""
    long_key = "sk-" + "a" * 1000
    config = {
        "type": "direct",
        "value": long_key
    }

    key = load_api_key("test_provider", config)
    assert key == long_key
    assert len(key) == 1003
