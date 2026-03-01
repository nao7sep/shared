"""Input validation helpers for tk."""

from datetime import date

from tk.errors import ValidationError


def validate_date_format(date_str: str) -> None:
    """Validate YYYY-MM-DD date format and semantic correctness.

    Args:
        date_str: Date string to validate

    Raises:
        ValueError: If date is not in YYYY-MM-DD format or is semantically invalid
    """
    try:
        date.fromisoformat(date_str)
    except ValueError:
        raise ValidationError(
            f"Invalid date: {date_str}. Expected valid YYYY-MM-DD format"
        )
