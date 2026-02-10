"""Tests for /history and /show commands."""

import pytest
from poly_chat.commands import CommandHandler
from src.poly_chat.session_manager import SessionManager


@pytest.fixture
def mock_session_manager_with_messages():
    """Create a mock SessionManager with sample messages."""
    chat_data = {
        "metadata": {},
        "messages": [
            {
                "timestamp": "2026-02-02T10:00:00+00:00",
                "role": "user",
                "content": ["Hello, how are you?"]
            },
            {
                "timestamp": "2026-02-02T10:00:01+00:00",
                "role": "assistant",
                "model": "claude-haiku-4-5",
                "content": ["I'm doing well, thank you!"]
            },
            {
                "timestamp": "2026-02-02T10:00:02+00:00",
                "role": "user",
                "content": ["What's the weather?"]
            },
            {
                "timestamp": "2026-02-02T10:00:03+00:00",
                "role": "error",
                "content": ["API timeout after 30 seconds"]
            },
            {
                "timestamp": "2026-02-02T10:00:04+00:00",
                "role": "user",
                "content": ["Try again"]
            },
            {
                "timestamp": "2026-02-02T10:00:05+00:00",
                "role": "assistant",
                "model": "claude-haiku-4-5",
                "content": ["The weather is sunny today!"]
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
            "logs_dir": "/test/logs",
            "pages_dir": "/test/pages",
            "timeout": 30,
        },
        current_ai="claude",
        current_model="claude-haiku-4-5",
        chat=chat_data,
        chat_path="/test/chat.json",
        profile_path="/test/profile.json",
        log_file="/test/log.txt",
    )

    # Set up hex IDs as the tests expect
    manager.chat["messages"][0]["hex_id"] = "a3f"
    manager.chat["messages"][1]["hex_id"] = "b2c"
    manager.chat["messages"][2]["hex_id"] = "c1d"
    manager.chat["messages"][3]["hex_id"] = "d4e"
    manager.chat["messages"][4]["hex_id"] = "e5f"
    manager.chat["messages"][5]["hex_id"] = "f6a"
    manager._state.hex_id_set = {"a3f", "b2c", "c1d", "d4e", "e5f", "f6a"}

    return manager


@pytest.fixture
def command_handler_with_messages(mock_session_manager_with_messages):
    """Create a CommandHandler with messages."""
    return CommandHandler(mock_session_manager_with_messages)


@pytest.mark.asyncio
async def test_history_no_messages(command_handler):
    """Test /history with no messages."""
    result = await command_handler.show_history("")

    assert "No messages in chat history" in result


@pytest.mark.asyncio
async def test_history_no_open_chat(command_handler_with_messages, mock_session_manager_with_messages):
    """Test /history when no chat is open."""
    mock_session_manager_with_messages.close_chat()

    result = await command_handler_with_messages.show_history("")

    assert result == "No chat is currently open"


@pytest.mark.asyncio
async def test_history_default_last_10(command_handler_with_messages, mock_session_manager_with_messages):
    """Test /history without arguments shows last 10 messages."""
    handler = command_handler_with_messages

    result = await handler.show_history("")

    # Should show all 6 messages (less than 10)
    assert "showing 6 of 6 messages" in result
    assert "[a3f]" in result
    assert "[f6a]" in result
    assert "👤 User" in result
    assert "🤖 Assistant" in result
    assert "❌ Error" in result


@pytest.mark.asyncio
async def test_history_with_limit(command_handler_with_messages, mock_session_manager_with_messages):
    """Test /history <n> shows last n messages."""
    handler = command_handler_with_messages

    result = await handler.show_history("3")

    # Should show last 3 messages
    assert "showing 3 of 6 messages" in result
    assert "[d4e]" in result  # Error message (4th)
    assert "[e5f]" in result  # User message (5th)
    assert "[f6a]" in result  # Assistant message (6th)
    assert "[a3f]" not in result  # First message should not appear


@pytest.mark.asyncio
async def test_history_all(command_handler_with_messages, mock_session_manager_with_messages):
    """Test /history all shows all messages."""
    handler = command_handler_with_messages

    result = await handler.show_history("all")

    assert "all 6 messages" in result
    assert "[a3f]" in result
    assert "[f6a]" in result


@pytest.mark.asyncio
async def test_history_errors_only(command_handler_with_messages, mock_session_manager_with_messages):
    """Test /history --errors shows only error messages."""
    handler = command_handler_with_messages

    result = await handler.show_history("--errors")

    assert "Error Messages" in result
    assert "1 of 6 total messages" in result
    assert "[d4e]" in result
    assert "API timeout" in result
    # Other messages should not appear
    assert "[a3f]" not in result
    assert "[b2c]" not in result


@pytest.mark.asyncio
async def test_history_no_errors(command_handler_with_messages, mock_session_manager_with_messages):
    """Test /history --errors when no errors exist."""
    # Remove error message
    mock_session_manager_with_messages.chat["messages"] = [
        msg for msg in mock_session_manager_with_messages.chat["messages"]
        if msg.get("role") != "error"
    ]

    handler = command_handler_with_messages

    result = await handler.show_history("--errors")

    assert "No error messages found" in result


@pytest.mark.asyncio
async def test_history_invalid_number(command_handler_with_messages, mock_session_manager_with_messages):
    """Test /history with invalid number."""
    handler = command_handler_with_messages

    result = await handler.show_history("abc")

    assert "Invalid argument" in result


@pytest.mark.asyncio
async def test_history_zero_or_negative(command_handler_with_messages, mock_session_manager_with_messages):
    """Test /history with zero or negative number."""
    handler = command_handler_with_messages

    result = await handler.show_history("0")
    assert "Invalid number" in result

    result = await handler.show_history("-5")
    assert "Invalid number" in result


@pytest.mark.asyncio
async def test_history_truncates_long_messages(command_handler_with_messages, mock_session_manager_with_messages):
    """Test that /history truncates long messages."""
    # Add a very long message
    long_content = "x" * 200
    mock_session_manager_with_messages.chat["messages"][0]["content"] = [long_content]

    handler = command_handler_with_messages

    result = await handler.show_history("")

    # Should be truncated with "..."
    assert "..." in result
    # Should not show full 200 characters
    assert "x" * 200 not in result


@pytest.mark.asyncio
async def test_history_no_extra_blank_line_before_footer(command_handler_with_messages):
    """History output should not have a blank line right before footer divider."""
    result = await command_handler_with_messages.show_history("")
    assert "\n\n" + ("━" * 60) not in result


@pytest.mark.asyncio
async def test_show_message_no_arg(command_handler_with_messages, mock_session_manager_with_messages):
    """Test /show without argument."""
    handler = command_handler_with_messages

    result = await handler.show_message("")

    assert "Usage: /show <hex_id>" in result


@pytest.mark.asyncio
async def test_show_message_no_open_chat(command_handler_with_messages, mock_session_manager_with_messages):
    """Test /show when no chat is open."""
    mock_session_manager_with_messages.close_chat()

    result = await command_handler_with_messages.show_message("a3f")

    assert result == "No chat is currently open"


@pytest.mark.asyncio
async def test_show_message_valid_hex_id(command_handler_with_messages, mock_session_manager_with_messages):
    """Test /show with valid hex ID."""
    handler = command_handler_with_messages

    result = await handler.show_message("a3f")

    assert "Message [a3f]" in result
    assert "User" in result
    assert "Hello, how are you?" in result
    assert "━" in result


@pytest.mark.asyncio
async def test_show_message_invalid_hex_id(command_handler_with_messages, mock_session_manager_with_messages):
    """Test /show with invalid hex ID."""
    handler = command_handler_with_messages

    result = await handler.show_message("zzz")

    assert "Invalid hex ID: zzz" in result


@pytest.mark.asyncio
async def test_show_assistant_message_includes_model(command_handler_with_messages, mock_session_manager_with_messages):
    """Test /show for assistant message includes model info."""
    handler = command_handler_with_messages

    result = await handler.show_message("b2c")

    assert "Assistant (claude-haiku-4-5)" in result
    assert "I'm doing well, thank you!" in result


@pytest.mark.asyncio
async def test_show_error_message(command_handler_with_messages, mock_session_manager_with_messages):
    """Test /show for error message."""
    handler = command_handler_with_messages

    result = await handler.show_message("d4e")

    assert "Error" in result
    assert "API timeout" in result
