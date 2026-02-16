"""Tests for logging utilities."""

import logging

from polychat.logging_utils import StructuredTextFormatter


def test_structured_formatter_extracts_httpx_request_fields():
    formatter = StructuredTextFormatter()
    record = logging.LogRecord(
        name="httpx",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='HTTP Request: %s %s "%s %d %s"',
        args=(
            "POST",
            "https://api.perplexity.ai/chat/completions",
            "HTTP/1.1",
            200,
            "OK",
        ),
        exc_info=None,
    )

    result = formatter.format(record)

    assert "=== httpx_request ===" in result
    assert "logger: httpx" in result
    assert "http_method: POST" in result
    assert "http_url: https://api.perplexity.ai/chat/completions" in result
    assert "http_version: HTTP/1.1" in result
    assert "http_status: 200" in result
    assert "http_reason: OK" in result
    assert "message: HTTP Request:" not in result


def test_structured_formatter_uses_logger_name_for_non_httpx_messages():
    formatter = StructuredTextFormatter()
    record = logging.LogRecord(
        name="httpx",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Arbitrary message",
        args=(),
        exc_info=None,
    )

    result = formatter.format(record)

    assert "=== httpx ===" in result
    assert "=== log ===" not in result
    assert "logger: httpx" in result
    assert "message: Arbitrary message" in result


def test_structured_formatter_uses_full_logger_name_for_non_httpx_messages():
    formatter = StructuredTextFormatter()
    record = logging.LogRecord(
        name="polychat.repl",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Unexpected command error",
        args=(),
        exc_info=None,
    )

    result = formatter.format(record)

    assert "=== polychat.repl ===" in result
    assert "=== log ===" not in result
    assert "logger: polychat.repl" in result
    assert "message: Unexpected command error" in result
