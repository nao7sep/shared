"""Prompt-toolkit theme helpers for interactive terminal rendering."""

from __future__ import annotations

from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.styles import Style

from ..domain.config import AppConfig


DEFAULT_USER_INPUT_COLOR = "ansibrightgreen"
DEFAULT_COST_LINE_COLOR = "ansibrightyellow"


def build_interactive_style(app_config: AppConfig | None = None) -> Style:
    """Build prompt-toolkit style rules from app config plus UI defaults."""
    text_colors = app_config.text_colors if app_config is not None else None
    user_input_color = (
        text_colors.user_input
        if text_colors is not None and text_colors.user_input
        else DEFAULT_USER_INPUT_COLOR
    )
    cost_line_color = (
        text_colors.cost_line
        if text_colors is not None and text_colors.cost_line
        else DEFAULT_COST_LINE_COLOR
    )

    try:
        return Style.from_dict(
            {
                "user-input": user_input_color,
                "cost-line": cost_line_color,
            }
        )
    except Exception as e:
        raise ValueError(f"Invalid text color configuration: {e}") from e


def validate_interactive_style(app_config: AppConfig | None = None) -> None:
    """Validate interactive color config without storing prompt-toolkit state."""
    build_interactive_style(app_config)


DEFAULT_INTERACTIVE_STYLE = build_interactive_style()


def print_cost_line(text: str, app_config: AppConfig | None = None) -> None:
    """Print the cost summary using the shared interactive theme."""
    print_formatted_text(
        FormattedText([("class:cost-line", text)]),
        style=DEFAULT_INTERACTIVE_STYLE
        if app_config is None
        else build_interactive_style(app_config),
    )
