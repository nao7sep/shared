"""Tests for shared provider logging helpers."""

from __future__ import annotations

import logging
from unittest.mock import patch

from polychat.ai.provider_logging import (
    api_error_after_retries_message,
    authentication_failed_message,
    bad_request_message,
    log_provider_error,
    unexpected_error_message,
)


def test_authentication_failed_message() -> None:
    error = RuntimeError("invalid key")
    assert authentication_failed_message(error) == "Authentication failed: invalid key"


def test_bad_request_message_with_and_without_detail() -> None:
    error = ValueError("bad payload")
    assert bad_request_message(error) == "Bad request: bad payload"
    assert bad_request_message(error, detail="check params") == "Bad request (check params): bad payload"


def test_retry_and_unexpected_message_templates() -> None:
    error = TimeoutError("request timed out")
    assert api_error_after_retries_message(error) == "API error after retries: TimeoutError: request timed out"
    assert unexpected_error_message(error) == "Unexpected error: TimeoutError: request timed out"


def test_log_provider_error_emits_structured_event() -> None:
    with patch("polychat.ai.provider_logging.log_event") as mock_log_event:
        log_provider_error("openai", "Authentication failed: bad key")

    mock_log_event.assert_called_once_with(
        "provider_log",
        level=logging.ERROR,
        provider="openai",
        message="Authentication failed: bad key",
    )
