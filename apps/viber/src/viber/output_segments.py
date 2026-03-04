"""Helpers for the CLI's cross-cutting output segment spacing rules."""

from __future__ import annotations

import sys
from typing import TextIO

# This module intentionally owns a tiny bit of process-wide state so segment
# starts can follow the CLI spacing spec without threading "is first segment"
# through unrelated layers. The shared state is a pragmatic escape hatch to
# avoid a much larger refactor across the REPL, startup flow, and prompts.
_has_started_segment = False


def reset_output_segments() -> None:
    global _has_started_segment
    _has_started_segment = False


def start_output_segment(*, file: TextIO | None = None) -> None:
    global _has_started_segment

    target = sys.stdout if file is None else file
    if _has_started_segment:
        print(file=target)
    _has_started_segment = True
