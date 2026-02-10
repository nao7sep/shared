"""Tests for secret mode + search mode combinations."""

import pytest
from poly_chat.session_manager import SessionManager


@pytest.fixture
def session_manager():
    """Create a session manager for testing."""
    profile = {
        "default_ai": "openai",
        "models": {"openai": "gpt-5"},
        "timeout": 30,
    }
    chat = {"messages": [], "metadata": {}}
    return SessionManager(
        profile=profile,
        current_ai="openai",
        current_model="gpt-5",
        helper_ai="openai",
        helper_model="gpt-5-mini",
        chat=chat,
    )


def test_session_manager_both_modes_enabled(session_manager):
    """Test that SessionManager can enable both secret and search modes."""
    session_manager.secret_mode = True
    session_manager.search_mode = True

    assert session_manager.secret_mode is True
    assert session_manager.search_mode is True


def test_session_manager_modes_independent(session_manager):
    """Test that modes can be toggled independently."""
    # Enable only search
    session_manager.search_mode = True
    assert session_manager.search_mode is True
    assert session_manager.secret_mode is False

    # Enable only secret
    session_manager.search_mode = False
    session_manager.secret_mode = True
    assert session_manager.secret_mode is True
    assert session_manager.search_mode is False

    # Enable both
    session_manager.search_mode = True
    assert session_manager.secret_mode is True
    assert session_manager.search_mode is True


def test_session_manager_clear_chat_clears_search_mode(session_manager):
    """Test that clearing chat state also clears search mode."""
    session_manager.search_mode = True
    session_manager.secret_mode = True

    session_manager._clear_chat_scoped_state()

    assert session_manager.search_mode is False
    assert session_manager.secret_mode is False


def test_session_manager_to_dict_includes_both_modes(session_manager):
    """Test that to_dict includes both modes."""
    session_manager.secret_mode = True
    session_manager.search_mode = True

    state_dict = session_manager.to_dict()

    assert "secret_mode" in state_dict
    assert "search_mode" in state_dict
    assert state_dict["secret_mode"] is True
    assert state_dict["search_mode"] is True


def test_mode_combination_case1_both_persistent(session_manager):
    """Test Case 1: /secret on + /search on (both persistent)."""
    # Simulate /secret on
    session_manager.secret_mode = True
    # Simulate /search on
    session_manager.search_mode = True

    # Verify both modes are active
    assert session_manager.secret_mode is True
    assert session_manager.search_mode is True

    # Verify state is correct for message handling
    state_dict = session_manager.to_dict()
    assert state_dict["secret_mode"] is True
    assert state_dict["search_mode"] is True


def test_unsupported_provider_with_search_mode(session_manager):
    """Test that search mode can be set even with unsupported provider (validation happens at use time)."""
    from poly_chat.models import provider_supports_search

    # Switch to unsupported provider
    session_manager._state.current_ai = "mistral"

    # Search mode can be set (validation happens when sending message)
    session_manager.search_mode = True
    assert session_manager.search_mode is True

    # But provider doesn't support search
    assert provider_supports_search(session_manager.current_ai) is False
