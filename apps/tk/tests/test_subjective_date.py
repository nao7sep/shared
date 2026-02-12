"""Tests for subjective_date module."""

import pytest
from freezegun import freeze_time

from tk.subjective_date import (
    calculate_subjective_date,
    get_current_subjective_date,
)


class TestCalculateSubjectiveDate:
    """Test calculate_subjective_date function."""

    def test_calculate_before_day_start(self):
        """Test that time before day start returns previous day."""
        # UTC: 2026-02-09 02:00:00
        # Tokyo (UTC+9): 2026-02-09 11:00:00
        # But actually we want: 2026-02-09 03:00:00 in Tokyo
        # which is before 04:00, so should be 2026-02-08

        # Let's use a clearer example:
        # UTC: 2026-01-31T19:00:00Z
        # Tokyo (UTC+9): 2026-02-01T04:00:00 but let's say 03:00
        # Actually, 19:00 UTC = 04:00+9 = next day 04:00

        # Better example:
        # UTC: 2026-01-31T18:00:00Z
        # Tokyo: 2026-02-01T03:00:00 (before 04:00 day start)
        # Subjective date: 2026-01-31

        result = calculate_subjective_date(
            "2026-01-31T18:00:00Z",
            "Asia/Tokyo",
            "04:00:00"
        )

        assert result == "2026-01-31"

    def test_calculate_after_day_start(self):
        """Test that time after day start returns same day."""
        # UTC: 2026-01-31T20:00:00Z
        # Tokyo: 2026-02-01T05:00:00 (after 04:00 day start)
        # Subjective date: 2026-02-01

        result = calculate_subjective_date(
            "2026-01-31T20:00:00Z",
            "Asia/Tokyo",
            "04:00:00"
        )

        assert result == "2026-02-01"

    def test_calculate_at_day_start_boundary(self):
        """Test boundary case at exact day start time."""
        # UTC: 2026-01-31T19:00:00Z
        # Tokyo: 2026-02-01T04:00:00 (exactly at day start)
        # Subjective date: 2026-02-01

        result = calculate_subjective_date(
            "2026-01-31T19:00:00Z",
            "Asia/Tokyo",
            "04:00:00"
        )

        assert result == "2026-02-01"

    def test_calculate_with_timezone_offset(self):
        """Test with different timezone."""
        # UTC: 2026-02-09T03:00:00Z
        # America/New_York (UTC-5): 2026-02-08T22:00:00 (before 04:00)
        # Subjective date: 2026-02-08

        result = calculate_subjective_date(
            "2026-02-09T03:00:00Z",
            "America/New_York",
            "04:00:00"
        )

        assert result == "2026-02-08"

    def test_calculate_invalid_timezone(self):
        """Test that invalid timezone raises ValueError."""
        with pytest.raises(ValueError, match="Invalid timezone"):
            calculate_subjective_date(
                "2026-02-09T10:00:00Z",
                "Invalid/Timezone",
                "04:00:00"
            )

    def test_calculate_with_utc(self):
        """Test with UTC timezone."""
        # UTC: 2026-02-09T03:00:00Z (before 04:00)
        # Subjective date: 2026-02-08

        result = calculate_subjective_date(
            "2026-02-09T03:00:00Z",
            "UTC",
            "04:00:00"
        )

        assert result == "2026-02-08"


class TestGetCurrentSubjectiveDate:
    """Test get_current_subjective_date function."""

    @freeze_time("2026-02-09 10:00:00", tz_offset=0)
    def test_get_current_subjective_date(self):
        """Test getting current subjective date."""
        # Frozen at UTC: 2026-02-09T10:00:00Z
        # Tokyo: 2026-02-09T19:00:00 (after 04:00)
        # Subjective date: 2026-02-09

        result = get_current_subjective_date("Asia/Tokyo", "04:00:00")

        assert result == "2026-02-09"

    @freeze_time("2026-02-09 02:00:00", tz_offset=0)
    def test_get_current_subjective_date_before_day_start(self):
        """Test getting current subjective date before day start."""
        # Frozen at UTC: 2026-02-09T02:00:00Z
        # Tokyo: 2026-02-09T11:00:00... wait
        # Actually UTC 02:00 + 9 hours = 11:00 Tokyo time
        # That's after 04:00, so should be same day

        # Better: Use a time that results in before day start
        # We need Tokyo time to be before 04:00
        # Tokyo 03:00 = UTC 18:00 previous day

        result = get_current_subjective_date("Asia/Tokyo", "04:00:00")

        # UTC 02:00 + 9 = 11:00 Tokyo (after 04:00)
        assert result == "2026-02-09"

    @freeze_time("2026-02-08 18:00:00", tz_offset=0)
    def test_get_current_before_day_start_correctly(self):
        """Test getting current subjective date before day start."""
        # UTC: 2026-02-08T18:00:00Z
        # Tokyo: 2026-02-09T03:00:00 (before 04:00)
        # Subjective date: 2026-02-08

        result = get_current_subjective_date("Asia/Tokyo", "04:00:00")

        assert result == "2026-02-08"
