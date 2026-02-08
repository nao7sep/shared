"""Input validation helpers for tk."""

import re

DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_date_format(date_str: str) -> None:
    """Validate YYYY-MM-DD date format."""
    if not DATE_REGEX.match(date_str):
        raise ValueError("Invalid date format. Expected: YYYY-MM-DD")
