"""Typed chat domain models and serialization helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ..ai.types import Citation

REQUIRED_METADATA_KEYS = (
    "title",
    "summary",
    "system_prompt",
    "created_utc",
    "updated_utc",
)


def _utc_now_roundtrip() -> str:
    """Return a high-precision UTC timestamp with explicit UTC marker."""
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def _text_to_lines(text: str) -> list[str]:
    """Convert multiline text to line array with trimming."""
    lines = text.split("\n")

    start = 0
    for index, line in enumerate(lines):
        if line.strip():
            start = index
            break
    else:
        return []

    end = len(lines)
    for index in range(len(lines) - 1, -1, -1):
        if lines[index].strip():
            end = index + 1
            break

    return lines[start:end]


def _normalize_content(raw_content: Any) -> list[str]:
    """Normalize message content to list[str]."""
    if isinstance(raw_content, str):
        return _text_to_lines(raw_content)
    if isinstance(raw_content, list):
        return [str(part) for part in raw_content]
    raise ValueError("Invalid message content: expected string or list")


@dataclass(slots=True)
class ChatMetadata:
    """Structured chat metadata payload."""

    title: str | None = None
    summary: str | None = None
    system_prompt: str | None = None
    created_utc: str | None = None
    updated_utc: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_raw(cls, raw_metadata: Any) -> ChatMetadata:
        """Validate metadata shape and backfill missing known keys."""
        if not isinstance(raw_metadata, dict):
            raise ValueError("Invalid chat metadata: expected object")

        metadata = dict(raw_metadata)
        extras = {
            key: value
            for key, value in metadata.items()
            if key not in REQUIRED_METADATA_KEYS
        }
        return cls(
            title=metadata.get("title"),
            summary=metadata.get("summary"),
            system_prompt=metadata.get("system_prompt"),
            created_utc=metadata.get("created_utc"),
            updated_utc=metadata.get("updated_utc"),
            extras=extras,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize metadata to persisted dict shape."""
        payload = {
            "title": self.title,
            "summary": self.summary,
            "system_prompt": self.system_prompt,
            "created_utc": self.created_utc,
            "updated_utc": self.updated_utc,
        }
        payload.update(self.extras)
        return payload


@dataclass(slots=True, frozen=True)
class ChatListEntry:
    """Structured record returned by list_chats()."""

    filename: str
    path: str
    title: str | None
    created_utc: str | None
    updated_utc: str | None
    message_count: int


@dataclass(slots=True)
class RetryAttempt:
    """Structured retry attempt stored during retry mode."""

    user_msg: str
    assistant_msg: str
    citations: list[Citation] | None = None


