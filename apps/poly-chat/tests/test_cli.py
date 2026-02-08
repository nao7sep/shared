"""Tests for CLI helper logic."""

from poly_chat.cli import resolve_strict_system_prompt


def test_resolve_strict_system_prompt_uses_profile_when_no_cli_override():
    assert resolve_strict_system_prompt({"system_prompt_strict": True}, None) is True
    assert resolve_strict_system_prompt({"system_prompt_strict": False}, None) is False
    assert resolve_strict_system_prompt({}, None) is False


def test_resolve_strict_system_prompt_honors_cli_override_both_directions():
    assert resolve_strict_system_prompt({"system_prompt_strict": True}, False) is False
    assert resolve_strict_system_prompt({"system_prompt_strict": False}, True) is True
