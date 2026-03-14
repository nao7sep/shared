"""Tests for typed chat domain models."""

from polychat.domain.chat import ChatDocument, ChatMessage


def test_chat_document_from_raw_normalizes_content_and_metadata() -> None:
    raw = {
        "metadata": {"title": "Legacy"},
        "messages": [
            {"role": "user", "content": "Hello\nWorld", "hex_id": "a3f"},
        ],
    }

    document = ChatDocument.from_raw(raw, strip_runtime_hex_id=True)
    payload = document.to_dict(include_runtime_hex_id=False)

    assert payload["metadata"]["title"] == "Legacy"
    assert payload["metadata"]["summary"] is None
    assert payload["messages"][0]["content"] == ["Hello", "World"]
    assert "hex_id" not in payload["messages"][0]


def test_chat_document_to_dict_orders_top_level_and_metadata_fields() -> None:
    raw = {
        "metadata": {
            "title": "Legacy",
            "custom": "keep-me",
        },
        "messages": [],
    }

    document = ChatDocument.from_raw(raw)
    payload = document.to_dict(include_runtime_hex_id=False)

    assert list(payload.keys()) == ["metadata", "messages"]
    assert list(payload["metadata"].keys()) == [
        "title",
        "summary",
        "system_prompt",
        "created_utc",
        "updated_utc",
        "custom",
    ]


def test_chat_document_touch_updated_utc_sets_created_and_updated() -> None:
    document = ChatDocument.empty()
    updated_utc = document.touch_updated_utc()

    assert document.metadata.created_utc == updated_utc
    assert document.metadata.updated_utc == updated_utc


def test_chat_message_to_dict_includes_runtime_hex_id_when_requested() -> None:
    message = ChatMessage.new_user("hello")
    message.hex_id = "a3f"

    runtime_payload = message.to_dict(include_runtime_hex_id=True)
    persist_payload = message.to_dict(include_runtime_hex_id=False)

    assert runtime_payload["hex_id"] == "a3f"
    assert "hex_id" not in persist_payload


def test_chat_message_to_dict_orders_user_fields() -> None:
    message = ChatMessage.new_user("hello")
    payload = message.to_dict(include_runtime_hex_id=False)

    assert list(payload.keys()) == ["timestamp_utc", "role", "content"]


def test_chat_message_to_dict_orders_assistant_fields() -> None:
    message = ChatMessage.new_assistant(
        "hello",
        model="gpt-5-mini",
        citations=[{"title": "Example", "url": "https://example.com"}],
    )
    payload = message.to_dict(include_runtime_hex_id=False)

    assert list(payload.keys()) == [
        "timestamp_utc",
        "role",
        "model",
        "content",
        "citations",
    ]


def test_chat_message_to_dict_orders_citation_fields() -> None:
    message = ChatMessage.new_assistant(
        "hello",
        model="gpt-5-mini",
        citations=[
            {
                "url": "https://example.com",
                "title": "Example",
                "number": 1,
            }
        ],
    )

    payload = message.to_dict(include_runtime_hex_id=False)

    assert list(payload["citations"][0].keys()) == ["number", "title", "url"]


def test_chat_document_roundtrip_canonicalizes_citation_field_order() -> None:
    raw = {
        "metadata": {},
        "messages": [
            {
                "role": "assistant",
                "content": ["hello"],
                "citations": [
                    {
                        "title": "Example",
                        "url": "https://example.com",
                        "number": 1,
                    }
                ],
            }
        ],
    }

    document = ChatDocument.from_raw(raw)
    payload = document.to_dict(include_runtime_hex_id=False)

    assert list(payload["messages"][0]["citations"][0].keys()) == [
        "number",
        "title",
        "url",
    ]


def test_chat_message_to_dict_orders_error_fields() -> None:
    message = ChatMessage.new_error("boom", details={"error_code": 429})
    payload = message.to_dict(include_runtime_hex_id=False)

    assert list(payload.keys()) == [
        "timestamp_utc",
        "role",
        "content",
        "details",
    ]
