"""Structured plaintext log formatter implementation."""

from __future__ import annotations

import json
import logging
from typing import Any

from ..time_utils import utc_now_iso as _utc_now_roundtrip
from .schema import DEFAULT_EVENT_KEY_ORDER, EVENT_KEY_ORDER


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
        preferred = EVENT_KEY_ORDER.get(event_name, DEFAULT_EVENT_KEY_ORDER)
        preferred_present = [k for k in preferred if k in data and data[k] is not None]
        remaining = sorted(
            k for k in data.keys() if k not in preferred and data[k] is not None
        )
        return preferred_present + remaining

    def format(self, record: logging.LogRecord) -> str:
        base: dict[str, Any] = {
            "ts_utc": _utc_now_roundtrip(),
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
