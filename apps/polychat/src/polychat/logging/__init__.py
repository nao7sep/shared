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
from .schema import DEFAULT_EVENT_KEY_ORDER, EVENT_KEY_ORDER, LOG_PATH_FIELDS

__all__ = [
    "DEFAULT_EVENT_KEY_ORDER",
    "EVENT_KEY_ORDER",
    "LOG_PATH_FIELDS",
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
