"""Helper AI invocation for background tasks.

This module provides functions to invoke the helper AI for tasks like
title generation, summary generation, and safety checks.
"""

import logging
import time
from typing import Optional, Any

logger = logging.getLogger(__name__)


async def invoke_helper_ai(
    helper_ai: str,
    helper_model: str,
    profile: dict[str, Any],
    messages: list[dict],
    system_prompt: Optional[str] = None,
    task: str = "helper_task",
    session: Optional[Any] = None,
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
    from .ai_runtime import get_provider_instance
    from .ai.limits import resolve_request_limits

    from .logging_utils import (
        extract_http_error_context,
        log_event,
        estimate_message_chars,
    )

    # Get API key for helper AI
    key_config = profile["api_keys"].get(helper_ai)
    if not key_config:
        log_event(
            "helper_ai_error",
            level=logging.ERROR,
            task=task,
            provider=helper_ai,
            model=helper_model,
            latency_ms=0.0,
            error_type="ValueError",
            error=f"No API key configured for helper AI: {helper_ai}",
        )
        logging.error(
            "Helper AI invocation failed: no API key configured (provider=%s, model=%s)",
            helper_ai,
            helper_model,
        )
        raise ValueError(f"No API key configured for helper AI: {helper_ai}")

    try:
        api_key = load_api_key(helper_ai, key_config)
    except Exception as e:
        log_event(
            "helper_ai_error",
            level=logging.ERROR,
            task=task,
            provider=helper_ai,
            model=helper_model,
            latency_ms=0.0,
            error_type=type(e).__name__,
            error=str(e),
        )
        logging.error(
            "Helper AI API key loading failed (provider=%s, model=%s): %s",
            helper_ai,
            helper_model,
            e,
            exc_info=True,
        )
        raise ValueError(f"Error loading helper AI API key: {e}")

    # Get provider instance (cached when a session manager/state is provided)
    provider_instance = get_provider_instance(helper_ai, api_key, session=session)

    # Send request (non-streaming for simplicity)
    started = time.perf_counter()
    resolved_limits = resolve_request_limits(
        profile,
        helper_ai,
        helper=True,
        search=False,
    )
    max_output_tokens = resolved_limits.get("max_output_tokens")
    log_event(
        "helper_ai_request",
        level=logging.INFO,
        task=task,
        provider=helper_ai,
        model=helper_model,
        message_count=len(messages),
        input_chars=estimate_message_chars(messages),
        has_system_prompt=bool(system_prompt),
        max_output_tokens=max_output_tokens,
    )
    try:
        request_kwargs: dict[str, Any] = {
            "messages": messages,
            "model": helper_model,
            "system_prompt": system_prompt,
        }
        if max_output_tokens is not None:
            request_kwargs["max_output_tokens"] = max_output_tokens

        response_text, metadata = await provider_instance.get_full_response(**request_kwargs)

        # Log successful helper AI response
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        usage = metadata.get("usage", {}) if isinstance(metadata, dict) else {}

        log_event(
            "helper_ai_response",
            level=logging.INFO,
            task=task,
            provider=helper_ai,
            model=helper_model,
            latency_ms=latency_ms,
            output_chars=len(response_text),
            input_tokens=usage.get("prompt_tokens"),
            cached_tokens=usage.get("cached_tokens"),
            cache_write_tokens=usage.get("cache_write_tokens"),
            output_tokens=usage.get("completion_tokens"),
            total_tokens=usage.get("total_tokens"),
        )

        return response_text.strip()

    except Exception as e:
        http_context = extract_http_error_context(e)
        log_event(
            "helper_ai_error",
            level=logging.ERROR,
            task=task,
            provider=helper_ai,
            model=helper_model,
            latency_ms=round((time.perf_counter() - started) * 1000, 1),
            error_type=type(e).__name__,
            error=str(e),
            **http_context,
        )
        logging.error(
            "Error invoking helper AI (provider=%s, model=%s): %s",
            helper_ai,
            helper_model,
            e,
            exc_info=True,
        )
        raise
