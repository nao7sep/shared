"""Shared typed contracts for provider/runtime metadata exchange."""

from __future__ import annotations

from typing import Callable, TypedDict


class TokenUsage(TypedDict, total=False):
    """Token usage metadata returned by providers."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cached_tokens: int
    reasoning_tokens: int


class Citation(TypedDict, total=False):
    """Citation metadata emitted by providers/search integrations."""

    number: int
    title: str | None
    url: str


class SearchResult(TypedDict, total=False):
    """Normalized search result metadata from providers."""

    url: str
    title: str | None
    date: str | None


class AIResponseMetadata(TypedDict, total=False):
    """Streaming metadata shared between runtime, providers, and REPL."""

    model: str
    started: float
    usage: TokenUsage
    citations: list[Citation]
    search_results: list[SearchResult]
    search_executed: bool
    search_evidence: list[str]
    thought_callback: Callable[[str], None]
    thoughts: list[str]
    reasoning_content: str
