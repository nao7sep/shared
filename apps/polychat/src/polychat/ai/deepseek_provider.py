"""DeepSeek provider implementation for PolyChat.

Note: DeepSeek uses OpenAI-compatible API.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, AsyncIterator
from openai import (
    APIConnectionError,
    RateLimitError,
    APITimeoutError,
    InternalServerError,
    BadRequestError,
    AuthenticationError,
    APIStatusError,
)
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from ..logging import before_sleep_log_event, log_event
from ..timeouts import (
    DEFAULT_PROFILE_TIMEOUT_SEC,
    RETRY_BACKOFF_INITIAL_SEC,
    RETRY_BACKOFF_MAX_SEC,
    STANDARD_RETRY_ATTEMPTS,
    build_ai_httpx_timeout,
)
from .provider_logging import (
    api_error_after_retries_message,
    authentication_failed_message,
    bad_request_message,
    log_provider_error,
    unexpected_error_message,
)
from .provider_utils import format_chat_messages
from .types import AIResponseMetadata


if TYPE_CHECKING:
    from ..domain.chat import ChatMessage

class DeepSeekProvider:
    """DeepSeek provider implementation.

    DeepSeek uses OpenAI-compatible API.
    """

    def __init__(self, api_key: str, timeout: float = DEFAULT_PROFILE_TIMEOUT_SEC):
        """Initialize DeepSeek provider.

        Args:
            api_key: DeepSeek API key
            timeout: Request timeout in seconds (0 = no timeout, default: 300.0)
        """
        from openai import AsyncOpenAI

        timeout_config = build_ai_httpx_timeout(timeout)

        self.api_key = api_key
        self.timeout = timeout

        # DeepSeek has NO default retries in client - we handle explicitly
        # 503 errors are common during peak times, need aggressive retries
        self.client: Any = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
            timeout=timeout_config,
            max_retries=0,  # We handle retries explicitly with tenacity
        )

    def format_messages(self, chat_messages: list[ChatMessage]) -> list[dict[str, str]]:
        """Convert chat format to DeepSeek format."""
        return format_chat_messages(chat_messages)

    @retry(
        retry=retry_if_exception_type(
            (APIConnectionError, RateLimitError, APITimeoutError, InternalServerError, APIStatusError)
        ),
        # Use shared exponential backoff policy across providers.
        wait=wait_exponential(
            multiplier=RETRY_BACKOFF_INITIAL_SEC,
            min=RETRY_BACKOFF_INITIAL_SEC,
            max=RETRY_BACKOFF_MAX_SEC,
        ),
        stop=stop_after_attempt(STANDARD_RETRY_ATTEMPTS),
        before_sleep=before_sleep_log_event(
            provider="deepseek",
            operation="_create_chat_completion",
            level=logging.WARNING,
        ),
    )
    async def _create_chat_completion(
        self,
        model: str,
        messages: list[dict[str, str]],
        stream: bool,
        max_output_tokens: int | None = None,
    ):
        """Create chat completion with aggressive retry logic for DeepSeek's 503 errors.

        Args:
            model: Model name
            messages: Formatted messages
            stream: Whether to stream
            max_output_tokens: Optional output token cap

        Returns:
            API response
        """
        stream_options = {"include_usage": True} if stream else None
        kwargs: dict[str, object] = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "stream_options": stream_options,
        }
        if max_output_tokens is not None:
            kwargs["max_tokens"] = max_output_tokens
        return await self.client.chat.completions.create(**kwargs)

    async def send_message(
        self,
        messages: list[ChatMessage],
        model: str,
        system_prompt: str | None = None,
        stream: bool = True,
        search: bool = False,
        max_output_tokens: int | None = None,
        metadata: AIResponseMetadata | None = None,
    ) -> AsyncIterator[str]:
        """Send message to DeepSeek and yield response chunks.

        Args:
            messages: Chat messages in PolyChat format
            model: Model name
            system_prompt: Optional system prompt
            stream: Whether to stream the response
            metadata: Optional dict to populate with usage info after streaming

        Yields:
            Response text chunks
        """
        try:
            formatted_messages = self.format_messages(messages)

            if system_prompt:
                formatted_messages.insert(0, {"role": "system", "content": system_prompt})

            # Create streaming request with aggressive retry logic
            response = await self._create_chat_completion(
                model=model,
                messages=formatted_messages,
                stream=stream,
                max_output_tokens=max_output_tokens,
            )

            # Yield chunks
            async for chunk in response:
                # Extract usage from any chunk (may arrive with or without choices)
                if chunk.usage and metadata is not None:
                    metadata["usage"] = {
                        "prompt_tokens": chunk.usage.prompt_tokens,
                        "completion_tokens": chunk.usage.completion_tokens,
                        "total_tokens": chunk.usage.total_tokens,
                    }
                    cache_hit = getattr(chunk.usage, "prompt_cache_hit_tokens", None)
                    if cache_hit:
                        metadata["usage"]["cached_tokens"] = cache_hit
                    log_event(
                        "provider_log",
                        level=logging.INFO,
                        provider="deepseek",
                        message=(
                            f"Stream usage: {chunk.usage.prompt_tokens} prompt + "
                            f"{chunk.usage.completion_tokens} completion = "
                            f"{chunk.usage.total_tokens} total tokens"
                        ),
                    )
                    # Log reasoning tokens if present (R1/reasoning models)
                    if hasattr(chunk.usage, "completion_tokens_details"):
                        details = chunk.usage.completion_tokens_details
                        if hasattr(details, "reasoning_tokens"):
                            log_event(
                                "provider_log",
                                level=logging.INFO,
                                provider="deepseek",
                                message=f"Reasoning tokens: {details.reasoning_tokens}",
                            )

                # Skip chunks with no choices (usage-only)
                if not chunk.choices:
                    continue

                # Check for content
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content

                # Check finish reason for edge cases
                if chunk.choices[0].finish_reason:
                    finish_reason = chunk.choices[0].finish_reason
                    if finish_reason == "length":
                        log_event(
                            "provider_log",
                            level=logging.WARNING,
                            provider="deepseek",
                            message="Response truncated due to max_tokens limit",
                        )
                    elif finish_reason == "content_filter":
                        log_event(
                            "provider_log",
                            level=logging.WARNING,
                            provider="deepseek",
                            message="Response filtered due to content policy",
                        )
                        yield "\n[Response was filtered due to content policy]"

        except APIStatusError as e:
            # DeepSeek-specific error handling
            if e.status_code == 503:
                # Most common DeepSeek error - server overloaded
                log_provider_error(
                    "deepseek",
                    (
                        f"DeepSeek server overloaded (503) after retries: {e}. "
                        "Peak load on DeepSeek infrastructure; consider retry or fallback."
                    ),
                )
            elif e.status_code == 402:
                # Payment required - prepaid balance exhausted
                log_provider_error(
                    "deepseek",
                    (
                        f"DeepSeek account balance exhausted (402): {e}. "
                        "Top up DeepSeek prepaid balance."
                    ),
                )
            else:
                log_provider_error(
                    "deepseek",
                    f"DeepSeek API error ({e.status_code}) after retries: {e}",
                )
            raise
        except APITimeoutError as e:
            log_provider_error(
                "deepseek",
                (
                    f"Timeout error (reasoning model took too long): {e}. "
                    "Consider increasing timeout for R1/reasoning models."
                ),
            )
            raise
        except BadRequestError as e:
            # 400 often means reasoning_content was included in history
            log_provider_error(
                "deepseek",
                bad_request_message(e, detail="check if reasoning_content in history"),
            )
            raise
        except AuthenticationError as e:
            log_provider_error("deepseek", authentication_failed_message(e))
            raise
        except (APIConnectionError, RateLimitError, InternalServerError) as e:
            # These are handled by retry decorator, but if all retries fail:
            log_provider_error("deepseek", api_error_after_retries_message(e))
            raise
        except Exception as e:
            log_provider_error("deepseek", unexpected_error_message(e))
            raise

    async def get_full_response(
        self,
        messages: list[ChatMessage],
        model: str,
        system_prompt: str | None = None,
        search: bool = False,
        max_output_tokens: int | None = None,
    ) -> tuple[str, dict]:
        """Get full response from DeepSeek."""
        try:
            formatted_messages = self.format_messages(messages)

            if system_prompt:
                formatted_messages.insert(0, {"role": "system", "content": system_prompt})

            # Create non-streaming request with aggressive retry logic
            response = await self._create_chat_completion(
                model=model,
                messages=formatted_messages,
                stream=False,
                max_output_tokens=max_output_tokens,
            )

            # Extract response
            content = response.choices[0].message.content or ""

            # Check finish reason for edge cases
            finish_reason = response.choices[0].finish_reason
            if finish_reason == "length":
                log_event(
                    "provider_log",
                    level=logging.WARNING,
                    provider="deepseek",
                    message="Response truncated due to max_tokens limit",
                )
                content += "\n[Response was truncated due to length limit]"
            elif finish_reason == "content_filter":
                log_event(
                    "provider_log",
                    level=logging.WARNING,
                    provider="deepseek",
                    message="Response filtered due to content policy",
                )
                content = "[Response was filtered due to content policy]"

            # Extract metadata
            metadata = {
                "model": response.model,
                "finish_reason": finish_reason,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": (
                        response.usage.completion_tokens if response.usage else 0
                    ),
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
            }

            # Add reasoning tokens if available (for cost tracking)
            if response.usage and hasattr(response.usage, "completion_tokens_details"):
                if hasattr(response.usage.completion_tokens_details, "reasoning_tokens"):
                    metadata["usage"]["reasoning_tokens"] = (
                        response.usage.completion_tokens_details.reasoning_tokens
                    )
                    log_event(
                        "provider_log",
                        level=logging.INFO,
                        provider="deepseek",
                        message=(
                            f"Reasoning tokens used: {metadata['usage']['reasoning_tokens']}"
                        ),
                    )

            log_event(
                "provider_log",
                level=logging.INFO,
                provider="deepseek",
                message=(
                    f"Response: {metadata['usage']['total_tokens']} tokens, "
                    f"finish_reason={finish_reason}"
                ),
            )

            return content, metadata

        except APIStatusError as e:
            # DeepSeek-specific error handling
            if e.status_code == 503:
                # Most common DeepSeek error - server overloaded
                log_provider_error(
                    "deepseek",
                    (
                        f"DeepSeek server overloaded (503) after retries: {e}. "
                        "Peak load on DeepSeek infrastructure; consider retry or fallback."
                    ),
                )
            elif e.status_code == 402:
                # Payment required - prepaid balance exhausted
                log_provider_error(
                    "deepseek",
                    (
                        f"DeepSeek account balance exhausted (402): {e}. "
                        "Top up DeepSeek prepaid balance."
                    ),
                )
            else:
                log_provider_error(
                    "deepseek",
                    f"DeepSeek API error ({e.status_code}) after retries: {e}",
                )
            raise
        except APITimeoutError as e:
            log_provider_error(
                "deepseek",
                (
                    f"Timeout error (reasoning model took too long): {e}. "
                    "Consider increasing timeout for R1/reasoning models."
                ),
            )
            raise
        except BadRequestError as e:
            # 400 often means reasoning_content was included in history
            log_provider_error(
                "deepseek",
                bad_request_message(e, detail="check if reasoning_content in history"),
            )
            raise
        except AuthenticationError as e:
            log_provider_error("deepseek", authentication_failed_message(e))
            raise
        except (APIConnectionError, RateLimitError, InternalServerError) as e:
            # These are handled by retry decorator, but if all retries fail:
            log_provider_error("deepseek", api_error_after_retries_message(e))
            raise
        except Exception as e:
            log_provider_error("deepseek", unexpected_error_message(e))
            raise
