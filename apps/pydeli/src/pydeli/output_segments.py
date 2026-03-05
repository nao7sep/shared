"""Console output segment management.

Every output segment emits exactly one leading empty line except the first
segment of the process, which emits none. No segment emits a trailing empty
line.
"""

from collections.abc import Callable

OutputFn = Callable[..., None]

_has_started_segment = False


def reset_segment_state() -> None:
    global _has_started_segment
    _has_started_segment = False


def start_segment(output_fn: OutputFn = print) -> None:
    global _has_started_segment
    if _has_started_segment:
        output_fn("")
    _has_started_segment = True
