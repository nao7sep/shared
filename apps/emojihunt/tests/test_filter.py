"""Tests for emojihunt.filter — ignore pattern matching edge cases."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from emojihunt.errors import IgnoreFileError
from emojihunt.filter import PathFilter


class TestPatternMatching:
    def test_backslash_normalized_to_forward_slash(self) -> None:
        """Windows-style backslashes must match forward-slash patterns."""
        f = PathFilter([re.compile(r"vendor/lib")])
        assert f.is_ignored("vendor\\lib\\thing.js")

    def test_anchored_pattern_only_matches_start(self) -> None:
        f = PathFilter([re.compile(r"^\.git/")])
        assert f.is_ignored(".git/config")
        assert not f.is_ignored("src/.git/config")

    def test_unanchored_pattern_matches_anywhere(self) -> None:
        f = PathFilter([re.compile(r"__pycache__")])
        assert f.is_ignored("__pycache__/mod.pyc")
        assert f.is_ignored("deep/nested/__pycache__/mod.pyc")

    def test_first_matching_pattern_wins(self) -> None:
        """Multiple patterns — any single match is sufficient."""
        f = PathFilter([re.compile(r"nope"), re.compile(r"\.lock$")])
        assert f.is_ignored("poetry.lock")

    def test_pattern_uses_search_not_fullmatch(self) -> None:
        """Pattern should match substrings, not require a full match."""
        f = PathFilter([re.compile(r"node_modules")])
        assert f.is_ignored("frontend/node_modules/pkg/index.js")


class TestFromFile:
    def test_comment_and_blank_lines_ignored(self, tmp_path: Path) -> None:
        content = "# skip this\n\n\\.pyc$\n  \n# also skip\n\\.pyo$\n"
        (tmp_path / "ignore").write_text(content, encoding="utf-8")
        f = PathFilter.from_file(tmp_path / "ignore")
        assert f.is_ignored("mod.pyc")
        assert f.is_ignored("mod.pyo")
        assert not f.is_ignored("mod.py")

    def test_invalid_regex_includes_line_number(self, tmp_path: Path) -> None:
        content = "valid\n[broken\n"
        (tmp_path / "ignore").write_text(content, encoding="utf-8")
        with pytest.raises(IgnoreFileError, match="line 2"):
            PathFilter.from_file(tmp_path / "ignore")

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(IgnoreFileError, match="not found"):
            PathFilter.from_file(tmp_path / "nonexistent")
