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
MODEL_REGISTRY: Dict[str, List[str]] = {
    "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"],
    "claude": [
        "claude-sonnet-4",
        "claude-opus-4",
        "claude-3-5-sonnet-20241022",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
    ],
    "gemini": [
        "gemini-2.0-flash",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-1.0-pro",
    ],
    "grok": ["grok-2", "grok-1"],
    "perplexity": ["sonar-pro", "sonar"],
    "mistral": ["mistral-large", "mistral-medium", "mistral-small"],
    "deepseek": ["deepseek-chat", "deepseek-coder"],
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
