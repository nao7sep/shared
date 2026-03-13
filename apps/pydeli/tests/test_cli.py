from __future__ import annotations

import pytest

from pydeli.cli import _map_user_path, _validate_app_dir
from pydeli.errors import PydeliError


class TestMapUserPath:
    """Path mapping from user input strings to absolute Paths."""

    def test_absolute_path_passthrough(self) -> None:
        result = _map_user_path("/usr/local/bin")
        assert result.is_absolute()
        assert str(result) == "/usr/local/bin"

    def test_tilde_expands_to_home(self) -> None:
        result = _map_user_path("~/some/dir")
        assert result.is_absolute()
        assert "~" not in str(result)

    def test_rejects_nul_character(self) -> None:
        with pytest.raises(PydeliError, match="NUL"):
            _map_user_path("/path/with\0null")

    def test_rejects_empty_input(self) -> None:
        with pytest.raises(PydeliError, match="empty"):
            _map_user_path("")

    def test_rejects_whitespace_only(self) -> None:
        with pytest.raises(PydeliError, match="empty"):
            _map_user_path("   ")

    def test_rejects_windows_drive_relative(self) -> None:
        with pytest.raises(PydeliError, match="Windows rooted"):
            _map_user_path("C:temp")

    def test_accepts_windows_drive_absolute(self) -> None:
        """C:/temp is fully qualified and should not be rejected."""
        # This will resolve relative to cwd on Unix, but the regex should not block it.
        result = _map_user_path("C:/temp")
        assert result.is_absolute()

    def test_backslash_normalized_to_forward_slash(self) -> None:
        result = _map_user_path("/some\\path\\here")
        assert "\\" not in str(result)

    def test_relative_path_resolves(self) -> None:
        """Relative paths resolve against cwd as a convenience."""
        result = _map_user_path("relative/dir")
        assert result.is_absolute()

    def test_nfc_normalization(self) -> None:
        """NFD input (e.g., macOS filesystem) should be normalized to NFC."""
        # 'é' as NFD (e + combining acute) vs NFC (single codepoint)
        nfd = "caf\u0065\u0301"
        result = _map_user_path(f"/tmp/{nfd}")
        # The path should contain the NFC form
        assert "\u0065\u0301" not in str(result) or "\u00e9" in str(result)


class TestValidateAppDir:
    """Validation of app directory candidates."""

    def test_accepts_valid_app_dir(self, tmp_path: pytest.TempPathFactory) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\n")
        assert _validate_app_dir(tmp_path) == tmp_path

    def test_rejects_nonexistent_directory(self, tmp_path: pytest.TempPathFactory) -> None:
        fake = tmp_path / "does-not-exist"
        with pytest.raises(PydeliError, match="Directory not found"):
            _validate_app_dir(fake)

    def test_rejects_missing_pyproject(self, tmp_path: pytest.TempPathFactory) -> None:
        with pytest.raises(PydeliError, match="No pyproject.toml"):
            _validate_app_dir(tmp_path)
