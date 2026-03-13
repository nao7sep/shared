"""Tests for emojihunt.path_mapping — @ mapping, Windows rejection, NFC normalization."""

from __future__ import annotations

from pathlib import Path

import pytest

from emojihunt.errors import PathMappingError
from emojihunt.path_mapping import map_path

APP_ROOT = Path("/app/root")


class TestAppRootMapping:
    """The @ prefix maps to app_root_abs. Edge cases around trailing slashes
    and separator handling matter because the stripping logic is manual."""

    def test_bare_at(self) -> None:
        assert map_path("@", app_root_abs=APP_ROOT) == APP_ROOT.resolve()

    def test_at_with_slash(self) -> None:
        result = map_path("@/config", app_root_abs=APP_ROOT)
        assert result == (APP_ROOT / "config").resolve()

    def test_at_with_multiple_slashes(self) -> None:
        """Repeated slashes after @ should collapse, not create empty segments."""
        result = map_path("@///config///file.txt", app_root_abs=APP_ROOT)
        assert result == (APP_ROOT / "config" / "file.txt").resolve()

    def test_at_with_backslash(self) -> None:
        result = map_path("@\\config\\file.txt", app_root_abs=APP_ROOT)
        assert result == (APP_ROOT / "config" / "file.txt").resolve()

    def test_relative_app_root_raises(self) -> None:
        with pytest.raises(PathMappingError, match="absolute"):
            map_path("@/something", app_root_abs=Path("relative"))


class TestWindowsRejection:
    def test_single_backslash_prefix_rejected(self) -> None:
        with pytest.raises(PathMappingError, match="Windows"):
            map_path("\\temp", app_root_abs=APP_ROOT)

    def test_unc_path_not_rejected(self) -> None:
        """Double backslash (UNC) is NOT a rooted-not-qualified form."""
        # Should not raise — it's treated as a regular path
        result = map_path("\\\\server\\share", app_root_abs=APP_ROOT)
        assert result is not None

    def test_drive_relative_rejected(self) -> None:
        with pytest.raises(PathMappingError, match="Windows"):
            map_path("C:temp", app_root_abs=APP_ROOT)

    def test_drive_absolute_not_rejected(self) -> None:
        """C:\\temp is fully qualified — should not be rejected."""
        # On Unix this won't be "absolute" in the Path sense, but it must
        # not trigger the Windows-rooted-not-qualified rejection.
        try:
            map_path("C:\\temp", app_root_abs=APP_ROOT)
        except PathMappingError as exc:
            # Only PathMappingError about "Windows" form is a failure
            assert "Windows" not in str(exc)


class TestNFCNormalization:
    def test_nfd_input_normalized(self) -> None:
        """NFD é (e + combining acute) must be normalized to NFC before mapping."""
        nfd = "/path/caf\u0065\u0301"  # e + combining acute
        result = map_path(nfd, app_root_abs=APP_ROOT)
        assert "\u00e9" in str(result)  # NFC é


class TestNulRejection:
    def test_nul_in_path(self) -> None:
        with pytest.raises(PathMappingError, match="NUL"):
            map_path("/path/\0/bad", app_root_abs=APP_ROOT)


class TestRelativePathRequiresBaseDir:
    def test_relative_without_base_dir_raises(self) -> None:
        with pytest.raises(PathMappingError, match="Relative"):
            map_path("some/relative/path", app_root_abs=APP_ROOT)

    def test_relative_with_base_dir_resolves(self) -> None:
        result = map_path("sub/file.txt", app_root_abs=APP_ROOT, base_dir=Path("/base"))
        assert result == Path("/base/sub/file.txt").resolve()

    def test_dot_segments_resolved_after_joining(self) -> None:
        result = map_path("../sibling", app_root_abs=APP_ROOT, base_dir=Path("/base/dir"))
        assert result == Path("/base/sibling").resolve()
