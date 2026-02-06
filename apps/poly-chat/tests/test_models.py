"""Tests for models module."""

import pytest
from poly_chat.models import (
    get_provider_for_model,
    get_models_for_provider,
    get_all_providers,
    get_all_models,
    resolve_provider_shortcut,
    get_provider_shortcut,
    PROVIDER_SHORTCUTS,
    MODEL_REGISTRY,
)


def test_get_provider_for_model_openai():
    """Test getting provider for OpenAI models."""
    assert get_provider_for_model("gpt-5.2") == "openai"
    assert get_provider_for_model("gpt-5-mini") == "openai"
    assert get_provider_for_model("gpt-4.1") == "openai"


def test_get_provider_for_model_claude():
    """Test getting provider for Claude models."""
    assert get_provider_for_model("claude-opus-4-6") == "claude"
    assert get_provider_for_model("claude-sonnet-4-5") == "claude"
    assert get_provider_for_model("claude-haiku-4-5") == "claude"


def test_get_provider_for_model_gemini():
    """Test getting provider for Gemini models."""
    assert get_provider_for_model("gemini-3-pro-preview") == "gemini"
    assert get_provider_for_model("gemini-3-flash-preview") == "gemini"
    assert get_provider_for_model("gemini-2.5-pro") == "gemini"


def test_get_provider_for_model_grok():
    """Test getting provider for Grok models."""
    assert get_provider_for_model("grok-4-1-fast-reasoning") == "grok"
    assert get_provider_for_model("grok-4-1-fast-non-reasoning") == "grok"
    assert get_provider_for_model("grok-3") == "grok"


def test_get_provider_for_model_perplexity():
    """Test getting provider for Perplexity models."""
    assert get_provider_for_model("sonar") == "perplexity"
    assert get_provider_for_model("sonar-pro") == "perplexity"
    assert get_provider_for_model("sonar-reasoning-pro") == "perplexity"


def test_get_provider_for_model_mistral():
    """Test getting provider for Mistral models."""
    assert get_provider_for_model("mistral-large-latest") == "mistral"
    assert get_provider_for_model("mistral-small-latest") == "mistral"
    assert get_provider_for_model("ministral-8b-latest") == "mistral"


def test_get_provider_for_model_deepseek():
    """Test getting provider for DeepSeek models."""
    assert get_provider_for_model("deepseek-chat") == "deepseek"
    assert get_provider_for_model("deepseek-reasoner") == "deepseek"


def test_get_provider_for_model_unknown():
    """Test getting provider for unknown model returns None."""
    assert get_provider_for_model("unknown-model") is None
    assert get_provider_for_model("gpt-999") is None
    assert get_provider_for_model("") is None


def test_get_models_for_provider_openai():
    """Test getting models for OpenAI provider."""
    models = get_models_for_provider("openai")
    assert isinstance(models, list)
    assert "gpt-5.2" in models
    assert "gpt-5-mini" in models
    assert len(models) > 0


def test_get_models_for_provider_claude():
    """Test getting models for Claude provider."""
    models = get_models_for_provider("claude")
    assert isinstance(models, list)
    assert "claude-opus-4-6" in models
    assert "claude-haiku-4-5" in models
    assert len(models) > 0


def test_get_models_for_provider_unknown():
    """Test getting models for unknown provider returns empty list."""
    models = get_models_for_provider("unknown-provider")
    assert models == []


def test_get_all_providers():
    """Test getting all supported providers."""
    providers = get_all_providers()
    assert isinstance(providers, list)
    assert "openai" in providers
    assert "claude" in providers
    assert "gemini" in providers
    assert "grok" in providers
    assert "perplexity" in providers
    assert "mistral" in providers
    assert "deepseek" in providers
    assert len(providers) == 7


def test_get_all_models():
    """Test getting all supported models."""
    models = get_all_models()
    assert isinstance(models, list)
    assert "gpt-5.2" in models
    assert "claude-opus-4-6" in models
    assert "gemini-3-pro-preview" in models
    assert "grok-4-1-fast-reasoning" in models
    assert "sonar" in models
    assert "mistral-large-latest" in models
    assert "deepseek-chat" in models
    assert len(models) >= 31  # Should have many models (5+3+5+9+4+6+2=34)


def test_resolve_provider_shortcut_all():
    """Test resolving all provider shortcuts."""
    assert resolve_provider_shortcut("gpt") == "openai"
    assert resolve_provider_shortcut("gem") == "gemini"
    assert resolve_provider_shortcut("cla") == "claude"
    assert resolve_provider_shortcut("grok") == "grok"
    assert resolve_provider_shortcut("perp") == "perplexity"
    assert resolve_provider_shortcut("mist") == "mistral"
    assert resolve_provider_shortcut("deep") == "deepseek"


def test_resolve_provider_shortcut_unknown():
    """Test resolving unknown shortcut returns None."""
    assert resolve_provider_shortcut("xxx") is None
    assert resolve_provider_shortcut("") is None
    assert resolve_provider_shortcut("openai") is None  # Full name, not shortcut


def test_get_provider_shortcut_all():
    """Test getting shortcut for all providers."""
    assert get_provider_shortcut("openai") == "gpt"
    assert get_provider_shortcut("gemini") == "gem"
    assert get_provider_shortcut("claude") == "cla"
    assert get_provider_shortcut("grok") == "grok"
    assert get_provider_shortcut("perplexity") == "perp"
    assert get_provider_shortcut("mistral") == "mist"
    assert get_provider_shortcut("deepseek") == "deep"


def test_get_provider_shortcut_unknown():
    """Test getting shortcut for unknown provider returns None."""
    assert get_provider_shortcut("unknown") is None
    assert get_provider_shortcut("") is None


def test_provider_shortcuts_bidirectional():
    """Test that shortcuts and providers map correctly both ways."""
    for shortcut, provider in PROVIDER_SHORTCUTS.items():
        # Shortcut -> Provider
        assert resolve_provider_shortcut(shortcut) == provider
        # Provider -> Shortcut
        assert get_provider_shortcut(provider) == shortcut


def test_model_registry_completeness():
    """Test that MODEL_REGISTRY has entries for all providers."""
    for provider in PROVIDER_SHORTCUTS.values():
        models = get_models_for_provider(provider)
        assert len(models) > 0, f"Provider {provider} has no models"


def test_model_to_provider_reverse_mapping():
    """Test that all models map back to their providers correctly."""
    for provider, models in MODEL_REGISTRY.items():
        for model in models:
            assert get_provider_for_model(model) == provider


def test_no_duplicate_models():
    """Test that no model appears in multiple providers."""
    all_models = []
    for models in MODEL_REGISTRY.values():
        all_models.extend(models)

    # Check for duplicates
    assert len(all_models) == len(set(all_models)), "Found duplicate models across providers"
