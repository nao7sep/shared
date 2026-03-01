"""Chat message mutation and query helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Sequence

from ..ai.types import Citation
from ..domain.chat import ChatDocument, ChatMessage


LastInteractionKind = Literal[
    "user_assistant",
    "user_error",
    "standalone_error",
]


@dataclass(slots=True, frozen=True)
class LastInteractionSpan:
    """Resolved slice boundaries for the current last interaction."""

    kind: LastInteractionKind
    replace_start: int
    replace_end: int
    context_end_exclusive: int


def add_user_message(data: ChatDocument, content: str) -> None:
    """Add user message to chat."""
    message = ChatMessage.new_user(content)
    data.messages.append(message)


def add_assistant_message(
    data: ChatDocument,
    content: str,
    model: str,
    citations: list[Citation] | None = None,
) -> None:
    """Add assistant message to chat."""
    message = ChatMessage.new_assistant(
        content,
        model=model,
        citations=citations,
    )
    data.messages.append(message)


def add_error_message(
    data: ChatDocument, content: str, details: dict[str, Any] | None = None
) -> None:
    """Add error message to chat."""
    message = ChatMessage.new_error(content, details=details)
    data.messages.append(message)


def delete_message_and_following(data: ChatDocument, index: int) -> int:
    """Delete message at index and all following messages."""
    messages = data.messages

    if index < 0 or index >= len(messages):
        raise IndexError(f"Message index {index} out of range")

    deleted_count = len(messages) - index
    data.messages = messages[:index]

    return deleted_count


def update_metadata(data: ChatDocument, **kwargs: object) -> None:
    """Update chat metadata."""
    for key, value in kwargs.items():
        if hasattr(data.metadata, key):
            setattr(data.metadata, key, value)
        else:
            raise ValueError(f"Unknown metadata field: {key}")


def filter_messages_for_ai(
    messages: Sequence[ChatMessage],
    max_messages: int | None = None,
) -> list[ChatMessage]:
    """Return only user/assistant messages for provider context."""
    ai_messages = [msg for msg in messages if msg.role in ("user", "assistant")]

    if max_messages is not None:
        ai_messages = ai_messages[-max_messages:]

    return ai_messages


def get_messages_for_ai(
    data: ChatDocument, max_messages: int | None = None
) -> list[ChatMessage]:
    """Get messages formatted for AI (excluding error messages)."""
    return filter_messages_for_ai(data.messages, max_messages=max_messages)


def resolve_last_interaction_span(
    messages: Sequence[ChatMessage],
) -> LastInteractionSpan | None:
    """Resolve the current last-interaction shape and slice bounds."""
    if not messages:
        return None

    last_index = len(messages) - 1
    last_message = messages[last_index]

    if last_message.role == "assistant":
        if last_index == 0 or messages[last_index - 1].role != "user":
            return None
        return LastInteractionSpan(
            kind="user_assistant",
            replace_start=last_index - 1,
            replace_end=last_index,
            context_end_exclusive=last_index - 1,
        )

    if last_message.role == "error":
        if last_index > 0 and messages[last_index - 1].role == "user":
            return LastInteractionSpan(
                kind="user_error",
                replace_start=last_index - 1,
                replace_end=last_index,
                context_end_exclusive=last_index - 1,
            )
        return LastInteractionSpan(
            kind="standalone_error",
            replace_start=last_index,
            replace_end=last_index,
            context_end_exclusive=last_index,
        )

    return None


def get_retry_context_for_last_interaction(data: ChatDocument) -> list[ChatMessage]:
    """Get retry context excluding the interaction currently being retried."""
    interaction_span = resolve_last_interaction_span(data.messages)
    if interaction_span is None:
        return get_messages_for_ai(data)

    committed_prefix = data.messages[: interaction_span.context_end_exclusive]
    return filter_messages_for_ai(committed_prefix)
