"""Tests that user docs stay aligned with dispatcher command metadata."""

from pathlib import Path

from tk import dispatcher


def _readme_commands_section() -> str:
    readme_path = Path(__file__).resolve().parent.parent / "README.md"
    content = readme_path.read_text(encoding="utf-8")

    start = content.find("## Commands")
    if start == -1:
        raise AssertionError("README.md is missing '## Commands' section")

    end = content.find("\n## ", start + 1)
    if end == -1:
        return content[start:]
    return content[start:end]


def _expected_readme_line(entry) -> str:
    command = entry.command
    alias = entry.alias
    usage = entry.usage
    summary = entry.summary

    label = command if not alias else f"{command} ({alias})"
    args = ""
    if usage != command and usage.startswith(f"{command} "):
        args = usage[len(command) + 1 :]

    if args:
        return f"**{label}** `{args}` - {summary}"
    return f"**{label}** - {summary}"


def test_readme_command_lines_match_dispatcher_metadata():
    section = _readme_commands_section()

    for entry in dispatcher.command_doc_entries():
        # README documents exit/quit as a combined line outside registry commands.
        if entry.command == "exit":
            continue

        expected = _expected_readme_line(entry)
        assert expected in section

    assert "**exit** / **quit** - Exit REPL" in section
