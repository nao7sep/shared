"""AI provider initialization, validation, and request/response runtime."""

import logging
import time
from typing import Any, AsyncIterator, Optional, Protocol

from ..keys.loader import load_api_key, validate_api_key
from ..domain.profile import RuntimeProfile
from ..logging import (
    extract_http_error_context,
    estimate_message_chars,
    log_event,
)

from .openai_provider import OpenAIProvider
from .claude_provider import ClaudeProvider
from .gemini_provider import GeminiProvider
from .grok_provider import GrokProvider
from .perplexity_provider import PerplexityProvider
from .mistral_provider import MistralProvider
from .deepseek_provider import DeepSeekProvider
from .limits import resolve_request_limits
from .types import AIResponseMetadata
from ..timeouts import resolve_ai_read_timeout, resolve_profile_timeout

ProviderInstance = (
    OpenAIProvider
    | ClaudeProvider
    | GeminiProvider
    | GrokProvider
    | PerplexityProvider
    | MistralProvider
    | DeepSeekProvider
)

ProviderClass = (
    type[OpenAIProvider]
    | type[ClaudeProvider]
    | type[GeminiProvider]
    | type[GrokProvider]
    | type[PerplexityProvider]
    | type[MistralProvider]
    | type[DeepSeekProvider]
)


class SessionContext(Protocol):
    """Structural interface for runtime session state/manager."""

    @property
    def current_ai(self) -> str:
        ...

    @property
    def current_model(self) -> str:
        ...

    @property
    def profile(self) -> RuntimeProfile:
        ...

    def get_cached_provider(
        self,
        provider_name: str,
        api_key: str,
        timeout_sec: int | float | None = None,
    ) -> Optional[Any]:
        ...

    def cache_provider(
        self,
        provider_name: str,
        api_key: str,
        instance: Any,
        timeout_sec: int | float | None = None,
    ) -> None:
        ...


PROVIDER_CLASSES: dict[str, ProviderClass] = {
    "openai": OpenAIProvider,
    "claude": ClaudeProvider,
    "gemini": GeminiProvider,
    "grok": GrokProvider,
    "perplexity": PerplexityProvider,
    "mistral": MistralProvider,
    "deepseek": DeepSeekProvider,
}


def _coerce_provider_instance(candidate: Any) -> ProviderInstance | None:
    """Return a typed provider instance when the cached object is valid."""
    if isinstance(
        candidate,
        (
            OpenAIProvider,
            ClaudeProvider,
            GeminiProvider,
            GrokProvider,
            PerplexityProvider,
            MistralProvider,
            DeepSeekProvider,
        ),
    ):
        return candidate
    return None


def _provider_limit_key(
    provider_name: Optional[str],
    provider_instance: ProviderInstance,
) -> str:
    """Resolve provider registry key used by ai_limits."""
    if provider_name:
        return provider_name

    class_name = provider_instance.__class__.__name__.lower()
    for known_provider in (
        "openai",
        "claude",
        "gemini",
        "grok",
        "perplexity",
        "mistral",
        "deepseek",
    ):
        if known_provider in class_name:
            return known_provider
    return class_name


def get_provider_instance(
    provider_name: str,
    api_key: str,
    session: Optional[SessionContext] = None,
    timeout_sec: int | float | None = None,
) -> ProviderInstance:
    """Get AI provider instance, using cache if available."""
    effective_timeout = (
        timeout_sec
        if timeout_sec is not None
        else resolve_profile_timeout(session.profile if session else None)
    )

    if session:
        cached = _coerce_provider_instance(
            session.get_cached_provider(
                provider_name,
                api_key,
                timeout_sec=effective_timeout,
            )
        )
        if cached is not None:
            return cached

    provider_class = PROVIDER_CLASSES.get(provider_name)
    if not provider_class:
        raise ValueError(f"Unsupported provider: {provider_name}")

    instance = provider_class(api_key, timeout=effective_timeout)

    if session:
        session.cache_provider(
            provider_name,
            api_key,
            instance,
            timeout_sec=effective_timeout,
        )

    return instance


