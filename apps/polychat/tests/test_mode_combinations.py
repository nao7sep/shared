"""Tests for secret mode + search mode combinations."""

import pytest

from polychat.domain.chat import ChatDocument
from polychat.session_manager import SessionManager
from test_helpers import make_profile


@pytest.fixture
def session_manager():
    """Create a session manager for testing."""
    return SessionManager(
        profile=make_profile(
            default_ai="openai",
            models={"openai": "gpt-5"},
        ),
        current_ai="openai",
        current_model="gpt-5",
        helper_ai="openai",
        helper_model="gpt-5-mini",
        chat=ChatDocument.empty(),
    )


def test_session_manager_both_modes_enabled(session_manager):
    """SessionManager can enable secret and search modes."""
    session_manager.secret_mode = True
    session_manager.search_mode = True

    assert session_manager.secret_mode is True
    assert session_manager.search_mode is True


def test_session_manager_modes_independent(session_manager):
    """Modes can be toggled independently."""
    session_manager.search_mode = True
    assert session_manager.search_mode is True
    assert session_manager.secret_mode is False

    session_manager.search_mode = False
    session_manager.secret_mode = True
    assert session_manager.secret_mode is True
    assert session_manager.search_mode is False


def test_session_manager_clear_chat_clears_modes(session_manager):
    """Clearing chat state also clears chat-scoped modes."""
    session_manager.search_mode = True
    session_manager.secret_mode = True

    session_manager._clear_chat_scoped_state()

    assert session_manager.search_mode is False
    assert session_manager.secret_mode is False


def test_session_manager_to_dict_includes_modes(session_manager):
    """to_dict includes secret/search mode flags."""
    session_manager.secret_mode = True
    session_manager.search_mode = True

    state_dict = session_manager.to_dict()

    assert "secret_mode" in state_dict
    assert "search_mode" in state_dict
    assert state_dict["secret_mode"] is True
    assert state_dict["search_mode"] is True


def test_mode_combination_case1_both_persistent(session_manager):
    """Case 1: /secret on + /search on (both persistent)."""
    session_manager.secret_mode = True
    session_manager.search_mode = True

    assert session_manager.secret_mode is True
    assert session_manager.search_mode is True

    state_dict = session_manager.to_dict()
    assert state_dict["secret_mode"] is True
    assert state_dict["search_mode"] is True


def test_unsupported_provider_with_search_mode(session_manager):
    """Search mode can be set even with unsupported provider."""
    from polychat.ai.capabilities import provider_supports_search

    session_manager._state.current_ai = "mistral"

    session_manager.search_mode = True
    assert session_manager.search_mode is True

    assert provider_supports_search(session_manager.current_ai) is False
