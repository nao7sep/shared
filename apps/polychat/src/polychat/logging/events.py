"""Structured event emission and logging helpers."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from ..constants import APP_NAME, DATETIME_FORMAT_FILENAME, LOG_FILE_EXTENSION
from .formatter import StructuredTextFormatter

_LOG_PATH_FIELDS = {
    "profile_file",
    "chat_file",
    "log_file",
    "chats_dir",
    "logs_dir",
    "previous_chat_file",
    "old_chat_file",
    "new_chat_file",
    "system_prompt",
    # Backward compatibility if an older call site still emits this key.
    "system_prompt_path",
}


def _to_log_safe(value: Any) -> Any:
    """Convert values to JSON-serializable, log-safe representations."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _to_log_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_log_safe(v) for v in value]
    return str(value)


def _resolve_log_path(path_value: str) -> str:
    """Resolve a path-ish string to absolute form for log readability."""
    value = path_value.strip()
    if not value:
        return path_value
    try:
        from ..path_utils import map_path

        # Use path_utils for all special prefixes (~, @) and absolute paths.
        return map_path(value)
    except Exception:
        # If path mapping fails, return original value.
        return path_value


def extract_http_error_context(error: Exception) -> dict[str, Any]:
    """Extract safe HTTP context from an exception when available."""
    context: dict[str, Any] = {}

    response = getattr(error, "response", None)
    request = getattr(error, "request", None)
    if request is None and response is not None:
        request = getattr(response, "request", None)

    # Extract request info.
    if request is not None:
        method = getattr(request, "method", None)
        if method:
            context["http_method"] = str(method)
        url = getattr(request, "url", None)
        if url:
            context["http_url"] = str(url)

    # Extract response info.
    if response is not None:
        version = getattr(response, "http_version", None)
        if version:
            context["http_version"] = str(version)

        status = getattr(response, "status_code", None)
        if status is not None:
            context["http_status"] = status

        reason = getattr(response, "reason_phrase", None)
        if reason:
            context["http_reason"] = str(reason)
    else:
        status = getattr(error, "status_code", None)
        if status is not None:
            context["http_status"] = status

    return context


def summarize_text(text: Any) -> str:
    """Return normalized summary text for logs."""
    if text is None:
        return ""
    return " ".join(str(text).split())


def summarize_command_args(_command: str, args: str) -> str:
    """Summarize command args for logs."""
    if not args.strip():
        return ""
    return summarize_text(args)


def estimate_message_chars(messages: list[dict]) -> int:
    """Estimate total character length across chat messages."""
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, list):
            total += sum(len(str(part)) for part in content)
        else:
            total += len(str(content))
    return total


def log_event(event: str, level: int = logging.INFO, **fields: Any) -> None:
    """Emit a structured log event."""
    payload = {
        "ts": datetime.now().astimezone().isoformat(),
        "event": event,
    }
    for key, value in fields.items():
        if key in _LOG_PATH_FIELDS and isinstance(value, str):
            value = _resolve_log_path(value)
        payload[key] = _to_log_safe(value)
    logging.log(level, json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


def before_sleep_log_event(
    *,
    provider: str,
    operation: str,
    level: int = logging.WARNING,
):
    """Build a tenacity before_sleep callback that emits structured retry logs."""

    def _callback(retry_state: Any) -> None:
        try:
            outcome = getattr(retry_state, "outcome", None)
            next_action = getattr(retry_state, "next_action", None)
            if outcome is None or next_action is None:
                return

            payload: dict[str, Any] = {
                "provider": provider,
                "operation": operation,
                "attempt": getattr(retry_state, "attempt_number", None),
                "sleep_sec": getattr(next_action, "sleep", None),
            }

            fn = getattr(retry_state, "fn", None)
            if fn is not None:
                payload["function"] = getattr(fn, "__name__", str(fn))

            if getattr(outcome, "failed", False):
                error = outcome.exception()
                payload["result"] = "raised"
                if error is not None:
                    payload["error_type"] = type(error).__name__
                    payload["error"] = str(error)
            else:
                payload["result"] = "returned"

            log_event("provider_retry", level=level, **payload)
        except Exception:
            # Retry logging must never break request flow.
            return

    return _callback


def build_run_log_path(logs_dir: str) -> str:
    """Build a unique run log path in the configured logs directory."""
    logs_dir_path = Path(logs_dir)
    logs_dir_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime(DATETIME_FORMAT_FILENAME)
    base_name = f"{APP_NAME}_{timestamp}"
    candidate = logs_dir_path / f"{base_name}{LOG_FILE_EXTENSION}"

    suffix = 1
    while candidate.exists():
        candidate = logs_dir_path / f"{base_name}_{suffix}{LOG_FILE_EXTENSION}"
        suffix += 1

    return str(candidate)


def setup_logging(log_file: Optional[str] = None) -> None:
    """Set up logging configuration."""
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(str(log_path), encoding="utf-8")
        handler.setFormatter(StructuredTextFormatter())
        logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    else:
        logging.disable(logging.CRITICAL)
