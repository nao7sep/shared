"""Tests for /safe command."""

import pytest
from unittest.mock import AsyncMock, patch
from poly_chat.commands import CommandHandler
from src.poly_chat.session_manager import SessionManager


@pytest.fixture
def mock_session_manager_safe():
    """Create a mock SessionManager for safe tests."""
    chat_data = {
        "metadata": {},
        "messages": [
            {
                "timestamp": "2026-02-02T00:00:00+00:00",
                "role": "user",
                "content": ["Hello, my name is John Doe"]
            },
            {
                "timestamp": "2026-02-02T00:00:01+00:00",
                "role": "assistant",
                "model": "claude-haiku-4-5",
                "content": ["Hi John! How can I help you?"]
            },
            {
                "timestamp": "2026-02-02T00:00:02+00:00",
                "role": "user",
                "content": ["My API key is sk-abc123"]
            }
        ]
    }

    manager = SessionManager(
        profile={
            "default_ai": "claude",
            "input_mode": "quick",
            "models": {
                "claude": "claude-haiku-4-5",
            },
            "api_keys": {
                "claude": {
                    "type": "direct",
                    "value": "test-key"
                }
            },
            "chats_dir": "/test/chats",
            "log_dir": "/test/logs",
            "timeout": 30,
        },
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
    manager.chat["messages"][0]["hex_id"] = "a3f"
    manager.chat["messages"][1]["hex_id"] = "b2c"
    manager.chat["messages"][2]["hex_id"] = "c1d"
    manager._state.hex_id_set = {"a3f", "b2c", "c1d"}

    return manager


@pytest.fixture
def command_handler_safe(mock_session_manager_safe):
    """Create a CommandHandler for safe tests."""
    return CommandHandler(mock_session_manager_safe)


@pytest.mark.asyncio
async def test_safe_command_no_messages(command_handler_safe, mock_session_manager_safe):
    """Test /safe command with no messages."""
    mock_session_manager_safe.chat["messages"] = []
    handler = command_handler_safe

    result = await handler.check_safety("")

    assert result == "No messages to check"


@pytest.mark.asyncio
async def test_safe_command_full_chat(command_handler_safe, mock_session_manager_safe):
    """Test /safe command checking entire chat."""
    handler = command_handler_safe

    # Mock the invoke_helper_ai function
    with patch("poly_chat.commands.invoke_helper_ai", new_callable=AsyncMock) as mock_helper:
        mock_helper.return_value = """PII: ⚠ Found: name "John Doe" in message
CREDENTIALS: ⚠ Found: potential API key in message
PROPRIETARY: ✓ None
OFFENSIVE: ✓ None"""

        result = await handler.check_safety("")

        # Verify helper AI was called
        assert mock_helper.called

        # Verify result format
        assert "Safety Check Results (entire chat):" in result
        assert "━" in result
        assert "PII:" in result
        assert "CREDENTIALS:" in result
        assert "PROPRIETARY:" in result
        assert "OFFENSIVE:" in result


@pytest.mark.asyncio
async def test_safe_command_specific_message(command_handler_safe, mock_session_manager_safe):
    """Test /safe command checking specific message by hex ID."""
    handler = command_handler_safe

    with patch("poly_chat.commands.invoke_helper_ai", new_callable=AsyncMock) as mock_helper:
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

    with patch("poly_chat.commands.invoke_helper_ai", new_callable=AsyncMock) as mock_helper:
        mock_helper.side_effect = Exception("API error")

        result = await handler.check_safety("")

        assert "Error performing safety check: API error" in result


@pytest.mark.asyncio
async def test_format_message_for_safety_check(command_handler_safe, mock_session_manager_safe):
    """Test message formatting for safety check."""
    handler = command_handler_safe

    messages = [
        {"role": "user", "content": ["Test message 1"]},
        {"role": "assistant", "content": ["Test message 2"]}
    ]

    formatted = handler._format_message_for_safety_check(messages)

    assert "USER: Test message 1" in formatted
    assert "ASSISTANT: Test message 2" in formatted


@pytest.mark.asyncio
async def test_format_message_with_hex_ids(command_handler_safe, mock_session_manager_safe):
    """Test message formatting includes hex IDs."""
    handler = command_handler_safe

    # Use messages with hex IDs from session
    messages = mock_session_manager_safe.chat["messages"][:1]

    formatted = handler._format_message_for_safety_check(messages)

    # Should include hex ID in format
    assert "[a3f]" in formatted
    assert "USER:" in formatted
