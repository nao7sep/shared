"""Formatting helpers grouped by output domain."""

from .chat_list import format_chat_list_item
from .citations import format_citation_item, format_citation_list
from .costs import format_cost_line, format_cost_usd
from .history import (
    create_history_formatter,
    format_for_ai_context,
    format_for_safety_check,
    format_for_show,
    format_message_for_ai_context,
    format_message_for_safety_check,
    format_message_for_show,
)
from .text import (
    format_messages,
    lines_to_text,
    make_borderline,
    minify_text,
    text_to_lines,
    truncate_text,
)

__all__ = [
    "text_to_lines",
    "lines_to_text",
    "minify_text",
    "truncate_text",
    "make_borderline",
    "format_messages",
    "format_message_for_ai_context",
    "format_message_for_safety_check",
    "format_message_for_show",
    "create_history_formatter",
    "format_for_ai_context",
    "format_for_safety_check",
    "format_for_show",
    "format_chat_list_item",
    "format_citation_item",
    "format_citation_list",
    "format_cost_line",
    "format_cost_usd",
]
