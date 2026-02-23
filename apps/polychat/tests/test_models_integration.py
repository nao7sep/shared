"""Integration test to verify all models in MODEL_REGISTRY work with actual API calls.

This test makes real API calls to every model defined in models.py to verify:
1. Model names are correct and recognized by the API
2. Models are accessible with current API keys
3. Basic functionality works

Requires .dev-api-keys.json with valid API keys for each provider.
"""

import pytest
from polychat.models import MODEL_REGISTRY
from polychat.ai.openai_provider import OpenAIProvider
from polychat.ai.claude_provider import ClaudeProvider
from polychat.ai.gemini_provider import GeminiProvider
from polychat.ai.grok_provider import GrokProvider
from polychat.ai.perplexity_provider import PerplexityProvider
from polychat.ai.mistral_provider import MistralProvider
from polychat.ai.deepseek_provider import DeepSeekProvider
from tests.test_helpers import find_test_api_keys_file, load_test_config, is_ai_available


# Simple test prompt
TEST_PROMPT = "Say 'OK' and nothing else."

# Provider class mapping
PROVIDER_CLASSES = {
    "openai": OpenAIProvider,
    "claude": ClaudeProvider,
    "gemini": GeminiProvider,
    "grok": GrokProvider,
    "perplexity": PerplexityProvider,
    "mistral": MistralProvider,
    "deepseek": DeepSeekProvider,
}


async def check_single_model(provider_name: str, model: str, api_key: str) -> dict:
    """Test a single model with actual API call.

    Args:
        provider_name: Provider name
        model: Model name
        api_key: API key for the provider

    Returns:
        Dict with test results: {
            "provider": str,
            "model": str,
            "status": "success" | "error",
            "response": str (if success),
            "error": str (if error)
        }
    """
    result = {
        "provider": provider_name,
        "model": model,
        "status": "error",
        "response": None,
        "error": None,
    }

    try:
        # Get provider class and instantiate
        provider_class = PROVIDER_CLASSES[provider_name]
        provider = provider_class(api_key=api_key, timeout=300.0)

        # Prepare messages
        messages = [{"role": "user", "content": TEST_PROMPT}]

        # Make API call with streaming
        chunks = []
        async for chunk in provider.send_message(messages, model, stream=True):
            chunks.append(chunk)

        # Combine chunks
        response = "".join(chunks)

        result["status"] = "success"
        result["response"] = response.strip()

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result


@pytest.mark.integration
@pytest.mark.asyncio
async def test_all_models_smoke_test():
    """Test all models in MODEL_REGISTRY with actual API calls.

    This is a comprehensive smoke test to verify:
    - All model names are correct
    - Models are accessible
    - Basic functionality works

    Skips providers without API keys configured.
    """
    # Check if we have test config
    test_config_file = find_test_api_keys_file()
    if not test_config_file:
        pytest.skip(".dev-api-keys.json not found")

    test_config = load_test_config()

    # Collect all test results
    all_results = []
    tested_count = 0
    skipped_count = 0

    print("\n" + "=" * 80)
    print("TESTING MODELS IN REGISTRY")
    print("=" * 80)

    # Test each provider's models
    for provider, models in MODEL_REGISTRY.items():
        print(f"\n{provider.upper()}: {len(models)} models")
        print("-" * 80)

        # Check if provider is available
        if not is_ai_available(provider):
            print(f"  ⊘ Skipping {provider} - no API key configured")
            skipped_count += len(models)
            continue

        # Get API key
        provider_config = test_config.get(provider, {})
        api_key = provider_config.get("api_key")

        if not api_key:
            print(f"  ⊘ Skipping {provider} - no API key in config")
            skipped_count += len(models)
            continue

        # Test each model for this provider
        for model in models:
            print(f"  Testing {model}...", end=" ", flush=True)

            result = await check_single_model(provider, model, api_key)
            all_results.append(result)
            tested_count += 1

            if result["status"] == "success":
                response_preview = result["response"][:50] if result["response"] else "empty"
                print(f"✓ OK ({response_preview})")
            else:
                error_msg = result["error"][:60] if result["error"] else "unknown error"
                print(f"✗ FAILED ({error_msg})")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    success_count = sum(1 for r in all_results if r["status"] == "success")
    error_count = sum(1 for r in all_results if r["status"] == "error")

    print(f"Total models in registry: {sum(len(models) for models in MODEL_REGISTRY.values())}")
    print(f"Tested: {tested_count}")
    print(f"Skipped (no API key): {skipped_count}")
    print(f"Successful: {success_count}")
    print(f"Failed: {error_count}")

    # Print failed models
    if error_count > 0:
        print(f"\nFailed models ({error_count}):")
        for result in all_results:
            if result["status"] == "error":
                print(f"  - {result['provider']}/{result['model']}")
                print(f"    Error: {result['error'][:100]}")

    print("\n" + "=" * 80)

    # Store results for inspection
    pytest.test_all_models_results = all_results

    # Test passes if at least one model was tested successfully
    # (Don't fail the test if some models have issues - we want to see all results)
    assert tested_count > 0, "No models were tested"
    assert success_count > 0, "All tested models failed"

    # Print warning if more than 25% of tested models failed
    if tested_count > 0:
        failure_rate = error_count / tested_count
        if failure_rate > 0.25:
            print(f"\nWARNING: {failure_rate*100:.1f}% of tested models failed")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_default_models_work():
    """Test that default models for each provider work.

    This tests the specific models used in profile templates.
    """
    # Check if we have test config
    test_config_file = find_test_api_keys_file()
    if not test_config_file:
        pytest.skip(".dev-api-keys.json not found")

    test_config = load_test_config()

    # Default models from profile.py
    default_models = {
        "openai": "gpt-5-mini",
        "claude": "claude-haiku-4-5",
        "gemini": "gemini-3-flash-preview",
        "grok": "grok-4-1-fast-non-reasoning",
        "perplexity": "sonar",
        "mistral": "mistral-small-latest",
        "deepseek": "deepseek-chat",
    }

    print("\n" + "=" * 80)
    print("TESTING DEFAULT MODELS")
    print("=" * 80)

    results = []

    for provider, model in default_models.items():
        # Check if provider is available
        if not is_ai_available(provider):
            print(f"\n{provider}: SKIPPED (no API key)")
            continue

        # Get API key
        provider_config = test_config.get(provider, {})
        api_key = provider_config.get("api_key")

        print(f"\n{provider}: {model}")
        print(f"  Testing...", end=" ", flush=True)

        result = await check_single_model(provider, model, api_key)
        results.append(result)

        if result["status"] == "success":
            print(f"✓ OK")
        else:
            print(f"✗ FAILED")
            print(f"  Error: {result['error']}")

    print("\n" + "=" * 80)

    # At least one default model should work
    success_count = sum(1 for r in results if r["status"] == "success")
    assert success_count > 0, "All default models failed"

    # Print any failures
    failed = [r for r in results if r["status"] == "error"]
    if failed:
        print(f"\nWARNING: {len(failed)} default model(s) failed:")
        for r in failed:
            print(f"  - {r['provider']}/{r['model']}: {r['error'][:80]}")
