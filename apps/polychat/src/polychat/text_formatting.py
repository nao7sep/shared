"""Backward-compatible facade for text and display formatting helpers."""

from .formatting.chat_list import format_chat_list_item
from .formatting.citations import format_citation_item, format_citation_list
from .formatting.history import (
    create_history_formatter,
    format_for_ai_context,
    format_for_safety_check,
    format_for_show,
    format_message_for_ai_context,
    format_message_for_safety_check,
    format_message_for_show,
)
from .formatting.text import (
    _find_truncate_position,
    _is_truncate_boundary,
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
    "_is_truncate_boundary",
    "_find_truncate_position",
]
