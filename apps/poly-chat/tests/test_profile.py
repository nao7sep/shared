"""Tests for profile module."""

import json
import pytest
from pathlib import Path
from poly_chat.profile import (
    map_path,
    load_profile,
    validate_profile,
    create_profile,
)


def test_map_path_tilde_with_subpath():
    """Test mapping tilde with subpath."""
    result = map_path("~/test/path")
    expected = str(Path.home() / "test/path")
    assert result == expected


def test_map_path_tilde_alone():
    """Test mapping tilde alone."""
    result = map_path("~")
    expected = str(Path.home())
    assert result == expected


def test_map_path_at_with_subpath():
    """Test mapping @ with subpath."""
    result = map_path("@/test/path")
    # App root is where pyproject.toml is (poly-chat/)
    assert result.endswith("test/path")
    assert "poly-chat" in result


def test_map_path_at_alone():
    """Test mapping @ alone."""
    result = map_path("@")
    # App root is where pyproject.toml is (poly-chat/)
    assert "poly-chat" in result


def test_map_path_absolute():
    """Test mapping absolute path."""
    abs_path = "/absolute/path/to/file"
    result = map_path(abs_path)
    assert result == abs_path


def test_map_path_relative_error():
    """Test that relative paths raise ValueError."""
    with pytest.raises(ValueError, match="Relative paths without prefix are not supported"):
        map_path("relative/path")


def test_map_path_relative_no_slash_error():
    """Test that relative path without slash raises ValueError."""
    with pytest.raises(ValueError, match="Relative paths without prefix are not supported"):
        map_path("file.txt")


def test_load_profile_nonexistent(tmp_path):
    """Test loading non-existent profile raises error."""
    profile_path = tmp_path / "nonexistent.json"

    with pytest.raises(FileNotFoundError, match="Profile not found"):
        load_profile(str(profile_path))


def test_load_profile_invalid_json(tmp_path):
    """Test loading profile with invalid JSON."""
    profile_path = tmp_path / "invalid.json"
    profile_path.write_text("{ invalid json }")

    with pytest.raises(json.JSONDecodeError):
        load_profile(str(profile_path))


def test_load_profile_missing_required_field(tmp_path):
    """Test loading profile with missing required field."""
    profile_path = tmp_path / "missing.json"

    # Missing "models" field
    profile_data = {
        "default_ai": "claude",
        "chats_dir": "~/chats",
        "log_dir": "~/logs",
        "api_keys": {}
    }

    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(profile_data, f)

    with pytest.raises(ValueError, match="Profile missing required fields"):
        load_profile(str(profile_path))


def test_load_profile_valid(tmp_path):
    """Test loading valid profile."""
    profile_path = tmp_path / "valid.json"
    chats_dir = tmp_path / "chats"
    log_dir = tmp_path / "logs"

    profile_data = {
        "default_ai": "claude",
        "models": {
            "claude": "claude-haiku-4-5",
            "openai": "gpt-5-mini"
        },
        "timeout": 30,
        "input_mode": "quick",
        "system_prompt": "@/system-prompts/default.txt",
        "chats_dir": str(chats_dir),
        "log_dir": str(log_dir),
        "api_keys": {
            "claude": {
                "type": "env",
                "key": "CLAUDE_API_KEY"
            }
        }
    }

    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(profile_data, f)

    profile = load_profile(str(profile_path))

    assert profile["default_ai"] == "claude"
    assert profile["models"]["claude"] == "claude-haiku-4-5"
    assert profile["chats_dir"] == str(chats_dir)
    assert profile["log_dir"] == str(log_dir)


def test_load_profile_maps_tilde_paths(tmp_path):
    """Test that load_profile maps tilde paths."""
    profile_path = tmp_path / "tilde.json"

    profile_data = {
        "default_ai": "claude",
        "models": {"claude": "claude-haiku-4-5"},
        "timeout": 30,
        "input_mode": "quick",
        "system_prompt": "~/system-prompt.txt",
        "chats_dir": "~/chats",
        "log_dir": "~/logs",
        "api_keys": {}
    }

    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(profile_data, f)

    profile = load_profile(str(profile_path))

    # Should map tilde to home directory
    assert profile["chats_dir"] == str(Path.home() / "chats")
    assert profile["log_dir"] == str(Path.home() / "logs")


