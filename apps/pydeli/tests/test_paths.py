"""Tests for pydeli.paths module."""

import os
from pathlib import Path

import pytest

from pydeli.errors import PathError
from pydeli.paths import _APP_ROOT, resolve_path, sanitize_filename_segment


class TestResolvePath:
    def test_absolute_path(self, tmp_path):
        result = resolve_path(str(tmp_path))
        assert result == tmp_path

    def test_tilde_expansion(self):
        result = resolve_path("~/some-dir")
        assert result == Path(os.path.normpath(os.path.expanduser("~/some-dir")))

    def test_at_prefix_maps_to_app_root(self):
        result = resolve_path("@/subdir")
        assert result == _APP_ROOT / "subdir"

    def test_at_prefix_bare_maps_to_app_root(self):
        result = resolve_path("@")
        assert result == _APP_ROOT

    def test_at_prefix_with_dotdot_raises(self):
        with pytest.raises(PathError, match=r"\.\.|escape"):
            resolve_path("@/../outside")

    def test_relative_with_base_dir(self, tmp_path):
        result = resolve_path("sub/dir", base_dir=tmp_path)
        assert result == tmp_path / "sub" / "dir"

    def test_relative_without_base_dir_raises(self):
        with pytest.raises(PathError, match="Relative paths"):
            resolve_path("some/relative/path")

    def test_empty_string_raises(self):
        with pytest.raises(PathError, match="must not be empty"):
            resolve_path("")

    def test_nul_byte_raises(self):
        with pytest.raises(PathError, match="NUL"):
            resolve_path("/tmp/foo\x00bar")

    def test_windows_rooted_raises(self):
        with pytest.raises(PathError, match="Windows"):
            resolve_path("C:temp")

    def test_windows_backslash_raises(self):
        with pytest.raises(PathError, match="Windows"):
            resolve_path("\\temp")

    def test_nfc_normalization(self):
        # NFD form of é (e + combining acute accent)
        nfd = "/tmp/caf\u0065\u0301"
        result = resolve_path(nfd)
        assert "caf" in str(result)

    def test_dot_segment_resolution(self, tmp_path):
        result = resolve_path(str(tmp_path / "a" / ".." / "b"))
        assert result == tmp_path / "b"

    def test_cwd_never_used_for_relative(self):
        # Pure relative with no base_dir must be rejected, not resolved against CWD
        with pytest.raises(PathError):
            resolve_path("some/path")

    def test_base_dir_must_be_absolute(self):
        with pytest.raises(PathError, match="base_dir must be absolute"):
            resolve_path("sub", base_dir=Path("relative/base"))

    def test_at_app_root_is_absolute(self):
        assert _APP_ROOT.is_absolute()

    def test_at_app_root_contains_paths_module(self):
        # _APP_ROOT is the pydeli package dir, which contains paths.py
        assert (_APP_ROOT / "paths.py").is_file()

    def test_mixed_separators_in_absolute_path(self):
        # Forward and backward slashes are both accepted
        result = resolve_path("/tmp//subdir")
        assert result == Path("/tmp/subdir")


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
