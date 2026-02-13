"""Tests for status command formatting."""

import pytest


@pytest.mark.asyncio
async def test_show_status_assistant_fields_align_values(command_handler, mock_session_manager):
    """Assistant section values should begin in the same column."""
    mock_session_manager.chat["metadata"]["system_prompt"] = "@/prompts/system/default.txt"

    result = await command_handler.show_status("")

    assistant_prefixes = (
        "Assistant:",
        "Helper:",
        "System Prompt:",
        "Timeout:",
        "Input Mode:",
    )
    assistant_lines = [line for line in result.splitlines() if line.startswith(assistant_prefixes)]

    assert len(assistant_lines) == len(assistant_prefixes)

    value_starts = []
    for line in assistant_lines:
        colon_index = line.index(":")
        value_index = next(
            i for i, ch in enumerate(line[colon_index + 1 :], start=colon_index + 1) if ch != " "
        )
        value_starts.append(value_index)

    assert len(set(value_starts)) == 1


@pytest.mark.asyncio
async def test_show_status_system_prompt_none_has_readable_spacing(command_handler, mock_session_manager):
    """System prompt should include a separator space even when unset."""
    mock_session_manager.chat["metadata"]["system_prompt"] = None
    mock_session_manager.system_prompt_path = None

    result = await command_handler.show_status("")

    assert "System Prompt: (none)" in result


