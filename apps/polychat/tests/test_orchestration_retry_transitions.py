"""Tests for retry-apply transition helper logic."""

import pytest

from polychat.orchestration.retry_transitions import (
    build_retry_replacement_plan,
    resolve_replace_start,
)


def test_resolve_replace_start_prefers_preceding_user() -> None:
    messages = [
        {"role": "user", "content": "q"},
        {"role": "assistant", "content": "a"},
    ]
    assert resolve_replace_start(messages, 1) == 0


def test_resolve_replace_start_keeps_target_when_not_preceded_by_user() -> None:
    messages = [
        {"role": "user", "content": "q1"},
        {"role": "assistant", "content": "a1"},
        {"role": "error", "content": "timeout"},
    ]
    assert resolve_replace_start(messages, 2) == 2


def test_build_retry_replacement_plan_preserves_hex_ids_for_user_assistant_pair() -> None:
    messages = [
        {"role": "user", "content": "q", "hex_id": "u123"},
        {"role": "assistant", "content": "a", "hex_id": "a456"},
    ]
    retry_attempt = {
        "user_msg": "retry question",
        "assistant_msg": "retry answer",
    }

    plan = build_retry_replacement_plan(
        messages,
        1,
        retry_attempt,
        "claude-haiku-4-5",
        timestamp_factory=lambda: "2026-02-24T00:00:00+00:00",
    )

    assert plan.replace_start == 0
    assert plan.replace_end == 1
    assert plan.replacement_messages[0]["hex_id"] == "u123"
    assert plan.replacement_messages[1]["hex_id"] == "a456"
    assert plan.replacement_messages[1]["model"] == "claude-haiku-4-5"
    assert plan.replacement_messages[0]["content"] == ["retry question"]
    assert plan.replacement_messages[1]["content"] == ["retry answer"]


def test_build_retry_replacement_plan_for_trailing_error_does_not_backtrack() -> None:
    messages = [
        {"role": "user", "content": "q1"},
        {"role": "assistant", "content": "a1"},
        {"role": "error", "content": "timeout", "hex_id": "e999"},
    ]
    retry_attempt = {
        "user_msg": "retry user",
        "assistant_msg": "retry assistant",
        "citations": [{"url": "https://example.com", "title": "Example"}],
    }

    plan = build_retry_replacement_plan(
        messages,
        2,
        retry_attempt,
        "gpt-5-mini",
        timestamp_factory=lambda: "2026-02-24T00:00:00+00:00",
    )

    assert plan.replace_start == 2
    assert plan.replace_end == 2
    assert "hex_id" not in plan.replacement_messages[0]
    assert plan.replacement_messages[1]["hex_id"] == "e999"
    assert plan.replacement_messages[1]["citations"] == [
        {"url": "https://example.com", "title": "Example"}
    ]


def test_build_retry_replacement_plan_rejects_invalid_target_index() -> None:
    messages = [{"role": "assistant", "content": "a"}]

    with pytest.raises(ValueError, match="Retry target is no longer valid"):
        build_retry_replacement_plan(
            messages,
            5,
            {"user_msg": "u", "assistant_msg": "a"},
            "claude-haiku-4-5",
        )
