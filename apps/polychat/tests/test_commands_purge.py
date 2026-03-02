"""Tests for /purge command."""

import pytest
from polychat.commands import CommandHandler
from polychat.domain.chat import ChatDocument
from polychat.session_manager import SessionManager
from test_helpers import make_profile


class FakeInteraction:
    """Deterministic async interaction adapter for command tests."""

    def __init__(self, responses: list[str] | None = None):
        self.responses = list(responses or ["yes"])

    async def prompt_text(self, prompt: str) -> str:
        if self.responses:
            return self.responses.pop(0)
        return "yes"

    async def notify(self, message: str) -> None:
        del message

    async def prompt_chat_selection(
        self,
        chats_dir: str,
        *,
        action: str = "open",
        allow_cancel: bool = True,
    ) -> str | None:
        return None


@pytest.fixture
def mock_session_manager_purge():
    """Create a mock SessionManager with sample messages for purge tests."""
    chat_data = ChatDocument.from_raw({
        "metadata": {},
        "messages": [
            {
                "timestamp_utc": "2026-02-02T10:00:00+00:00",
                "role": "user",
                "content": ["Message 1"]
            },
            {
                "timestamp_utc": "2026-02-02T10:00:01+00:00",
                "role": "assistant",
                "model": "claude-haiku-4-5",
                "content": ["Response 1"]
            },
            {
                "timestamp_utc": "2026-02-02T10:00:02+00:00",
                "role": "user",
                "content": ["Message 2"]
            },
            {
                "timestamp_utc": "2026-02-02T10:00:03+00:00",
                "role": "assistant",
                "model": "claude-haiku-4-5",
                "content": ["Response 2"]
            },
        ]
    })

    manager = SessionManager(
        profile=make_profile(
            chats_dir="/test/chats",
            logs_dir="/test/logs",
        ),
        current_ai="claude",
        current_model="claude-haiku-4-5",
        chat=chat_data,
        chat_path="/tmp/test-chat.json",
        profile_path="/test/profile.json",
        log_file="/test/log.txt",
    )

    # Set up hex IDs as the tests expect
    manager.chat.messages[0].hex_id = "a3f"
    manager.chat.messages[1].hex_id = "b2c"
    manager.chat.messages[2].hex_id = "c1d"
    manager.chat.messages[3].hex_id = "d4e"
    manager._state.hex_id_set = {"a3f", "b2c", "c1d", "d4e"}

    return manager


@pytest.fixture
def command_handler_purge(mock_session_manager_purge):
    """Create a CommandHandler for purge tests."""
    return CommandHandler(
        mock_session_manager_purge,
        interaction=FakeInteraction(["yes"] * 20),
    )


@pytest.mark.asyncio
async def test_purge_no_args(command_handler_purge, mock_session_manager_purge):
    """Test /purge without arguments."""
    handler = command_handler_purge

    result = await handler.purge_messages("")

    assert "Usage: /purge" in result


@pytest.mark.asyncio
async def test_purge_single_message(command_handler_purge, mock_session_manager_purge):
    """Test purging a single message."""
    handler = command_handler_purge

    result = await handler.purge_messages("b2c")

    # Check result
    assert "Purged 1 message" in result
    assert "[b2c]" in result

    # Verify message was deleted
    messages = mock_session_manager_purge.chat.messages
    assert len(messages) == 3


@pytest.mark.asyncio
async def test_purge_multiple_messages(command_handler_purge, mock_session_manager_purge):
    """Test purging multiple messages."""
    handler = command_handler_purge

    result = await handler.purge_messages("a3f c1d")

    # Check result
    assert "Purged 2 message" in result
    assert "[a3f]" in result
    assert "[c1d]" in result

    # Verify messages were deleted
    messages = mock_session_manager_purge.chat.messages
    assert len(messages) == 2


@pytest.mark.asyncio
async def test_purge_invalid_hex_id(command_handler_purge, mock_session_manager_purge):
    """Test purging with invalid hex ID."""
    handler = command_handler_purge

    result = await handler.purge_messages("zzz")

    assert "Invalid hex ID: zzz" in result

    # Verify no messages were deleted
    messages = mock_session_manager_purge.chat.messages
    assert len(messages) == 4


@pytest.mark.asyncio
async def test_purge_preserves_remaining_hex_ids(command_handler_purge, mock_session_manager_purge):
    """Test that purge preserves hex IDs for remaining messages."""
    handler = command_handler_purge

    original_ids = [
        msg.hex_id
        for msg in mock_session_manager_purge.chat.messages
    ]

    # Purge middle message
    await handler.purge_messages("b2c")

    # Remaining IDs should be preserved
    remaining_ids = [msg.hex_id for msg in mock_session_manager_purge.chat.messages]
    assert remaining_ids == [original_ids[0], original_ids[2], original_ids[3]]


@pytest.mark.asyncio
async def test_purge_no_messages(command_handler_purge, mock_session_manager_purge):
    """Test purge with no messages in chat."""
    mock_session_manager_purge.chat.messages = []

    handler = command_handler_purge

    result = await handler.purge_messages("a3f")

    assert "No messages to purge" in result


@pytest.mark.asyncio
async def test_purge_cleans_up_hex_ids(command_handler_purge, mock_session_manager_purge):
    """Test that purge removes hex IDs from the in-memory set."""
    handler = command_handler_purge

    await handler.purge_messages("a3f")

    hex_id_set = mock_session_manager_purge.hex_id_set

    assert "a3f" not in hex_id_set


@pytest.mark.asyncio
async def test_purge_multiple_messages_order_independent(command_handler_purge, mock_session_manager_purge):
    """Test that purge works regardless of hex ID order."""
    handler = command_handler_purge

    # Provide IDs in non-sequential order
    result = await handler.purge_messages("d4e a3f")

    # Should still delete both
    assert "Purged 2 message" in result

    # Verify correct messages remain
    messages = mock_session_manager_purge.chat.messages
    assert len(messages) == 2


@pytest.mark.asyncio
async def test_purge_cancelled_on_non_yes(command_handler_purge, mock_session_manager_purge):
    """Test purge cancellation when confirmation is not 'yes'."""
    command_handler_purge.context.interaction = FakeInteraction(["no"])

    result = await command_handler_purge.purge_messages("a3f")

    assert result == "Purge cancelled"
    assert len(mock_session_manager_purge.chat.messages) == 4
