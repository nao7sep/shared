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


def test_runtime_profile_to_dict_orders_known_sections() -> None:
    raw = {
        "default_ai": "claude",
        "default_helper_ai": "openai",
        "models": {
            "claude": "claude-haiku-4-5",
            "openai": "gpt-5-mini",
        },
        "timeout": 300,
        "input_mode": "quick",
        "system_prompt": "/tmp/system.txt",
        "title_prompt": "/tmp/title.txt",
        "summary_prompt": "/tmp/summary.txt",
        "safety_prompt": "/tmp/safety.txt",
        "chats_dir": "/tmp/chats",
        "logs_dir": "/tmp/logs",
        "api_keys": {"claude": {"type": "env", "key": "CLAUDE_API_KEY"}},
        "ai_limits": {
            "default": {"max_output_tokens": None, "search_max_output_tokens": None},
        },
        "custom_setting": "keep-me",
    }

    profile = RuntimeProfile.from_dict(raw)
    payload = profile.to_dict()

    assert list(payload.keys()) == [
        "default_ai",
        "default_helper_ai",
        "models",
        "timeout",
        "input_mode",
        "system_prompt",
        "title_prompt",
        "summary_prompt",
        "safety_prompt",
        "chats_dir",
        "logs_dir",
        "api_keys",
        "ai_limits",
        "custom_setting",
    ]


def test_runtime_profile_to_dict_orders_nested_key_config_and_limits() -> None:
    raw = {
        "default_ai": "claude",
        "models": {"claude": "claude-haiku-4-5"},
        "timeout": 300,
        "input_mode": "quick",
        "chats_dir": "/tmp/chats",
        "logs_dir": "/tmp/logs",
        "api_keys": {
            "claude": {
                "key": "claude",
                "path": "/tmp/api-keys.json",
                "type": "json",
                "custom": "keep-me",
            },
            "openai": {
                "key": "OPENAI_API_KEY",
                "type": "env",
            },
            "grok": {
                "value": "xai-test",
                "type": "direct",
            },
            "perplexity": {
                "account": "perplexity-api-key",
                "service": "polychat",
                "type": "keychain",
            },
        },
        "ai_limits": {
            "helper": {
                "search_max_output_tokens": 256,
                "max_output_tokens": 128,
                "custom": "helper-extra",
            },
            "providers": {
                "claude": {
                    "search_max_output_tokens": 512,
                    "max_output_tokens": 256,
                    "custom": "provider-extra",
                }
            },
            "default": {
                "search_max_output_tokens": 1024,
                "max_output_tokens": 512,
                "custom": "default-extra",
            },
            "extra_section": "keep-me",
        },
    }

    profile = RuntimeProfile.from_dict(raw)
    payload = profile.to_dict()

    assert list(payload["api_keys"]["claude"].keys()) == [
        "type",
        "path",
        "key",
        "custom",
    ]
    assert list(payload["api_keys"]["openai"].keys()) == ["type", "key"]
    assert list(payload["api_keys"]["grok"].keys()) == ["type", "value"]
    assert list(payload["api_keys"]["perplexity"].keys()) == [
        "type",
        "service",
        "account",
    ]

    assert list(payload["ai_limits"].keys()) == [
        "default",
        "providers",
        "helper",
        "extra_section",
    ]
    assert list(payload["ai_limits"]["default"].keys()) == [
        "max_output_tokens",
        "search_max_output_tokens",
        "custom",
    ]
    assert list(payload["ai_limits"]["providers"]["claude"].keys()) == [
        "max_output_tokens",
        "search_max_output_tokens",
        "custom",
    ]
    assert list(payload["ai_limits"]["helper"].keys()) == [
        "max_output_tokens",
        "search_max_output_tokens",
        "custom",
    ]


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
