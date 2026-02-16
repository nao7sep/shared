"""Tests for centralized AI limit resolution."""

from polychat.ai.limits import (
    resolve_profile_limits,
    resolve_request_limits,
    select_max_output_tokens,
)


def test_resolve_profile_limits_merges_default_provider_and_helper():
    profile = {
        "ai_limits": {
            "default": {
                "max_output_tokens": 900,
                "search_max_output_tokens": 1200,
            },
            "providers": {
                "claude": {
                    "max_output_tokens": 800,
                }
            },
            "helper": {
                "max_output_tokens": 300,
            },
        }
    }

    interactive = resolve_profile_limits(profile, "claude")
    helper = resolve_profile_limits(profile, "claude", helper=True)

    assert interactive["max_output_tokens"] == 800
    assert interactive["search_max_output_tokens"] == 1200

    assert helper["max_output_tokens"] == 300
    assert helper["search_max_output_tokens"] == 1200


def test_resolve_profile_limits_ignores_invalid_values():
    profile = {
        "ai_limits": {
            "default": {
                "max_output_tokens": 0,
                "search_max_output_tokens": -1,
            }
        }
    }

    limits = resolve_profile_limits(profile, "openai")
    assert limits["max_output_tokens"] is None
    assert limits["search_max_output_tokens"] is None


def test_select_max_output_tokens_prefers_search_override():
    limits = {
        "max_output_tokens": 1000,
        "search_max_output_tokens": 2000,
    }

    assert select_max_output_tokens(limits, search=False) == 1000
    assert select_max_output_tokens(limits, search=True) == 2000


def test_select_max_output_tokens_returns_none_when_unset():
    limits = {
        "max_output_tokens": None,
        "search_max_output_tokens": None,
    }
    assert select_max_output_tokens(limits, search=False) is None
    assert select_max_output_tokens(limits, search=True) is None


def test_resolve_request_limits_applies_claude_fallback_when_unset():
    limits = resolve_request_limits(profile={}, provider="claude", search=False)

    assert limits["max_output_tokens"] == 4096


def test_resolve_request_limits_applies_helper_overrides():
    profile = {
        "ai_limits": {
            "default": {"max_output_tokens": 1000},
            "helper": {
                "max_output_tokens": 250,
            },
        }
    }

    limits = resolve_request_limits(
        profile=profile,
        provider="openai",
        helper=True,
        search=False,
    )

    assert limits["max_output_tokens"] == 250
