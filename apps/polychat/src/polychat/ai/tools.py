"""Centralized provider tool definitions.

This module keeps provider-specific tool payloads in one place so SDK calls
don't embed magic strings throughout providers.
"""

from __future__ import annotations

from typing import Any


# OpenAI Responses API built-in web search tool.
OPENAI_WEB_SEARCH_TOOL: dict[str, str] = {"type": "web_search"}

# xAI Grok (OpenAI-compatible Responses API) built-in web search tool.
GROK_WEB_SEARCH_TOOL: dict[str, str] = {"type": "web_search"}

# Anthropic currently uses a dated web search tool type.
CLAUDE_WEB_SEARCH_TOOL: dict[str, str] = {
    "type": "web_search_20250305",
    "name": "web_search",
}


def openai_web_search_tools() -> list[dict[str, str]]:
    """Return OpenAI web search tools payload."""
    return [dict(OPENAI_WEB_SEARCH_TOOL)]


def grok_web_search_tools() -> list[dict[str, str]]:
    """Return Grok web search tools payload."""
    return [dict(GROK_WEB_SEARCH_TOOL)]


def claude_web_search_tools() -> list[dict[str, str]]:
    """Return Claude web search tools payload."""
    return [dict(CLAUDE_WEB_SEARCH_TOOL)]


def gemini_web_search_tools(genai_types: Any) -> list[Any]:
    """Return Gemini web search tools payload.

    Args:
        genai_types: `google.genai.types` module (injected to avoid hard dependency here)
    """
    return [genai_types.Tool(google_search=genai_types.GoogleSearch())]
