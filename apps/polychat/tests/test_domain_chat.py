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
