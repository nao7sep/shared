"""Tests for emojihunt.scanner — lazy traversal, ignore-before-enter, binary detection."""

from __future__ import annotations

import io
import re
from pathlib import Path

from emojihunt.filter import PathFilter
from emojihunt.models import HandledPathStatus
from emojihunt.scanner import DirectoryScanner


class TestIgnoreBeforeEnter:
    """The scanner must check ignore patterns BEFORE descending into a directory.
    If a directory matches, none of its children should appear in results."""

    def test_ignored_directory_children_never_yielded(self, tmp_path: Path) -> None:
        # Create: target/ok.txt, target/ignored_dir/should_not_appear.txt
        (tmp_path / "ok.txt").write_text("hello", encoding="utf-8")
        ignored = tmp_path / "ignored_dir"
        ignored.mkdir()
        (ignored / "should_not_appear.txt").write_text("secret", encoding="utf-8")

        f = PathFilter([re.compile(r"^ignored_dir$")])
        scanner = DirectoryScanner([tmp_path], f, warning_file=io.StringIO())
        results = list(scanner.scan())

        paths = [r.handled_path.path for r in results]
        assert any("ok.txt" in p for p in paths)
        assert not any("should_not_appear" in p for p in paths)

    def test_deeply_nested_ignored_directory(self, tmp_path: Path) -> None:
        """Pattern matching a nested directory should prevent recursion into it."""
        deep = tmp_path / "a" / "b" / "skip_me"
        deep.mkdir(parents=True)
        (deep / "hidden.txt").write_text("x", encoding="utf-8")
        (tmp_path / "a" / "visible.txt").write_text("y", encoding="utf-8")

        f = PathFilter([re.compile(r"skip_me")])
        scanner = DirectoryScanner([tmp_path], f, warning_file=io.StringIO())
        results = list(scanner.scan())

        paths = [r.handled_path.path for r in results]
        assert any("visible.txt" in p for p in paths)
        assert not any("hidden.txt" in p for p in paths)


class TestBinaryFileDetection:
    def test_binary_file_yields_skipped_status(self, tmp_path: Path) -> None:
        binary_file = tmp_path / "image.bin"
        binary_file.write_bytes(b"\x89PNG\r\n\x1a\n" + bytes(range(256)))

        scanner = DirectoryScanner([tmp_path], PathFilter.empty(), warning_file=io.StringIO())
        results = list(scanner.scan())

        assert len(results) == 1
        assert results[0].handled_path.status == HandledPathStatus.SKIPPED
        assert results[0].file_content is None


class TestFileTarget:
    def test_single_file_target(self, tmp_path: Path) -> None:
        """Passing a file (not directory) as target should process it directly."""
        f = tmp_path / "direct.txt"
        f.write_text("content", encoding="utf-8")

        scanner = DirectoryScanner([f], PathFilter.empty(), warning_file=io.StringIO())
        results = list(scanner.scan())

        assert len(results) == 1
        assert results[0].handled_path.status == HandledPathStatus.OK
        assert results[0].file_content is not None


class TestRelativePathComputation:
    def test_relative_path_from_target_root(self, tmp_path: Path) -> None:
        """Ignore patterns are matched against relative paths from the target root.
        A pattern anchored to 'sub/' should match target/sub/ but not target/other/sub/."""
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "file.txt").write_text("a", encoding="utf-8")

        # Pattern that only matches 'sub' at the root of the relative path
        f = PathFilter([re.compile(r"^sub/")])
        scanner = DirectoryScanner([tmp_path], f, warning_file=io.StringIO())
        results = list(scanner.scan())

        assert not any("file.txt" in r.handled_path.path for r in results)

    def test_multiple_targets_have_independent_roots(self, tmp_path: Path) -> None:
        """Each --target has its own root for relative path computation."""
        t1 = tmp_path / "project_a"
        t2 = tmp_path / "project_b"
        t1.mkdir()
        t2.mkdir()
        (t1 / "src").mkdir()
        (t2 / "src").mkdir()
        (t1 / "src" / "a.txt").write_text("a", encoding="utf-8")
        (t2 / "src" / "b.txt").write_text("b", encoding="utf-8")

        scanner = DirectoryScanner([t1, t2], PathFilter.empty(), warning_file=io.StringIO())
        results = list(scanner.scan())

        paths = [r.handled_path.path for r in results]
        assert any("a.txt" in p for p in paths)
        assert any("b.txt" in p for p in paths)


class TestWarningOutput:
    def test_nonexistent_target_warns(self, tmp_path: Path) -> None:
        warning_buf = io.StringIO()
        scanner = DirectoryScanner(
            [tmp_path / "does_not_exist"], PathFilter.empty(), warning_file=warning_buf
        )
        list(scanner.scan())
        assert "does not exist" in warning_buf.getvalue().lower()