@dataclass(slots=True)
class ChatMessage:
    """Structured message payload in chat history."""

    role: str
    content: list[str]
    timestamp_utc: str | None = None
    model: str | None = None
    citations: list[Citation] | None = None
    details: dict[str, Any] | None = None
    hex_id: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_raw(
        cls,
        raw_message: Any,
        *,
        index: int | None = None,
        strip_runtime_hex_id: bool = False,
    ) -> ChatMessage:
        """Create a typed chat message from raw dict payload."""
        if not isinstance(raw_message, dict):
            idx = f" at index {index}" if index is not None else ""
            raise ValueError(f"Invalid chat message{idx}: expected object")
        if "content" not in raw_message:
            idx = f" at index {index}" if index is not None else ""
            raise ValueError(f"Invalid chat message{idx}: missing content")

        message = dict(raw_message)
        extras = {
            key: value
            for key, value in message.items()
            if key
            not in {
                "timestamp_utc",
                "role",
                "content",
                "model",
                "citations",
                "details",
                "hex_id",
            }
        }

        citations_payload = message.get("citations")
        citations: list[Citation] | None = None
        if isinstance(citations_payload, list):
            normalized: list[Citation] = []
            for citation in citations_payload:
                if isinstance(citation, dict):
                    number = citation.get("number")
                    record: Citation = {
                        "title": citation.get("title"),
                        "url": citation.get("url"),
                    }
                    if isinstance(number, int):
                        record["number"] = number
                    normalized.append(record)
            citations = normalized if normalized else None

        details_payload = message.get("details")
        details = details_payload if isinstance(details_payload, dict) else None

        return cls(
            timestamp_utc=message.get("timestamp_utc"),
            role=str(message.get("role", "")),
            content=_normalize_content(message.get("content")),
            model=message.get("model"),
            citations=citations,
            details=details,
            hex_id=None if strip_runtime_hex_id else message.get("hex_id"),
            extras=extras,
        )

    @classmethod
    def new_user(cls, content: str) -> ChatMessage:
        """Create a user message with current UTC timestamp."""
        return cls(
            timestamp_utc=_utc_now_roundtrip(),
            role="user",
            content=_text_to_lines(content),
        )

    @classmethod
    def new_assistant(
        cls,
        content: str,
        *,
        model: str,
        citations: list[Citation] | None = None,
    ) -> ChatMessage:
        """Create an assistant message with current UTC timestamp."""
        return cls(
            timestamp_utc=_utc_now_roundtrip(),
            role="assistant",
            model=model,
            content=_text_to_lines(content),
            citations=citations,
        )

    @classmethod
    def new_error(
        cls,
        content: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> ChatMessage:
        """Create an error message with current UTC timestamp."""
        return cls(
            timestamp_utc=_utc_now_roundtrip(),
            role="error",
            content=_text_to_lines(content),
            details=details,
        )

    def to_dict(self, *, include_runtime_hex_id: bool = True) -> dict[str, Any]:
        """Serialize chat message to persisted dict shape."""
        payload: dict[str, Any] = {
            "timestamp_utc": self.timestamp_utc,
            "role": self.role,
        }

        if self.role == "assistant":
            if self.model is not None:
                payload["model"] = self.model
            payload["content"] = list(self.content)
            if self.citations:
                payload["citations"] = list(self.citations)
            if self.details is not None:
                payload["details"] = dict(self.details)
        elif self.role == "error":
            payload["content"] = list(self.content)
            if self.details is not None:
                payload["details"] = dict(self.details)
            if self.model is not None:
                payload["model"] = self.model
            if self.citations:
                payload["citations"] = list(self.citations)
        else:
            payload["content"] = list(self.content)
            if self.model is not None:
                payload["model"] = self.model
            if self.citations:
                payload["citations"] = list(self.citations)
            if self.details is not None:
                payload["details"] = dict(self.details)

        if include_runtime_hex_id and self.hex_id:
            payload["hex_id"] = self.hex_id
        payload.update(self.extras)
        return payload


@dataclass(slots=True)
class ChatDocument:
    """Structured chat document with metadata + message list."""

    metadata: ChatMetadata
    messages: list[ChatMessage]

    @classmethod
    def empty(cls) -> ChatDocument:
        """Create empty chat document structure."""
        return cls(metadata=ChatMetadata(), messages=[])

    @classmethod
    def from_raw(
        cls,
        raw_document: Any,
        *,
        strip_runtime_hex_id: bool = False,
    ) -> ChatDocument:
        """Create typed chat document from raw persisted payload."""
        if not isinstance(raw_document, dict):
            raise ValueError("Invalid chat history file structure")
        if "metadata" not in raw_document or "messages" not in raw_document:
            raise ValueError("Invalid chat history file structure")

        metadata = ChatMetadata.from_raw(raw_document.get("metadata"))

        raw_messages = raw_document.get("messages")
        if not isinstance(raw_messages, list):
            raise ValueError("Invalid chat messages: expected list")

        messages = [
            ChatMessage.from_raw(
                item,
                index=index,
                strip_runtime_hex_id=strip_runtime_hex_id,
            )
            for index, item in enumerate(raw_messages)
        ]
        return cls(metadata=metadata, messages=messages)

    def touch_updated_utc(self) -> str:
        """Set and return updated timestamp in UTC ISO format."""
        now_utc = _utc_now_roundtrip()
        self.metadata.updated_utc = now_utc
        if not self.metadata.created_utc:
            self.metadata.created_utc = now_utc
        return now_utc

    def to_dict(self, *, include_runtime_hex_id: bool = True) -> dict[str, Any]:
        """Serialize chat document to dict form."""
        return {
            "metadata": self.metadata.to_dict(),
            "messages": [
                message.to_dict(include_runtime_hex_id=include_runtime_hex_id)
                for message in self.messages
            ],
        }
