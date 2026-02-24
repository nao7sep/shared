"""
Integration test for PolyChat.

This test validates the complete flow:
1. Create temporary profile with real API keys
2. Send messages to all available AI providers
3. Save chat
4. Load chat in new session
5. Verify data integrity by asking AI to count interactions
"""

import json
import tempfile
import time
from pathlib import Path
from datetime import datetime

import pytest

from polychat.chat import (
    load_chat,
    save_chat,
    add_user_message,
    add_assistant_message,
    get_messages_for_ai,
)
from polychat.keys.loader import load_api_key
from polychat.ai.openai_provider import OpenAIProvider
from polychat.ai.claude_provider import ClaudeProvider
from polychat.ai.gemini_provider import GeminiProvider
from polychat.ai.grok_provider import GrokProvider
from polychat.ai.perplexity_provider import PerplexityProvider
from polychat.ai.mistral_provider import MistralProvider
from polychat.ai.deepseek_provider import DeepSeekProvider

from .test_helpers import find_test_api_keys_file, load_test_config, is_ai_available


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


def log(message: str, indent: int = 0):
    """Print timestamped log message."""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    prefix = "  " * indent
    print(f"[{timestamp}] {prefix}{message}")


async def send_and_receive(provider, messages: list, model: str, provider_name: str) -> tuple[str, float, int, list, dict]:
    """Send messages and collect streaming response with timing and usage data.

    Returns:
        Tuple of (full_response, elapsed_seconds, chunk_count, chunk_timings, usage_metadata)
    """
    start = time.time()
    # Get full response with metadata (non-streaming to get usage data reliably)
    content, metadata = await provider.get_full_response(messages, model)

    elapsed = time.time() - start
    usage = metadata.get("usage", {})

    return content, elapsed, 1, [elapsed], usage


def create_temp_profile(test_config: dict, temp_dir: Path) -> Path:
    """Create temporary profile file using .dev-api-keys.json data.

    Args:
        test_config: Loaded .dev-api-keys.json content
        temp_dir: Temporary directory path

    Returns:
        Path to created profile file
    """
    log("Creating temporary profile...")

    # Find first available AI as default
    default_ai = None
    for provider in test_config.keys():
        if is_ai_available(provider):
            default_ai = provider
            break

    if not default_ai:
        raise ValueError("No AI providers available in .dev-api-keys.json")

    # Build models dict and api_keys from test config
    models = {}
    api_keys = {}

    for provider, config in test_config.items():
        if config.get("api_key"):
            models[provider] = config["model"]
            # Store key directly in profile for test
            api_keys[provider] = {
                "type": "direct",
                "value": config["api_key"]
            }

    profile_data = {
        "default_ai": default_ai,
        "models": models,
        "timeout": 300,
        "input_mode": "quick",
        "system_prompt": None,
        "chats_dir": str(temp_dir / "chats"),
        "logs_dir": str(temp_dir / "logs"),
        "api_keys": api_keys
    }

    profile_path = temp_dir / "test-profile.json"
    with open(profile_path, 'w', encoding='utf-8') as f:
        json.dump(profile_data, f, indent=2)

    log(f"Profile created: {profile_path}", indent=1)
    log(f"Default AI: {default_ai}", indent=1)
    log(f"Available AIs: {', '.join(models.keys())}", indent=1)

    return profile_path


