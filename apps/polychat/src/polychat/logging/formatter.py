"""Structured plaintext log formatter implementation."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any


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
        "estimated_cost",
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
        "estimated_cost",
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


class StructuredTextFormatter(logging.Formatter):
    """Format all log records as human-readable structured blocks."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Emit a blank line between entries without adding extra trailing lines.
        self._first_entry = True

    @staticmethod
    def _format_value(value: Any) -> str:
        value_str = str(value)
        return value_str.replace("\n", "\\n")

    @staticmethod
    def _ordered_keys(event_name: str, data: dict[str, Any]) -> list[str]:
        preferred = EVENT_KEY_ORDER.get(event_name, ["ts", "level", "logger"])
        preferred_present = [k for k in preferred if k in data and data[k] is not None]
        remaining = sorted(
            k for k in data.keys() if k not in preferred and data[k] is not None
        )
        return preferred_present + remaining

    def format(self, record: logging.LogRecord) -> str:
        base: dict[str, Any] = {
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
                base["http_status"] = int(status) if isinstance(status, int) else str(status)
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
