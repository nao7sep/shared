"""Helper AI invocation for background tasks.

This module provides functions to invoke the helper AI for tasks like
title generation, summary generation, and safety checks.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Optional, Any

from ..domain.config import AIEndpoint
from ..domain.profile import RuntimeProfile

if TYPE_CHECKING:
    from ..domain.chat import ChatMessage

logger = logging.getLogger(__name__)


async def invoke_helper_ai(
    endpoint: AIEndpoint,
    profile: RuntimeProfile,
    messages: list[ChatMessage],
    system_prompt: Optional[str] = None,
    task: str = "helper_task",
    session: Optional[Any] = None,
) -> str:
    """Invoke helper AI for background tasks (non-streaming).

    Args:
        endpoint: Helper AI provider+model endpoint
        profile: Runtime profile with API keys
        messages: Messages to send (typically a single prompt)
        system_prompt: Optional system prompt

    Returns:
        Response text from helper AI

    Raises:
        Exception: If helper AI invocation fails
    """
    return await _invoke_helper(endpoint, profile, messages, system_prompt, task, session)


async def _invoke_helper(
    helper: AIEndpoint,
    profile: RuntimeProfile,
    messages: list[ChatMessage],
    system_prompt: Optional[str],
    task: str,
    session: Optional[Any],
) -> str:
    """Core helper AI invocation logic."""
    from ..keys.loader import load_api_key
    from .runtime import get_provider_instance
    from .limits import resolve_request_limits

    from .costing import estimate_cost
    from ..formatting.costs import format_cost_usd
    from ..logging import (
        extract_http_error_context,
        log_event,
        estimate_message_chars,
        sanitize_error_message,
    )

    key_config = profile.api_keys.get(helper.provider)
    if not key_config:
        log_event(
            "helper_ai_error",
            level=logging.ERROR,
            task=task,
            provider=helper.provider,
            model=helper.model,
            latency_ms=0.0,
            error_type="ValueError",
            error=f"No API key configured for helper AI: {helper.provider}",
        )
        logging.error(
            "Helper AI invocation failed: no API key configured (provider=%s, model=%s)",
            helper.provider,
            helper.model,
        )
        raise ValueError(f"No API key configured for helper AI: {helper.provider}")

    try:
        api_key = load_api_key(helper.provider, key_config)
    except Exception as e:
        sanitized_error = sanitize_error_message(str(e))
        log_event(
            "helper_ai_error",
            level=logging.ERROR,
            task=task,
            provider=helper.provider,
            model=helper.model,
            latency_ms=0.0,
            error_type=type(e).__name__,
            error=sanitized_error,
        )
        logging.error(
            "Helper AI API key loading failed (provider=%s, model=%s): %s",
            helper.provider,
            helper.model,
            sanitized_error,
        )
        raise ValueError(f"Error loading helper AI API key: {sanitized_error}")

    provider_instance = get_provider_instance(helper.provider, api_key, session=session)

    started = time.perf_counter()
    resolved_limits = resolve_request_limits(
        profile,
        helper.provider,
        helper=True,
        search=False,
    )
    max_output_tokens = resolved_limits.get("max_output_tokens")
    log_event(
        "helper_ai_request",
        level=logging.INFO,
        task=task,
        provider=helper.provider,
        model=helper.model,
        message_count=len(messages),
        input_chars=estimate_message_chars(messages),
        has_system_prompt=bool(system_prompt),
        max_output_tokens=max_output_tokens,
    )
    try:
        request_kwargs: dict[str, Any] = {
            "messages": messages,
            "model": helper.model,
            "system_prompt": system_prompt,
        }
        if max_output_tokens is not None:
            request_kwargs["max_output_tokens"] = max_output_tokens

        response_text, metadata = await provider_instance.get_full_response(**request_kwargs)

        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        usage = metadata.get("usage", {}) if isinstance(metadata, dict) else {}

        cost_est = estimate_cost(helper.model, usage)
        log_event(
            "helper_ai_response",
            level=logging.INFO,
            task=task,
            provider=helper.provider,
            model=helper.model,
            latency_ms=latency_ms,
            output_chars=len(response_text),
            input_tokens=usage.get("prompt_tokens"),
            cached_tokens=usage.get("cached_tokens"),
            cache_write_tokens=usage.get("cache_write_tokens"),
            output_tokens=usage.get("completion_tokens"),
            total_tokens=usage.get("total_tokens"),
            estimated_cost=format_cost_usd(cost_est.total_cost) if cost_est is not None else None,
        )

        return response_text.strip()

    except Exception as e:
        sanitized_error = sanitize_error_message(str(e))
        http_context = extract_http_error_context(e)
        log_event(
            "helper_ai_error",
            level=logging.ERROR,
            task=task,
            provider=helper.provider,
            model=helper.model,
            latency_ms=round((time.perf_counter() - started) * 1000, 1),
            error_type=type(e).__name__,
            error=sanitized_error,
            **http_context,
        )
        logging.error(
            "Error invoking helper AI (provider=%s, model=%s): %s",
            helper.provider,
            helper.model,
            sanitized_error,
        )
        raise ValueError(f"Error invoking helper AI: {sanitized_error}")
