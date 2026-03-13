from __future__ import annotations


# This module intentionally keeps one tiny piece of process-wide CLI output state.
# It centralizes the "later segments own the blank line" rule and avoids threading
# first-segment flags through many prompt, workflow, and error paths.
_has_started_segment = False


def start_segment() -> None:
    global _has_started_segment

    if _has_started_segment:
        print()
    _has_started_segment = True


def reset_segments() -> None:
    global _has_started_segment

    _has_started_segment = False