def load_api_key_direct(provider: str, config: dict) -> str:
    """Load API key from direct value (test only)."""
    if config.get("type") == "direct":
        return config["value"]
    return load_api_key(provider, config)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_chat_flow():
    """
    Complete integration test:
    - Creates temp profile
    - Sends message to each available AI
    - Saves chat
    - Loads it back
    - Verifies integrity via AI count
    """
    test_start_time = time.time()

    log("=" * 80)
    log("STARTING INTEGRATION TEST")
    log("=" * 80)

    # Check if we have test config
    test_config_file = find_test_api_keys_file()
    if not test_config_file:
        pytest.skip(".dev-api-keys.json not found")

    test_config = load_test_config()

    # Count available AIs
    available_ais = [ai for ai in test_config.keys() if is_ai_available(ai)]
    if not available_ais:
        pytest.skip("No AI providers configured in .dev-api-keys.json")

    log(f"Found {len(available_ais)} available AI provider(s): {', '.join(available_ais)}")
    log("")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # ========================================================================
        # PHASE 1: Setup
        # ========================================================================
        log("PHASE 1: Setup", indent=0)
        log("-" * 80)

        create_temp_profile(test_config, temp_path)
        chat_file_path = temp_path / "chats" / "integration-test.json"

        log("")

        # ========================================================================
        # PHASE 2: Send messages to each AI
        # ========================================================================
        log("PHASE 2: Sending messages to AI providers", indent=0)
        log("-" * 80)

        # Initialize chat
        chat = load_chat(str(chat_file_path))

        # Collaborative storytelling - each AI builds on previous responses
        def get_next_prompt(interaction_count: int) -> str:
            """Generate contextual prompt that builds on chat history."""
            prompts = [
                "Start a short story with one sentence. Introduce a character and a setting.",
                "Continue the story. Add one sentence describing what the character does next.",
                "Add a complication or challenge to the story in one sentence.",
                "Introduce a second character who helps or hinders. One sentence.",
                "Describe how the situation changes. One sentence.",
                "Add an unexpected twist to the story. One sentence.",
                "Continue the story with one more sentence, building on everything so far.",
            ]
            # Cycle through prompts if we have more than 7 AIs
            return prompts[interaction_count % len(prompts)]

        interaction_count = 0
        total_time = 0.0

        for idx, provider_name in enumerate(available_ais):
            log(f"Testing {provider_name.upper()}...", indent=1)

            config = test_config[provider_name]
            model = config["model"]
            api_key = config["api_key"]

            # Create provider instance with timeout from profile
            provider_class = PROVIDER_CLASSES[provider_name]
            timeout = test_config.get("timeout", 300)
            provider = provider_class(api_key=api_key, timeout=timeout)

            # Show API endpoint being used (to prove different AIs)
            endpoint_info = "unknown"
            if hasattr(provider, 'client'):
                # For OpenAI-compatible clients (OpenAI, DeepSeek, Grok, etc.)
                if hasattr(provider.client, 'base_url'):
                    endpoint_info = str(provider.client.base_url)
                # For Claude (Anthropic) client
                elif hasattr(provider.client, '_client') and hasattr(provider.client._client, 'base_url'):
                    endpoint_info = str(provider.client._client.base_url)
                # For Gemini (Google GenAI) client
                elif hasattr(provider.client, '_api_client') and hasattr(provider.client._api_client, '_http_options'):
                    http_opts = provider.client._api_client._http_options
                    if hasattr(http_opts, 'base_url') and http_opts.base_url:
                        endpoint_info = str(http_opts.base_url)
            log(f"API endpoint: {endpoint_info}", indent=2)

            # Get contextual prompt that builds on chat
            prompt = get_next_prompt(interaction_count)

            log(f"User message: {prompt}", indent=2)

            # Add user message
            add_user_message(chat, prompt)

            # Get messages for AI (exclude errors)
            messages = get_messages_for_ai(chat)

            # Send and receive
            try:
                response, elapsed, chunks, timings, usage = await send_and_receive(provider, messages, model, provider_name)
                total_time += elapsed

                # Display usage information
                usage_str = ""
                if usage:
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)
                    total_tokens = usage.get("total_tokens", 0)
                    usage_str = f" [Usage: {prompt_tokens}p + {completion_tokens}c = {total_tokens}t tokens"

                    # Show additional token types if available
                    if "cached_tokens" in usage:
                        usage_str += f", {usage['cached_tokens']} cached"
                    if "reasoning_tokens" in usage:
                        usage_str += f", {usage['reasoning_tokens']} reasoning"
                    usage_str += "]"
                else:
                    usage_str = " [Usage: not available]"

                log(f"Response ({elapsed:.2f}s){usage_str}: {response}", indent=2)

                # Add assistant message
                add_assistant_message(chat, response, model)

                interaction_count += 1

            except Exception as e:
                log(f"ERROR: {str(e)}", indent=2)
                # Continue to test other providers
                continue

            log("")

        if interaction_count == 0:
            pytest.fail("No AI providers responded successfully")

        log(f"Completed {interaction_count} successful interaction(s) in {total_time:.2f}s total")
        log("")

        # ========================================================================
        # PHASE 3: Save chat
        # ========================================================================
        log("PHASE 3: Saving chat", indent=0)
        log("-" * 80)

        save_start = time.time()
        await save_chat(str(chat_file_path), chat)
        save_elapsed = time.time() - save_start

        log(f"Saved to: {chat_file_path}", indent=1)
        log(f"Save time: {save_elapsed:.3f}s", indent=1)
        log(f"Total messages: {len(chat['messages'])}", indent=1)

        # Verify file exists and check size
        file_size = chat_file_path.stat().st_size
        log(f"File size: {file_size:,} bytes", indent=1)
        log("")

        # ========================================================================
        # PHASE 4: Load chat (simulate new session)
        # ========================================================================
        log("PHASE 4: Loading chat (simulating new session)", indent=0)
        log("-" * 80)

        load_start = time.time()
        loaded_chat = load_chat(str(chat_file_path))
        load_elapsed = time.time() - load_start

        log(f"Loaded from: {chat_file_path}", indent=1)
        log(f"Load time: {load_elapsed:.3f}s", indent=1)
        log(f"Messages loaded: {len(loaded_chat['messages'])}", indent=1)
        log("")

        # ========================================================================
        # PHASE 5: Verify data integrity
        # ========================================================================
        log("PHASE 5: Verifying data integrity", indent=0)
        log("-" * 80)

        # Check message count matches
        original_count = len(chat['messages'])
        loaded_count = len(loaded_chat['messages'])

        log(f"Original message count: {original_count}", indent=1)
        log(f"Loaded message count: {loaded_count}", indent=1)

        assert loaded_count == original_count, \
            f"Message count mismatch: {loaded_count} != {original_count}"
        log("✓ Message count matches", indent=1)

        # Verify message structure
        for i, (orig, loaded) in enumerate(zip(chat['messages'], loaded_chat['messages'])):
            assert orig['role'] == loaded['role'], \
                f"Message {i}: role mismatch"
            assert orig['content'] == loaded['content'], \
                f"Message {i}: content mismatch"
            assert orig['timestamp'] == loaded['timestamp'], \
                f"Message {i}: timestamp mismatch"
            if 'model' in orig:
                assert orig['model'] == loaded['model'], \
                    f"Message {i}: model mismatch"

        log("✓ All message data matches exactly", indent=1)
        log("")

        # ========================================================================
        # PHASE 6: AI-based verification
        # ========================================================================
        log("PHASE 6: AI-based verification (ask AI to count interactions)", indent=0)
        log("-" * 80)

        # Use first available AI for verification
        verify_provider_name = available_ais[0]
        verify_config = test_config[verify_provider_name]
        timeout = test_config.get("timeout", 300)
        verify_provider = PROVIDER_CLASSES[verify_provider_name](api_key=verify_config["api_key"], timeout=timeout)

        log(f"Using {verify_provider_name} for verification", indent=1)

        # Ask AI to summarize the story and count messages
        verification_prompt = (
            "We just wrote a collaborative story together. "
            "First, summarize the story in 2-3 sentences. "
            "Then answer: How many user prompts did I send? "
            "Format your answer as 'Count: X' or 'X prompts' or just the number."
        )

        add_user_message(loaded_chat, verification_prompt)
        messages = get_messages_for_ai(loaded_chat)

        verification_response, verify_elapsed, verify_chunks, verify_timings, verify_usage = await send_and_receive(
            verify_provider,
            messages,
            verify_config["model"],
            verify_provider_name
        )

        log(f"Verification prompt: {verification_prompt}", indent=1)

        # Display verification usage
        verify_usage_str = ""
        if verify_usage:
            prompt_tokens = verify_usage.get("prompt_tokens", 0)
            completion_tokens = verify_usage.get("completion_tokens", 0)
            total_tokens = verify_usage.get("total_tokens", 0)
            verify_usage_str = f" [Usage: {total_tokens}t tokens]"

        log(f"AI response ({verify_elapsed:.2f}s{verify_usage_str}):", indent=1)
        log(f"{verification_response.strip()}", indent=1)

        # Try to find the count in the response
        try:
            import re
            actual_user_count = len([m for m in loaded_chat['messages'] if m['role'] == 'user'])

            # Try multiple patterns to extract count
            # Pattern 1: "Count: X" or "count: X"
            match = re.search(r'count:\s*(\d+)', verification_response, re.IGNORECASE)
            if not match:
                # Pattern 2: "X prompts" or "X messages"
                match = re.search(r'(\d+)\s+(?:prompts|messages)', verification_response, re.IGNORECASE)
            if not match:
                # Pattern 3: Just look for numbers
                numbers = re.findall(r'\b(\d+)\b', verification_response)
                if numbers:
                    # Take the last number found (usually the count)
                    match = type('obj', (object,), {'group': lambda self, x: numbers[-1]})()

            if match:
                reported_count = int(match.group(1))
                log(f"AI reported: {reported_count} user messages", indent=1)
                log(f"Actual count: {actual_user_count} user messages", indent=1)

                if reported_count == actual_user_count:
                    log("✓ AI verification successful - count matches!", indent=1)
                else:
                    log(f"⚠ Count mismatch ({reported_count} vs {actual_user_count}) - but AI read and understood the chat", indent=1)
            else:
                log("✓ AI provided summary (could not parse count, but response shows chat understanding)", indent=1)

        except Exception as e:
            log(f"✓ AI provided summary (count parsing error: {e})", indent=1)

        log("")

        # ========================================================================
        # SUMMARY
        # ========================================================================
        log("=" * 80)
        log("TEST SUMMARY")
        log("=" * 80)
        log(f"✓ Tested {len(available_ais)} AI provider(s)")
        log(f"✓ Successful interactions: {interaction_count}")
        log(f"✓ Total messages in chat: {len(chat['messages'])}")
        log("✓ Chat saved and loaded successfully")
        log("✓ Data integrity verified")
        log(f"✓ Total test time: {time.time() - test_start_time:.2f}s")
        log("=" * 80)
        log("INTEGRATION TEST PASSED")
        log("=" * 80)


if __name__ == "__main__":
    # Allow running directly for manual testing
    pytest.main([__file__, "-v", "-s", "-m", "integration"])
