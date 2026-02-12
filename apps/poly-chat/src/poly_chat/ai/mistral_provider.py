"""Mistral AI provider implementation for PolyChat.

Note: Mistral uses OpenAI-compatible API.
"""

import logging
from typing import AsyncIterator
from openai import (
    APIConnectionError,
    RateLimitError,
    APITimeoutError,
    InternalServerError,
    BadRequestError,
    AuthenticationError,
    UnprocessableEntityError,
)
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception_type,
)

from ..logging_utils import before_sleep_log_event, log_event
from ..message_formatter import lines_to_text
from ..timeouts import (
    DEFAULT_PROFILE_TIMEOUT_SEC,
    RETRY_BACKOFF_INITIAL_SEC,
    RETRY_BACKOFF_MAX_SEC,
    STANDARD_RETRY_ATTEMPTS,
    build_ai_httpx_timeout,
)
from .types import AIResponseMetadata


class MistralProvider:
    """Mistral AI provider implementation.

    Mistral uses OpenAI-compatible API.
    """

    def __init__(self, api_key: str, timeout: float = DEFAULT_PROFILE_TIMEOUT_SEC):
        """Initialize Mistral provider.

        Args:
            api_key: Mistral API key
            timeout: Request timeout in seconds (0 = no timeout, default: 30.0)
        """
        from openai import AsyncOpenAI

        timeout_config = build_ai_httpx_timeout(timeout)

        self.api_key = api_key
        self.timeout = timeout

        # Disable SDK retries - we handle retries explicitly with tenacity
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.mistral.ai/v1",
            timeout=timeout_config,
            max_retries=0,
        )

    def format_messages(self, chat_messages: list[dict]) -> list[dict]:
        """Convert Chat format to Mistral format."""
        formatted = []
        for msg in chat_messages:
            content = lines_to_text(msg["content"])
            formatted.append({"role": msg["role"], "content": content})
        return formatted

    @retry(
        retry=retry_if_exception_type(
            (APIConnectionError, RateLimitError, APITimeoutError, InternalServerError)
        ),
        wait=wait_exponential_jitter(
            initial=RETRY_BACKOFF_INITIAL_SEC,
            max=RETRY_BACKOFF_MAX_SEC,
        ),
        stop=stop_after_attempt(STANDARD_RETRY_ATTEMPTS),
        before_sleep=before_sleep_log_event(
            provider="mistral",
            operation="_create_chat_completion",
            level=logging.WARNING,
        ),
    )
    async def _create_chat_completion(
        self,
        model: str,
        messages: list[dict],
        stream: bool,
        max_output_tokens: int | None = None,
    ):
        """Create chat completion with retry logic.

        Args:
            model: Model name
            messages: Formatted messages
            stream: Whether to stream
            max_output_tokens: Optional output token cap

        Returns:
            API response
        """
        # VERIFIED: Mistral does NOT support stream_options parameter
        # Returns 422 error: "Input should be a valid dictionary or object to extract fields from"
        # Mistral automatically includes usage data in responses without needing stream_options
        kwargs: dict[str, object] = {
            "model": model,
            "messages": messages,
            "stream": stream,
            # stream_options NOT included - Mistral rejects it with 422
        }
        if max_output_tokens is not None:
            kwargs["max_tokens"] = max_output_tokens
        return await self.client.chat.completions.create(**kwargs)

    async def send_message(
        self,
        messages: list[dict],
        model: str,
        system_prompt: str | None = None,
        stream: bool = True,
        search: bool = False,
        max_output_tokens: int | None = None,
        metadata: AIResponseMetadata | None = None,
    ) -> AsyncIterator[str]:
        """Send message to Mistral and yield response chunks.

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

            # Create streaming request with retry logic
            response = await self._create_chat_completion(
                model=model,
                messages=formatted_messages,
                stream=stream,
                max_output_tokens=max_output_tokens,
            )

            # Yield chunks
            async for chunk in response:
                # Check if this chunk has choices
                if not chunk.choices:
                    # Mistral automatically includes usage in final chunk (no need to request it)
                    if hasattr(chunk, "usage") and chunk.usage:
                        # Populate metadata with usage info if provided
                        if metadata is not None:
                            metadata["usage"] = {
                                "prompt_tokens": chunk.usage.prompt_tokens,
                                "completion_tokens": chunk.usage.completion_tokens,
                                "total_tokens": chunk.usage.total_tokens,
                            }
                        log_event(
                            "provider_log",
                            level=logging.INFO,
                            provider="mistral",
                            message=(
                                f"Stream usage: {chunk.usage.prompt_tokens} prompt + "
                                f"{chunk.usage.completion_tokens} completion = "
                                f"{chunk.usage.total_tokens} total tokens"
                            ),
                        )
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
                            provider="mistral",
                            message="Response truncated due to max_tokens limit",
                        )
                    elif finish_reason == "content_filter":
                        log_event(
                            "provider_log",
                            level=logging.WARNING,
                            provider="mistral",
                            message="Response filtered due to content policy",
                        )
                        yield "\n[Response was filtered due to content policy]"

        except UnprocessableEntityError as e:
            # 422 - Common with Mistral for config mismatches (e.g., stream_options)
            log_event(
                "provider_log",
                level=logging.ERROR,
                provider="mistral",
                message=(
                    f"Unprocessable entity (422): {e}. "
                    "Check for unsupported parameters like stream_options."
                ),
            )
            raise
        except AuthenticationError as e:
            log_event(
                "provider_log",
                level=logging.ERROR,
                provider="mistral",
                message=f"Authentication failed: {e}",
            )
            raise
        except BadRequestError as e:
            log_event(
                "provider_log",
                level=logging.ERROR,
                provider="mistral",
                message=f"Bad request (check parameters): {e}",
            )
            raise
        except (
            APIConnectionError,
            RateLimitError,
            APITimeoutError,
            InternalServerError,
        ) as e:
            # These are handled by retry decorator, but if all retries fail:
            log_event(
                "provider_log",
                level=logging.ERROR,
                provider="mistral",
                message=f"API error after retries: {type(e).__name__}: {e}",
            )
            raise
        except Exception as e:
            log_event(
                "provider_log",
                level=logging.ERROR,
                provider="mistral",
                message=f"Unexpected error: {type(e).__name__}: {e}",
            )
            raise

    async def get_full_response(
        self,
        messages: list[dict],
        model: str,
        system_prompt: str | None = None,
        search: bool = False,
        max_output_tokens: int | None = None,
    ) -> tuple[str, dict]:
        """Get full response from Mistral."""
        try:
            formatted_messages = self.format_messages(messages)

            if system_prompt:
                formatted_messages.insert(0, {"role": "system", "content": system_prompt})

            # Create non-streaming request with retry logic
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
                    provider="mistral",
                    message="Response truncated due to max_tokens limit",
                )
                content += "\n[Response was truncated due to length limit]"
            elif finish_reason == "content_filter":
                log_event(
                    "provider_log",
                    level=logging.WARNING,
                    provider="mistral",
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

            log_event(
                "provider_log",
                level=logging.INFO,
                provider="mistral",
                message=(
                    f"Response: {metadata['usage']['total_tokens']} tokens, "
                    f"finish_reason={finish_reason}"
                ),
            )

            return content, metadata

        except UnprocessableEntityError as e:
            # 422 - Common with Mistral for config mismatches (e.g., stream_options)
            log_event(
                "provider_log",
                level=logging.ERROR,
                provider="mistral",
                message=(
                    f"Unprocessable entity (422): {e}. "
                    "Check for unsupported parameters like stream_options."
                ),
            )
            raise
        except AuthenticationError as e:
            log_event(
                "provider_log",
                level=logging.ERROR,
                provider="mistral",
                message=f"Authentication failed: {e}",
            )
            raise
        except BadRequestError as e:
            log_event(
                "provider_log",
                level=logging.ERROR,
                provider="mistral",
                message=f"Bad request (check parameters): {e}",
            )
            raise
        except (
            APIConnectionError,
            RateLimitError,
            APITimeoutError,
            InternalServerError,
        ) as e:
            # These are handled by retry decorator, but if all retries fail:
            log_event(
                "provider_log",
                level=logging.ERROR,
                provider="mistral",
                message=f"API error after retries: {type(e).__name__}: {e}",
            )
            raise
        except Exception as e:
            log_event(
                "provider_log",
                level=logging.ERROR,
                provider="mistral",
                message=f"Unexpected error: {type(e).__name__}: {e}",
            )
            raise
