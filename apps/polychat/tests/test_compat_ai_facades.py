"""Compatibility tests for legacy models/costs facade modules."""

from polychat import costs as legacy_costs
from polychat import models as legacy_models
from polychat.ai.capabilities import (
    SEARCH_SUPPORTED_PROVIDERS as search_supported_providers_new,
    provider_supports_search as provider_supports_search_new,
)
from polychat.ai.catalog import (
    MODEL_REGISTRY as model_registry_new,
    PROVIDER_SHORTCUTS as provider_shortcuts_new,
    get_provider_for_model as get_provider_for_model_new,
)
from polychat.ai.costing import estimate_cost as estimate_cost_new
from polychat.ai.pricing import get_model_pricing as get_model_pricing_new
from polychat.formatting.costs import (
    format_cost_line as format_cost_line_new,
    format_cost_usd as format_cost_usd_new,
)


def test_models_facade_re_exports_catalog_symbols() -> None:
    assert legacy_models.PROVIDER_SHORTCUTS == provider_shortcuts_new
    assert legacy_models.MODEL_REGISTRY == model_registry_new
    assert legacy_models.get_provider_for_model is get_provider_for_model_new
    assert legacy_models.get_provider_for_model("gpt-5") == "openai"


def test_models_facade_re_exports_capabilities_and_pricing() -> None:
    assert legacy_models.SEARCH_SUPPORTED_PROVIDERS == search_supported_providers_new
    assert legacy_models.provider_supports_search is provider_supports_search_new
    assert legacy_models.provider_supports_search("openai") is True
    assert legacy_models.get_model_pricing("gpt-5") == get_model_pricing_new("gpt-5")


def test_costs_facade_re_exports_costing_and_formatting() -> None:
    usage = {"prompt_tokens": 1000, "completion_tokens": 500}

    assert legacy_costs.estimate_cost is estimate_cost_new
    assert legacy_costs.format_cost_line is format_cost_line_new
    assert legacy_costs.format_cost_usd is format_cost_usd_new
    assert legacy_costs.estimate_cost("grok-2-vision-1212", usage) == estimate_cost_new(
        "grok-2-vision-1212", usage
    )
    assert legacy_costs.format_cost_line("grok-2-vision-1212", usage) == format_cost_line_new(
        "grok-2-vision-1212", usage
    )
    assert legacy_costs.format_cost_usd(0.007) == format_cost_usd_new(0.007)

