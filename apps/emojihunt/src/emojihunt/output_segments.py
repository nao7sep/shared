"""Helpers for emojihunt's CLI output segment spacing.

Follows the shared CLI output formatting spec: every segment emits exactly one
leading empty line, except the first segment which emits none.
"""

from __future__ import annotations

import sys
from typing import TextIO

_has_started_segment = False


def reset_output_segments() -> None:
    """Reset segment spacing state for a new CLI run."""
    global _has_started_segment
    _has_started_segment = False


def start_output_segment(*, file: TextIO | None = None) -> None:
    """Emit the segment separator owned by the later segment."""
    global _has_started_segment

    target = sys.stdout if file is None else file
    if _has_started_segment:
        print(file=target)
    _has_started_segment = True
