"""Provider capability flags."""

from __future__ import annotations


# Search support registry
SEARCH_SUPPORTED_PROVIDERS: set[str] = {
    "openai",
    "claude",
    "gemini",
    "grok",
    "perplexity",
}


def provider_supports_search(provider: str) -> bool:
    """Check whether a provider supports web search."""
    return provider in SEARCH_SUPPORTED_PROVIDERS

