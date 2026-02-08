"""Tests for /purge command."""

import pytest
from unittest.mock import AsyncMock, patch
from poly_chat.commands import CommandHandler


@pytest.fixture
def mock_session_with_messages():
    """Create a mock session with sample messages."""
    return {
        "current_ai": "claude",
        "current_model": "claude-haiku-4-5",
        "helper_ai": "claude",
        "helper_model": "claude-haiku-4-5",
        "profile": {
            "default_ai": "claude",
            "models": {"claude": "claude-haiku-4-5"},
            "input_mode": "quick",
            "api_keys": {}
        },
        "chat": {
            "metadata": {},
            "messages": [
                {
                    "timestamp": "2026-01-01T10:00:00+00:00",
                    "role": "user",
                    "content": ["Message 1"]
                },
                {
                    "timestamp": "2026-01-01T10:00:01+00:00",
                    "role": "assistant",
                    "model": "claude-haiku-4-5",
                    "content": ["Response 1"]
                },
                {
                    "timestamp": "2026-01-01T10:00:02+00:00",
                    "role": "user",
                    "content": ["Message 2"]
                },
                {
                    "timestamp": "2026-01-01T10:00:03+00:00",
                    "role": "assistant",
                    "model": "claude-haiku-4-5",
                    "content": ["Response 2"]
                },
            ]
        },
        "message_hex_ids": {
            0: "a3f",
            1: "b2c",
            2: "c1d",
            3: "d4e"
        },
        "hex_id_set": {"a3f", "b2c", "c1d", "d4e"},
        "chat_path": "/tmp/test-chat.json"
    }


@pytest.mark.asyncio
async def test_purge_no_args(mock_session_with_messages):
    """Test /purge without arguments."""
    handler = CommandHandler(mock_session_with_messages)

    result = await handler.purge_messages("")

    assert "Usage: /purge" in result


@pytest.mark.asyncio
async def test_purge_single_message(mock_session_with_messages):
    """Test purging a single message."""
    handler = CommandHandler(mock_session_with_messages)

    # Mock save_chat
    with patch("poly_chat.commands.save_chat", new_callable=AsyncMock) as mock_save:
        result = await handler.purge_messages("b2c")

        # Check result
        assert "⚠️  WARNING" in result
        assert "Purged 1 message" in result
        assert "[b2c]" in result
        assert "breaks conversation context" in result

        # Verify message was deleted
        messages = mock_session_with_messages["chat"]["messages"]
        assert len(messages) == 3

        # Verify save was called
        assert mock_save.called


@pytest.mark.asyncio
async def test_purge_multiple_messages(mock_session_with_messages):
    """Test purging multiple messages."""
    handler = CommandHandler(mock_session_with_messages)

    with patch("poly_chat.commands.save_chat", new_callable=AsyncMock):
        result = await handler.purge_messages("a3f c1d")

        # Check result
        assert "Purged 2 message" in result
        assert "[a3f]" in result
        assert "[c1d]" in result

        # Verify messages were deleted
        messages = mock_session_with_messages["chat"]["messages"]
        assert len(messages) == 2


@pytest.mark.asyncio
async def test_purge_invalid_hex_id(mock_session_with_messages):
    """Test purging with invalid hex ID."""
    handler = CommandHandler(mock_session_with_messages)

    result = await handler.purge_messages("zzz")

    assert "Invalid hex ID: zzz" in result

    # Verify no messages were deleted
    messages = mock_session_with_messages["chat"]["messages"]
    assert len(messages) == 4


@pytest.mark.asyncio
async def test_purge_reassigns_hex_ids(mock_session_with_messages):
    """Test that purge reassigns hex IDs to remaining messages."""
    handler = CommandHandler(mock_session_with_messages)

    with patch("poly_chat.commands.save_chat", new_callable=AsyncMock):
        # Purge middle message
        await handler.purge_messages("b2c")

        # Hex IDs should be reassigned
        hex_map = mock_session_with_messages["message_hex_ids"]
        messages = mock_session_with_messages["chat"]["messages"]

        # Should have hex IDs for all 3 remaining messages
        assert len(hex_map) == len(messages)
        assert len(hex_map) == 3


@pytest.mark.asyncio
async def test_purge_no_messages(mock_session_with_messages):
    """Test purge with no messages in chat."""
    mock_session_with_messages["chat"]["messages"] = []

    handler = CommandHandler(mock_session_with_messages)

    result = await handler.purge_messages("a3f")

    assert "No messages to purge" in result


@pytest.mark.asyncio
async def test_purge_updates_hex_id_set(mock_session_with_messages):
    """Test that purge updates the hex_id_set."""
    handler = CommandHandler(mock_session_with_messages)

    initial_set_size = len(mock_session_with_messages["hex_id_set"])

    with patch("poly_chat.commands.save_chat", new_callable=AsyncMock):
        await handler.purge_messages("a3f")

        # Hex ID set should be cleared and regenerated
        hex_id_set = mock_session_with_messages["hex_id_set"]

        # Should have new IDs for remaining 3 messages
        assert len(hex_id_set) == 3


@pytest.mark.asyncio
async def test_purge_saves_chat(mock_session_with_messages):
    """Test that purge saves chat after deletion."""
    handler = CommandHandler(mock_session_with_messages)

    with patch("poly_chat.commands.save_chat", new_callable=AsyncMock) as mock_save:
        await handler.purge_messages("a3f")

        # Verify save_chat was called with correct arguments
        mock_save.assert_called_once()
        call_args = mock_save.call_args
        assert call_args[0][0] == "/tmp/test-chat.json"
        assert call_args[0][1] == mock_session_with_messages["chat"]


@pytest.mark.asyncio
async def test_purge_multiple_messages_order_independent(mock_session_with_messages):
    """Test that purge works regardless of hex ID order."""
    handler = CommandHandler(mock_session_with_messages)

    with patch("poly_chat.commands.save_chat", new_callable=AsyncMock):
        # Provide IDs in non-sequential order
        result = await handler.purge_messages("d4e a3f")

        # Should still delete both
        assert "Purged 2 message" in result

        # Verify correct messages remain
        messages = mock_session_with_messages["chat"]["messages"]
        assert len(messages) == 2
