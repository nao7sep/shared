"""Single-source command documentation renderers."""

from __future__ import annotations

try:  # pragma: no cover - fallback used by standalone doc generator script
    from .command_docs_data import (
        COMMAND_DOC_SECTIONS,
        README_CHAT_FILE_NOTE,
        README_COMMANDS_FOOTER,
        README_LAST_INTERACTION_BLOCK,
    )
    from .command_docs_models import CommandDocSection
except ImportError:  # pragma: no cover
    from command_docs_data import (  # type: ignore[import-not-found,no-redef]
        COMMAND_DOC_SECTIONS,
        README_CHAT_FILE_NOTE,
        README_COMMANDS_FOOTER,
        README_LAST_INTERACTION_BLOCK,
    )
    from command_docs_models import CommandDocSection  # type: ignore[import-not-found,no-redef]

README_COMMANDS_BEGIN_MARKER = "<!-- BEGIN GENERATED:COMMANDS -->"
README_COMMANDS_END_MARKER = "<!-- END GENERATED:COMMANDS -->"


def documented_command_names() -> set[str]:
    """Return all documented command names and aliases."""
    names: set[str] = set()
    for section in COMMAND_DOC_SECTIONS:
        for entry in section.entries:
            names.update(entry.command_names)
    return names


def _render_help_section(section: CommandDocSection) -> list[str]:
    lines: list[str] = [f"{section.title}:"]
    width = max(len(entry.help_signature) for entry in section.entries)
    continuation_prefix = " " * (2 + width + 2)

    for entry in section.entries:
        lines.append(f"  {entry.help_signature.ljust(width)}  {entry.help_description}")
        for continuation in entry.help_continuations:
            lines.append(f"{continuation_prefix}{continuation}")
    return lines


def render_help_text() -> str:
    """Render in-chat `/help` output from metadata."""
    lines: list[str] = ["PolyChat Commands:", ""]

    for section in COMMAND_DOC_SECTIONS:
        lines.extend(_render_help_section(section))
        lines.append("")

    return "\n".join(lines).rstrip()


def _render_readme_section(section: CommandDocSection) -> list[str]:
    lines: list[str] = [f"**{section.title}:**"]
    for entry in section.entries:
        lines.append(f"- `{entry.readme_signature}` - {entry.readme_description}")
        lines.extend(entry.readme_continuations)
    return lines


def render_readme_commands_content() -> str:
    """Render README in-chat commands markdown from metadata."""
    lines: list[str] = ["### In-Chat Commands", ""]

    for section in COMMAND_DOC_SECTIONS:
        lines.extend(_render_readme_section(section))
        lines.append("")
        if section.title == "Chat File Management":
            lines.append(README_CHAT_FILE_NOTE)
            lines.append("")
            lines.append(README_LAST_INTERACTION_BLOCK)
            lines.append("")

    lines.append(README_COMMANDS_FOOTER)
    return "\n".join(lines).rstrip() + "\n"


def render_readme_commands_block() -> str:
    """Render the full README generated block with boundary markers."""
    content = render_readme_commands_content().strip()
    return (
        f"{README_COMMANDS_BEGIN_MARKER}\n"
        f"{content}\n"
        f"{README_COMMANDS_END_MARKER}"
    )
