"""UI helpers: prompts, confirmations, console formatting.

Uses Rich for terminal output and Questionary for structured prompts.
"""

from __future__ import annotations

from typing import NoReturn

import questionary
from prompt_toolkit import prompt as pt_prompt
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .output_segments import start_segment

console = Console()


def banner(version: str) -> None:
    """Print the pydeli banner."""
    start_segment()
    console.print(Panel(f"[bold]pydeli[/bold] {version}", expand=False))


def info(message: str) -> None:
    """Print an informational message as a new segment."""
    start_segment()
    console.print(message)


def info_continuation(message: str) -> None:
    """Print a continuation line within the current segment (no leading blank)."""
    console.print(message)


def warning(message: str) -> None:
    """Print a warning message."""
    start_segment()
    console.print(f"[yellow]WARNING:[/yellow] {message}")


def error(message: str) -> None:
    """Print an error message."""
    start_segment()
    console.print(f"[red]ERROR:[/red] {message}")


def farewell(message: str = "Done.") -> None:
    """Print a farewell message."""
    start_segment()
    console.print(message)


def key_value_block(pairs: list[tuple[str, str]]) -> None:
    """Print aligned key: value pairs as a new segment."""
    if not pairs:
        return
    start_segment()
    max_key_len = max(len(k) for k, _ in pairs)
    for key, value in pairs:
        console.print(f"  {key:<{max_key_len}}  {value}")


def version_table(
    title: str, rows: list[tuple[str, str]], *, highlight_col: int | None = None
) -> None:
    """Print a version information table."""
    start_segment()
    table = Table(title=title, show_header=True, expand=False)
    table.add_column("Source", style="cyan")
    table.add_column("Version", style="green" if highlight_col == 1 else None)
    for row in rows:
        table.add_row(*row)
    console.print(table)


def confirm(message: str, *, default: bool = False) -> bool:
    """Ask a yes/no confirmation via Questionary."""
    start_segment()
    return questionary.confirm(message, default=default).unsafe_ask()


def select(message: str, choices: list[str]) -> str:
    """Present a selection menu via Questionary."""
    start_segment()
    return questionary.select(message, choices=choices).unsafe_ask()


def secret_input(message: str) -> str:
    """Prompt for masked secret input via Questionary."""
    start_segment()
    return questionary.password(message).unsafe_ask()


def text_input(message: str, *, default: str = "") -> str:
    """Prompt for free-text input via prompt_toolkit."""
    start_segment()
    return pt_prompt(f"{message}: ", default=default).strip()


def empty_state(message: str) -> None:
    """Print explicit empty-state feedback."""
    start_segment()
    console.print(f"[dim]{message}[/dim]")


def progress_message(message: str) -> None:
    """Print a progress indication."""
    start_segment()
    console.print(f"[blue]⏳[/blue] {message}")


def success_message(message: str) -> None:
    """Print a success indication."""
    start_segment()
    console.print(f"[green]✓[/green] {message}")


def fail_fast_not_interactive() -> NoReturn:
    """Print error and exit when stdin/stdout are not a terminal."""
    import sys

    err_console = Console(stderr=True)
    err_console.print(
        "[red]ERROR:[/red] pydeli requires an interactive terminal (stdin and stdout must be a TTY)."
    )
    sys.exit(1)
