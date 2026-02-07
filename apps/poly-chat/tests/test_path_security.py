"""Tests for path security - ensuring relative paths are rejected."""

import pytest
from pathlib import Path
from poly_chat.profile import map_path


def test_map_path_rejects_relative_paths():
    """Test that map_path rejects relative paths without prefix."""
    # Relative paths should raise ValueError
    with pytest.raises(ValueError, match="Relative paths without prefix are not supported"):
        map_path("relative/path/file.txt")

    with pytest.raises(ValueError, match="Relative paths without prefix are not supported"):
        map_path("./current/dir/file.txt")

    with pytest.raises(ValueError, match="Relative paths without prefix are not supported"):
        map_path("../parent/file.txt")

    with pytest.raises(ValueError, match="Relative paths without prefix are not supported"):
        map_path("file.txt")


def test_map_path_accepts_home_prefix():
    """Test that map_path accepts ~/... paths."""
    result = map_path("~/test/file.txt")
    assert str(Path.home()) in result
    assert "test/file.txt" in result

    result = map_path("~")
    assert result == str(Path.home())


def test_map_path_accepts_app_prefix():
    """Test that map_path accepts @/... paths."""
    result = map_path("@/test/file.txt")
    assert "test/file.txt" in result
    # Should be absolute
    assert Path(result).is_absolute()

    result = map_path("@")
    # Should be absolute
    assert Path(result).is_absolute()


def test_map_path_accepts_absolute_paths():
    """Test that map_path accepts absolute paths."""
    abs_path = "/absolute/path/to/file.txt"
    result = map_path(abs_path)
    assert result == abs_path


def test_map_path_home_returns_absolute():
    """Test that home paths return absolute paths."""
    result = map_path("~/documents/file.txt")
    assert Path(result).is_absolute()


def test_map_path_app_returns_absolute():
    """Test that app paths return absolute paths."""
    result = map_path("@/chats/file.json")
    assert Path(result).is_absolute()


def test_map_path_does_not_use_cwd():
    """Test that map_path never uses current working directory."""
    # This should fail, not resolve to cwd
    with pytest.raises(ValueError):
        map_path("local-file.txt")


def test_all_valid_path_types():
    """Test all valid path types are handled correctly."""
    # Home directory paths
    assert Path(map_path("~")).is_absolute()
    assert Path(map_path("~/test")).is_absolute()

    # App directory paths
    assert Path(map_path("@")).is_absolute()
    assert Path(map_path("@/test")).is_absolute()

    # Absolute paths
    assert Path(map_path("/tmp/test")).is_absolute()

    # Windows absolute paths (on Windows only)
    if Path("C:/").exists():
        assert Path(map_path("C:/test")).is_absolute()


def test_path_security_error_message():
    """Test that error messages provide helpful guidance."""
    try:
        map_path("relative/path")
    except ValueError as e:
        error_msg = str(e)
        # Should mention alternatives
        assert "~/" in error_msg
        assert "@/" in error_msg
        assert "absolute path" in error_msg


def test_edge_cases():
    """Test edge cases in path handling."""
    # Just a directory name (relative)
    with pytest.raises(ValueError):
        map_path("documents")

    # Hidden file (relative)
    with pytest.raises(ValueError):
        map_path(".hidden")

    # Double dots (relative)
    with pytest.raises(ValueError):
        map_path("../sibling")

    # Current directory
    with pytest.raises(ValueError):
        map_path(".")

    # Current directory explicit
    with pytest.raises(ValueError):
        map_path("./file")
