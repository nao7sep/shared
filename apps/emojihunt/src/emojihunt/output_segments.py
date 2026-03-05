from collections.abc import Callable

OutputFn = Callable[[str], None]

# Process-wide CLI formatting state for the single-spacing rule:
# each segment emits one leading empty line except the first.
_has_started_segment = False


def reset_segment_state() -> None:
    global _has_started_segment
    _has_started_segment = False


def start_segment(output_fn: OutputFn = print) -> None:
    global _has_started_segment
    if _has_started_segment:
        output_fn("")
    _has_started_segment = True
