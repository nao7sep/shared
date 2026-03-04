"""Helpers for tk's CLI output segment spacing."""

from typing import TextIO

# This module intentionally owns a tiny bit of process-wide state so segment
# starts can follow the CLI spacing spec without threading "is first segment"
# flags through the CLI bootstrap, banner, and REPL entry paths.
_has_started_segment = False


def reset_output_segments() -> None:
    """Reset segment spacing state for a new CLI run."""
    global _has_started_segment
    _has_started_segment = False


def start_output_segment(*, file: TextIO | None = None) -> None:
    """Emit the segment separator owned by the later segment."""
    global _has_started_segment

    if _has_started_segment:
        print(file=file)
    _has_started_segment = True
