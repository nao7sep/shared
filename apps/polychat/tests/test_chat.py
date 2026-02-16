"""Tests for chat module."""

import json
import pytest
from polychat.chat import (
    load_chat,
    save_chat,
    add_user_message,
    add_assistant_message,
    add_error_message,
    delete_message_and_following,
    update_metadata,
    get_messages_for_ai
)


def test_load_chat_nonexistent_file(tmp_path):
    """Test loading chat from non-existent file returns empty structure."""
    chat_path = tmp_path / "nonexistent.json"

    chat = load_chat(str(chat_path))

    # Should return empty structure
    assert "metadata" in chat
    assert "messages" in chat
    assert chat["messages"] == []
    assert chat["metadata"]["title"] is None
    assert chat["metadata"]["created_at"] is None


def test_load_chat_valid_file(tmp_path):
    """Test loading chat from valid JSON file."""
    chat_path = tmp_path / "valid.json"

    # Create valid chat file
    chat_data = {
        "metadata": {
            "title": "Test Chat",
            "summary": None,
            "system_prompt": None,
            "created_at": "2026-02-02T00:00:00+00:00",
            "updated_at": "2026-02-02T00:00:00+00:00",
        },
        "messages": [
            {
                "timestamp": "2026-02-02T00:00:00+00:00",
                "role": "user",
                "content": ["Hello"]
            }
        ]
    }

    with open(chat_path, "w", encoding="utf-8") as f:
        json.dump(chat_data, f)

    chat = load_chat(str(chat_path))

    assert chat["metadata"]["title"] == "Test Chat"
    assert len(chat["messages"]) == 1
    assert chat["messages"][0]["role"] == "user"


def test_load_chat_invalid_json(tmp_path):
    """Test loading chat from file with invalid JSON."""
    chat_path = tmp_path / "invalid.json"
    chat_path.write_text("{ invalid json }")

    with pytest.raises(ValueError, match="Invalid JSON"):
        load_chat(str(chat_path))


def test_load_chat_missing_metadata(tmp_path):
    """Test loading chat with missing metadata field."""
    chat_path = tmp_path / "missing_metadata.json"

    # Missing "metadata" field
    chat_data = {"messages": []}

    with open(chat_path, "w", encoding="utf-8") as f:
        json.dump(chat_data, f)

    with pytest.raises(ValueError, match="Invalid chat history file structure"):
        load_chat(str(chat_path))


def test_load_chat_missing_messages(tmp_path):
    """Test loading chat with missing messages field."""
    chat_path = tmp_path / "missing_messages.json"

    # Missing "messages" field
    chat_data = {
        "metadata": {
            "title": None,
            "summary": None,
            "system_prompt": None,
            "created_at": None,
            "updated_at": None,
        }
    }

    with open(chat_path, "w", encoding="utf-8") as f:
        json.dump(chat_data, f)

    with pytest.raises(ValueError, match="Invalid chat history file structure"):
        load_chat(str(chat_path))


def test_load_chat_normalizes_string_content_and_metadata_defaults(tmp_path):
    """String content should normalize to line arrays and metadata keys should be backfilled."""
    chat_path = tmp_path / "legacy_string_content.json"
    chat_data = {
        "metadata": {"title": "Legacy"},
        "messages": [
            {
                "role": "user",
                "content": "Hello\nWorld",
            }
        ],
    }
    with open(chat_path, "w", encoding="utf-8") as f:
        json.dump(chat_data, f)

    loaded = load_chat(str(chat_path))

    assert loaded["messages"][0]["content"] == ["Hello", "World"]
    assert loaded["metadata"]["title"] == "Legacy"
    assert loaded["metadata"]["summary"] is None
    assert loaded["metadata"]["system_prompt"] is None
    assert loaded["metadata"]["created_at"] is None
    assert loaded["metadata"]["updated_at"] is None


def test_load_chat_rejects_invalid_metadata_type(tmp_path):
    """Metadata must be an object."""
    chat_path = tmp_path / "invalid_metadata_type.json"
    chat_data = {"metadata": [], "messages": []}
    with open(chat_path, "w", encoding="utf-8") as f:
        json.dump(chat_data, f)

    with pytest.raises(ValueError, match="Invalid chat metadata"):
        load_chat(str(chat_path))


def test_load_chat_rejects_invalid_messages_type(tmp_path):
    """Messages must be a list."""
    chat_path = tmp_path / "invalid_messages_type.json"
    chat_data = {"metadata": {}, "messages": {"role": "user"}}
    with open(chat_path, "w", encoding="utf-8") as f:
        json.dump(chat_data, f)

    with pytest.raises(ValueError, match="Invalid chat messages"):
        load_chat(str(chat_path))


def test_load_chat_rejects_invalid_message_content_type(tmp_path):
    """Message content must be string or list."""
    chat_path = tmp_path / "invalid_message_content_type.json"
    chat_data = {
        "metadata": {},
        "messages": [
            {"role": "user", "content": {"nested": "invalid"}},
        ],
    }
    with open(chat_path, "w", encoding="utf-8") as f:
        json.dump(chat_data, f)

    with pytest.raises(ValueError, match="Invalid message content"):
        load_chat(str(chat_path))


