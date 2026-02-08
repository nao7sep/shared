"""AI provider initialization, validation, and request/response runtime."""

import logging
import time
from typing import Optional

from .app_state import SessionState
from .keys.loader import load_api_key, validate_api_key
from .logging_utils import (
    chat_file_label,
    estimate_message_chars,
    log_event,
    sanitize_error_message,
)
from .streaming import display_streaming_response

from .ai.openai_provider import OpenAIProvider
from .ai.claude_provider import ClaudeProvider
from .ai.gemini_provider import GeminiProvider
from .ai.grok_provider import GrokProvider
from .ai.perplexity_provider import PerplexityProvider
from .ai.mistral_provider import MistralProvider
from .ai.deepseek_provider import DeepSeekProvider

ProviderInstance = (
    OpenAIProvider
    | ClaudeProvider
    | GeminiProvider
    | GrokProvider
    | PerplexityProvider
    | MistralProvider
    | DeepSeekProvider
)

PROVIDER_CLASSES: dict[str, type] = {
    "openai": OpenAIProvider,
    "claude": ClaudeProvider,
    "gemini": GeminiProvider,
    "grok": GrokProvider,
    "perplexity": PerplexityProvider,
    "mistral": MistralProvider,
    "deepseek": DeepSeekProvider,
}


def get_provider_instance(
    provider_name: str, api_key: str, session: Optional[SessionState] = None
) -> ProviderInstance:
    """Get AI provider instance, using cache if available."""
    if session:
        cached = session.get_cached_provider(provider_name, api_key)
        if cached:
            return cached

    provider_class = PROVIDER_CLASSES.get(provider_name)
    if not provider_class:
        raise ValueError(f"Unsupported provider: {provider_name}")

    timeout = session.profile.get("timeout", 30) if session else 30
    instance = provider_class(api_key, timeout=timeout)

    if session:
        session.cache_provider(provider_name, api_key, instance)

    return instance


async def send_message_to_ai(
    provider_instance: ProviderInstance,
    messages: list[dict],
    model: str,
    system_prompt: Optional[str] = None,
    provider_name: Optional[str] = None,
    mode: str = "normal",
    chat_path: Optional[str] = None,
) -> tuple[str, dict]:
    """Send message to AI and get response."""
    provider_label = provider_name or provider_instance.__class__.__name__
    log_event(
        "ai_request",
        level=logging.INFO,
        mode=mode,
        provider=provider_label,
        model=model,
        chat_file=chat_file_label(chat_path),
        message_count=len(messages),
        input_chars=estimate_message_chars(messages),
        has_system_prompt=bool(system_prompt),
    )

    started = time.perf_counter()
    try:
        response_stream = provider_instance.send_message(
            messages=messages, model=model, system_prompt=system_prompt, stream=True
        )
        response_text = await display_streaming_response(response_stream, prefix="")
        metadata = {"model": model}

        log_event(
            "ai_response",
            level=logging.INFO,
            mode=mode,
            provider=provider_label,
            model=model,
            chat_file=chat_file_label(chat_path),
            latency_ms=round((time.perf_counter() - started) * 1000, 1),
            output_chars=len(response_text),
        )

        return response_text, metadata
    except Exception as e:
        log_event(
            "ai_error",
            level=logging.ERROR,
            mode=mode,
            provider=provider_label,
            model=model,
            chat_file=chat_file_label(chat_path),
            latency_ms=round((time.perf_counter() - started) * 1000, 1),
            error_type=type(e).__name__,
            error=sanitize_error_message(str(e)),
        )
        logging.error(
            "Error sending message to AI (provider=%s, model=%s, mode=%s): %s",
            provider_label,
            model,
            mode,
            e,
            exc_info=True,
        )
        raise


def validate_and_get_provider(
    session: SessionState,
    chat_path: Optional[str] = None,
) -> tuple[Optional[ProviderInstance], Optional[str]]:
    """Validate API key and get provider instance."""
    provider_name = session.current_ai
    key_config = session.profile["api_keys"].get(provider_name)

    if not key_config:
        log_event(
            "provider_validation_error",
            level=logging.ERROR,
            provider=provider_name,
            model=session.current_model,
            phase="key_config_missing",
            chat_file=chat_file_label(chat_path),
            error_type="ValueError",
            error=f"No API key configured for {provider_name}",
        )
        return None, f"No API key configured for {provider_name}"

    try:
        api_key = load_api_key(provider_name, key_config)
    except Exception as e:
        sanitized = sanitize_error_message(str(e))
        log_event(
            "provider_validation_error",
            level=logging.ERROR,
            provider=provider_name,
            model=session.current_model,
            phase="key_load_failed",
            chat_file=chat_file_label(chat_path),
            error_type=type(e).__name__,
            error=sanitized,
        )
        logging.error("API key loading error: %s", e, exc_info=True)
        return None, f"Error loading API key: {e}"

    if not validate_api_key(api_key, provider_name):
        log_event(
            "provider_validation_error",
            level=logging.ERROR,
            provider=provider_name,
            model=session.current_model,
            phase="key_validation_failed",
            chat_file=chat_file_label(chat_path),
            error_type="ValueError",
            error=f"Invalid API key for {provider_name}",
        )
        return None, f"Invalid API key for {provider_name}"

    try:
        provider_instance = get_provider_instance(provider_name, api_key, session)
    except Exception as e:
        sanitized = sanitize_error_message(str(e))
        log_event(
            "provider_validation_error",
            level=logging.ERROR,
            provider=provider_name,
            model=session.current_model,
            phase="provider_init_failed",
            chat_file=chat_file_label(chat_path),
            error_type=type(e).__name__,
            error=sanitized,
        )
        logging.error("Provider initialization error: %s", e, exc_info=True)
        return None, f"Error initializing provider: {e}"

    return provider_instance, None
