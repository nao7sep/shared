"""Structured logging primitives for PolyChat."""

from .events import (
    before_sleep_log_event,
    build_run_log_path,
    estimate_message_chars,
    extract_http_error_context,
    log_event,
    setup_logging,
    summarize_command_args,
    summarize_text,
)
from .formatter import StructuredTextFormatter
from .sanitization import sanitize_error_message

__all__ = [
    "StructuredTextFormatter",
    "before_sleep_log_event",
    "build_run_log_path",
    "estimate_message_chars",
    "extract_http_error_context",
    "log_event",
    "sanitize_error_message",
    "setup_logging",
    "summarize_command_args",
    "summarize_text",
]
