"""Tests for /safe command."""

import pytest
from unittest.mock import AsyncMock, patch
from polychat.commands import CommandHandler
from polychat.domain.chat import ChatDocument
from polychat.session_manager import SessionManager
from test_helpers import make_profile


@pytest.fixture
def mock_session_manager_safe():
    """Create a mock SessionManager for safe tests."""
    chat_data = ChatDocument.from_raw({
        "metadata": {},
        "messages": [
            {
                "timestamp_utc": "2026-02-02T00:00:00+00:00",
                "role": "user",
                "content": ["Hello, my name is John Doe"]
            },
            {
                "timestamp_utc": "2026-02-02T00:00:01+00:00",
                "role": "assistant",
                "model": "claude-haiku-4-5",
                "content": ["Hi John! How can I help you?"]
            },
            {
                "timestamp_utc": "2026-02-02T00:00:02+00:00",
                "role": "user",
                "content": ["My API key is sk-abc123"]
            }
        ]
    })

    manager = SessionManager(
        profile=make_profile(
            title_prompt="/test/prompts/title.txt",
            summary_prompt="/test/prompts/summary.txt",
            safety_prompt="/test/prompts/safety.txt",
            chats_dir="/test/chats",
            logs_dir="/test/logs",
            api_keys={
                "claude": {
                    "type": "direct",
                    "value": "test-key"
                }
            },
        ),
        current_ai="claude",
        current_model="claude-haiku-4-5",
        helper_ai="claude",
        helper_model="claude-haiku-4-5",
        chat=chat_data,
        chat_path="/test/chat.json",
        profile_path="/test/profile.json",
        log_file="/test/log.txt",
    )

    # Set up hex IDs as the tests expect
    manager.chat.messages[0].hex_id = "a3f"
    manager.chat.messages[1].hex_id = "b2c"
    manager.chat.messages[2].hex_id = "c1d"
    manager._state.hex_id_set = {"a3f", "b2c", "c1d"}

    return manager


@pytest.fixture
def command_handler_safe(mock_session_manager_safe):
    """Create a CommandHandler for safe tests."""
    return CommandHandler(mock_session_manager_safe)


@pytest.mark.asyncio
async def test_safe_command_no_messages(command_handler_safe, mock_session_manager_safe):
    """Test /safe command with no messages."""
    mock_session_manager_safe.chat.messages = []
    handler = command_handler_safe

    result = await handler.check_safety("")

    assert result == "No messages to check"


@pytest.mark.asyncio
async def test_safe_command_no_open_chat(command_handler_safe, mock_session_manager_safe):
    """Test /safe when no chat is open."""
    mock_session_manager_safe.close_chat()

    result = await command_handler_safe.check_safety("")

    assert result == "No chat is currently open"


@pytest.mark.asyncio
async def test_safe_command_full_chat(command_handler_safe, mock_session_manager_safe):
    """Test /safe command checking entire chat."""
    handler = command_handler_safe

    # Mock prompt loading and helper AI
    with patch("polychat.prompts.templates._load_prompt_from_path") as mock_load_prompt, \
         patch.object(handler.context, "invoke_helper_ai", new_callable=AsyncMock) as mock_helper:
        mock_load_prompt.return_value = "Check safety:\n{CONTENT}"
        mock_helper.return_value = """PII: ⚠ Found: name "John Doe" in message
CREDENTIALS: ⚠ Found: potential API key in message
PROPRIETARY: ✓ None
OFFENSIVE: ✓ None"""

        result = await handler.check_safety("")

        # Verify helper AI was called
        assert mock_helper.called

        # Verify result format
        assert "Safety Check Results (entire chat):" in result
        assert "=" in result
        assert "PII:" in result
        assert "CREDENTIALS:" in result
        assert "PROPRIETARY:" in result
        assert "OFFENSIVE:" in result


@pytest.mark.asyncio
async def test_safe_command_specific_message(command_handler_safe, mock_session_manager_safe):
    """Test /safe command checking specific message by hex ID."""
    handler = command_handler_safe

    with patch("polychat.prompts.templates._load_prompt_from_path") as mock_load_prompt, \
         patch.object(handler.context, "invoke_helper_ai", new_callable=AsyncMock) as mock_helper:
        mock_load_prompt.return_value = "Check safety:\n{CONTENT}"
        mock_helper.return_value = """PII: ⚠ Found: name "John Doe"
CREDENTIALS: ✓ None
PROPRIETARY: ✓ None
OFFENSIVE: ✓ None"""

        result = await handler.check_safety("a3f")

        # Verify helper AI was called
        assert mock_helper.called

        # Verify result format indicates specific message
        assert "Safety Check Results (message [a3f]):" in result
        assert "PII:" in result


@pytest.mark.asyncio
async def test_safe_command_invalid_hex_id(command_handler_safe, mock_session_manager_safe):
    """Test /safe command with invalid hex ID."""
    handler = command_handler_safe

    result = await handler.check_safety("zzz")

    assert "Invalid hex ID: zzz" in result


@pytest.mark.asyncio
async def test_safe_command_error_handling(command_handler_safe, mock_session_manager_safe):
    """Test /safe command error handling."""
    handler = command_handler_safe

    with patch("polychat.prompts.templates._load_prompt_from_path") as mock_load_prompt, \
         patch.object(handler.context, "invoke_helper_ai", new_callable=AsyncMock) as mock_helper:
        mock_load_prompt.return_value = "Check safety:\n{CONTENT}"
        mock_helper.side_effect = Exception("API error")

        result = await handler.check_safety("")

        assert "Error performing safety check: API error" in result


@pytest.mark.asyncio
async def test_format_message_for_safety_check(command_handler_safe, mock_session_manager_safe):
    """Test message formatting for safety check."""
    from polychat.domain.chat import ChatMessage
    from polychat.formatting.history import format_message_for_safety_check
    from polychat.formatting.text import format_messages

    messages = [
        ChatMessage(role="user", content=["Test message 1"]),
        ChatMessage(role="assistant", content=["Test message 2"]),
    ]

    formatted = format_messages(messages, format_message_for_safety_check)

    assert "user: Test message 1" in formatted
    assert "assistant: Test message 2" in formatted
    assert "=" * 80 in formatted


@pytest.mark.asyncio
async def test_format_message_with_hex_ids(command_handler_safe, mock_session_manager_safe):
    """Safety formatting should not include hex IDs."""
    from polychat.formatting.history import format_for_safety_check

    # Use messages with hex IDs from session
    messages = mock_session_manager_safe.chat.messages[:1]

    formatted = format_for_safety_check(messages)

    assert "[a3f]" not in formatted
    assert "user:" in formatted
    assert "=" * 80 in formatted
