"""Model registry and provider mapping for PolyChat.

This module maintains a registry of all supported models and provides
functions for model-to-provider mapping and smart model switching.
It also provides per-model pricing data for cost estimation.
"""

from dataclasses import dataclass
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
        "claude-sonnet-4-6",
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


@dataclass(frozen=True, slots=True)
class ModelPricing:
    """Per-model pricing in USD per million tokens.

    Prices are approximate and may not reflect the latest provider changes.
    """

    input_per_mtok: float
    output_per_mtok: float
    cached_input_per_mtok: float | None = None


# Pricing registry: model name -> ModelPricing
# Sources (Feb 2026):
#   OpenAI:     https://developers.openai.com/api/docs/models
#   Anthropic:  https://platform.claude.com/docs/en/about-claude/pricing
#   Google:     https://ai.google.dev/gemini-api/docs/pricing
#   xAI:        https://docs.x.ai/developers/models
#   Perplexity: https://docs.perplexity.ai/docs/getting-started/pricing
#   Mistral:    https://mistral.ai/pricing
#   DeepSeek:   https://api-docs.deepseek.com/quick_start/pricing
MODEL_PRICING: Dict[str, ModelPricing] = {
    # OpenAI
    "gpt-5.2":   ModelPricing(1.75, 14.00, cached_input_per_mtok=0.175),
    "gpt-5":     ModelPricing(1.25, 10.00, cached_input_per_mtok=0.125),
    "gpt-5-mini": ModelPricing(0.25, 2.00, cached_input_per_mtok=0.025),
    "gpt-5-nano": ModelPricing(0.05, 0.40, cached_input_per_mtok=0.005),
    "gpt-4.1":   ModelPricing(2.00, 8.00, cached_input_per_mtok=0.50),
    # Claude
    "claude-opus-4-6":   ModelPricing(5.00, 25.00, cached_input_per_mtok=0.50),
    "claude-sonnet-4-6": ModelPricing(3.00, 15.00, cached_input_per_mtok=0.30),
    "claude-haiku-4-5":  ModelPricing(1.00, 5.00,  cached_input_per_mtok=0.10),
    # Gemini
    "gemini-3-pro-preview":  ModelPricing(2.00, 12.00, cached_input_per_mtok=0.20),
    "gemini-3-flash-preview": ModelPricing(0.50, 3.00, cached_input_per_mtok=0.05),
    "gemini-2.5-pro":        ModelPricing(1.25, 10.00, cached_input_per_mtok=0.125),
    "gemini-2.5-flash":      ModelPricing(0.30, 2.50,  cached_input_per_mtok=0.03),
    "gemini-2.5-flash-lite": ModelPricing(0.10, 0.40,  cached_input_per_mtok=0.01),
    # Grok
    "grok-4-1-fast-reasoning":     ModelPricing(0.20, 0.50, cached_input_per_mtok=0.05),
    "grok-4-1-fast-non-reasoning": ModelPricing(0.20, 0.50, cached_input_per_mtok=0.05),
    "grok-code-fast-1":            ModelPricing(0.20, 1.50, cached_input_per_mtok=0.02),
    "grok-4-fast-reasoning":       ModelPricing(0.20, 0.50, cached_input_per_mtok=0.05),
    "grok-4-fast-non-reasoning":   ModelPricing(0.20, 0.50, cached_input_per_mtok=0.05),
    "grok-4-0709":                 ModelPricing(3.00, 15.00, cached_input_per_mtok=0.75),
    "grok-3-mini":                 ModelPricing(0.30, 0.50, cached_input_per_mtok=0.075),
    "grok-3":                      ModelPricing(3.00, 15.00, cached_input_per_mtok=0.75),
    "grok-2-vision-1212":          ModelPricing(2.00, 10.00),
    # Perplexity
    "sonar":                ModelPricing(1.00, 1.00),
    "sonar-pro":            ModelPricing(3.00, 15.00),
    "sonar-reasoning-pro":  ModelPricing(2.00, 8.00),
    "sonar-deep-research":  ModelPricing(2.00, 8.00),
    # Mistral
    "mistral-large-latest":   ModelPricing(0.50, 1.50),
    "mistral-medium-latest":  ModelPricing(0.40, 2.00),
    "mistral-small-latest":   ModelPricing(0.10, 0.30),
    "ministral-14b-latest":   ModelPricing(0.20, 0.20),
    "ministral-8b-latest":    ModelPricing(0.15, 0.15),
    "ministral-3b-latest":    ModelPricing(0.10, 0.10),
    # DeepSeek
    "deepseek-chat":     ModelPricing(0.28, 0.42, cached_input_per_mtok=0.028),
    "deepseek-reasoner": ModelPricing(0.28, 0.42, cached_input_per_mtok=0.028),
}


def get_model_pricing(model: str) -> ModelPricing | None:
    """Get pricing data for a model, or None if unknown."""
    return MODEL_PRICING.get(model)


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
) -> List[str]:
    """Find models whose normalized names contain pattern as subsequence."""
    normalized_pattern = normalize_model_query(pattern)
    if not normalized_pattern:
        return []

    if provider:
        candidates = MODEL_REGISTRY.get(provider, [])
    else:
        candidates: List[str] = []
        for provider_models in MODEL_REGISTRY.values():
            candidates.extend(provider_models)

    matches: List[str] = []
    for model in candidates:
        if _is_subsequence(normalized_pattern, normalize_model_query(model)):
            matches.append(model)
    return matches


def resolve_model_candidates(
    pattern: str,
    *,
    provider: Optional[str] = None,
) -> List[str]:
    """Resolve a model query to exact or fuzzy candidates.

    Resolution order:
    1. exact registry match (case-sensitive, then lowercase variant)
    2. normalized subsequence matching across registry models
    """
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
