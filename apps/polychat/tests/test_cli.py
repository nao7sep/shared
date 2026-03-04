"""CLI behavior tests."""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from polychat.cli import main
from polychat import config as app_config
from polychat.session_manager import SessionManager
from test_helpers import make_app_config, make_profile


def _run_cli(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, argv: list[str]
):
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
    assert "ERROR: -p/--profile is required for init command" in out
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
    assert "ERROR: 'init' must be the first argument" in out
    assert "Usage: polychat init -p <profile-path>" in out
    assert not profile_path.exists()


def test_unknown_command_returns_error(monkeypatch, capsys):
    """Unknown commands should fail fast with usage guidance."""
    code, out, _err = _run_cli(monkeypatch, capsys, ["polychat", "unknown"])
    assert code == 1
    assert "ERROR: unknown command 'unknown'" in out
    assert "Supported commands: init" in out


def test_setup_command_runs_wizard_then_starts_repl(monkeypatch):
    """Successful setup should hand the new profile path into normal startup."""
    app_config_data = make_app_config()
    profile_path = "/tmp/polychat-profile.json"
    profile_data = make_profile(
        chats_dir="/tmp/chats",
        logs_dir="/tmp/logs",
    )
    monkeypatch.setattr(sys, "argv", ["polychat", "setup"])

    with (
        patch(
            "polychat.cli.setup_wizard.run_setup_wizard", return_value=profile_path
        ) as mock_wizard,
        patch(
            "polychat.cli.app_config.load_or_create_startup_config",
            return_value=SimpleNamespace(
                config=app_config_data,
                path="/tmp/config.json",
                messages=[],
            ),
        ),
        patch(
            "polychat.cli.prepare_ui_runtime",
            return_value=SimpleNamespace(notification_player=object()),
        ),
        patch(
            "polychat.cli.profile.load_profile", return_value=profile_data
        ) as mock_load_profile,
        patch.object(
            SessionManager,
            "load_system_prompt",
            return_value=(("system prompt", "@/prompts/system/default.txt"), None),
        ) as mock_load_prompt,
        patch("polychat.cli.build_run_log_path", return_value="/tmp/polychat.log"),
        patch("polychat.cli.setup_logging"),
        patch("polychat.cli.log_event"),
        patch("polychat.cli.repl_loop", new_callable=AsyncMock) as mock_repl_loop,
    ):
        main()

    mock_wizard.assert_called_once_with()
    mock_load_profile.assert_called_once()
    assert (
        Path(mock_load_profile.call_args.args[0]).resolve()
        == Path(profile_path).resolve()
    )
    mock_load_prompt.assert_called_once()
    assert mock_load_prompt.call_args.args[0] == profile_data
    assert (
        Path(mock_load_prompt.call_args.args[1]).resolve()
        == Path(profile_path).resolve()
    )
    mock_repl_loop.assert_awaited_once()
    assert mock_repl_loop.await_args.args[0] == app_config_data
    assert mock_repl_loop.await_args.args[2] == profile_data
    assert mock_repl_loop.await_args.args[6] == "@/prompts/system/default.txt"
    assert (
        Path(mock_repl_loop.await_args.args[7]).resolve()
        == Path(profile_path).resolve()
    )


def test_setup_command_exits_when_wizard_is_canceled(monkeypatch):
    """Canceled setup should stop before profile load or REPL startup."""
    monkeypatch.setattr(sys, "argv", ["polychat", "setup"])

    with (
        patch(
            "polychat.cli.setup_wizard.run_setup_wizard", return_value=None
        ) as mock_wizard,
        patch("polychat.cli.repl_loop", new_callable=AsyncMock) as mock_repl_loop,
        pytest.raises(SystemExit) as exc_info,
    ):
        main()

    assert exc_info.value.code == 1
    mock_wizard.assert_called_once_with()
    mock_repl_loop.assert_not_called()


def test_startup_creates_missing_app_config_before_loading_profile(monkeypatch):
    """Normal startup should create app config on first run before loading profile."""
    app_config_data = make_app_config()
    profile_path = "/tmp/polychat-profile.json"
    profile_data = make_profile(
        chats_dir="/tmp/chats",
        logs_dir="/tmp/logs",
    )
    call_order: list[str] = []
    monkeypatch.setattr(sys, "argv", ["polychat", "-p", profile_path])

    def _load_or_create_startup_config():
        call_order.append("config-startup")
        return SimpleNamespace(
            config=app_config_data,
            path="/tmp/polychat-config.json",
            messages=["Created app config: /tmp/polychat-config.json"],
        )

    def _prepare_ui_runtime(_config):
        call_order.append("ui-runtime")
        return SimpleNamespace(notification_player=object())

    def _load_profile(path: str):
        call_order.append("profile-load")
        return profile_data

    with (
        patch(
            "polychat.cli.app_config.load_or_create_startup_config",
            side_effect=_load_or_create_startup_config,
        ),
        patch("polychat.cli.prepare_ui_runtime", side_effect=_prepare_ui_runtime),
        patch("polychat.cli.profile.load_profile", side_effect=_load_profile),
        patch.object(
            SessionManager,
            "load_system_prompt",
            return_value=(("system prompt", "@/prompts/system/default.txt"), None),
        ),
        patch("polychat.cli.build_run_log_path", return_value="/tmp/polychat.log"),
        patch("polychat.cli.setup_logging"),
        patch("polychat.cli.log_event"),
        patch("polychat.cli.repl_loop", new_callable=AsyncMock),
    ):
        main()

    assert call_order == ["config-startup", "ui-runtime", "profile-load"]


