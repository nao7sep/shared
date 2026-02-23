"""Model registry and provider/model lookup helpers."""

from __future__ import annotations

from typing import Optional


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
MODEL_REGISTRY: dict[str, list[str]] = {
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
        "claude-sonnet-4-6",
        "claude-haiku-4-5",
    ],
    "gemini": [
        "gemini-3.1-pro-preview",
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

# Reverse mapping: model -> provider
MODEL_TO_PROVIDER: dict[str, str] = {}
for provider, models in MODEL_REGISTRY.items():
    for model in models:
        MODEL_TO_PROVIDER[model] = provider


def get_provider_for_model(model: str) -> Optional[str]:
    """Get AI provider for a given model name."""
    return MODEL_TO_PROVIDER.get(model)


def normalize_model_query(value: str) -> str:
    """Normalize a model query by keeping only lowercase alphanumeric chars."""
    return "".join(ch.lower() for ch in value if ch.isalnum())


def _is_subsequence(pattern: str, target: str) -> bool:
    """Return True when pattern chars appear in target in-order."""
    if not pattern:
        return False
    index = 0
    for ch in target:
        if ch == pattern[index]:
            index += 1
            if index == len(pattern):
                return True
    return False


def find_models_by_subsequence(
    pattern: str,
    *,
    provider: Optional[str] = None,
) -> list[str]:
    """Find models whose normalized names contain pattern as subsequence."""
    normalized_pattern = normalize_model_query(pattern)
    if not normalized_pattern:
        return []

    if provider:
        candidates = MODEL_REGISTRY.get(provider, [])
    else:
        candidates: list[str] = []
        for provider_models in MODEL_REGISTRY.values():
            candidates.extend(provider_models)

    matches: list[str] = []
    for model in candidates:
        if _is_subsequence(normalized_pattern, normalize_model_query(model)):
            matches.append(model)
    return matches


def resolve_model_candidates(
    pattern: str,
    *,
    provider: Optional[str] = None,
) -> list[str]:
    """Resolve a model query to exact or fuzzy candidates."""
    query = pattern.strip()
    if not query:
        return []

    exact_provider = get_provider_for_model(query)
    if exact_provider and (provider is None or exact_provider == provider):
        return [query]

    lowered = query.lower()
    if lowered != query:
        lowered_provider = get_provider_for_model(lowered)
        if lowered_provider and (provider is None or lowered_provider == provider):
            return [lowered]

    return find_models_by_subsequence(query, provider=provider)


def get_models_for_provider(provider: str) -> list[str]:
    """Get list of models for a given provider."""
    return MODEL_REGISTRY.get(provider, [])


def get_all_providers() -> list[str]:
    """Get list of all supported providers."""
    return list(MODEL_REGISTRY.keys())


def get_all_models() -> list[str]:
    """Get list of all supported models."""
    return list(MODEL_TO_PROVIDER.keys())


def resolve_provider_shortcut(shortcut: str) -> Optional[str]:
    """Resolve provider shortcut to full provider name."""
    return PROVIDER_SHORTCUTS.get(shortcut)


def get_provider_shortcut(provider: str) -> Optional[str]:
    """Get shortcut for a provider."""
    for shortcut, prov in PROVIDER_SHORTCUTS.items():
        if prov == provider:
            return shortcut
    return None

