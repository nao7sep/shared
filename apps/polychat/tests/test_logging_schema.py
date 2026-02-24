"""Tests for logging schema compatibility and formatter ordering."""

from __future__ import annotations

import json
import logging
from unittest.mock import patch

from polychat.logging import EVENT_KEY_ORDER, LOG_PATH_FIELDS, StructuredTextFormatter
from polychat.logging.events import log_event


def _formatted_keys(output: str) -> list[str]:
    keys: list[str] = []
    for line in output.splitlines():
        if line.startswith("==="):
            continue
        if ": " in line:
            key, _ = line.split(": ", 1)
            keys.append(key)
    return keys


def test_ai_response_order_matches_schema_prefix() -> None:
    formatter = StructuredTextFormatter()
    payload = {
        "event": "ai_response",
        "ts": "2026-02-24T00:00:00+00:00",
        "level": "INFO",
        "mode": "normal",
        "provider": "openai",
        "model": "gpt-5-mini",
        "chat_file": "/tmp/chat.json",
        "latency_ms": 123,
        "ttft_ms": 45,
        "output_chars": 100,
        "input_tokens": 200,
        "cached_tokens": 50,
        "cache_write_tokens": 0,
        "output_tokens": 300,
        "total_tokens": 500,
        "estimated_cost": 0.001,
        "zzz_extra": "z",
        "aaa_extra": "a",
    }
    record = logging.LogRecord(
        name="polychat.repl",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=json.dumps(payload),
        args=(),
        exc_info=None,
    )

    output = formatter.format(record)
    keys = _formatted_keys(output)
    expected_prefix = EVENT_KEY_ORDER["ai_response"]

    assert keys[: len(expected_prefix)] == expected_prefix
    assert keys[len(expected_prefix) :] == sorted(keys[len(expected_prefix) :])


def test_provider_retry_order_matches_schema_prefix() -> None:
    formatter = StructuredTextFormatter()
    payload = {
        "event": "provider_retry",
        "ts": "2026-02-24T00:00:00+00:00",
        "level": "WARNING",
        "provider": "openai",
        "operation": "_create_response",
        "attempt": 2,
        "sleep_sec": 1.5,
        "result": "raised",
        "error_type": "RateLimitError",
        "error": "too many requests",
        "function": "_create_response",
        "misc": "extra",
    }
    record = logging.LogRecord(
        name="polychat.logging",
        level=logging.WARNING,
        pathname=__file__,
        lineno=1,
        msg=json.dumps(payload),
        args=(),
        exc_info=None,
    )

    output = formatter.format(record)
    keys = _formatted_keys(output)
    expected_prefix = EVENT_KEY_ORDER["provider_retry"]

    assert keys[: len(expected_prefix)] == expected_prefix
    assert keys[len(expected_prefix) :] == sorted(keys[len(expected_prefix) :])


def test_log_event_resolves_backward_compatible_path_key() -> None:
    with (
        patch("polychat.logging.events._resolve_log_path") as mock_resolve,
        patch("polychat.logging.events.logging.log") as mock_logging_log,
    ):
        mock_resolve.side_effect = lambda value: f"/resolved/{value.strip()}"

        log_event(
            "app_start",
            profile_file="~/profile.json",
            system_prompt_path="@/prompt.txt",
            non_path_field="~/not-resolved",
        )

    assert mock_resolve.call_count == 2
    message_json = mock_logging_log.call_args.args[1]
    payload = json.loads(message_json)
    assert payload["profile_file"] == "/resolved/~/profile.json"
    assert payload["system_prompt_path"] == "/resolved/@/prompt.txt"
    assert payload["non_path_field"] == "~/not-resolved"


def test_schema_keeps_compatibility_fields() -> None:
    assert "system_prompt_path" in LOG_PATH_FIELDS
    assert "cached_tokens" in EVENT_KEY_ORDER["ai_response"]
    assert "cache_write_tokens" in EVENT_KEY_ORDER["ai_response"]
