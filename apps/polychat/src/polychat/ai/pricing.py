"""Per-model pricing registry for AI providers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelPricing:
    """Per-model pricing in USD per million tokens."""

    input_per_mtok: float
    output_per_mtok: float
    cached_input_per_mtok: float | None = None
    cache_write_per_mtok: float | None = None


# Pricing registry: model name -> ModelPricing
# Sources (Feb 2026):
#   OpenAI:     https://developers.openai.com/api/docs/models
#   Anthropic:  https://platform.claude.com/docs/en/about-claude/pricing
#   Google:     https://ai.google.dev/gemini-api/docs/pricing
#   xAI:        https://docs.x.ai/developers/models
#   Perplexity: https://docs.perplexity.ai/docs/getting-started/pricing
#   Mistral:    https://mistral.ai/pricing
#   DeepSeek:   https://api-docs.deepseek.com/quick_start/pricing
MODEL_PRICING: dict[str, ModelPricing] = {
    # OpenAI
    "gpt-5.2": ModelPricing(1.75, 14.00, cached_input_per_mtok=0.175),
    "gpt-5": ModelPricing(1.25, 10.00, cached_input_per_mtok=0.125),
    "gpt-5-mini": ModelPricing(0.25, 2.00, cached_input_per_mtok=0.025),
    "gpt-5-nano": ModelPricing(0.05, 0.40, cached_input_per_mtok=0.005),
    "gpt-4.1": ModelPricing(2.00, 8.00, cached_input_per_mtok=0.50),
    # Claude — cache_write_per_mtok reflects the 25% write surcharge that
    # applies at the default 5-minute TTL. Longer TTLs cost more.
    "claude-opus-4-6": ModelPricing(
        5.00,
        25.00,
        cached_input_per_mtok=0.50,
        cache_write_per_mtok=6.25,
    ),
    "claude-sonnet-4-6": ModelPricing(
        3.00,
        15.00,
        cached_input_per_mtok=0.30,
        cache_write_per_mtok=3.75,
    ),
    "claude-haiku-4-5": ModelPricing(
        1.00,
        5.00,
        cached_input_per_mtok=0.10,
        cache_write_per_mtok=1.25,
    ),
    # Gemini
    "gemini-3.1-pro-preview": ModelPricing(2.00, 12.00, cached_input_per_mtok=0.20),
    "gemini-3-pro-preview": ModelPricing(2.00, 12.00, cached_input_per_mtok=0.20),
    "gemini-3-flash-preview": ModelPricing(0.50, 3.00, cached_input_per_mtok=0.05),
    "gemini-2.5-pro": ModelPricing(1.25, 10.00, cached_input_per_mtok=0.125),
    "gemini-2.5-flash": ModelPricing(0.30, 2.50, cached_input_per_mtok=0.03),
    "gemini-2.5-flash-lite": ModelPricing(0.10, 0.40, cached_input_per_mtok=0.01),
    # Grok
    "grok-4-1-fast-reasoning": ModelPricing(0.20, 0.50, cached_input_per_mtok=0.05),
    "grok-4-1-fast-non-reasoning": ModelPricing(0.20, 0.50, cached_input_per_mtok=0.05),
    "grok-code-fast-1": ModelPricing(0.20, 1.50, cached_input_per_mtok=0.02),
    "grok-4-fast-reasoning": ModelPricing(0.20, 0.50, cached_input_per_mtok=0.05),
    "grok-4-fast-non-reasoning": ModelPricing(0.20, 0.50, cached_input_per_mtok=0.05),
    "grok-4-0709": ModelPricing(3.00, 15.00, cached_input_per_mtok=0.75),
    "grok-3-mini": ModelPricing(0.30, 0.50, cached_input_per_mtok=0.075),
    "grok-3": ModelPricing(3.00, 15.00, cached_input_per_mtok=0.75),
    "grok-2-vision-1212": ModelPricing(2.00, 10.00),
    # Perplexity
    "sonar": ModelPricing(1.00, 1.00),
    "sonar-pro": ModelPricing(3.00, 15.00),
    "sonar-reasoning-pro": ModelPricing(2.00, 8.00),
    "sonar-deep-research": ModelPricing(2.00, 8.00),
    # Mistral
    "mistral-large-latest": ModelPricing(0.50, 1.50),
    "mistral-medium-latest": ModelPricing(0.40, 2.00),
    "mistral-small-latest": ModelPricing(0.10, 0.30),
    "ministral-14b-latest": ModelPricing(0.20, 0.20),
    "ministral-8b-latest": ModelPricing(0.15, 0.15),
    "ministral-3b-latest": ModelPricing(0.10, 0.10),
    # DeepSeek
    "deepseek-chat": ModelPricing(0.28, 0.42, cached_input_per_mtok=0.028),
    "deepseek-reasoner": ModelPricing(0.28, 0.42, cached_input_per_mtok=0.028),
}


def get_model_pricing(model: str) -> ModelPricing | None:
    """Get pricing data for a model, or None if unknown."""
    return MODEL_PRICING.get(model)

