"""Tests for status command formatting."""

import pytest


@pytest.mark.asyncio
async def test_show_status_all_fields_align_values(command_handler, mock_session_manager):
    """All field values should begin in the same column."""
    mock_session_manager.chat["metadata"]["system_prompt"] = "@/prompts/system/default.txt"

    result = await command_handler.show_status("")

    # All fields that should be aligned
    field_prefixes = (
        "Chats:",
        "Logs:",
        "Profile:",
        "Chat:",
        "Log:",
        "Title:",
        "Summary:",
        "Messages:",
        "Updated:",
        "Assistant:",
        "Helper:",
        "System:",
        "Safety:",
        "Input:",
        "Timeout:",
        "Retry:",
        "Secret:",
        "Search:",
    )
    field_lines = [line for line in result.splitlines() if any(line.startswith(prefix) for prefix in field_prefixes)]

    # Should have all fields
    assert len(field_lines) >= 18

    value_starts = []
    for line in field_lines:
        colon_index = line.index(":")
        value_index = next(
            i for i, ch in enumerate(line[colon_index + 1 :], start=colon_index + 1) if ch != " "
        )
        value_starts.append(value_index)

    # All values should start at same position
    assert len(set(value_starts)) == 1


@pytest.mark.asyncio
async def test_show_status_system_prompt_none_has_readable_spacing(command_handler, mock_session_manager):
    """System prompt should include a separator space even when unset."""
    mock_session_manager.chat["metadata"]["system_prompt"] = None
    mock_session_manager.system_prompt_path = None

    result = await command_handler.show_status("")

    assert "System:        none" in result


