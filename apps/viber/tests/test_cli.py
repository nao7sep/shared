"""Tests for CLI argument parsing and startup behavior."""

from pathlib import Path

import pytest

import viber.cli as cli_module
from viber.errors import StartupValidationError, ViberError
from viber.models import Database
from viber.service import create_group

DATA_PATH = Path("/tmp/viber-data.json")
CHECK_PATH = Path("/tmp/viber-check.html")


def test_parse_args_help_prints_usage_and_returns_none(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = cli_module.parse_args(["--help"])

    assert result is None
    out = capsys.readouterr().out
    assert "Usage: viber --data <path> [--check <path>]" in out


def test_parse_args_maps_data_and_check_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, Path]] = []

    def fake_map_path(raw: str, *, app_root_abs: Path) -> Path:
        calls.append((raw, app_root_abs))
        if raw == "~/data.json":
            return DATA_PATH
        if raw == "@/check.html":
            return CHECK_PATH
        raise AssertionError(f"Unexpected path: {raw}")

    monkeypatch.setattr(cli_module, "map_path", fake_map_path)

    result = cli_module.parse_args(["--data", "~/data.json", "--check", "@/check.html"])

    assert result == cli_module.AppArgs(data_path=DATA_PATH, check_path=CHECK_PATH)
    assert [raw for raw, _app_root in calls] == ["~/data.json", "@/check.html"]


def test_parse_args_missing_data_exits_with_usage_hint(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli_module.parse_args([])

    assert exc_info.value.code == 1
    err = capsys.readouterr().err
    assert "ERROR: --data is required." in err
    assert "Run 'viber --help' for usage." in err


def test_main_exits_on_startup_validation_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_parse_args() -> cli_module.AppArgs | None:
        raise StartupValidationError("bad path")

    monkeypatch.setattr(cli_module, "parse_args", fake_parse_args)

    with pytest.raises(SystemExit) as exc_info:
        cli_module.main()

    assert exc_info.value.code == 1
    err = capsys.readouterr().err
    assert "ERROR: bad path" in err
    assert "Run 'viber --help' for usage." in err


def test_main_exits_when_load_database_fails(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cli_module, "parse_args", lambda: cli_module.AppArgs(data_path=DATA_PATH, check_path=None)
    )

    def fake_load_database(_path: Path) -> Database:
        raise OSError("boom")

    monkeypatch.setattr(cli_module, "load_database", fake_load_database)

    with pytest.raises(SystemExit) as exc_info:
        cli_module.main()

    assert exc_info.value.code == 1
    err = capsys.readouterr().err
    assert "ERROR: Could not load data file: boom" in err


def test_main_saves_pruned_database_before_starting_repl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = Database()
    events: list[str] = []

    monkeypatch.setattr(
        cli_module, "parse_args", lambda: cli_module.AppArgs(data_path=DATA_PATH, check_path=None)
    )
    monkeypatch.setattr(cli_module, "load_database", lambda _path: db)
    monkeypatch.setattr(cli_module, "prune_orphan_tasks", lambda _db: [1])

    def fake_save_database(saved_db: Database, saved_path: Path) -> None:
        assert saved_db is db
        assert saved_path == DATA_PATH
        events.append("save")

    def fake_run_repl(repl_db: Database, data_path: Path, check_path: Path | None) -> None:
        assert repl_db is db
        assert data_path == DATA_PATH
        assert check_path is None
        events.append("repl")

    monkeypatch.setattr(cli_module, "save_database", fake_save_database)
    monkeypatch.setattr(cli_module, "run_repl", fake_run_repl)

    cli_module.main()

    assert events == ["save", "repl"]


def test_main_warns_on_check_render_failure_but_still_starts_repl(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db = Database()
    create_group(db, "Backend")
    events: list[str] = []

    monkeypatch.setattr(
        cli_module,
        "parse_args",
        lambda: cli_module.AppArgs(data_path=DATA_PATH, check_path=CHECK_PATH),
    )
    monkeypatch.setattr(cli_module, "load_database", lambda _path: db)
    monkeypatch.setattr(cli_module, "prune_orphan_tasks", lambda _db: [])

    def fake_render_check_pages(_db: Database, _check_path: Path) -> None:
        raise RuntimeError("disk full")

    def fake_run_repl(_db: Database, _data_path: Path, _check_path: Path | None) -> None:
        events.append("repl")

    monkeypatch.setattr(cli_module, "render_check_pages", fake_render_check_pages)
    monkeypatch.setattr(cli_module, "run_repl", fake_run_repl)

    cli_module.main()

    assert events == ["repl"]
    err = capsys.readouterr().err
    assert "WARNING: Could not generate HTML check pages: disk full" in err


def test_main_exits_on_fatal_repl_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db = Database()

    monkeypatch.setattr(
        cli_module, "parse_args", lambda: cli_module.AppArgs(data_path=DATA_PATH, check_path=None)
    )
    monkeypatch.setattr(cli_module, "load_database", lambda _path: db)
    monkeypatch.setattr(cli_module, "prune_orphan_tasks", lambda _db: [])

    def fake_run_repl(_db: Database, _data_path: Path, _check_path: Path | None) -> None:
        raise ViberError("fatal")

    monkeypatch.setattr(cli_module, "run_repl", fake_run_repl)

    with pytest.raises(SystemExit) as exc_info:
        cli_module.main()

    assert exc_info.value.code == 1
    err = capsys.readouterr().err
    assert "ERROR: Fatal: fatal" in err
