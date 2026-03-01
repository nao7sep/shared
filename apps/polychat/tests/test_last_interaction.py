"""Tests for last-interaction shape resolution and retry context building."""

from polychat.chat import (
    get_retry_context_for_last_interaction,
    resolve_last_interaction_span,
)
from polychat.domain.chat import ChatDocument


def _chat(messages: list[dict]) -> ChatDocument:
    return ChatDocument.from_raw({"metadata": {}, "messages": messages})


def test_resolve_last_interaction_user_assistant() -> None:
    doc = _chat([
        {"role": "user", "content": "u1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "u2"},
        {"role": "assistant", "content": "a2"},
    ])

    span = resolve_last_interaction_span(doc.messages)

    assert span is not None
    assert span.kind == "user_assistant"
    assert span.replace_start == 2
    assert span.replace_end == 3
    assert span.context_end_exclusive == 2


def test_resolve_last_interaction_user_error() -> None:
    doc = _chat([
        {"role": "user", "content": "u1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "u2"},
        {"role": "error", "content": "e2"},
    ])

    span = resolve_last_interaction_span(doc.messages)

    assert span is not None
    assert span.kind == "user_error"
    assert span.replace_start == 2
    assert span.replace_end == 3
    assert span.context_end_exclusive == 2


def test_resolve_last_interaction_standalone_error() -> None:
    doc = _chat([
        {"role": "user", "content": "u1"},
        {"role": "assistant", "content": "a1"},
        {"role": "error", "content": "e2"},
    ])

    span = resolve_last_interaction_span(doc.messages)

    assert span is not None
    assert span.kind == "standalone_error"
    assert span.replace_start == 2
    assert span.replace_end == 2
    assert span.context_end_exclusive == 2


def test_resolve_last_interaction_returns_none_for_incomplete_tail_user() -> None:
    doc = _chat([
        {"role": "user", "content": "u1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "u2"},
    ])

    assert resolve_last_interaction_span(doc.messages) is None


def test_retry_context_excludes_trailing_user_assistant_pair() -> None:
    doc = _chat([
        {"role": "user", "content": "u1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "u2"},
        {"role": "assistant", "content": "a2"},
    ])

    context = get_retry_context_for_last_interaction(doc)

    assert [message.content for message in context] == [["u1"], ["a1"]]


def test_retry_context_excludes_trailing_user_error_pair() -> None:
    doc = _chat([
        {"role": "user", "content": "u1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "u2"},
        {"role": "error", "content": "e2"},
    ])

    context = get_retry_context_for_last_interaction(doc)

    assert [message.content for message in context] == [["u1"], ["a1"]]


def test_retry_context_excludes_trailing_standalone_error_only() -> None:
    doc = _chat([
        {"role": "user", "content": "u1"},
        {"role": "assistant", "content": "a1"},
        {"role": "error", "content": "e2"},
    ])

    context = get_retry_context_for_last_interaction(doc)

    assert [message.content for message in context] == [["u1"], ["a1"]]
