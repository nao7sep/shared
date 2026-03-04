"""Minimal helper for CLI segment boundary spacing.

This module intentionally keeps tiny process-local state so callers can say
"a new segment starts here" without threading `is_first_segment` through the
CLI stack or sprinkling manual separator `print()` calls everywhere.
"""

from __future__ import annotations

_segments_started = 0


def reset_output_segments() -> None:
    """Reset process-local segment tracking for a fresh top-level run."""
    global _segments_started
    _segments_started = 0


def begin_output_segment() -> None:
    """Emit the segment separator when this is not the first segment."""
    global _segments_started
    if _segments_started > 0:
        print()
    _segments_started += 1
