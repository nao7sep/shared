"""Backward-compatible facade for AI model registry APIs."""

from .ai.capabilities import SEARCH_SUPPORTED_PROVIDERS, provider_supports_search
from .ai.catalog import (
    MODEL_REGISTRY,
    MODEL_TO_PROVIDER,
    PROVIDER_SHORTCUTS,
    find_models_by_subsequence,
    get_all_models,
    get_all_providers,
    get_models_for_provider,
    get_provider_for_model,
    get_provider_shortcut,
    normalize_model_query,
    resolve_model_candidates,
    resolve_provider_shortcut,
)
from .ai.pricing import MODEL_PRICING, ModelPricing, get_model_pricing

__all__ = [
    "PROVIDER_SHORTCUTS",
    "MODEL_REGISTRY",
    "SEARCH_SUPPORTED_PROVIDERS",
    "ModelPricing",
    "MODEL_PRICING",
    "MODEL_TO_PROVIDER",
    "get_model_pricing",
    "get_provider_for_model",
    "normalize_model_query",
    "find_models_by_subsequence",
    "resolve_model_candidates",
    "get_models_for_provider",
    "get_all_providers",
    "get_all_models",
    "resolve_provider_shortcut",
    "get_provider_shortcut",
    "provider_supports_search",
]