def test_load_chat_casts_list_content_entries_to_strings(tmp_path):
    """List content entries should be normalized to strings."""
    chat_path = tmp_path / "list_content_cast.json"
    chat_data = {
        "metadata": {},
        "messages": [
            {"role": "assistant", "content": ["ok", 1, None]},
        ],
    }
    with open(chat_path, "w", encoding="utf-8") as f:
        json.dump(chat_data, f)

    loaded = load_chat(str(chat_path))
    assert loaded["messages"][0]["content"] == ["ok", "1", "None"]


@pytest.mark.asyncio
async def test_save_chat_basic(tmp_path):
    """Test basic chat save operation."""
    chat_path = tmp_path / "save_test.json"

    chat_data = {
        "metadata": {
            "title": "Save Test",
            "summary": None,
            "system_prompt": None,
            "created_at": None,
            "updated_at": None,
        },
        "messages": [
            {
                "timestamp": "2026-02-02T00:00:00+00:00",
                "role": "user",
                "content": ["Test message"]
            }
        ]
    }

    await save_chat(str(chat_path), chat_data)

    # Verify file was created
    assert chat_path.exists()

    # Verify content
    with open(chat_path, "r", encoding="utf-8") as f:
        saved_data = json.load(f)

    assert saved_data["metadata"]["title"] == "Save Test"
    assert len(saved_data["messages"]) == 1


@pytest.mark.asyncio
async def test_save_chat_creates_directory(tmp_path):
    """Test that save_chat creates parent directory if missing."""
    chat_path = tmp_path / "nested" / "dir" / "chat.json"

    chat_data = {
        "metadata": {
            "title": None,
            "summary": None,
            "system_prompt": None,
            "created_at": None,
            "updated_at": None,
        },
        "messages": []
    }

    await save_chat(str(chat_path), chat_data)

    # Verify directory and file were created
    assert chat_path.exists()
    assert chat_path.parent.exists()


@pytest.mark.asyncio
async def test_save_chat_updates_timestamps(tmp_path):
    """Test that save_chat updates timestamps."""
    chat_path = tmp_path / "timestamps.json"

    chat_data = {
        "metadata": {
            "title": None,
            "summary": None,
            "system_prompt": None,
            "created_at": None,
            "updated_at": None,
        },
        "messages": []
    }

    await save_chat(str(chat_path), chat_data)

    # Both should be set
    assert chat_data["metadata"]["created_at"] is not None
    assert chat_data["metadata"]["updated_at"] is not None

    # They should be the same on first save
    assert chat_data["metadata"]["created_at"] == chat_data["metadata"]["updated_at"]

    # Save again
    original_created = chat_data["metadata"]["created_at"]
    await save_chat(str(chat_path), chat_data)

    # created_at should not change, updated_at should
    assert chat_data["metadata"]["created_at"] == original_created
    assert chat_data["metadata"]["updated_at"] != original_created


@pytest.mark.asyncio
async def test_save_chat_json_format(tmp_path):
    """Test that saved JSON is properly formatted."""
    chat_path = tmp_path / "formatted.json"

    chat_data = {
        "metadata": {
            "title": "Formatted Test",
            "summary": None,
            "system_prompt": None,
            "created_at": None,
            "updated_at": None,
        },
        "messages": []
    }

    await save_chat(str(chat_path), chat_data)

    # Read raw content
    content = chat_path.read_text(encoding="utf-8")

    # Should be indented (not minified)
    assert "  " in content

    # Should be valid JSON
    json.loads(content)


@pytest.mark.asyncio
async def test_save_chat_does_not_persist_hex_id(tmp_path):
    """Runtime-only message hex IDs should not be written to disk."""
    chat_path = tmp_path / "no-hex-id.json"
    chat_data = {
        "metadata": {
            "title": "Hex Test",
            "summary": None,
            "system_prompt": None,
            "created_at": None,
            "updated_at": None,
        },
        "messages": [
            {
                "timestamp": "2026-02-02T00:00:00+00:00",
                "role": "user",
                "content": ["Hello"],
                "hex_id": "a3f",
            }
        ],
    }

    await save_chat(str(chat_path), chat_data)

    with open(chat_path, "r", encoding="utf-8") as f:
        saved_data = json.load(f)

    assert "hex_id" not in saved_data["messages"][0]
    # In-memory object keeps runtime field for session UX.
    assert chat_data["messages"][0]["hex_id"] == "a3f"


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


def test_add_assistant_message_with_citations(sample_chat):
    """Test adding assistant message with search citations."""
    citations = [{"url": "https://example.com", "title": "Example"}]
    add_assistant_message(sample_chat, "Response text", "gpt-5-mini", citations=citations)

    messages = sample_chat["messages"]
    assert len(messages) == 3
    assert messages[-1]["role"] == "assistant"
    assert messages[-1]["model"] == "gpt-5-mini"
    assert messages[-1]["citations"] == citations


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
