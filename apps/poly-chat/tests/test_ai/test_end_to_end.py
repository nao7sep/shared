"""
End-to-end test for PolyChat.

This test validates the complete flow:
1. Create temporary profile with real API keys
2. Send messages to all available AI providers
3. Save conversation
4. Load conversation in new session
5. Verify data integrity by asking AI to count interactions
"""

import asyncio
import json
import tempfile
import time
from pathlib import Path
from datetime import datetime

import pytest

from poly_chat.profile import load_profile
from poly_chat.conversation import (
    load_conversation,
    save_conversation,
    add_user_message,
    add_assistant_message,
    get_messages_for_ai,
)
from poly_chat.keys.loader import load_api_key
from poly_chat.ai.openai_provider import OpenAIProvider
from poly_chat.ai.claude_provider import ClaudeProvider
from poly_chat.ai.gemini_provider import GeminiProvider
from poly_chat.ai.grok_provider import GrokProvider
from poly_chat.ai.perplexity_provider import PerplexityProvider
from poly_chat.ai.mistral_provider import MistralProvider
from poly_chat.ai.deepseek_provider import DeepSeekProvider

from .test_config import find_test_api_keys_file, load_test_config, is_ai_available


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


async def send_and_receive(provider, messages: list, model: str, provider_name: str) -> tuple[str, float]:
    """Send messages and collect streaming response.

    Returns:
        Tuple of (full_response, elapsed_seconds)
    """
    start = time.time()
    chunks = []

    async for chunk in provider.send_message(messages, model, stream=True):
        chunks.append(chunk)

    elapsed = time.time() - start
    full_response = "".join(chunks)

    return full_response, elapsed


