"""Tests for command documentation metadata and generated surfaces."""

from __future__ import annotations

from pathlib import Path

import pytest

from polychat.ai.catalog import PROVIDER_SHORTCUTS
from polychat.commands.command_docs import (
    README_COMMANDS_BEGIN_MARKER,
    README_COMMANDS_END_MARKER,
    documented_command_names,
    render_help_text,
    render_readme_commands_block,
)
from polychat.commands.misc import MiscCommandHandlers
from polychat.commands.registry import COMMAND_SPECS


def test_command_docs_cover_registered_commands_and_shortcuts() -> None:
    registered = {spec.name for spec in COMMAND_SPECS}
    for spec in COMMAND_SPECS:
        registered.update(spec.aliases)
    registered.update(PROVIDER_SHORTCUTS.keys())

    documented = documented_command_names()
    missing = sorted(registered - documented)
    assert not missing, f"Undocumented registered commands: {', '.join(missing)}"


@pytest.mark.asyncio
async def test_misc_help_uses_rendered_command_docs() -> None:
    handlers = MiscCommandHandlers()
    assert await handlers.show_help("") == render_help_text()


def test_readme_generated_commands_block_matches_renderer() -> None:
    readme_path = Path(__file__).resolve().parents[1] / "README.md"
    readme = readme_path.read_text(encoding="utf-8")

    begin = readme.find(README_COMMANDS_BEGIN_MARKER)
    end = readme.find(README_COMMANDS_END_MARKER)
    assert begin >= 0 and end >= 0 and end >= begin, "README command markers missing or malformed"

    end += len(README_COMMANDS_END_MARKER)
    existing_block = readme[begin:end]
    assert existing_block == render_readme_commands_block()
