from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

import revzip.repl as repl
from revzip.models import IgnoreRuleSet, ResolvedPaths, SnapshotMetadata, SnapshotRecord
from revzip.presenters import (
    render_app_banner,
    render_loaded_parameters,
    render_main_menu,
)


def test_run_repl_formats_startup_segments_without_trailing_blank_line(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    resolved_paths = _make_resolved_paths(tmp_path)
    ignore_rule_set = IgnoreRuleSet(patterns_raw=[], compiled_patterns=[])
    _install_scripted_input(monkeypatch, [EOFError()])

    exit_code = repl.run_repl(
        resolved_paths=resolved_paths,
        ignore_rule_set=ignore_rule_set,
    )

    captured = capsys.readouterr()
    expected = (
        f"{render_app_banner()}\n\n"
        + "\n".join(
            render_loaded_parameters(
                resolved_paths=resolved_paths,
                ignore_rule_set=ignore_rule_set,
            )
        )
        + "\n\n"
        + render_main_menu()
        + "\nSelect option: Exiting.\n"
    )
    assert exit_code == 0
    assert captured.out == expected
    assert not captured.out.startswith("\n")
    assert not captured.out.endswith("\n\n")


def test_run_repl_gives_snapshot_selection_prompt_its_own_leading_blank_line(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    resolved_paths = _make_resolved_paths(tmp_path)
    snapshot_record = SnapshotRecord(
        metadata_path=resolved_paths.dest_dir_abs / "2026-03-04_10-00-00_test.json",
        zip_path=resolved_paths.dest_dir_abs / "2026-03-04_10-00-00_test.zip",
        metadata=SnapshotMetadata(
            created_utc="2026-03-04T01:00:00.000000Z",
            created_at="2026-03-04 10:00:00",
            comment="Test snapshot",
            comment_filename_segment="test-snapshot",
            zip_filename="2026-03-04_10-00-00_test.zip",
            archived_files=[],
            empty_directories=[],
        ),
        created_utc_dt=datetime(2026, 3, 4, 1, 0, tzinfo=timezone.utc),
    )
    monkeypatch.setattr(
        repl,
        "discover_snapshots",
        lambda *, dest_dir_abs: ([snapshot_record], []),
    )
    _install_scripted_input(monkeypatch, ["2", EOFError(), "3"])

    exit_code = repl.run_repl(
        resolved_paths=resolved_paths,
        ignore_rule_set=IgnoreRuleSet(patterns_raw=[], compiled_patterns=[]),
    )

    captured = capsys.readouterr()
    snapshot_row = "1 | 2026-03-04 10:00:00 | Test snapshot"
    expected_fragment = (
        render_main_menu()
        + "\nSelect option: \n\n"
        + "Available snapshots:\n"
        + f"{snapshot_row}\n\n"
        + "Select snapshot number: ERROR: Selection is required.\n\n"
        + render_main_menu()
        + "\nSelect option: \nExiting.\n"
    )
    assert exit_code == 0
    assert expected_fragment in captured.out
    assert f"{snapshot_row}\n\n\nSelect snapshot number:" not in captured.out
    assert not captured.out.endswith("\n\n")


def _make_resolved_paths(tmp_path: Path) -> ResolvedPaths:
    source_dir_abs = tmp_path / "source"
    dest_dir_abs = tmp_path / "dest"
    source_dir_abs.mkdir()
    dest_dir_abs.mkdir()
    return ResolvedPaths(
        source_arg_raw=str(source_dir_abs),
        source_dir_abs=source_dir_abs,
        dest_arg_raw=str(dest_dir_abs),
        dest_dir_abs=dest_dir_abs,
        ignore_arg_raw=None,
        ignore_file_abs=None,
    )


def _install_scripted_input(
    monkeypatch: pytest.MonkeyPatch,
    responses: list[str | BaseException],
) -> None:
    response_iter = iter(responses)

    def _input(prompt: str) -> str:
        print(prompt, end="")
        response = next(response_iter)
        if isinstance(response, BaseException):
            raise response
        print()
        return response

    monkeypatch.setattr("builtins.input", _input)
