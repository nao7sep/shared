"""Tests for typed runtime profile model."""

from polychat.domain.profile import RuntimeProfile


def test_runtime_profile_from_dict_parses_required_fields() -> None:
    raw = {
        "default_ai": "claude",
        "models": {"claude": "claude-haiku-4-5"},
        "timeout": 300,
        "input_mode": "quick",
        "system_prompt": "/tmp/system.txt",
        "chats_dir": "/tmp/chats",
        "logs_dir": "/tmp/logs",
        "api_keys": {"claude": {"type": "env", "key": "CLAUDE_API_KEY"}},
    }

    profile = RuntimeProfile.from_dict(raw)
    payload = profile.to_dict()

    assert payload["default_ai"] == "claude"
    assert payload["models"]["claude"] == "claude-haiku-4-5"
    assert payload["timeout"] == 300
    assert payload["api_keys"]["claude"]["type"] == "env"


def test_runtime_profile_roundtrip_preserves_extra_fields() -> None:
    raw = {
        "default_ai": "claude",
        "models": {"claude": "claude-haiku-4-5"},
        "timeout": 300,
        "input_mode": "quick",
        "chats_dir": "/tmp/chats",
        "logs_dir": "/tmp/logs",
        "api_keys": {"claude": {"type": "env", "key": "CLAUDE_API_KEY"}},
        "custom_setting": "keep-me",
    }

    profile = RuntimeProfile.from_dict(raw)
    payload = profile.to_dict()

    assert payload["custom_setting"] == "keep-me"
