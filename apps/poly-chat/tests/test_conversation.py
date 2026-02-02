"""Tests for conversation module."""

import pytest
from poly_chat.conversation import (
    add_user_message,
    add_assistant_message,
    add_error_message,
    delete_message_and_following,
    update_metadata,
    get_messages_for_ai
)


def test_add_user_message(sample_conversation):
    """Test adding user message."""
    add_user_message(sample_conversation, "New message")

    messages = sample_conversation["messages"]
    assert len(messages) == 3
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == ["New message"]


def test_add_assistant_message(sample_conversation):
    """Test adding assistant message."""
    add_assistant_message(sample_conversation, "Response text", "gpt-4o")

    messages = sample_conversation["messages"]
    assert len(messages) == 3
    assert messages[-1]["role"] == "assistant"
    assert messages[-1]["content"] == ["Response text"]
    assert messages[-1]["model"] == "gpt-4o"


def test_add_error_message(sample_conversation):
    """Test adding error message."""
    add_error_message(
        sample_conversation,
        "API Error",
        {"error_code": 429}
    )

    messages = sample_conversation["messages"]
    assert len(messages) == 3
    assert messages[-1]["role"] == "error"
    assert messages[-1]["content"] == ["API Error"]
    assert messages[-1]["details"]["error_code"] == 429


def test_delete_message_and_following(sample_conversation):
    """Test deleting messages."""
    # Add more messages
    add_user_message(sample_conversation, "Message 3")
    add_assistant_message(sample_conversation, "Response 3", "gpt-4o")

    # Delete from index 1 onwards
    count = delete_message_and_following(sample_conversation, 1)

    assert count == 3  # Deleted 3 messages
    assert len(sample_conversation["messages"]) == 1


def test_delete_message_invalid_index(sample_conversation):
    """Test deleting with invalid index."""
    with pytest.raises(IndexError):
        delete_message_and_following(sample_conversation, 10)


def test_update_metadata(sample_conversation):
    """Test updating metadata."""
    update_metadata(sample_conversation, title="New Title", summary="New Summary")

    assert sample_conversation["metadata"]["title"] == "New Title"
    assert sample_conversation["metadata"]["summary"] == "New Summary"


def test_update_metadata_invalid_field(sample_conversation):
    """Test updating invalid metadata field."""
    with pytest.raises(ValueError):
        update_metadata(sample_conversation, invalid_field="value")


def test_get_messages_for_ai(sample_conversation):
    """Test getting messages for AI (excluding errors)."""
    # Add error message
    add_error_message(sample_conversation, "Error")

    # Get messages for AI
    messages = get_messages_for_ai(sample_conversation)

    # Should only have user and assistant messages
    assert len(messages) == 2
    assert all(msg["role"] in ("user", "assistant") for msg in messages)


def test_get_messages_for_ai_with_limit(sample_conversation):
    """Test getting limited messages for AI."""
    # Add more messages
    add_user_message(sample_conversation, "Message 3")
    add_assistant_message(sample_conversation, "Response 3", "gpt-4o")

    # Get last 2 messages
    messages = get_messages_for_ai(sample_conversation, max_messages=2)

    assert len(messages) == 2
    assert messages[0]["content"] == ["Message 3"]
