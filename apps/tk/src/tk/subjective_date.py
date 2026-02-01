"""Subjective date calculation with timezone and day-start offset."""

from datetime import datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from tk.profile import parse_time


def calculate_subjective_date(
    utc_timestamp: str,
    timezone_str: str,
    day_start: str
) -> str:
    """Convert UTC timestamp to subjective date (YYYY-MM-DD).

    Args:
        utc_timestamp: ISO 8601 UTC timestamp
        timezone_str: IANA timezone string (e.g., "Asia/Tokyo")
        day_start: Day start time in HH:MM or HH:MM:SS format

    Returns:
        Subjective date as YYYY-MM-DD string

    Algorithm:
    1. Parse UTC timestamp to datetime
    2. Convert to target timezone
    3. Parse day_start to hours/minutes/seconds
    4. If local time < day_start:
       subjective_date = local_date - 1 day
    5. Else:
       subjective_date = local_date
    6. Return as YYYY-MM-DD string

    Example:
        UTC: 2026-01-30T16:00:00Z
        Timezone: Asia/Tokyo (UTC+9)
        Local: 2026-01-31T01:00:00
        Day start: 04:00:00
        Local time (01:00) < Day start (04:00)
        → Subjective date: 2026-01-30
    """
    # Parse UTC timestamp
    utc_dt = datetime.fromisoformat(utc_timestamp.replace('Z', '+00:00'))

    # Convert to target timezone
    try:
        tz = ZoneInfo(timezone_str)
    except ZoneInfoNotFoundError as e:
        raise ValueError(f"Invalid timezone '{timezone_str}': {e}")

    local_dt = utc_dt.astimezone(tz)

    # Parse day start time
    hours, minutes, seconds = parse_time(day_start)
    day_start_time = time(hours, minutes, seconds)

    # Get local time
    local_time = local_dt.time()

    # Calculate subjective date
    if local_time < day_start_time:
        # Before day start, so it's still the previous day
        from datetime import timedelta
        subjective_dt = local_dt.date() - timedelta(days=1)
    else:
        # After day start, so it's the current day
        subjective_dt = local_dt.date()

    return subjective_dt.isoformat()


def get_current_subjective_date(timezone_str: str, day_start: str) -> str:
    """Get current subjective date based on current time.

    Args:
        timezone_str: IANA timezone string
        day_start: Day start time in HH:MM or HH:MM:SS format

    Returns:
        Current subjective date as YYYY-MM-DD string
    """
    from datetime import timezone
    now_utc = datetime.now(timezone.utc).isoformat()
    return calculate_subjective_date(now_utc, timezone_str, day_start)
