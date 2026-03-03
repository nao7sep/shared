"""Prompt-toolkit theme helpers for interactive terminal rendering."""

import functools

from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.styles import Style

from ..config import load_config


@functools.lru_cache(maxsize=1)
def get_style() -> Style:
    """Return the prompt-toolkit Style, resolved once from user config."""
    display = load_config().display
    return Style.from_dict({
        "user-input": display.user_input_color,
        "cost-line": display.cost_line_color,
    })


def print_cost_line(text: str) -> None:
    """Print the cost summary using the shared interactive theme."""
    print_formatted_text(
        FormattedText([("class:cost-line", text)]),
        style=get_style(),
    )
