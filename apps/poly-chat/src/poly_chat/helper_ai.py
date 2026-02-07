"""Helper AI invocation for background tasks.

This module provides functions to invoke the helper AI for tasks like
title generation, summary generation, and safety checks.
"""

import logging
from typing import Optional, Any


async def invoke_helper_ai(
    helper_ai: str,
    helper_model: str,
    profile: dict[str, Any],
    messages: list[dict],
    system_prompt: Optional[str] = None,
) -> str:
    """Invoke helper AI for background tasks (non-streaming).

    Args:
        helper_ai: Helper AI provider name
        helper_model: Helper AI model name
        profile: Profile dictionary with API keys
        messages: Messages to send (typically a single prompt)
        system_prompt: Optional system prompt

    Returns:
        Response text from helper AI

    Raises:
        Exception: If helper AI invocation fails
    """
    # Import here to avoid circular dependency
    from .keys.loader import load_api_key
    from .cli import get_provider_instance

    # Get API key for helper AI
    key_config = profile["api_keys"].get(helper_ai)
    if not key_config:
        raise ValueError(f"No API key configured for helper AI: {helper_ai}")

    try:
        api_key = load_api_key(helper_ai, key_config)
    except Exception as e:
        raise ValueError(f"Error loading helper AI API key: {e}")

    # Get provider instance
    provider_instance = get_provider_instance(helper_ai, api_key, session=None)

    # Send request (non-streaming for simplicity)
    try:
        response_stream = provider_instance.send_message(
            messages=messages,
            model=helper_model,
            system_prompt=system_prompt,
            stream=False
        )

        # For non-streaming, the response should be immediate
        response_text = ""
        async for chunk in response_stream:
            response_text += chunk

        return response_text.strip()

    except Exception as e:
        logging.error(f"Error invoking helper AI: {e}", exc_info=True)
        raise
