"""Tests for profile module."""

import json
import pytest
from pathlib import Path

from tk.profile import (
    map_path,
    parse_time,
    validate_profile,
    load_profile,
    create_profile,
)


class TestMapPath:
    """Test map_path function."""

    def test_map_path_tilde_with_subpath(self):
        """Test mapping tilde with subpath."""
        result = map_path("~/test/path", "/profile/dir")
        expected = str(Path.home() / "test/path")
        assert result == expected

    def test_map_path_tilde_alone(self):
        """Test mapping tilde alone."""
        result = map_path("~", "/profile/dir")
        expected = str(Path.home())
        assert result == expected

    def test_map_path_at_with_subpath(self):
        """Test mapping @ with subpath."""
        result = map_path("@/test/path", "/profile/dir")
        # App root is where pyproject.toml is (tk/)
        assert result.endswith("test/path")
        assert "tk" in result or "src" in result

    def test_map_path_at_alone(self):
        """Test mapping @ alone."""
        result = map_path("@", "/profile/dir")
        # App root is where pyproject.toml is (tk/)
        assert "tk" in result or "src" in result

    def test_map_path_absolute(self):
        """Test mapping absolute path."""
        abs_path = "/absolute/path/to/file"
        result = map_path(abs_path, "/profile/dir")
        assert result == abs_path

    def test_map_path_relative(self, temp_dir):
        """Test mapping relative path."""
        profile_dir = str(temp_dir)
        result = map_path("relative/path", profile_dir)
        expected = str(temp_dir / "relative/path")
        assert result == expected


class TestParseTime:
    """Test parse_time function."""

    def test_parse_time_hh_mm(self):
        """Test parsing HH:MM format."""
        hours, minutes, seconds = parse_time("04:00")
        assert hours == 4
        assert minutes == 0
        assert seconds == 0

    def test_parse_time_hh_mm_ss(self):
        """Test parsing HH:MM:SS format."""
        hours, minutes, seconds = parse_time("04:30:15")
        assert hours == 4
        assert minutes == 30
        assert seconds == 15

    def test_parse_time_single_digit_hour(self):
        """Test parsing single-digit hour."""
        hours, minutes, seconds = parse_time("4:00")
        assert hours == 4
        assert minutes == 0
        assert seconds == 0

    def test_parse_time_invalid_format(self):
        """Test that invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid time format"):
            parse_time("4:00 AM")

        # Note: parse_time uses regex, so 25:00 matches the pattern (doesn't validate range)
        # The validation happens at profile validation level

        with pytest.raises(ValueError, match="Invalid time format"):
            parse_time("not a time")

    def test_parse_time_midnight(self):
        """Test parsing midnight."""
        hours, minutes, seconds = parse_time("00:00:00")
        assert hours == 0
        assert minutes == 0
        assert seconds == 0

    def test_parse_time_end_of_day(self):
        """Test parsing end of day."""
        hours, minutes, seconds = parse_time("23:59:59")
        assert hours == 23
        assert minutes == 59
        assert seconds == 59


class TestValidateProfile:
    """Test validate_profile function."""

    def test_validate_profile_valid(self):
        """Test that valid profile passes validation."""
        profile = {
            "data_path": "~/tasks.json",
            "output_path": "~/TODO.md",
            "timezone": "Asia/Tokyo",
            "subjective_day_start": "04:00:00",
        }
        validate_profile(profile)  # Should not raise

    def test_validate_profile_missing_field(self):
        """Test that missing required field raises ValueError."""
        # Missing data_path
        with pytest.raises(ValueError, match="missing required fields"):
            validate_profile({
                "output_path": "~/TODO.md",
                "timezone": "Asia/Tokyo",
                "subjective_day_start": "04:00:00",
            })

        # Missing timezone
        with pytest.raises(ValueError, match="missing required fields"):
            validate_profile({
                "data_path": "~/tasks.json",
                "output_path": "~/TODO.md",
                "subjective_day_start": "04:00:00",
            })

    def test_validate_profile_invalid_time(self):
        """Test that invalid time format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid subjective_day_start"):
            validate_profile({
                "data_path": "~/tasks.json",
                "output_path": "~/TODO.md",
                "timezone": "Asia/Tokyo",
                "subjective_day_start": "not a time",
            })

    def test_validate_profile_empty_timezone(self):
        """Test that empty timezone raises ValueError."""
        with pytest.raises(ValueError, match="timezone must be a non-empty string"):
            validate_profile({
                "data_path": "~/tasks.json",
                "output_path": "~/TODO.md",
                "timezone": "",
                "subjective_day_start": "04:00:00",
            })


