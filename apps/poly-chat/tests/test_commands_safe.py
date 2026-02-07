"""Tests for /safe command."""

import pytest
from unittest.mock import AsyncMock, patch
from poly_chat.commands import CommandHandler


@pytest.fixture
def mock_session():
    """Create a mock session state."""
    return {
        "current_ai": "claude",
        "current_model": "claude-haiku-4-5",
        "helper_ai": "claude",
        "helper_model": "claude-haiku-4-5",
        "profile": {
            "default_ai": "claude",
            "models": {
                "claude": "claude-haiku-4-5",
            },
            "api_keys": {
                "claude": {
                    "type": "direct",
                    "value": "test-key"
                }
            }
        },
        "chat": {
            "metadata": {},
            "messages": [
                {
                    "timestamp": "2026-01-01T00:00:00+00:00",
                    "role": "user",
                    "content": ["Hello, my name is John Doe"]
                },
                {
                    "timestamp": "2026-01-01T00:00:01+00:00",
                    "role": "assistant",
                    "model": "claude-haiku-4-5",
                    "content": ["Hi John! How can I help you?"]
                },
                {
                    "timestamp": "2026-01-01T00:00:02+00:00",
                    "role": "user",
                    "content": ["My API key is sk-abc123"]
                }
            ]
        },
        "message_hex_ids": {
            0: "a3f",
            1: "b2c",
            2: "c1d"
        },
        "hex_id_set": {"a3f", "b2c", "c1d"}
    }


@pytest.mark.asyncio
async def test_safe_command_no_messages(mock_session):
    """Test /safe command with no messages."""
    mock_session["chat"]["messages"] = []
    handler = CommandHandler(mock_session)

    result = await handler.check_safety("")

    assert result == "No messages to check"


@pytest.mark.asyncio
async def test_safe_command_full_chat(mock_session):
    """Test /safe command checking entire chat."""
    handler = CommandHandler(mock_session)

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
async def test_safe_command_specific_message(mock_session):
    """Test /safe command checking specific message by hex ID."""
    handler = CommandHandler(mock_session)

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
async def test_safe_command_invalid_hex_id(mock_session):
    """Test /safe command with invalid hex ID."""
    handler = CommandHandler(mock_session)

    result = await handler.check_safety("zzz")

    assert "Invalid hex ID: zzz" in result


@pytest.mark.asyncio
async def test_safe_command_error_handling(mock_session):
    """Test /safe command error handling."""
    handler = CommandHandler(mock_session)

    with patch("poly_chat.commands.invoke_helper_ai", new_callable=AsyncMock) as mock_helper:
        mock_helper.side_effect = Exception("API error")

        result = await handler.check_safety("")

        assert "Error performing safety check: API error" in result


@pytest.mark.asyncio
async def test_format_message_for_safety_check(mock_session):
    """Test message formatting for safety check."""
    handler = CommandHandler(mock_session)

    messages = [
        {"role": "user", "content": ["Test message 1"]},
        {"role": "assistant", "content": ["Test message 2"]}
    ]

    formatted = handler._format_message_for_safety_check(messages)

    assert "USER: Test message 1" in formatted
    assert "ASSISTANT: Test message 2" in formatted


@pytest.mark.asyncio
async def test_format_message_with_hex_ids(mock_session):
    """Test message formatting includes hex IDs."""
    handler = CommandHandler(mock_session)

    # Use messages with hex IDs from session
    messages = mock_session["chat"]["messages"][:1]

    formatted = handler._format_message_for_safety_check(messages)

    # Should include hex ID in format
    assert "[a3f]" in formatted
    assert "USER:" in formatted
