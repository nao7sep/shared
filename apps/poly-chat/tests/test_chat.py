"""Tests for chat module."""

import pytest
from poly_chat.chat import (
    add_user_message,
    add_assistant_message,
    add_error_message,
    delete_message_and_following,
    update_metadata,
    get_messages_for_ai
)


def test_add_user_message(sample_chat):
    """Test adding user message."""
    add_user_message(sample_chat, "New message")

    messages = sample_chat["messages"]
    assert len(messages) == 3
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == ["New message"]


def test_add_assistant_message(sample_chat):
    """Test adding assistant message."""
    add_assistant_message(sample_chat, "Response text", "gpt-5-mini")

    messages = sample_chat["messages"]
    assert len(messages) == 3
    assert messages[-1]["role"] == "assistant"
    assert messages[-1]["content"] == ["Response text"]
    assert messages[-1]["model"] == "gpt-5-mini"


def test_add_error_message(sample_chat):
    """Test adding error message."""
    add_error_message(
        sample_chat,
        "API Error",
        {"error_code": 429}
    )

    messages = sample_chat["messages"]
    assert len(messages) == 3
    assert messages[-1]["role"] == "error"
    assert messages[-1]["content"] == ["API Error"]
    assert messages[-1]["details"]["error_code"] == 429


def test_delete_message_and_following(sample_chat):
    """Test deleting messages."""
    # Add more messages
    add_user_message(sample_chat, "Message 3")
    add_assistant_message(sample_chat, "Response 3", "gpt-5-mini")

    # Delete from index 1 onwards
    count = delete_message_and_following(sample_chat, 1)

    assert count == 3  # Deleted 3 messages
    assert len(sample_chat["messages"]) == 1


def test_delete_message_invalid_index(sample_chat):
    """Test deleting with invalid index."""
    with pytest.raises(IndexError):
        delete_message_and_following(sample_chat, 10)


def test_update_metadata(sample_chat):
    """Test updating metadata."""
    update_metadata(sample_chat, title="New Title", summary="New Summary")

    assert sample_chat["metadata"]["title"] == "New Title"
    assert sample_chat["metadata"]["summary"] == "New Summary"


def test_update_metadata_invalid_field(sample_chat):
    """Test updating invalid metadata field."""
    with pytest.raises(ValueError):
        update_metadata(sample_chat, invalid_field="value")


def test_get_messages_for_ai(sample_chat):
    """Test getting messages for AI (excluding errors)."""
    # Add error message
    add_error_message(sample_chat, "Error")

    # Get messages for AI
    messages = get_messages_for_ai(sample_chat)

    # Should only have user and assistant messages
    assert len(messages) == 2
    assert all(msg["role"] in ("user", "assistant") for msg in messages)


def test_get_messages_for_ai_with_limit(sample_chat):
    """Test getting limited messages for AI."""
    # Add more messages
    add_user_message(sample_chat, "Message 3")
    add_assistant_message(sample_chat, "Response 3", "gpt-5-mini")

    # Get last 2 messages
    messages = get_messages_for_ai(sample_chat, max_messages=2)

    assert len(messages) == 2
    assert messages[0]["content"] == ["Message 3"]
