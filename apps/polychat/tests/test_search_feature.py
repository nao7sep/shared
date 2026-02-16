"""Tests for web search feature."""

import pytest
from polychat.models import provider_supports_search, SEARCH_SUPPORTED_PROVIDERS
from polychat.app_state import SessionState


def test_search_supported_providers():
    """Test that the correct providers support search."""
    assert provider_supports_search("openai") is True
    assert provider_supports_search("claude") is True
    assert provider_supports_search("gemini") is True
    assert provider_supports_search("grok") is True
    assert provider_supports_search("perplexity") is True
    assert provider_supports_search("mistral") is False
    assert provider_supports_search("deepseek") is False


def test_search_supported_providers_set():
    """Test that SEARCH_SUPPORTED_PROVIDERS contains the right providers."""
    assert SEARCH_SUPPORTED_PROVIDERS == {"openai", "claude", "gemini", "grok", "perplexity"}


def test_session_state_search_mode_default():
    """Test that search_mode defaults to False."""
    # Create a minimal state for testing
    state = SessionState(
        current_ai="openai",
        current_model="gpt-5",
        helper_ai="openai",
        helper_model="gpt-5-mini",
        profile={},
        chat={},
    )
    assert state.search_mode is False


def test_session_state_search_mode_can_be_set():
    """Test that search_mode can be set to True."""
    state = SessionState(
        current_ai="openai",
        current_model="gpt-5",
        helper_ai="openai",
        helper_model="gpt-5-mini",
        profile={},
        chat={},
    )
    state.search_mode = True
    assert state.search_mode is True


def test_session_state_both_modes_can_be_enabled():
    """Test that both secret_mode and search_mode can be enabled simultaneously."""
    state = SessionState(
        current_ai="openai",
        current_model="gpt-5",
        helper_ai="openai",
        helper_model="gpt-5-mini",
        profile={},
        chat={},
    )
    state.secret_mode = True
    state.search_mode = True
    assert state.secret_mode is True
    assert state.search_mode is True


def test_session_state_modes_are_independent():
    """Test that secret_mode and search_mode are independent."""
    state = SessionState(
        current_ai="openai",
        current_model="gpt-5",
        helper_ai="openai",
        helper_model="gpt-5-mini",
        profile={},
        chat={},
    )

    # Enable search, verify secret is still off
    state.search_mode = True
    assert state.search_mode is True
    assert state.secret_mode is False

    # Enable secret, verify search stays on
    state.secret_mode = True
    assert state.secret_mode is True
    assert state.search_mode is True

    # Disable search, verify secret stays on
    state.search_mode = False
    assert state.search_mode is False
    assert state.secret_mode is True
