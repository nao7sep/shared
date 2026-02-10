"""Logging utilities for PolyChat."""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


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
            "system_prompt_path",
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
            "system_prompt_path",
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
            "search",
            "search_requested",
            "system_prompt_path",
        ],
        "ai_response": [
            "ts",
            "level",
            "mode",
            "provider",
            "model",
            "chat_file",
            "latency_ms",
            "output_chars",
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "search",
            "search_requested",
            "search_executed",
            "search_evidence",
            "citations",
            "citation_urls",
            "search_results",
            "thought_chars",
            "thoughts",
        ],
        "ai_error": [
            "ts",
            "level",
            "mode",
            "provider",
            "model",
            "chat_file",
            "latency_ms",
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
            "output_chars",
            "input_tokens",
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
            "error_type",
            "error",
        ],
        # Generic log messages
        "log": [
            "ts",
            "level",
            "logger",
            "message",
        ],
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Emit a blank line between entries without adding extra trailing lines.
        self._first_entry = True

    def _format_value(self, value: Any, max_len: int = 400) -> str:
        value_str = sanitize_error_message(str(value))
        if len(value_str) > max_len:
            value_str = value_str[: max_len - 3] + "..."
        return value_str.replace("\n", "\\n")

    def _field_max_len(self, key: str) -> int:
        """Allow larger payloads for search-related fields."""
        if key == "citation_urls":
            return 4000
        if key == "search_results":
            return 10000
        if key == "search_evidence":
            return 2000
        if key == "thoughts":
            return 20000
        return 400

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
            base["event"] = "log"
            base["message"] = sanitize_error_message(message)

        event_name = str(base.pop("event", "log"))
        lines = [f"=== {event_name} ==="]

        ordered_keys = self._ordered_keys(event_name, base)
        for key in ordered_keys:
            lines.append(f"{key}: {self._format_value(base[key], max_len=self._field_max_len(key))}")

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


def summarize_text(text: Any, max_len: int = 160) -> str:
    """Return a short, redacted summary for logs."""
    if text is None:
        return ""
    normalized = " ".join(str(text).split())
    redacted = sanitize_error_message(normalized)
    if len(redacted) <= max_len:
        return redacted
    return redacted[: max_len - 3] + "..."


def summarize_command_args(command: str, args: str) -> str:
    """Summarize command args while avoiding sensitive/free-form text leakage."""
    safe_preview_commands = {
        "open",
        "switch",
        "close",
        "new",
        "rename",
        "delete",
        "model",
        "helper",
        "timeout",
        "system",
        "history",
        "show",
        "safe",
        "input",
        "status",
        "title",
        "summary",
    }
    if not args.strip():
        return ""
    if command in safe_preview_commands:
        return summarize_text(args, max_len=100)
    return "[redacted]"


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


def chat_file_label(chat_path: Optional[str]) -> Optional[str]:
    """Return a compact chat file label for logs."""
    if not chat_path:
        return None
    return Path(chat_path).name


def log_event(event: str, level: int = logging.INFO, **fields: Any) -> None:
    """Emit a structured log event."""
    payload = {
        "ts": datetime.now().astimezone().isoformat(),
        "event": event,
    }
    for key, value in fields.items():
        payload[key] = _to_log_safe(value)
    logging.log(level, json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


def build_run_log_path(logs_dir: str) -> str:
    """Build a unique run log path in the configured logs directory."""
    logs_dir_path = Path(logs_dir)
    logs_dir_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    base_name = f"poly-chat_{timestamp}"
    candidate = logs_dir_path / f"{base_name}.log"

    suffix = 1
    while candidate.exists():
        candidate = logs_dir_path / f"{base_name}_{suffix}.log"
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
