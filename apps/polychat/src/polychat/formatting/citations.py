"""Citation rendering helpers."""

from __future__ import annotations

from ..ai.types import Citation
from .text import make_borderline


def format_citation_item(citation: Citation, number: int, width: int = 1) -> list[str]:
    """Format one citation record into display lines.

    Args:
        citation: Citation data.
        number: Citation number to display.
        width: Minimum digit width for left-padding the number so columns align.
    """
    title = citation.get("title")
    url = citation.get("url")

    title_text = str(title) if title else ""
    url_text = str(url) if url else ""

    prefix = f"[{number:>{width}}] "
    indent = " " * len(prefix)

    if title_text and url_text:
        return [f"{prefix}{title_text}", f"{indent}{url_text}"]
    if url_text:
        return [f"{prefix}{url_text}"]
    if title_text:
        return [f"{prefix}{title_text} (URL unavailable)"]
    return [f"{prefix}[source unavailable]"]


def format_citation_list(citations: list[Citation]) -> list[str]:
    """Format citations into printable lines, framed with borderlines."""
    if not citations:
        return []

    width = len(str(len(citations)))
    lines: list[str] = ["Sources:", make_borderline()]
    for index, citation in enumerate(citations, 1):
        number = citation.get("number", index)
        try:
            number_int = int(number)
        except Exception:
            number_int = index
        lines.extend(format_citation_item(citation, number_int, width))
    lines.append(make_borderline())
    return lines
