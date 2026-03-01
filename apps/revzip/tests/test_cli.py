from __future__ import annotations

from pathlib import Path

import pytest

import revzip.cli as cli
import revzip.path_mapping as path_mapping


def test_main_reports_expanduser_failures_as_cli_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def _raise_expanduser(self: Path) -> Path:
        raise RuntimeError("Could not determine home directory.")

    monkeypatch.setattr(path_mapping.Path, "expanduser", _raise_expanduser)

    exit_code = cli.main(
        [
            "--source",
            "~missing-user/source",
            "--dest",
            str(tmp_path / "dest"),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "ERROR: Failed to expand user home in path" in captured.out
