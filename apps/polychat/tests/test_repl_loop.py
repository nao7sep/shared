"""Tests for REPL prompt session construction."""

from unittest.mock import patch

from prompt_toolkit.history import DummyHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.lexers import SimpleLexer
from prompt_toolkit.styles import Style

from polychat.repl.loop import create_prompt_session
from polychat.session_manager import SessionManager
from test_helpers import make_app_config, make_profile


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
    app_config = make_app_config()
    style = Style.from_dict({"user-input": "ansicyan"})

    with (
        patch("polychat.repl.loop.build_interactive_style", return_value=style) as mock_build_style,
        patch("polychat.repl.loop.PromptSession", return_value="session") as mock_prompt_session,
    ):
        result = create_prompt_session(manager, app_config)

    assert result == "session"
    mock_build_style.assert_called_once_with(app_config)
    kwargs = mock_prompt_session.call_args.kwargs
    assert isinstance(kwargs["history"], DummyHistory)
    assert isinstance(kwargs["key_bindings"], KeyBindings)
    assert kwargs["multiline"] is True
    assert kwargs["style"] is style
    assert isinstance(kwargs["lexer"], SimpleLexer)
    assert kwargs["lexer"].style == "class:user-input"
