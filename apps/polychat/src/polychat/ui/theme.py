"""Prompt-toolkit theme helpers for interactive terminal rendering."""

from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.styles import Style

POLYCHAT_STYLE = Style.from_dict({
    "user-input": "ansibrightgreen",
    "cost-line": "ansibrightyellow",
})


def print_cost_line(text: str) -> None:
    """Print the cost summary using the shared interactive theme."""
    print_formatted_text(
        FormattedText([("class:cost-line", text)]),
        style=POLYCHAT_STYLE,
    )
