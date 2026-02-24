"""Helpers for retry-apply message replacement transitions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from ..formatting.text import text_to_lines

TimestampFactory = Callable[[], str]


@dataclass(slots=True, frozen=True)
class RetryReplacementPlan:
    """Planned slice replacement for applying one retry attempt."""

    replace_start: int
    replace_end: int
    replacement_messages: list[dict[str, Any]]


def _utc_timestamp() -> str:
    """Create a UTC ISO timestamp for synthesized replacement messages."""
    return datetime.now(timezone.utc).isoformat()


def resolve_replace_start(messages: list[dict[str, Any]], target_index: int) -> int:
    """Resolve where replacement should start for retry apply."""
    if target_index > 0 and messages[target_index - 1].get("role") == "user":
        return target_index - 1
    return target_index


def build_retry_replacement_plan(
    messages: list[dict[str, Any]],
    target_index: int,
    retry_attempt: dict[str, Any],
    current_model: str,
    *,
    timestamp_factory: Optional[TimestampFactory] = None,
) -> RetryReplacementPlan:
    """Build a deterministic replacement plan for one retry attempt."""
    if target_index < 0 or target_index >= len(messages):
        raise ValueError("Retry target is no longer valid")

    make_timestamp = timestamp_factory or _utc_timestamp
    replace_start = resolve_replace_start(messages, target_index)

    existing_user_hex_id = (
        messages[replace_start].get("hex_id")
        if replace_start != target_index
        else None
    )
    existing_assistant_hex_id = messages[target_index].get("hex_id")

    replaced_user_message: dict[str, Any] = {
        "timestamp": make_timestamp(),
        "role": "user",
        "content": text_to_lines(retry_attempt["user_msg"]),
    }
    if isinstance(existing_user_hex_id, str):
        replaced_user_message["hex_id"] = existing_user_hex_id

    replaced_assistant_message: dict[str, Any] = {
        "timestamp": make_timestamp(),
        "role": "assistant",
        "model": current_model,
        "content": text_to_lines(retry_attempt["assistant_msg"]),
    }
    citations = retry_attempt.get("citations")
    if citations:
        replaced_assistant_message["citations"] = citations
    if isinstance(existing_assistant_hex_id, str):
        replaced_assistant_message["hex_id"] = existing_assistant_hex_id

    return RetryReplacementPlan(
        replace_start=replace_start,
        replace_end=target_index,
        replacement_messages=[replaced_user_message, replaced_assistant_message],
    )
