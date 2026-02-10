"""Tests for provider-side limit forwarding to SDK client calls."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import poly_chat.ai.gemini_provider as gemini_module
from poly_chat.ai.gemini_provider import GeminiProvider
from poly_chat.ai.openai_provider import OpenAIProvider
from poly_chat.ai.perplexity_provider import PerplexityProvider


@pytest.mark.asyncio
async def test_openai_create_response_forwards_max_output_tokens():
    provider = OpenAIProvider.__new__(OpenAIProvider)
    provider.client = MagicMock()
    provider.client.responses = MagicMock()
    provider.client.responses.create = AsyncMock(return_value=SimpleNamespace())

    await provider._create_response(
        model="gpt-5-mini",
        input_items=[{"role": "user", "content": "hi"}],
        stream=True,
        search=False,
        max_output_tokens=777,
    )

    kwargs = provider.client.responses.create.await_args.kwargs
    assert kwargs["max_output_tokens"] == 777


@pytest.mark.asyncio
async def test_perplexity_create_chat_completion_forwards_max_tokens():
    provider = PerplexityProvider.__new__(PerplexityProvider)
    provider.client = MagicMock()
    provider.client.chat = MagicMock()
    provider.client.chat.completions = MagicMock()
    provider.client.chat.completions.create = AsyncMock(return_value=SimpleNamespace())

    await provider._create_chat_completion(
        model="sonar",
        messages=[{"role": "user", "content": "hi"}],
        stream=False,
        max_output_tokens=555,
    )

    kwargs = provider.client.chat.completions.create.await_args.kwargs
    assert kwargs["max_tokens"] == 555


@pytest.mark.asyncio
async def test_gemini_get_full_response_forwards_max_output_tokens(monkeypatch):
    provider = GeminiProvider.__new__(GeminiProvider)
    provider.format_messages = MagicMock(return_value=[{"role": "user", "parts": []}])

    captured_config: dict[str, object] = {}

    def fake_generate_content_config(**kwargs):
        captured_config.update(kwargs)
        return kwargs

    monkeypatch.setattr(
        gemini_module.types,
        "GenerateContentConfig",
        fake_generate_content_config,
    )

    provider.client = MagicMock()
    provider.client.aio = MagicMock()
    provider.client.aio.models = MagicMock()
    provider.client.aio.models.generate_content = AsyncMock(
        return_value=SimpleNamespace(
            candidates=[],
            usage_metadata=SimpleNamespace(
                prompt_token_count=1,
                candidates_token_count=2,
                total_token_count=3,
            ),
            text="",
        )
    )

    await provider.get_full_response(
        messages=[{"role": "user", "content": "hi"}],
        model="gemini-3-flash-preview",
        max_output_tokens=321,
    )

    assert captured_config["max_output_tokens"] == 321