async def send_message_to_ai(
    provider_instance: ProviderInstance,
    messages: list[dict],
    model: str,
    system_prompt: Optional[str] = None,
    provider_name: Optional[str] = None,
    profile: Optional[RuntimeProfile] = None,
    mode: str = "normal",
    chat_path: Optional[str] = None,
    search: bool = False,
) -> tuple[AsyncIterator[str], AIResponseMetadata]:
    """Send message to AI and get streaming response.

    Returns:
        Tuple of (response_stream, metadata) where response_stream is an async
        generator that yields response chunks.
    """
    provider_label = provider_name or provider_instance.__class__.__name__
    limit_provider = _provider_limit_key(provider_name, provider_instance)
    resolved_limits = resolve_request_limits(
        profile,
        limit_provider,
        helper=False,
        search=search,
    )
    max_output_tokens = resolved_limits.get("max_output_tokens")
    log_event(
        "ai_request",
        level=logging.INFO,
        mode=mode,
        provider=provider_label,
        model=model,
        chat_file=chat_path,
        message_count=len(messages),
        input_chars=estimate_message_chars(messages),
        has_system_prompt=bool(system_prompt),
        max_output_tokens=max_output_tokens,
    )

    started = time.perf_counter()
    try:
        # Create metadata dict that provider can populate with usage info
        metadata: AIResponseMetadata = {"model": model, "started": started}
        if max_output_tokens is None:
            response_stream = provider_instance.send_message(
                messages=messages,
                model=model,
                system_prompt=system_prompt,
                stream=True,
                search=search,
                metadata=metadata,
            )
        else:
            response_stream = provider_instance.send_message(
                messages=messages,
                model=model,
                system_prompt=system_prompt,
                stream=True,
                search=search,
                max_output_tokens=max_output_tokens,
                metadata=metadata,
            )

        # Return stream for caller to display and log after consumption
        # Provider will populate metadata["usage"] after streaming completes
        return response_stream, metadata
    except Exception as e:
        http_context = extract_http_error_context(e)
        log_event(
            "ai_error",
            level=logging.ERROR,
            mode=mode,
            provider=provider_label,
            model=model,
            chat_file=chat_path,
            latency_ms=round((time.perf_counter() - started) * 1000, 1),
            error_type=type(e).__name__,
            error=str(e),
            **http_context,
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
    session: SessionContext,
    chat_path: Optional[str] = None,
    *,
    search: bool = False,
) -> tuple[Optional[ProviderInstance], Optional[str]]:
    """Validate API key and get provider instance."""
    provider_name = session.current_ai
    key_config = session.profile.api_keys.get(provider_name)

    if not key_config:
        log_event(
            "provider_validation_error",
            level=logging.ERROR,
            provider=provider_name,
            model=session.current_model,
            phase="key_config_missing",
            chat_file=chat_path,
            error_type="ValueError",
            error=f"No API key configured for {provider_name}",
        )
        return None, f"No API key configured for {provider_name}"

    try:
        api_key = load_api_key(provider_name, key_config)
    except Exception as e:
        http_context = extract_http_error_context(e)
        log_event(
            "provider_validation_error",
            level=logging.ERROR,
            provider=provider_name,
            model=session.current_model,
            phase="key_load_failed",
            chat_file=chat_path,
            error_type=type(e).__name__,
            error=str(e),
            **http_context,
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
            chat_file=chat_path,
            error_type="ValueError",
            error=f"Invalid API key for {provider_name}",
        )
        return None, f"Invalid API key for {provider_name}"

    try:
        profile_timeout = resolve_profile_timeout(session.profile)
        effective_timeout = resolve_ai_read_timeout(
            profile_timeout,
            search=search,
        )
        provider_instance = get_provider_instance(
            provider_name,
            api_key,
            session,
            timeout_sec=effective_timeout,
        )
    except Exception as e:
        http_context = extract_http_error_context(e)
        log_event(
            "provider_validation_error",
            level=logging.ERROR,
            provider=provider_name,
            model=session.current_model,
            phase="provider_init_failed",
            chat_file=chat_path,
            error_type=type(e).__name__,
            error=str(e),
            **http_context,
        )
        logging.error("Provider initialization error: %s", e, exc_info=True)
        return None, f"Error initializing provider: {e}"

    return provider_instance, None
