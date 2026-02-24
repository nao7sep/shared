"""Citation rendering helpers."""

from __future__ import annotations

from ..ai.types import Citation


def format_citation_item(citation: Citation, number: int) -> list[str]:
    """Format one citation record into display lines."""
    title = citation.get("title")
    url = citation.get("url")

    title_text = str(title) if title else ""
    url_text = str(url) if url else ""

    if title_text and url_text:
        return [f"  [{number}] {title_text}", f"      {url_text}"]
    if url_text:
        return [f"  [{number}] {url_text}"]
    if title_text:
        return [f"  [{number}] {title_text} (URL unavailable)"]
    return [f"  [{number}] [source unavailable]"]


def format_citation_list(citations: list[Citation]) -> list[str]:
    """Format citations into printable lines."""
    if not citations:
        return []

    lines: list[str] = ["", "Sources:"]
    for index, citation in enumerate(citations, 1):
        number = citation.get("number", index)
        try:
            number_int = int(number)
        except Exception:
            number_int = index
        lines.extend(format_citation_item(citation, number_int))
    return lines