def test_startup_creation_message_owns_trailing_blank_before_banner(
    monkeypatch,
    capsys,
):
    """Pre-banner config creation output should separate itself from the banner."""
    app_config_data = make_app_config()
    profile_path = "/tmp/polychat-profile.json"
    profile_data = make_profile(
        chats_dir="/tmp/chats",
        logs_dir="/tmp/logs",
    )
    monkeypatch.setattr(sys, "argv", ["polychat", "-p", profile_path])

    async def _fake_repl_loop(*_args, **_kwargs):
        print("BANNER")

    with (
        patch(
            "polychat.cli.app_config.load_or_create_startup_config",
            return_value=SimpleNamespace(
                config=app_config_data,
                path="/tmp/polychat-config.json",
                messages=["Created app config: /tmp/polychat-config.json"],
            ),
        ),
        patch(
            "polychat.cli.prepare_ui_runtime",
            return_value=SimpleNamespace(notification_player=object()),
        ),
        patch("polychat.cli.profile.load_profile", return_value=profile_data),
        patch.object(
            SessionManager,
            "load_system_prompt",
            return_value=(("system prompt", "@/prompts/system/default.txt"), None),
        ),
        patch("polychat.cli.build_run_log_path", return_value="/tmp/polychat.log"),
        patch("polychat.cli.setup_logging"),
        patch("polychat.cli.log_event"),
        patch("polychat.cli.repl_loop", side_effect=_fake_repl_loop),
    ):
        main()

    assert "Created app config: /tmp/polychat-config.json\n\nBANNER\n" in capsys.readouterr().out


def test_startup_exits_fast_when_app_config_is_invalid(monkeypatch, capsys):
    """Broken app config should stop startup before profile load."""
    monkeypatch.setattr(sys, "argv", ["polychat", "-p", "/tmp/polychat-profile.json"])

    with (
        patch(
            "polychat.cli.app_config.load_or_create_startup_config",
            side_effect=app_config.AppConfigStartupError(
                "App config file is invalid: /tmp/polychat-config.json: bad config"
            ),
        ),
        patch("polychat.cli.prepare_ui_runtime") as mock_prepare_ui_runtime,
        patch("polychat.cli.profile.load_profile") as mock_load_profile,
        pytest.raises(SystemExit) as exc_info,
    ):
        main()

    assert exc_info.value.code == 1
    assert (
        "ERROR: App config file is invalid: /tmp/polychat-config.json: bad config"
        in capsys.readouterr().out
    )
    mock_prepare_ui_runtime.assert_not_called()
    mock_load_profile.assert_not_called()


def test_startup_exits_fast_when_text_colors_are_invalid(monkeypatch, capsys):
    """Broken text colors should stop startup before notifications or profiles."""
    monkeypatch.setattr(sys, "argv", ["polychat", "-p", "/tmp/polychat-profile.json"])

    with (
        patch(
            "polychat.cli.app_config.load_or_create_startup_config",
            return_value=SimpleNamespace(
                config=make_app_config(
                    text_colors={
                        "user_input": "not-a-valid-style-token",
                        "cost_line": None,
                    }
                ),
                path="/tmp/polychat-config.json",
                messages=[],
            ),
        ),
        patch(
            "polychat.cli.prepare_ui_runtime",
            side_effect=ValueError("Invalid text color configuration"),
        ) as mock_prepare_ui_runtime,
        patch("polychat.cli.profile.load_profile") as mock_load_profile,
        pytest.raises(SystemExit) as exc_info,
    ):
        main()

    assert exc_info.value.code == 1
    assert (
        "ERROR: App config file is invalid: /tmp/polychat-config.json:"
        in capsys.readouterr().out
    )
    mock_prepare_ui_runtime.assert_called_once()
    mock_load_profile.assert_not_called()


def test_startup_exits_fast_when_profile_is_invalid(monkeypatch, capsys):
    """Broken profile should stop startup before entering the REPL."""
    monkeypatch.setattr(sys, "argv", ["polychat", "-p", "/tmp/polychat-profile.json"])

    with (
        patch(
            "polychat.cli.app_config.load_or_create_startup_config",
            return_value=SimpleNamespace(
                config=make_app_config(),
                path="/tmp/polychat-config.json",
                messages=[],
            ),
        ),
        patch(
            "polychat.cli.prepare_ui_runtime",
            return_value=SimpleNamespace(notification_player=object()),
        ),
        patch(
            "polychat.cli.profile.load_profile",
            side_effect=ValueError("bad profile"),
        ),
        patch("polychat.cli.repl_loop", new_callable=AsyncMock) as mock_repl_loop,
        pytest.raises(SystemExit) as exc_info,
    ):
        main()

    assert exc_info.value.code == 1
    expected_path = str(Path("/tmp/polychat-profile.json").resolve())
    assert (
        f"ERROR: Profile file is invalid: {expected_path}: bad profile"
        in capsys.readouterr().out
    )
    mock_repl_loop.assert_not_called()


def test_startup_exits_fast_when_notification_sound_is_invalid(monkeypatch, capsys):
    """Broken notification settings should stop startup before profile load."""
    monkeypatch.setattr(sys, "argv", ["polychat", "-p", "/tmp/polychat-profile.json"])

    with (
        patch(
            "polychat.cli.app_config.load_or_create_startup_config",
            return_value=SimpleNamespace(
                config=make_app_config(),
                path="/tmp/polychat-config.json",
                messages=[],
            ),
        ),
        patch(
            "polychat.cli.prepare_ui_runtime",
            side_effect=ValueError("bad sound"),
        ),
        patch("polychat.cli.profile.load_profile") as mock_load_profile,
        pytest.raises(SystemExit) as exc_info,
    ):
        main()

    assert exc_info.value.code == 1
    assert (
        "ERROR: App config file is invalid: /tmp/polychat-config.json: bad sound"
        in capsys.readouterr().out
    )
    mock_load_profile.assert_not_called()
