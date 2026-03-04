"""Tests for REPL prompt session construction."""

from unittest.mock import patch

from prompt_toolkit.history import DummyHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.lexers import SimpleLexer
from prompt_toolkit.styles import Style

from polychat.repl.loop import create_prompt_session, print_startup_banner
from polychat.session_manager import SessionManager
from polychat.ui.segments import begin_output_segment, reset_output_segments
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


def test_print_startup_banner_has_no_leading_blank_when_first_segment(
    capsys,
) -> None:
    """The first startup banner segment should not emit a leading blank line."""
    reset_output_segments()
    profile = make_profile(
        chats_dir="/test/chats",
        logs_dir="/test/logs",
    )
    manager = SessionManager(
        profile=profile,
        current_ai="claude",
        current_model="claude-haiku-4-5",
        helper_ai="claude",
        helper_model="claude-haiku-4-5",
        profile_path="/test/profile.json",
        log_file="/test/polychat.log",
    )

    print_startup_banner(manager, profile, None)

    output = capsys.readouterr().out
    assert not output.startswith("\n")
    assert "PolyChat" in output


def test_print_startup_banner_emits_leading_blank_when_not_first_segment(
    capsys,
) -> None:
    """Later startup banners should own the blank line before themselves."""
    reset_output_segments()
    profile = make_profile(
        chats_dir="/test/chats",
        logs_dir="/test/logs",
    )
    manager = SessionManager(
        profile=profile,
        current_ai="claude",
        current_model="claude-haiku-4-5",
        helper_ai="claude",
        helper_model="claude-haiku-4-5",
        profile_path="/test/profile.json",
        log_file="/test/polychat.log",
    )

    begin_output_segment()
    print("PREVIOUS")
    print_startup_banner(manager, profile, None)

    output = capsys.readouterr().out
    assert output.startswith("PREVIOUS\n\n")
    assert "PolyChat" in output
