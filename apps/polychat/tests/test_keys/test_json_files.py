"""Tests for JSON file key loading."""

import json
import pytest
from polychat.keys.json_files import load_from_json


def test_load_from_json_success(tmp_path):
    """Test loading API key from JSON file."""
    # Create test JSON file
    keys_file = tmp_path / "keys.json"
    keys_file.write_text(json.dumps({
        "openai": "sk-openai-test-key",
        "claude": "sk-ant-claude-key"
    }))

    key = load_from_json(str(keys_file), "openai")
    assert key == "sk-openai-test-key"


def test_load_from_json_nested_keys(tmp_path):
    """Test loading nested keys with dot notation."""
    # Create test JSON file with nested structure
    keys_file = tmp_path / "keys.json"
    keys_file.write_text(json.dumps({
        "production": {
            "openai": "sk-prod-openai",
            "claude": "sk-prod-claude"
        },
        "development": {
            "openai": "sk-dev-openai"
        }
    }))

    key = load_from_json(str(keys_file), "production.openai")
    assert key == "sk-prod-openai"

    key = load_from_json(str(keys_file), "development.openai")
    assert key == "sk-dev-openai"


def test_load_from_json_whitespace_stripping(tmp_path):
    """Test that whitespace is stripped from loaded keys."""
    keys_file = tmp_path / "keys.json"
    keys_file.write_text(json.dumps({
        "openai": "  sk-test-key-with-spaces  "
    }))

    key = load_from_json(str(keys_file), "openai")
    assert key == "sk-test-key-with-spaces"


def test_load_from_json_missing_file():
    """Test loading from non-existent file."""
    with pytest.raises(FileNotFoundError, match="API key file not found"):
        load_from_json("/non/existent/path.json", "openai")


def test_load_from_json_missing_key(tmp_path):
    """Test loading non-existent key from file."""
    keys_file = tmp_path / "keys.json"
    keys_file.write_text(json.dumps({
        "openai": "sk-test-key"
    }))

    with pytest.raises(ValueError, match="Key 'claude' not found"):
        load_from_json(str(keys_file), "claude")


def test_load_from_json_missing_nested_key(tmp_path):
    """Test loading non-existent nested key."""
    keys_file = tmp_path / "keys.json"
    keys_file.write_text(json.dumps({
        "production": {
            "openai": "sk-test-key"
        }
    }))

    with pytest.raises(ValueError, match="Key 'production.claude' not found"):
        load_from_json(str(keys_file), "production.claude")


def test_load_from_json_invalid_json(tmp_path):
    """Test loading from file with invalid JSON."""
    keys_file = tmp_path / "keys.json"
    keys_file.write_text("{ invalid json }")

    with pytest.raises(ValueError, match="Invalid JSON"):
        load_from_json(str(keys_file), "openai")


def test_load_from_json_non_string_value(tmp_path):
    """Test loading when value is not a string."""
    keys_file = tmp_path / "keys.json"
    keys_file.write_text(json.dumps({
        "openai": 12345,  # Number instead of string
        "claude": ["list", "of", "values"]  # List instead of string
    }))

    with pytest.raises(ValueError, match="is not a string"):
        load_from_json(str(keys_file), "openai")

    with pytest.raises(ValueError, match="is not a string"):
        load_from_json(str(keys_file), "claude")


def test_load_from_json_empty_file(tmp_path):
    """Test loading from empty JSON file."""
    keys_file = tmp_path / "keys.json"
    keys_file.write_text("{}")

    with pytest.raises(ValueError, match="Key 'openai' not found"):
        load_from_json(str(keys_file), "openai")
