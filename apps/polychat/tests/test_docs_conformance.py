"""Conformance checks between user docs and runtime help surfaces."""

import re
import sys
from pathlib import Path

import pytest

from polychat.cli import main


def _read_readme() -> str:
    """Load README text."""
    return (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")


def _run_cli_help(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> str:
    """Capture `polychat --help` output."""
    monkeypatch.setattr(sys, "argv", ["polychat", "--help"])
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    return captured.out


def _extract_cli_flag_pairs(help_output: str) -> set[str]:
    """Extract `-x/--long` pairs from argparse help output."""
    pairs = set()
    for short, long_name in re.findall(r"^\s*(-\w),\s*(--[a-z-]+)", help_output, flags=re.MULTILINE):
        if long_name == "--help":
            continue
        pairs.add(f"{short}/{long_name}")
    return pairs


def _extract_repl_help_commands(help_text: str) -> set[str]:
    """Extract `/command` names from REPL `/help` output."""
    commands: set[str] = set()
    for line in help_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("/"):
            continue
        # Parse only the left command-signature column (before description text).
        command_sig = re.split(r"\s{2,}", stripped, maxsplit=1)[0]
        first = re.match(r"^/([a-z]+)\b", command_sig)
        if first:
            commands.add(first.group(1))
        for alias in re.findall(r",\s*/([a-z]+)\b", command_sig):
            commands.add(alias)
    return commands


def _extract_readme_documented_commands(readme: str) -> set[str]:
    """Extract `/command` names documented in README command listings."""
    return set(re.findall(r"`/([a-z]+)\b[^`]*`", readme))


def test_readme_covers_cli_help_flags(monkeypatch, capsys):
    """README should cover CLI flag pairs shown by `polychat --help`."""
    readme = _read_readme()
    help_output = _run_cli_help(monkeypatch, capsys)
    flag_pairs = _extract_cli_flag_pairs(help_output)

    missing = sorted(pair for pair in flag_pairs if f"`{pair}`" not in readme)
    assert not missing, f"README missing CLI flag docs: {', '.join(missing)}"

    assert "polychat init -p <profile-path>" in readme


@pytest.mark.asyncio
async def test_readme_covers_repl_help_commands(command_handler):
    """README should cover all in-chat commands shown by `/help`."""
    readme = _read_readme()
    readme_commands = _extract_readme_documented_commands(readme)

    repl_help = await command_handler.execute_command("/help")
    repl_commands = _extract_repl_help_commands(repl_help)

    missing = sorted(repl_commands - readme_commands)
    assert not missing, f"README missing REPL commands: {', '.join(missing)}"
