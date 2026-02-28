"""Shared typed contracts for provider/runtime metadata exchange."""

from __future__ import annotations

from typing import TypedDict


class TokenUsage(TypedDict, total=False):
    """Token usage metadata returned by providers."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cached_tokens: int
    cache_write_tokens: int
    reasoning_tokens: int


class Citation(TypedDict, total=False):
    """Citation metadata emitted by providers/search integrations."""

    number: int
    title: str | None
    url: str | None


class AILimitBlock(TypedDict, total=False):
    """Single limit configuration block (default, per-provider, or helper)."""

    max_output_tokens: int | None
    search_max_output_tokens: int | None


class AILimitsConfig(TypedDict, total=False):
    """Structured ``ai_limits`` profile configuration."""

    default: AILimitBlock
    providers: dict[str, AILimitBlock]
    helper: AILimitBlock


class AIResponseMetadata(TypedDict, total=False):
    """Streaming metadata shared between runtime, providers, and REPL."""

    model: str
    started: float
    usage: TokenUsage
    citations: list[Citation]