def test_load_profile_maps_at_paths(tmp_path):
    """Test that load_profile maps @ paths."""
    profile_path = tmp_path / "at.json"

    profile_data = {
        "default_ai": "claude",
        "models": {"claude": "claude-haiku-4-5"},
        "timeout": 30,
        "input_mode": "quick",
        "system_prompt": "@/system-prompts/default.txt",
        "chats_dir": "@/chats",
        "log_dir": "@/logs",
        "api_keys": {}
    }

    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(profile_data, f)

    profile = load_profile(str(profile_path))

    # Should map @ to app root
    assert "poly-chat" in profile["chats_dir"]
    assert "poly-chat" in profile["log_dir"]
    assert "poly-chat" in profile["system_prompt"]


def test_load_profile_maps_json_api_key_path(tmp_path):
    """Test that load_profile maps JSON API key paths."""
    profile_path = tmp_path / "json_key.json"

    profile_data = {
        "default_ai": "claude",
        "models": {"claude": "claude-haiku-4-5"},
        "timeout": 30,
        "input_mode": "quick",
        "system_prompt": "@/system-prompts/default.txt",
        "chats_dir": "~/chats",
        "log_dir": "~/logs",
        "api_keys": {
            "claude": {
                "type": "json",
                "path": "~/.secrets/keys.json",
                "key": "claude"
            }
        }
    }

    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(profile_data, f)

    profile = load_profile(str(profile_path))

    # Should map tilde in JSON key path
    api_key_path = profile["api_keys"]["claude"]["path"]
    assert api_key_path == str(Path.home() / ".secrets/keys.json")


def test_load_profile_sets_default_timeout(tmp_path):
    """Test that load_profile sets default timeout if not present."""
    profile_path = tmp_path / "timeout.json"

    profile_data = {
        "default_ai": "claude",
        "models": {"claude": "claude-haiku-4-5"},
        "system_prompt": "@/system-prompts/default.txt",
        "chats_dir": "~/chats",
        "log_dir": "~/logs",
        "api_keys": {}
    }

    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(profile_data, f)

    profile = load_profile(str(profile_path))

    assert profile["timeout"] == 30


def test_validate_profile_missing_required_fields():
    """Test validation with missing required fields."""
    profile = {
        "default_ai": "claude",
        "models": {"claude": "claude-haiku-4-5"}
        # Missing: chats_dir, log_dir, api_keys
    }

    with pytest.raises(ValueError, match="Profile missing required fields"):
        validate_profile(profile)


def test_validate_profile_models_not_dict():
    """Test validation when models is not a dict."""
    profile = {
        "default_ai": "claude",
        "models": ["claude", "openai"],  # Should be dict
        "chats_dir": "~/chats",
        "log_dir": "~/logs",
        "api_keys": {}
    }

    with pytest.raises(ValueError, match="'models' must be a dictionary"):
        validate_profile(profile)


def test_validate_profile_models_empty():
    """Test validation when models is empty."""
    profile = {
        "default_ai": "claude",
        "models": {},  # Empty
        "chats_dir": "~/chats",
        "log_dir": "~/logs",
        "api_keys": {}
    }

    with pytest.raises(ValueError, match="'models' cannot be empty"):
        validate_profile(profile)


def test_validate_profile_default_ai_not_in_models():
    """Test validation when default_ai is not in models."""
    profile = {
        "default_ai": "gemini",  # Not in models
        "models": {"claude": "claude-haiku-4-5"},
        "chats_dir": "~/chats",
        "log_dir": "~/logs",
        "api_keys": {}
    }

    with pytest.raises(ValueError, match="default_ai 'gemini' not found in models"):
        validate_profile(profile)


def test_validate_profile_timeout_not_number():
    """Test validation when timeout is not a number."""
    profile = {
        "default_ai": "claude",
        "models": {"claude": "claude-haiku-4-5"},
        "timeout": "30",  # Should be number
        "chats_dir": "~/chats",
        "log_dir": "~/logs",
        "api_keys": {}
    }

    with pytest.raises(ValueError, match="'timeout' must be a number"):
        validate_profile(profile)


def test_validate_profile_timeout_negative():
    """Test validation when timeout is negative."""
    profile = {
        "default_ai": "claude",
        "models": {"claude": "claude-haiku-4-5"},
        "timeout": -10,
        "chats_dir": "~/chats",
        "log_dir": "~/logs",
        "api_keys": {}
    }

    with pytest.raises(ValueError, match="'timeout' cannot be negative"):
        validate_profile(profile)


