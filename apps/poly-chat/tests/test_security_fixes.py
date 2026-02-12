"""Tests for security fixes."""

import pytest
from pathlib import Path
from poly_chat.chat_manager import rename_chat
from poly_chat.cli import sanitize_error_message


def test_path_traversal_prevention_rename(tmp_path):
    """Test that rename_chat prevents path traversal attacks."""
    chats_dir = tmp_path / "chats"
    chats_dir.mkdir()

    # Create a test chat file
    old_file = chats_dir / "test.json"
    old_file.write_text('{"metadata":{}, "messages":[]}')

    # Try to use path traversal to escape chats_dir
    with pytest.raises(ValueError, match="outside chats directory"):
        rename_chat(str(old_file), "../../../etc/passwd", str(chats_dir))

    # Try with multiple levels
    with pytest.raises(ValueError, match="outside chats directory"):
        rename_chat(str(old_file), "../../sensitive.json", str(chats_dir))

    # Verify original file still exists
    assert old_file.exists()


def test_sanitize_error_message_openai_key():
    """Test that OpenAI API keys are sanitized."""
    error = "Authentication failed: Invalid API key sk-1234567890abcdefghijk"
    sanitized = sanitize_error_message(error)

    assert "sk-1234567890abcdefghijk" not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized


def test_sanitize_error_message_claude_key():
    """Test that Claude API keys are sanitized."""
    error = "Invalid API key: sk-ant-api03-abcdefghijklmnopqrstuvwxyz"
    sanitized = sanitize_error_message(error)

    assert "sk-ant-api03" not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized


def test_sanitize_error_message_xai_key():
    """Test that xAI (Grok) API keys are sanitized."""
    error = "Auth error with key xai-1234567890abcdefghijklmnopqrstuvwxyz"
    sanitized = sanitize_error_message(error)

    assert "xai-1234567890" not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized


def test_sanitize_error_message_perplexity_key():
    """Test that Perplexity API keys are sanitized."""
    error = "Request failed: pplx-1234567890abcdefghijklmnopqrstuvwxyz"
    sanitized = sanitize_error_message(error)

    assert "pplx-1234567890" not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized


def test_sanitize_error_message_bearer_token():
    """Test that Bearer tokens are sanitized."""
    error = "Unauthorized: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    sanitized = sanitize_error_message(error)

    assert "Bearer [REDACTED_TOKEN]" in sanitized or "[REDACTED_JWT]" in sanitized


def test_sanitize_error_message_jwt():
    """Test that JWT tokens are sanitized."""
    jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
    error = f"Token validation failed: {jwt}"
    sanitized = sanitize_error_message(error)

    assert jwt not in sanitized
    assert "[REDACTED_JWT]" in sanitized


def test_sanitize_error_message_multiple_keys():
    """Test that multiple API keys in one message are all sanitized."""
    error = "Failed to auth with sk-abc123def456ghi789 or sk-ant-xyz123abc456def789"
    sanitized = sanitize_error_message(error)

    assert "sk-abc123def456ghi789" not in sanitized
    assert "sk-ant-xyz123abc456def789" not in sanitized
    assert sanitized.count("[REDACTED_API_KEY]") == 2


def test_sanitize_error_message_no_sensitive_data():
    """Test that messages without sensitive data pass through."""
    error = "Connection timeout after 30 seconds"
    sanitized = sanitize_error_message(error)

    assert sanitized == error


def test_rename_chat_valid_name_works(tmp_path):
    """Test that valid renames still work after security fix."""
    chats_dir = tmp_path / "chats"
    chats_dir.mkdir()

    # Create a test chat file
    old_file = chats_dir / "test.json"
    old_file.write_text('{"metadata":{}, "messages":[]}')

    # Rename to valid name should work
    new_path = rename_chat(str(old_file), "renamed.json", str(chats_dir))

    # Check that rename worked
    assert Path(new_path).exists()
    assert Path(new_path).name == "renamed.json"
    assert not old_file.exists()
