"""CLI behavior tests."""

import sys

import pytest

from polychat.cli import main


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