def test_validate_profile_input_mode_valid():
    """Test validate_profile accepts valid input_mode values."""
    profile = {
        "default_ai": "claude",
        "models": {"claude": "claude-haiku-4-5"},
        "input_mode": "quick",
        "chats_dir": "~/chats",
        "log_dir": "~/logs",
        "api_keys": {}
    }
    validate_profile(profile)

    profile["input_mode"] = "compose"
    validate_profile(profile)


def test_validate_profile_input_mode_invalid_value():
    """Test validate_profile rejects unknown input_mode values."""
    profile = {
        "default_ai": "claude",
        "models": {"claude": "claude-haiku-4-5"},
        "input_mode": "invalid-mode",
        "chats_dir": "~/chats",
        "log_dir": "~/logs",
        "api_keys": {}
    }
    with pytest.raises(ValueError, match="'input_mode' must be 'quick' or 'compose'"):
        validate_profile(profile)


def test_validate_profile_input_mode_invalid_type():
    """Test validate_profile rejects non-string input_mode values."""
    profile = {
        "default_ai": "claude",
        "models": {"claude": "claude-haiku-4-5"},
        "input_mode": 123,
        "chats_dir": "~/chats",
        "log_dir": "~/logs",
        "api_keys": {}
    }
    with pytest.raises(ValueError, match="'input_mode' must be a string"):
        validate_profile(profile)


def test_validate_profile_timeout_zero_allowed():
    """Test validation allows timeout of zero."""
    profile = {
        "default_ai": "claude",
        "models": {"claude": "claude-haiku-4-5"},
        "timeout": 0,
        "input_mode": "quick",
        "chats_dir": "~/chats",
        "log_dir": "~/logs",
        "api_keys": {}
    }

    # Should not raise
    validate_profile(profile)


def test_validate_profile_api_keys_not_dict():
    """Test validation when api_keys is not a dict."""
    profile = {
        "default_ai": "claude",
        "models": {"claude": "claude-haiku-4-5"},
        "chats_dir": "~/chats",
        "log_dir": "~/logs",
        "api_keys": []  # Should be dict
    }

    with pytest.raises(ValueError, match="'api_keys' must be a dictionary"):
        validate_profile(profile)


def test_validate_profile_api_key_config_not_dict():
    """Test validation when API key config is not a dict."""
    profile = {
        "default_ai": "claude",
        "models": {"claude": "claude-haiku-4-5"},
        "chats_dir": "~/chats",
        "log_dir": "~/logs",
        "api_keys": {
            "claude": "sk-test-key"  # Should be dict
        }
    }

    with pytest.raises(ValueError, match="API key config for 'claude' must be a dictionary"):
        validate_profile(profile)


def test_validate_profile_api_key_missing_type():
    """Test validation when API key config missing type."""
    profile = {
        "default_ai": "claude",
        "models": {"claude": "claude-haiku-4-5"},
        "chats_dir": "~/chats",
        "log_dir": "~/logs",
        "api_keys": {
            "claude": {
                "key": "CLAUDE_API_KEY"
                # Missing "type"
            }
        }
    }

    with pytest.raises(ValueError, match="API key config for 'claude' missing 'type' field"):
        validate_profile(profile)


def test_validate_profile_api_key_env_missing_key():
    """Test validation when env type API key missing key field."""
    profile = {
        "default_ai": "claude",
        "models": {"claude": "claude-haiku-4-5"},
        "chats_dir": "~/chats",
        "log_dir": "~/logs",
        "api_keys": {
            "claude": {
                "type": "env"
                # Missing "key"
            }
        }
    }

    with pytest.raises(ValueError, match="API key config for 'claude' .* missing 'key' field"):
        validate_profile(profile)


def test_validate_profile_api_key_keychain_missing_service():
    """Test validation when keychain type missing service."""
    profile = {
        "default_ai": "claude",
        "models": {"claude": "claude-haiku-4-5"},
        "chats_dir": "~/chats",
        "log_dir": "~/logs",
        "api_keys": {
            "claude": {
                "type": "keychain",
                "account": "claude-api-key"
                # Missing "service"
            }
        }
    }

    with pytest.raises(ValueError, match="API key config for 'claude' .* missing 'service' field"):
        validate_profile(profile)


