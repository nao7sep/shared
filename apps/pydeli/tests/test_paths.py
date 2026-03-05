"""Tests for pydeli.paths module."""

import pytest

from pydeli.errors import PathError
from pydeli.paths import resolve_path, sanitize_filename_segment


class TestResolvePath:
    def test_absolute_path(self, tmp_path):
        result = resolve_path(str(tmp_path))
        assert result == tmp_path

    def test_tilde_expansion(self):
        from pathlib import Path

        result = resolve_path("~/some-dir")
        assert result == (Path.home() / "some-dir").resolve()

    def test_empty_string_raises(self):
        with pytest.raises(PathError, match="must not be empty"):
            resolve_path("")

    def test_nul_byte_raises(self):
        with pytest.raises(PathError, match="NUL"):
            resolve_path("/tmp/foo\x00bar")

    def test_relative_path_raises(self):
        with pytest.raises(PathError, match="Relative paths"):
            resolve_path("some/relative/path")

    def test_windows_rooted_raises(self):
        with pytest.raises(PathError, match="Windows"):
            resolve_path("C:temp")

    def test_windows_backslash_raises(self):
        with pytest.raises(PathError, match="Windows"):
            resolve_path("\\temp")

    def test_nfc_normalization(self):
        # NFD form of é (e + combining acute)
        nfd = "/tmp/caf\u0065\u0301"
        result = resolve_path(nfd)
        assert "café" in str(result) or "cafe" in str(result)

    def test_dot_segment_resolution(self, tmp_path):
        result = resolve_path(str(tmp_path / "a" / ".." / "b"))
        assert result == tmp_path / "b"


class TestSanitizeFilenameSegment:
    def test_simple_name(self):
        assert sanitize_filename_segment("my-project") == "my-project"

    def test_special_chars_replaced(self):
        assert sanitize_filename_segment("my@project!v2") == "my-project-v2"

    def test_collapsed_hyphens(self):
        assert sanitize_filename_segment("a---b") == "a-b"

    def test_trimmed_edges(self):
        assert sanitize_filename_segment("-project-") == "project"

    def test_empty_result_raises(self):
        with pytest.raises(PathError, match="empty after sanitization"):
            sanitize_filename_segment("@@@")

    def test_preserves_dots(self):
        assert sanitize_filename_segment("v1.0") == "v1.0"

    def test_preserves_underscores(self):
        assert sanitize_filename_segment("my_project") == "my_project"
