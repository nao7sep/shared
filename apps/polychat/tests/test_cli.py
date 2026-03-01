"""CLI behavior tests."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from polychat.cli import main
from polychat.session_manager import SessionManager
from test_helpers import make_profile


def _run_cli(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, argv: list[str]):
    """Run CLI main() with a patched argv and capture exit code/stdout/stderr."""
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit) as exc_info:
        main()
    captured = capsys.readouterr()
    return exc_info.value.code, captured.out, captured.err


def test_init_requires_profile_option(monkeypatch, capsys):
    """`polychat init` must require explicit -p/--profile."""
    code, out, _err = _run_cli(monkeypatch, capsys, ["polychat", "init"])
    assert code == 1
    assert "Error: -p/--profile is required for init command" in out
    assert "Usage: polychat init -p <profile-path>" in out


def test_init_rejects_legacy_positional_profile_path(monkeypatch, capsys, tmp_path):
    """Legacy positional init syntax should fail (must use -p)."""
    legacy_path = tmp_path / "legacy-profile.json"
    code, _out, err = _run_cli(
        monkeypatch,
        capsys,
        ["polychat", "init", str(legacy_path)],
    )
    assert code == 2
    assert "unrecognized arguments" in err


def test_init_creates_profile_with_profile_option(monkeypatch, capsys, tmp_path):
    """`polychat init -p <path>` should create the profile template."""
    profile_path = tmp_path / "new-profile.json"
    code, out, _err = _run_cli(
        monkeypatch,
        capsys,
        ["polychat", "init", "-p", str(profile_path)],
    )
    assert code == 0
    assert profile_path.exists()
    assert "Template profile created successfully!" in out


def test_init_must_be_first_positional_token(monkeypatch, capsys, tmp_path):
    """`init` must be the first positional argument."""
    profile_path = tmp_path / "out-of-order.json"
    code, out, _err = _run_cli(
        monkeypatch,
        capsys,
        ["polychat", "-p", str(profile_path), "init"],
    )
    assert code == 1
    assert "Error: 'init' must be the first argument" in out
    assert "Usage: polychat init -p <profile-path>" in out
    assert not profile_path.exists()


def test_unknown_command_returns_error(monkeypatch, capsys):
    """Unknown commands should fail fast with usage guidance."""
    code, out, _err = _run_cli(monkeypatch, capsys, ["polychat", "unknown"])
    assert code == 1
    assert "Error: unknown command 'unknown'" in out
    assert "Supported commands: init" in out


def test_setup_command_runs_wizard_then_starts_repl(monkeypatch):
    """Successful setup should hand the new profile path into normal startup."""
    profile_path = "/tmp/polychat-profile.json"
    profile_data = make_profile(
        chats_dir="/tmp/chats",
        logs_dir="/tmp/logs",
    )
    monkeypatch.setattr(sys, "argv", ["polychat", "setup"])

    with (
        patch("polychat.cli.setup_wizard.run_setup_wizard", return_value=profile_path) as mock_wizard,
        patch("polychat.cli.profile.load_profile", return_value=profile_data) as mock_load_profile,
        patch.object(
            SessionManager,
            "load_system_prompt",
            return_value=("system prompt", "@/prompts/system/default.txt", None),
        ) as mock_load_prompt,
        patch("polychat.cli.build_run_log_path", return_value="/tmp/polychat.log"),
        patch("polychat.cli.setup_logging"),
        patch("polychat.cli.log_event"),
        patch("polychat.cli.repl_loop", new_callable=AsyncMock) as mock_repl_loop,
    ):
        main()

    mock_wizard.assert_called_once_with()
    mock_load_profile.assert_called_once()
    assert Path(mock_load_profile.call_args.args[0]).resolve() == Path(profile_path).resolve()
    mock_load_prompt.assert_called_once()
    assert mock_load_prompt.call_args.args[0] == profile_data
    assert Path(mock_load_prompt.call_args.args[1]).resolve() == Path(profile_path).resolve()
    mock_repl_loop.assert_awaited_once()
    assert mock_repl_loop.await_args.args[0] == profile_data
    assert mock_repl_loop.await_args.args[4] == "@/prompts/system/default.txt"
    assert Path(mock_repl_loop.await_args.args[5]).resolve() == Path(profile_path).resolve()


def test_setup_command_exits_when_wizard_is_cancelled(monkeypatch):
    """Cancelled setup should stop before profile load or REPL startup."""
    monkeypatch.setattr(sys, "argv", ["polychat", "setup"])

    with (
        patch("polychat.cli.setup_wizard.run_setup_wizard", return_value=None) as mock_wizard,
        patch("polychat.cli.repl_loop", new_callable=AsyncMock) as mock_repl_loop,
        pytest.raises(SystemExit) as exc_info,
    ):
        main()

    assert exc_info.value.code == 1
    mock_wizard.assert_called_once_with()
    mock_repl_loop.assert_not_called()