def test_validate_profile_api_key_keychain_missing_account():
    """Test validation when keychain type missing account."""
    profile = {
        "default_ai": "claude",
        "models": {"claude": "claude-haiku-4-5"},
        "chats_dir": "~/chats",
        "log_dir": "~/logs",
        "api_keys": {
            "claude": {
                "type": "keychain",
                "service": "poly-chat"
                # Missing "account"
            }
        }
    }

    with pytest.raises(ValueError, match="API key config for 'claude' .* missing 'account' field"):
        validate_profile(profile)


def test_validate_profile_api_key_json_missing_path():
    """Test validation when json type missing path."""
    profile = {
        "default_ai": "claude",
        "models": {"claude": "claude-haiku-4-5"},
        "chats_dir": "~/chats",
        "log_dir": "~/logs",
        "api_keys": {
            "claude": {
                "type": "json",
                "key": "claude"
                # Missing "path"
            }
        }
    }

    with pytest.raises(ValueError, match="API key config for 'claude' .* missing 'path' field"):
        validate_profile(profile)


def test_validate_profile_api_key_json_missing_key():
    """Test validation when json type missing key."""
    profile = {
        "default_ai": "claude",
        "models": {"claude": "claude-haiku-4-5"},
        "chats_dir": "~/chats",
        "log_dir": "~/logs",
        "api_keys": {
            "claude": {
                "type": "json",
                "path": "~/.secrets/keys.json"
                # Missing "key"
            }
        }
    }

    with pytest.raises(ValueError, match="API key config for 'claude' .* missing 'key' field"):
        validate_profile(profile)


def test_validate_profile_api_key_direct_missing_value():
    """Test validation when direct type missing value."""
    profile = {
        "default_ai": "claude",
        "models": {"claude": "claude-haiku-4-5"},
        "chats_dir": "~/chats",
        "log_dir": "~/logs",
        "api_keys": {
            "claude": {
                "type": "direct"
                # Missing "value"
            }
        }
    }

    with pytest.raises(ValueError, match="API key config for 'claude' .* missing 'value' field"):
        validate_profile(profile)


def test_validate_profile_api_key_unknown_type():
    """Test validation when API key has unknown type."""
    profile = {
        "default_ai": "claude",
        "models": {"claude": "claude-haiku-4-5"},
        "chats_dir": "~/chats",
        "log_dir": "~/logs",
        "api_keys": {
            "claude": {
                "type": "unknown_type",
                "key": "test"
            }
        }
    }

    with pytest.raises(ValueError, match="API key config for 'claude' has unknown type 'unknown_type'"):
        validate_profile(profile)


def test_validate_profile_valid_all_api_key_types():
    """Test validation with all valid API key types."""
    profile = {
        "default_ai": "claude",
        "models": {
            "claude": "claude-haiku-4-5",
            "openai": "gpt-5-mini",
            "gemini": "gemini-3-flash-preview",
            "grok": "grok-4-1-fast"
        },
        "timeout": 60,
        "input_mode": "quick",
        "chats_dir": "~/chats",
        "log_dir": "~/logs",
        "api_keys": {
            "claude": {
                "type": "env",
                "key": "CLAUDE_API_KEY"
            },
            "openai": {
                "type": "keychain",
                "service": "poly-chat",
                "account": "openai-api-key"
            },
            "gemini": {
                "type": "json",
                "path": "~/.secrets/keys.json",
                "key": "gemini"
            },
            "grok": {
                "type": "direct",
                "value": "xai-test-key"
            }
        }
    }

    # Should not raise
    validate_profile(profile)


def test_create_profile_template_uses_inline_prompt_and_mixed_api_key_examples(tmp_path):
    """Generated template should be directly useful and avoid companion API-key files."""
    profile_path = tmp_path / "poly-chat-profile.json"

    created_profile, _messages = create_profile(str(profile_path))

    assert created_profile["system_prompt"] == {
        "type": "text",
        "content": "You are a helpful assistant."
    }
    assert created_profile["chats_dir"] == str(profile_path.parent / "chats")
    assert created_profile["log_dir"] == str(profile_path.parent / "logs")
    assert created_profile["api_keys"]["openai"] == {
        "type": "env",
        "key": "OPENAI_API_KEY",
    }
    assert created_profile["api_keys"]["claude"] == {
        "type": "keychain",
        "service": "poly-chat",
        "account": "claude-api-key",
    }
    assert created_profile["api_keys"]["gemini"]["type"] == "json"
    assert created_profile["api_keys"]["grok"]["type"] == "direct"
    assert not (profile_path.parent / "api-keys.json").exists()
