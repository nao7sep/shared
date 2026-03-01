"""Tests for retry-apply transition helper logic."""

import pytest

from polychat.chat import LastInteractionSpan
from polychat.domain.chat import ChatMessage, RetryAttempt
from polychat.orchestration.signals import build_retry_replacement_plan


def test_build_retry_replacement_plan_preserves_hex_ids_for_user_assistant_pair() -> None:
    messages = [
        ChatMessage.from_raw({"role": "user", "content": "q", "hex_id": "u123"}),
        ChatMessage.from_raw({"role": "assistant", "content": "a", "hex_id": "a456"}),
    ]
    retry_attempt = RetryAttempt(
        user_msg="retry question",
        assistant_msg="retry answer",
    )

    plan = build_retry_replacement_plan(
        messages,
        LastInteractionSpan(
            kind="user_assistant",
            replace_start=0,
            replace_end=1,
            context_end_exclusive=0,
        ),
        retry_attempt,
        "claude-haiku-4-5",
        timestamp_factory=lambda: "2026-02-24T00:00:00+00:00",
    )

    assert plan.replace_start == 0
    assert plan.replace_end == 1
    assert plan.replacement_messages[0].hex_id == "u123"
    assert plan.replacement_messages[1].hex_id == "a456"
    assert plan.replacement_messages[1].model == "claude-haiku-4-5"
    assert plan.replacement_messages[0].content == ["retry question"]
    assert plan.replacement_messages[1].content == ["retry answer"]


def test_build_retry_replacement_plan_preserves_user_and_error_hex_ids() -> None:
    messages = [
        ChatMessage.from_raw({"role": "user", "content": "q1", "hex_id": "u222"}),
        ChatMessage.from_raw({"role": "error", "content": "timeout", "hex_id": "e999"}),
    ]
    retry_attempt = RetryAttempt(
        user_msg="retry user",
        assistant_msg="retry assistant",
        citations=[{"url": "https://example.com", "title": "Example"}],
    )

    plan = build_retry_replacement_plan(
        messages,
        LastInteractionSpan(
            kind="user_error",
            replace_start=0,
            replace_end=1,
            context_end_exclusive=0,
        ),
        retry_attempt,
        "gpt-5-mini",
        timestamp_factory=lambda: "2026-02-24T00:00:00+00:00",
    )

    assert plan.replace_start == 0
    assert plan.replace_end == 1
    assert plan.replacement_messages[0].hex_id == "u222"
    assert plan.replacement_messages[1].hex_id == "e999"
    assert plan.replacement_messages[1].citations == [
        {"url": "https://example.com", "title": "Example"}
    ]


def test_build_retry_replacement_plan_for_trailing_error_generates_new_user_hex_id() -> None:
    messages = [
        ChatMessage.from_raw({"role": "user", "content": "q1"}),
        ChatMessage.from_raw({"role": "assistant", "content": "a1"}),
        ChatMessage.from_raw({"role": "error", "content": "timeout", "hex_id": "e999"}),
    ]
    retry_attempt = RetryAttempt(
        user_msg="retry user",
        assistant_msg="retry assistant",
        citations=[{"url": "https://example.com", "title": "Example"}],
    )

    plan = build_retry_replacement_plan(
        messages,
        LastInteractionSpan(
            kind="standalone_error",
            replace_start=2,
            replace_end=2,
            context_end_exclusive=2,
        ),
        retry_attempt,
        "gpt-5-mini",
        generated_user_hex_id="u777",
        timestamp_factory=lambda: "2026-02-24T00:00:00+00:00",
    )

    assert plan.replace_start == 2
    assert plan.replace_end == 2
    assert plan.replacement_messages[0].hex_id == "u777"
    assert plan.replacement_messages[1].hex_id == "e999"
    assert plan.replacement_messages[1].citations == [
        {"url": "https://example.com", "title": "Example"}
    ]


def test_build_retry_replacement_plan_rejects_invalid_target_span() -> None:
    messages = [ChatMessage.from_raw({"role": "assistant", "content": "a"})]

    with pytest.raises(ValueError, match="Retry target is no longer valid"):
        build_retry_replacement_plan(
            messages,
            LastInteractionSpan(
                kind="user_assistant",
                replace_start=4,
                replace_end=5,
                context_end_exclusive=4,
            ),
            RetryAttempt(user_msg="u", assistant_msg="a"),
            "claude-haiku-4-5",
        )
