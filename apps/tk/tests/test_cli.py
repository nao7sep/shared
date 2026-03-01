"""Tests for CLI bootstrap and startup wiring."""

from datetime import datetime as real_datetime
import sys

import pytest

from tk import cli
from tk.errors import AppError
from tk.models import Profile, TaskStore


def _make_profile(tmp_path) -> Profile:
    return Profile(
        timezone="Asia/Tokyo",
        subjective_day_start="04:00:00",
        data_path=str(tmp_path / "tasks.json"),
        output_path=str(tmp_path / "TODO.md"),
        auto_sync=True,
        sync_on_exit=False,
    )


class TestMain:
    """Test CLI main entry point."""

    def test_init_success_creates_profile_files(self, tmp_path, monkeypatch, capsys):
        """Test that init creates profile, task storage, and TODO output."""
        profile_path = tmp_path / "profile.json"
        prof = _make_profile(tmp_path)
        captured: dict[str, object] = {}

        monkeypatch.setattr(sys, "argv", ["tk", "init", "--profile", str(profile_path)])
        monkeypatch.setattr(cli.profile, "create_profile", lambda path: prof)

        def fake_save_tasks(path, tasks_data):
            captured["save"] = (path, tasks_data)

        def fake_generate_todo(tasks, output_path):
            captured["todo"] = (tasks, output_path)

        monkeypatch.setattr(cli.data, "save_tasks", fake_save_tasks)
        monkeypatch.setattr(cli.markdown, "generate_todo", fake_generate_todo)

        cli.main()

        output = capsys.readouterr().out
        assert f"Profile created: {profile_path}" in output
        assert captured["save"][0] == prof.data_path
        assert isinstance(captured["save"][1], TaskStore)
        assert captured["todo"] == ([], prof.output_path)

    def test_init_app_error_exits_with_message(self, tmp_path, monkeypatch, capsys):
        """Test that init surfaces profile creation errors to the user."""
        profile_path = tmp_path / "profile.json"

        monkeypatch.setattr(sys, "argv", ["tk", "init", "-p", str(profile_path)])
        monkeypatch.setattr(
            cli.profile,
            "create_profile",
            lambda path: (_ for _ in ()).throw(AppError("Bad profile path")),
        )

        with pytest.raises(SystemExit) as exc_info:
            cli.main()

        output = capsys.readouterr().out
        assert exc_info.value.code == 1
        assert "ERROR: Bad profile path" in output

    def test_startup_loads_profile_and_enters_repl(self, tmp_path, monkeypatch, capsys):
        """Test that normal startup loads data, prints profile info, and starts REPL."""
        profile_path = tmp_path / "profile.json"
        prof = _make_profile(tmp_path)
        tasks_data = TaskStore()
        captured: dict[str, object] = {}
        fixed_now = real_datetime(2026, 2, 9, 10, 11, 12, tzinfo=cli.ZoneInfo("Asia/Tokyo"))

        class FakeDateTime:
            @staticmethod
            def now(tz):
                return fixed_now.astimezone(tz)

        monkeypatch.setattr(sys, "argv", ["tk", "--profile", str(profile_path)])
        monkeypatch.setattr(cli.profile, "load_profile", lambda path: prof)
        monkeypatch.setattr(cli.data, "load_tasks", lambda path: tasks_data)
        monkeypatch.setattr(cli, "datetime", FakeDateTime)

        def fake_repl(session):
            captured["session"] = session

        monkeypatch.setattr(cli, "repl", fake_repl)

        cli.main()

        output = capsys.readouterr().out
        assert "Profile Information:" in output
        assert "Current time: 2026-02-09 10:11:12" in output
        assert captured["session"].profile_path == str(profile_path)
        assert captured["session"].profile is prof
        assert captured["session"].tasks is tasks_data

    def test_startup_with_missing_profile_shows_guidance(self, tmp_path, monkeypatch, capsys):
        """Test startup guidance when the profile file does not exist."""
        profile_path = tmp_path / "missing.json"

        monkeypatch.setattr(sys, "argv", ["tk", "--profile", str(profile_path)])
        monkeypatch.setattr(
            cli.profile,
            "load_profile",
            lambda path: (_ for _ in ()).throw(FileNotFoundError()),
        )

        with pytest.raises(SystemExit) as exc_info:
            cli.main()

        output = capsys.readouterr().out
        assert exc_info.value.code == 1
        assert f"ERROR: Profile not found: {profile_path}" in output
        assert f"Create it with: tk init --profile {profile_path}" in output

    def test_startup_without_profile_exits_with_usage_hint(self, monkeypatch, capsys):
        """Test startup guidance when no profile flag is provided."""
        monkeypatch.setattr(sys, "argv", ["tk"])

        with pytest.raises(SystemExit) as exc_info:
            cli.main()

        output = capsys.readouterr().out
        assert exc_info.value.code == 1
        assert "ERROR: No profile specified" in output
        assert "tk init --profile <path>" in output
