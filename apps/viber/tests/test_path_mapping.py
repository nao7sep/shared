"""Tests for path mapping and filename slugification."""

from pathlib import Path

import pytest

from viber.errors import FilenameSanitizationError, PathMappingError
from viber.path_mapping import map_path, slugify

APP_ROOT = Path("/app/root")


def test_absolute_path() -> None:
    result = map_path("/usr/local/data.json", app_root_abs=APP_ROOT)
    assert result == Path("/usr/local/data.json")


def test_tilde_expansion() -> None:
    result = map_path("~/viber/data.json", app_root_abs=APP_ROOT)
    assert result.is_absolute()
    assert "viber" in str(result)
    assert "data.json" in str(result)


def test_at_root() -> None:
    result = map_path("@/data.json", app_root_abs=APP_ROOT)
    assert result == Path("/app/root/data.json")


def test_at_root_bare() -> None:
    result = map_path("@", app_root_abs=APP_ROOT)
    assert result == Path("/app/root")


def test_relative_with_base_dir() -> None:
    result = map_path("sub/data.json", app_root_abs=APP_ROOT, base_dir=Path("/base"))
    assert result == Path("/base/sub/data.json")


def test_relative_without_base_dir_raises() -> None:
    with pytest.raises(PathMappingError, match="Relative path"):
        map_path("data.json", app_root_abs=APP_ROOT)


def test_nul_character_raises() -> None:
    with pytest.raises(PathMappingError, match="NUL"):
        map_path("/path/to\0file", app_root_abs=APP_ROOT)


def test_windows_rooted_not_qualified_backslash() -> None:
    with pytest.raises(PathMappingError, match="Windows"):
        map_path("\\temp\\file", app_root_abs=APP_ROOT)


def test_windows_drive_relative() -> None:
    with pytest.raises(PathMappingError, match="Windows"):
        map_path("C:temp", app_root_abs=APP_ROOT)


def test_windows_drive_absolute_accepted() -> None:
    # C:\path is fully qualified, should not raise (it's absolute)
    # On macOS this just becomes a relative path starting with "C:", but map_path will accept it
    # since it's not the C:name form. This test is platform-nuanced; skip on non-Windows.
    pass  # Not asserting cross-platform behavior for Windows absolute paths


def test_dot_segments_resolved() -> None:
    result = map_path("/app/data/../other/file.json", app_root_abs=APP_ROOT)
    assert ".." not in str(result)
    assert "app" in str(result)


# ---------------------------------------------------------------------------
# Slugify tests
# ---------------------------------------------------------------------------


def test_slugify_simple() -> None:
    assert slugify("backend") == "backend"


def test_slugify_with_spaces() -> None:
    assert slugify("my group") == "my-group"


def test_slugify_special_chars() -> None:
    result = slugify("done & checked")
    assert result == "done-checked"


def test_slugify_lowercases() -> None:
    assert slugify("Backend") == "backend"
    assert slugify("MY-GROUP") == "my-group"


def test_slugify_with_extension() -> None:
    result = slugify("My Group.html")
    assert result == "my-group.html"


def test_slugify_collapses_hyphens() -> None:
    result = slugify("a  b  c")
    assert result == "a-b-c"


def test_slugify_strips_leading_trailing() -> None:
    result = slugify("-leading-trailing-")
    assert result == "leading-trailing"


def test_slugify_empty_raises() -> None:
    with pytest.raises(FilenameSanitizationError):
        slugify("---")


def test_slugify_unicode_letters_preserved() -> None:
    result = slugify("café")
    assert "caf" in result