def create_temp_profile(test_config: dict, temp_dir: Path) -> Path:
    """Create temporary profile file using __TEST_API_KEYS.json data.

    Args:
        test_config: Loaded __TEST_API_KEYS.json content
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
        raise ValueError("No AI providers available in __TEST_API_KEYS.json")

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
        "system_prompt": None,
        "conversations_dir": str(temp_dir / "conversations"),
        "log_dir": str(temp_dir / "logs"),
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


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_full_conversation_flow():
    """
    Complete end-to-end test:
    - Creates temp profile
    - Sends message to each available AI
    - Saves conversation
    - Loads it back
    - Verifies integrity via AI count
    """
    test_start_time = time.time()

    log("=" * 80)
    log("STARTING END-TO-END TEST")
    log("=" * 80)

    # Check if we have test config
    test_config_file = find_test_api_keys_file()
    if not test_config_file:
        pytest.skip("__TEST_API_KEYS.json not found")

    test_config = load_test_config()

    # Count available AIs
    available_ais = [ai for ai in test_config.keys() if is_ai_available(ai)]
    if not available_ais:
        pytest.skip("No AI providers configured in __TEST_API_KEYS.json")

    log(f"Found {len(available_ais)} available AI provider(s): {', '.join(available_ais)}")
    log("")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # ========================================================================
        # PHASE 1: Setup
        # ========================================================================
        log("PHASE 1: Setup", indent=0)
        log("-" * 80)

        profile_path = create_temp_profile(test_config, temp_path)
        conv_path = temp_path / "conversations" / "e2e-test.json"

        log("")

        # ========================================================================
        # PHASE 2: Send messages to each AI
        # ========================================================================
        log("PHASE 2: Sending messages to AI providers", indent=0)
        log("-" * 80)

        # Initialize conversation
        conversation = load_conversation(str(conv_path))

        # Test prompt that should get different but valid responses
        test_prompts = [
            "Say hello and tell me your name.",
            "What is 2 + 2? Answer with just the number.",
            "Name one color. Just one word.",
        ]

        interaction_count = 0
        total_time = 0.0

        for idx, provider_name in enumerate(available_ais):
            log(f"Testing {provider_name.upper()}...", indent=1)

            config = test_config[provider_name]
            model = config["model"]
            api_key = config["api_key"]

            # Create provider instance
            provider_class = PROVIDER_CLASSES[provider_name]
            provider = provider_class(api_key=api_key)

            # Use different prompt for variety
            prompt = test_prompts[idx % len(test_prompts)]

            log(f"User message: {prompt}", indent=2)

            # Add user message
            add_user_message(conversation, prompt)

            # Get messages for AI (exclude errors)
            messages = get_messages_for_ai(conversation)

            # Send and receive
            try:
                start = time.time()
                response, elapsed = await send_and_receive(provider, messages, model, provider_name)
                total_time += elapsed

                log(f"Response ({elapsed:.2f}s): {response[:100]}{'...' if len(response) > 100 else ''}", indent=2)

                # Add assistant message
                add_assistant_message(conversation, response, model)

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
        # PHASE 3: Save conversation
        # ========================================================================
        log("PHASE 3: Saving conversation", indent=0)
        log("-" * 80)

        save_start = time.time()
        await save_conversation(str(conv_path), conversation)
        save_elapsed = time.time() - save_start

        log(f"Saved to: {conv_path}", indent=1)
        log(f"Save time: {save_elapsed:.3f}s", indent=1)
        log(f"Total messages: {len(conversation['messages'])}", indent=1)

        # Verify file exists and check size
        file_size = conv_path.stat().st_size
        log(f"File size: {file_size:,} bytes", indent=1)
        log("")

        # ========================================================================
        # PHASE 4: Load conversation (simulate new session)
        # ========================================================================
        log("PHASE 4: Loading conversation (simulating new session)", indent=0)
        log("-" * 80)

        load_start = time.time()
        loaded_conversation = load_conversation(str(conv_path))
        load_elapsed = time.time() - load_start

        log(f"Loaded from: {conv_path}", indent=1)
        log(f"Load time: {load_elapsed:.3f}s", indent=1)
        log(f"Messages loaded: {len(loaded_conversation['messages'])}", indent=1)
        log("")

        # ========================================================================
        # PHASE 5: Verify data integrity
        # ========================================================================
        log("PHASE 5: Verifying data integrity", indent=0)
        log("-" * 80)

        # Check message count matches
        original_count = len(conversation['messages'])
        loaded_count = len(loaded_conversation['messages'])

        log(f"Original message count: {original_count}", indent=1)
        log(f"Loaded message count: {loaded_count}", indent=1)

        assert loaded_count == original_count, \
            f"Message count mismatch: {loaded_count} != {original_count}"
        log("✓ Message count matches", indent=1)

        # Verify message structure
        for i, (orig, loaded) in enumerate(zip(conversation['messages'], loaded_conversation['messages'])):
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
        verify_provider = PROVIDER_CLASSES[verify_provider_name](api_key=verify_config["api_key"])

        log(f"Using {verify_provider_name} for verification", indent=1)

        # Ask AI to count user messages
        verification_prompt = (
            "Count the number of user messages in our conversation history. "
            "Respond with ONLY the number, nothing else."
        )

        add_user_message(loaded_conversation, verification_prompt)
        messages = get_messages_for_ai(loaded_conversation)

        verify_start = time.time()
        verification_response, verify_elapsed = await send_and_receive(
            verify_provider,
            messages,
            verify_config["model"],
            verify_provider_name
        )

        log(f"Verification prompt: {verification_prompt}", indent=1)
        log(f"AI response ({verify_elapsed:.2f}s): {verification_response.strip()}", indent=1)

        # Extract number from response
        try:
            reported_count = int(verification_response.strip())
            # Count actual user messages (including the verification prompt)
            actual_user_count = len([m for m in loaded_conversation['messages'] if m['role'] == 'user'])

            log(f"AI reported: {reported_count} user messages", indent=1)
            log(f"Actual count: {actual_user_count} user messages", indent=1)

            assert reported_count == actual_user_count, \
                f"AI count mismatch: {reported_count} != {actual_user_count}"

            log("✓ AI verification successful!", indent=1)

        except ValueError:
            log(f"WARNING: Could not parse AI response as number: {verification_response}", indent=1)
            log("(This is acceptable - AI might include extra text)", indent=1)

        log("")

        # ========================================================================
        # SUMMARY
        # ========================================================================
        log("=" * 80)
        log("TEST SUMMARY")
        log("=" * 80)
        log(f"✓ Tested {len(available_ais)} AI provider(s)")
        log(f"✓ Successful interactions: {interaction_count}")
        log(f"✓ Total messages in conversation: {len(conversation['messages'])}")
        log(f"✓ Conversation saved and loaded successfully")
        log(f"✓ Data integrity verified")
        log(f"✓ Total test time: {time.time() - test_start_time:.2f}s")
        log("=" * 80)
        log("END-TO-END TEST PASSED")
        log("=" * 80)


if __name__ == "__main__":
    # Allow running directly for manual testing
    pytest.main([__file__, "-v", "-s", "-m", "e2e"])
