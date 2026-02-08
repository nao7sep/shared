"""Tests for /purge command."""

import pytest
from unittest.mock import AsyncMock, patch
from poly_chat.commands import CommandHandler
from src.poly_chat.session_manager import SessionManager


@pytest.fixture
def mock_session_manager_purge():
    """Create a mock SessionManager with sample messages for purge tests."""
    chat_data = {
        "metadata": {},
        "messages": [
            {
                "timestamp": "2026-02-02T10:00:00+00:00",
                "role": "user",
                "content": ["Message 1"]
            },
            {
                "timestamp": "2026-02-02T10:00:01+00:00",
                "role": "assistant",
                "model": "claude-haiku-4-5",
                "content": ["Response 1"]
            },
            {
                "timestamp": "2026-02-02T10:00:02+00:00",
                "role": "user",
                "content": ["Message 2"]
            },
            {
                "timestamp": "2026-02-02T10:00:03+00:00",
                "role": "assistant",
                "model": "claude-haiku-4-5",
                "content": ["Response 2"]
            },
        ]
    }

    manager = SessionManager(
        profile={
            "default_ai": "claude",
            "models": {"claude": "claude-haiku-4-5"},
            "input_mode": "quick",
            "api_keys": {},
            "chats_dir": "/test/chats",
            "log_dir": "/test/logs",
            "timeout": 30,
        },
        current_ai="claude",
        current_model="claude-haiku-4-5",
        chat=chat_data,
    )

    # Set up hex IDs as the tests expect
    manager._state.message_hex_ids = {
        0: "a3f",
        1: "b2c",
        2: "c1d",
        3: "d4e"
    }
    manager._state.hex_id_set = {"a3f", "b2c", "c1d", "d4e"}

    return manager


@pytest.fixture
def mock_session_dict_purge():
    """Create a mock session_dict for purge tests."""
    return {
        "profile_path": "/test/profile.json",
        "chat_path": "/tmp/test-chat.json",
        "log_file": "/test/log.txt",
    }


@pytest.fixture
def command_handler_purge(mock_session_manager_purge, mock_session_dict_purge):
    """Create a CommandHandler for purge tests."""
    return CommandHandler(mock_session_manager_purge, mock_session_dict_purge)


@pytest.mark.asyncio
async def test_purge_no_args(command_handler_purge, mock_session_manager_purge, mock_session_dict_purge):
    """Test /purge without arguments."""
    handler = command_handler_purge

    result = await handler.purge_messages("")

    assert "Usage: /purge" in result


@pytest.mark.asyncio
async def test_purge_single_message(command_handler_purge, mock_session_manager_purge, mock_session_dict_purge):
    """Test purging a single message."""
    handler = command_handler_purge

    # Mock save_chat
    with patch("poly_chat.commands.save_chat", new_callable=AsyncMock) as mock_save:
        result = await handler.purge_messages("b2c")

        # Check result
        assert "⚠️  WARNING" in result
        assert "Purged 1 message" in result
        assert "[b2c]" in result
        assert "breaks conversation context" in result

        # Verify message was deleted
        messages = mock_session_manager_purge.chat["messages"]
        assert len(messages) == 3

        # Verify save was called
        assert mock_save.called


@pytest.mark.asyncio
async def test_purge_multiple_messages(command_handler_purge, mock_session_manager_purge, mock_session_dict_purge):
    """Test purging multiple messages."""
    handler = command_handler_purge

    with patch("poly_chat.commands.save_chat", new_callable=AsyncMock):
        result = await handler.purge_messages("a3f c1d")

        # Check result
        assert "Purged 2 message" in result
        assert "[a3f]" in result
        assert "[c1d]" in result

        # Verify messages were deleted
        messages = mock_session_manager_purge.chat["messages"]
        assert len(messages) == 2


@pytest.mark.asyncio
async def test_purge_invalid_hex_id(command_handler_purge, mock_session_manager_purge, mock_session_dict_purge):
    """Test purging with invalid hex ID."""
    handler = command_handler_purge

    result = await handler.purge_messages("zzz")

    assert "Invalid hex ID: zzz" in result

    # Verify no messages were deleted
    messages = mock_session_manager_purge.chat["messages"]
    assert len(messages) == 4


@pytest.mark.asyncio
async def test_purge_reassigns_hex_ids(command_handler_purge, mock_session_manager_purge, mock_session_dict_purge):
    """Test that purge reassigns hex IDs to remaining messages."""
    handler = command_handler_purge

    with patch("poly_chat.commands.save_chat", new_callable=AsyncMock):
        # Purge middle message
        await handler.purge_messages("b2c")

        # Hex IDs should be reassigned
        hex_map = mock_session_manager_purge.message_hex_ids
        messages = mock_session_manager_purge.chat["messages"]

        # Should have hex IDs for all 3 remaining messages
        assert len(hex_map) == len(messages)
        assert len(hex_map) == 3


@pytest.mark.asyncio
async def test_purge_no_messages(command_handler_purge, mock_session_manager_purge, mock_session_dict_purge):
    """Test purge with no messages in chat."""
    mock_session_manager_purge.chat["messages"] = []

    handler = command_handler_purge

    result = await handler.purge_messages("a3f")

    assert "No messages to purge" in result


@pytest.mark.asyncio
async def test_purge_updates_hex_id_set(command_handler_purge, mock_session_manager_purge, mock_session_dict_purge):
    """Test that purge updates the hex_id_set."""
    handler = command_handler_purge

    initial_set_size = len(mock_session_manager_purge.hex_id_set)

    with patch("poly_chat.commands.save_chat", new_callable=AsyncMock):
        await handler.purge_messages("a3f")

        # Hex ID set should be cleared and regenerated
        hex_id_set = mock_session_manager_purge.hex_id_set

        # Should have new IDs for remaining 3 messages
        assert len(hex_id_set) == 3


@pytest.mark.asyncio
async def test_purge_saves_chat(command_handler_purge, mock_session_manager_purge, mock_session_dict_purge):
    """Test that purge saves chat after deletion."""
    handler = command_handler_purge

    with patch("poly_chat.commands.save_chat", new_callable=AsyncMock) as mock_save:
        await handler.purge_messages("a3f")

        # Verify save_chat was called with correct arguments
        mock_save.assert_called_once()
        call_args = mock_save.call_args
        assert call_args[0][0] == "/tmp/test-chat.json"
        assert call_args[0][1] == mock_session_manager_purge.chat


@pytest.mark.asyncio
async def test_purge_multiple_messages_order_independent(command_handler_purge, mock_session_manager_purge, mock_session_dict_purge):
    """Test that purge works regardless of hex ID order."""
    handler = command_handler_purge

    with patch("poly_chat.commands.save_chat", new_callable=AsyncMock):
        # Provide IDs in non-sequential order
        result = await handler.purge_messages("d4e a3f")

        # Should still delete both
        assert "Purged 2 message" in result

        # Verify correct messages remain
        messages = mock_session_manager_purge.chat["messages"]
        assert len(messages) == 2
