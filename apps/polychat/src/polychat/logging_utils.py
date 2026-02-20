"""Logging utilities for PolyChat."""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .constants import APP_NAME, DATETIME_FORMAT_FILENAME, LOG_FILE_EXTENSION


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

def sanitize_error_message(error_msg: str) -> str:
    """Sanitize error messages to remove sensitive information."""
    sanitized = re.sub(r"sk-[A-Za-z0-9]{10,}", "[REDACTED_API_KEY]", error_msg)
    sanitized = re.sub(r"sk-ant-[A-Za-z0-9-]{10,}", "[REDACTED_API_KEY]", sanitized)
    sanitized = re.sub(r"xai-[A-Za-z0-9]{10,}", "[REDACTED_API_KEY]", sanitized)
    sanitized = re.sub(r"pplx-[A-Za-z0-9]{10,}", "[REDACTED_API_KEY]", sanitized)
    sanitized = re.sub(
        r"Bearer\s+[A-Za-z0-9_\-\.]{20,}",
        "Bearer [REDACTED_TOKEN]",
        sanitized,
    )
    sanitized = re.sub(
        r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
        "[REDACTED_JWT]",
        sanitized,
    )
    return sanitized


class StructuredTextFormatter(logging.Formatter):
    """Format all log records as human-readable structured blocks."""

    EVENT_KEY_ORDER: dict[str, list[str]] = {
        # Application lifecycle events
        "app_start": [
            "ts",
            "level",
            "assistant_provider",
            "assistant_model",
            "helper_provider",
            "helper_model",
            "profile_file",
            "chat_file",
            "log_file",
            "chats_dir",
            "logs_dir",
            "input_mode",
            "timeout",
            "system_prompt",
        ],
        "app_stop": [
            "ts",
            "level",
            "reason",
            "uptime_ms",
            "error_type",
            "error",
        ],
        "session_start": [
            "ts",
            "level",
            "assistant_provider",
            "assistant_model",
            "helper_provider",
            "helper_model",
            "profile_file",
            "chat_file",
            "log_file",
            "chats_dir",
            "logs_dir",
            "input_mode",
            "timeout",
            "system_prompt",
            "chat_title",
            "chat_summary",
            "message_count",
        ],
        "session_stop": [
            "ts",
            "level",
            "reason",
            "chat_file",
            "message_count",
        ],
        # Command execution events
        "command_exec": [
            "ts",
            "level",
            "command",
            "args_summary",
            "chat_file",
            "elapsed_ms",
        ],
        "command_error": [
            "ts",
            "level",
            "command",
            "args_summary",
            "chat_file",
            "error_type",
            "error",
        ],
        # Chat management events
        "chat_switch": [
            "ts",
            "level",
            "chat_file",
            "trigger",
            "previous_chat_file",
            "message_count",
        ],
        "chat_close": [
            "ts",
            "level",
            "chat_file",
            "message_count",
        ],
        "chat_rename": [
            "ts",
            "level",
            "old_chat_file",
            "new_chat_file",
        ],
        "chat_delete": [
            "ts",
            "level",
            "chat_file",
        ],
        # AI interaction events
        "ai_request": [
            "ts",
            "level",
            "mode",
            "provider",
            "model",
            "chat_file",
            "message_count",
            "input_chars",
            "has_system_prompt",
        ],
        "ai_response": [
            "ts",
            "level",
            "mode",
            "provider",
            "model",
            "chat_file",
            "latency_ms",
            "ttft_ms",
            "output_chars",
            "input_tokens",
            "cached_tokens",
            "cache_write_tokens",
            "output_tokens",
            "total_tokens",
        ],
        "ai_error": [
            "ts",
            "level",
            "mode",
            "provider",
            "model",
            "chat_file",
            "latency_ms",
            "http_method",
            "http_url",
            "http_version",
            "http_status",
            "http_reason",
            "error_type",
            "error",
        ],
        # Helper AI events
        "helper_ai_request": [
            "ts",
            "level",
            "task",
            "provider",
            "model",
            "message_count",
            "input_chars",
            "has_system_prompt",
        ],
        "helper_ai_response": [
            "ts",
            "level",
            "task",
            "provider",
            "model",
            "latency_ms",
            "ttft_ms",
            "output_chars",
            "input_tokens",
            "cached_tokens",
            "cache_write_tokens",
            "output_tokens",
            "total_tokens",
        ],
        "helper_ai_error": [
            "ts",
            "level",
            "task",
            "provider",
            "model",
            "latency_ms",
            "http_method",
            "http_url",
            "http_version",
            "http_status",
            "http_reason",
            "error_type",
            "error",
        ],
        # Provider validation events
        "provider_validation_error": [
            "ts",
            "level",
            "provider",
            "model",
            "phase",
            "chat_file",
            "http_method",
            "http_url",
            "http_version",
            "http_status",
            "http_reason",
            "error_type",
            "error",
        ],
        "provider_log": [
            "ts",
            "level",
            "provider",
            "message",
        ],
        "provider_retry": [
            "ts",
            "level",
            "provider",
            "operation",
            "attempt",
            "sleep_sec",
            "result",
            "error_type",
            "error",
            "function",
        ],
        "httpx_request": [
            "ts",
            "level",
            "logger",
            "http_method",
            "http_url",
            "http_version",
            "http_status",
            "http_reason",
        ],
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Emit a blank line between entries without adding extra trailing lines.
        self._first_entry = True

    def _format_value(self, value: Any) -> str:
        value_str = str(value)
        return value_str.replace("\n", "\\n")

    def _ordered_keys(self, event_name: str, data: dict[str, Any]) -> list[str]:
        preferred = self.EVENT_KEY_ORDER.get(event_name, ["ts", "level", "logger"])
        preferred_present = [k for k in preferred if k in data and data[k] is not None]
        remaining = sorted(
            k for k in data.keys() if k not in preferred and data[k] is not None
        )
        return preferred_present + remaining

    def format(self, record: logging.LogRecord) -> str:
        base = {
            "ts": datetime.now().astimezone().isoformat(),
            "level": record.levelname,
            "logger": record.name,
        }

        message = record.getMessage()
        parsed = None
        if message.startswith("{") and message.endswith("}"):
            try:
                parsed = json.loads(message)
            except Exception:
                parsed = None

        if isinstance(parsed, dict):
            base.update(parsed)
        else:
            # Decode known structured runtime logs emitted by httpx.
            if (
                record.name == "httpx"
                and isinstance(record.args, tuple)
                and len(record.args) == 5
                and str(record.msg) == 'HTTP Request: %s %s "%s %d %s"'
            ):
                method, url, version, status, reason = record.args
                base["event"] = "httpx_request"
                base["http_method"] = str(method)
                base["http_url"] = str(url)
                base["http_version"] = str(version)
                base["http_status"] = status
                base["http_reason"] = str(reason)
            else:
                base["event"] = record.name
                base["message"] = message

        event_name = str(base.pop("event", record.name))
        lines = [f"=== {event_name} ==="]

        ordered_keys = self._ordered_keys(event_name, base)
        for key in ordered_keys:
            lines.append(f"{key}: {self._format_value(base[key])}")

        if record.exc_info:
            lines.append("traceback:")
            lines.append(self.formatException(record.exc_info))

        body = "\n".join(lines)
        if self._first_entry:
            self._first_entry = False
            return body
        return "\n" + body


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
        from .path_utils import map_path

        # Use path_utils for all special prefixes (~, @) and absolute paths
        return map_path(value)
    except Exception:
        # If path mapping fails, return original value
        return path_value


def extract_http_error_context(error: Exception) -> dict[str, Any]:
    """Extract safe HTTP context from an exception when available."""
    context: dict[str, Any] = {}

    response = getattr(error, "response", None)
    request = getattr(error, "request", None)
    if request is None and response is not None:
        request = getattr(response, "request", None)

    # Extract request info
    if request is not None:
        method = getattr(request, "method", None)
        if method:
            context["http_method"] = str(method)
        url = getattr(request, "url", None)
        if url:
            context["http_url"] = str(url)

    # Extract response info
    if response is not None:
        # HTTP version
        version = getattr(response, "http_version", None)
        if version:
            context["http_version"] = str(version)

        # Status code
        status = getattr(response, "status_code", None)
        if status is not None:
            context["http_status"] = status

        # Reason phrase
        reason = getattr(response, "reason_phrase", None)
        if reason:
            context["http_reason"] = str(reason)
    else:
        # Fallback: try to get status from error directly
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