class TestLoadProfile:
    """Test load_profile function."""

    def test_load_profile_nonexistent(self, temp_dir):
        """Test that loading non-existent profile raises FileNotFoundError."""
        profile_path = temp_dir / "nonexistent.json"

        with pytest.raises(FileNotFoundError, match="Profile not found"):
            load_profile(str(profile_path))

    def test_load_profile_invalid_json(self, temp_dir):
        """Test that invalid JSON raises JSONDecodeError."""
        profile_path = temp_dir / "invalid.json"
        profile_path.write_text("{ invalid json }")

        with pytest.raises(json.JSONDecodeError):
            load_profile(str(profile_path))

    def test_load_profile_valid(self, temp_dir):
        """Test loading valid profile."""
        profile_path = temp_dir / "valid.json"

        profile_data = {
            "timezone": "Asia/Tokyo",
            "subjective_day_start": "04:00:00",
            "data_path": "./tasks.json",
            "output_path": "./TODO.md",
        }

        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(profile_data, f)

        profile = load_profile(str(profile_path))

        assert profile["timezone"] == "Asia/Tokyo"
        assert profile["subjective_day_start"] == "04:00:00"

    def test_load_profile_maps_paths(self, temp_dir):
        """Test that load_profile maps relative paths."""
        profile_path = temp_dir / "profile.json"

        profile_data = {
            "timezone": "Asia/Tokyo",
            "subjective_day_start": "04:00:00",
            "data_path": "./tasks.json",
            "output_path": "./TODO.md",
        }

        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(profile_data, f)

        profile = load_profile(str(profile_path))

        # Paths should be absolute now
        assert Path(profile["data_path"]).is_absolute()
        assert Path(profile["output_path"]).is_absolute()
        assert str(temp_dir) in profile["data_path"]

    def test_load_profile_sets_defaults(self, temp_dir):
        """Test that load_profile sets default sync settings."""
        profile_path = temp_dir / "profile.json"

        profile_data = {
            "timezone": "Asia/Tokyo",
            "subjective_day_start": "04:00:00",
            "data_path": "./tasks.json",
            "output_path": "./TODO.md",
        }

        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(profile_data, f)

        profile = load_profile(str(profile_path))

        assert profile["auto_sync"] is True
        assert profile["sync_on_exit"] is False


class TestCreateProfile:
    """Test create_profile function."""

    def test_create_profile_creates_file(self, temp_dir):
        """Test that create_profile creates file."""
        profile_path = temp_dir / "new-profile.json"

        create_profile(str(profile_path))

        assert profile_path.exists()

    def test_create_profile_creates_directory(self, temp_dir):
        """Test that create_profile creates parent directory."""
        profile_path = temp_dir / "subdir" / "profile.json"

        create_profile(str(profile_path))

        assert profile_path.exists()
        assert profile_path.parent.exists()

    def test_create_profile_detects_timezone(self, temp_dir):
        """Test that create_profile uses system timezone."""
        profile_path = temp_dir / "profile.json"

        create_profile(str(profile_path))

        with open(profile_path, "r", encoding="utf-8") as f:
            profile = json.load(f)

        # Should have detected timezone (not empty)
        assert "timezone" in profile
        assert profile["timezone"] != ""

    def test_create_profile_defaults(self, temp_dir):
        """Test that create_profile sets correct defaults."""
        profile_path = temp_dir / "profile.json"

        create_profile(str(profile_path))

        with open(profile_path, "r", encoding="utf-8") as f:
            profile = json.load(f)

        assert profile["subjective_day_start"] == "04:00:00"
        assert profile["data_path"] == "./tasks.json"
        assert profile["output_path"] == "./TODO.md"
        assert profile["auto_sync"] is True
        assert profile["sync_on_exit"] is False

    def test_create_profile_fallback_to_utc(self, temp_dir, mocker):
        """Test that create_profile falls back to UTC on error."""
        # Mock tzlocal.get_localzone to raise exception
        # The import happens inside create_profile, so we need to mock the module
        mocker.patch("tzlocal.get_localzone", side_effect=Exception("Cannot detect timezone"))

        profile_path = temp_dir / "profile.json"
        create_profile(str(profile_path))

        with open(profile_path, "r", encoding="utf-8") as f:
            profile = json.load(f)

        assert profile["timezone"] == "UTC"
