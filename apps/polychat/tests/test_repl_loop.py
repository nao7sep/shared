"""Tests for REPL prompt session construction."""

from unittest.mock import patch

from prompt_toolkit.history import DummyHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.lexers import SimpleLexer

from polychat.repl.loop import create_prompt_session
from polychat.ui.theme import POLYCHAT_STYLE
from polychat.session_manager import SessionManager
from test_helpers import make_profile


def test_create_prompt_session_applies_theme_and_input_lexer() -> None:
    """Prompt sessions should style live user input without affecting output."""
    manager = SessionManager(
        profile=make_profile(
            chats_dir="/test/chats",
            logs_dir="/test/logs",
        ),
        current_ai="claude",
        current_model="claude-haiku-4-5",
    )

    with patch("polychat.repl.loop.PromptSession", return_value="session") as mock_prompt_session:
        result = create_prompt_session(manager)

    assert result == "session"
    kwargs = mock_prompt_session.call_args.kwargs
    assert isinstance(kwargs["history"], DummyHistory)
    assert isinstance(kwargs["key_bindings"], KeyBindings)
    assert kwargs["multiline"] is True
    assert kwargs["style"] is POLYCHAT_STYLE
    assert isinstance(kwargs["lexer"], SimpleLexer)
    assert kwargs["lexer"].style == "class:user-input"
