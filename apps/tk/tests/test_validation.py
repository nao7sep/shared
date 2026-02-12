"""Tests for validation module."""

import pytest
from tk.validation import validate_date_format


class TestValidateDateFormat:
    """Test date format and semantic validation."""

    def test_validate_date_valid(self):
        """Test that valid date is accepted."""
        # Should not raise
        validate_date_format("2026-02-09")
        validate_date_format("2026-01-01")
        validate_date_format("2026-12-31")

    def test_validate_date_invalid_format(self):
        """Test that wrong format is rejected."""
        with pytest.raises(ValueError, match="Invalid date"):
            validate_date_format("02-09-2026")

        with pytest.raises(ValueError, match="Invalid date"):
            validate_date_format("2026/02/09")

        with pytest.raises(ValueError, match="Invalid date"):
            validate_date_format("09-02-2026")

    def test_validate_date_invalid_month(self):
        """Test that invalid month is rejected."""
        with pytest.raises(ValueError, match="Invalid date"):
            validate_date_format("2026-13-01")

        with pytest.raises(ValueError, match="Invalid date"):
            validate_date_format("2026-00-01")

    def test_validate_date_invalid_day(self):
        """Test that invalid day is rejected."""
        with pytest.raises(ValueError, match="Invalid date"):
            validate_date_format("2026-02-30")

        with pytest.raises(ValueError, match="Invalid date"):
            validate_date_format("2026-04-31")

        with pytest.raises(ValueError, match="Invalid date"):
            validate_date_format("2026-01-32")

    def test_validate_date_leap_year(self):
        """Test that leap year is handled correctly."""
        # 2024 is a leap year
        validate_date_format("2024-02-29")  # Should not raise

        # 2026 is not a leap year
        with pytest.raises(ValueError, match="Invalid date"):
            validate_date_format("2026-02-29")

    def test_validate_date_empty_string(self):
        """Test that empty string is rejected."""
        with pytest.raises(ValueError, match="Invalid date"):
            validate_date_format("")

    def test_validate_date_partial_date(self):
        """Test that partial dates are rejected."""
        with pytest.raises(ValueError, match="Invalid date"):
            validate_date_format("2026-02")

        with pytest.raises(ValueError, match="Invalid date"):
            validate_date_format("2026")
