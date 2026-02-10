"""Model registry and provider mapping for PolyChat.

This module maintains a registry of all supported models and provides
functions for model-to-provider mapping and smart model switching.
"""

from typing import Dict, List, Optional


# Provider short codes for commands
PROVIDER_SHORTCUTS = {
    "gpt": "openai",
    "gem": "gemini",
    "cla": "claude",
    "grok": "grok",
    "perp": "perplexity",
    "mist": "mistral",
    "deep": "deepseek",
}

# Model registry: provider -> list of models
# Official documentation for model verification:
# - OpenAI: https://platform.openai.com/docs/models
# - Claude: https://platform.claude.com/docs/en/about-claude/models/overview
# - Gemini: https://ai.google.dev/gemini-api/docs/models?hl=en
# - Grok: https://docs.x.ai/developers/models
# - Perplexity: https://docs.perplexity.ai/docs/getting-started/models
# - Mistral: https://docs.mistral.ai/getting-started/models
# - DeepSeek: https://api-docs.deepseek.com/quick_start/pricing
MODEL_REGISTRY: Dict[str, List[str]] = {
    "openai": [
        # "gpt-5.2-pro",  # Not a chat model
        "gpt-5.2",
        "gpt-5",
        "gpt-5-mini",
        "gpt-5-nano",
        "gpt-4.1",
    ],
    "claude": [
        "claude-opus-4-6",
        "claude-sonnet-4-5",
        "claude-haiku-4-5",
    ],
    "gemini": [
        "gemini-3-pro-preview",
        "gemini-3-flash-preview",
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
    ],
    "grok": [
        "grok-4-1-fast-reasoning",
        "grok-4-1-fast-non-reasoning",
        "grok-code-fast-1",
        "grok-4-fast-reasoning",
        "grok-4-fast-non-reasoning",
        "grok-4-0709",
        "grok-3-mini",
        "grok-3",
        "grok-2-vision-1212",
    ],
    "perplexity": [
        "sonar",
        "sonar-pro",
        "sonar-reasoning-pro",
        "sonar-deep-research",
    ],
    "mistral": [
        "mistral-large-latest",
        "mistral-medium-latest",
        "mistral-small-latest",
        "ministral-14b-latest",
        "ministral-8b-latest",
        "ministral-3b-latest",
        # "magistral-medium-latest",  # Requires different message format
        # "magistral-small-latest",  # Requires different message format
    ],
    "deepseek": [
        "deepseek-chat",
        "deepseek-reasoner",
    ],
}

# Search support registry
SEARCH_SUPPORTED_PROVIDERS: set[str] = {
    "openai", "claude", "gemini", "grok", "perplexity",
}

THINKING_SUPPORTED_PROVIDERS: set[str] = {
    "claude",
}

# Reverse mapping: model -> provider
MODEL_TO_PROVIDER: Dict[str, str] = {}
for provider, models in MODEL_REGISTRY.items():
    for model in models:
        MODEL_TO_PROVIDER[model] = provider


def get_provider_for_model(model: str) -> Optional[str]:
    """Get AI provider for a given model name.

    Args:
        model: Model name

    Returns:
        Provider name, or None if model not found
    """
    return MODEL_TO_PROVIDER.get(model)


def get_models_for_provider(provider: str) -> List[str]:
    """Get list of models for a given provider.

    Args:
        provider: Provider name

    Returns:
        List of model names
    """
    return MODEL_REGISTRY.get(provider, [])


def get_all_providers() -> List[str]:
    """Get list of all supported providers.

    Returns:
        List of provider names
    """
    return list(MODEL_REGISTRY.keys())


def get_all_models() -> List[str]:
    """Get list of all supported models.

    Returns:
        List of model names
    """
    return list(MODEL_TO_PROVIDER.keys())


def resolve_provider_shortcut(shortcut: str) -> Optional[str]:
    """Resolve provider shortcut to full provider name.

    Args:
        shortcut: Provider shortcut (e.g., "gpt", "cla")

    Returns:
        Full provider name, or None if not found
    """
    return PROVIDER_SHORTCUTS.get(shortcut)


def get_provider_shortcut(provider: str) -> Optional[str]:
    """Get shortcut for a provider.

    Args:
        provider: Provider name

    Returns:
        Shortcut, or None if not found
    """
    for shortcut, prov in PROVIDER_SHORTCUTS.items():
        if prov == provider:
            return shortcut
    return None


def provider_supports_search(provider: str) -> bool:
    """Check if provider supports web search.

    Args:
        provider: Provider name

    Returns:
        True if provider supports web search, False otherwise
    """
    return provider in SEARCH_SUPPORTED_PROVIDERS


def provider_supports_thinking(provider: str) -> bool:
    """Check if provider supports extended thinking/reasoning.

    Args:
        provider: Provider name

    Returns:
        True if provider supports thinking mode, False otherwise
    """
    return provider in THINKING_SUPPORTED_PROVIDERS
