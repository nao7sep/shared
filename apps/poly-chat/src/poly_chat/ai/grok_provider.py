"""Grok (xAI) provider implementation for PolyChat.

Note: Grok uses OpenAI-compatible API.
"""

import logging
from typing import AsyncIterator
import httpx
from openai import (
    APIConnectionError,
    RateLimitError,
    APITimeoutError,
    InternalServerError,
    BadRequestError,
    AuthenticationError,
)
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception_type,
    before_sleep_log,
)

from ..message_formatter import lines_to_text

logger = logging.getLogger(__name__)


class GrokProvider:
    """Grok (xAI) provider implementation.

    Note: Grok uses OpenAI-compatible API, so we can use the OpenAI SDK.
    """

    def __init__(self, api_key: str, timeout: float = 30.0):
        """Initialize Grok provider.

        Args:
            api_key: xAI API key
            timeout: Request timeout in seconds (0 = no timeout, default: 30.0)
        """
        from openai import AsyncOpenAI

        # Configure granular timeouts for better error handling
        # Reasoning models can have long TTFT (Time to First Token) delays
        if timeout > 0:
            timeout_config = httpx.Timeout(
                connect=5.0,  # Fast fail on connection issues
                read=timeout,  # Allow model time to generate (important for reasoning)
                write=10.0,  # Should be quick to send request
                pool=2.0,  # Fast fail if connection pool exhausted
            )
        else:
            timeout_config = None

        self.api_key = api_key
        self.timeout = timeout

        # Disable default retries - we handle retries explicitly
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1",
            timeout=timeout_config,
            max_retries=0,
        )

    def format_messages(self, conversation_messages: list[dict]) -> list[dict]:
        """Convert conversation format to Grok format."""
        formatted = []
        for msg in conversation_messages:
            content = lines_to_text(msg["content"])
            formatted.append({"role": msg["role"], "content": content})
        return formatted

    @retry(
        retry=retry_if_exception_type(
            (APIConnectionError, RateLimitError, APITimeoutError, InternalServerError)
        ),
        wait=wait_exponential_jitter(initial=1, max=60),
        stop=stop_after_attempt(4),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def _create_chat_completion(self, model: str, messages: list[dict], stream: bool):
        """Create chat completion with retry logic.

        Args:
            model: Model name
            messages: Formatted messages
            stream: Whether to stream

        Returns:
            API response
        """
        stream_options = {"include_usage": True} if stream else None
        return await self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=stream,
            stream_options=stream_options,
        )

    async def send_message(
        self,
        messages: list[dict],
        model: str,
        system_prompt: str | None = None,
        stream: bool = True,
    ) -> AsyncIterator[str]:
        """Send message to Grok and yield response chunks."""
        try:
            formatted_messages = self.format_messages(messages)

            if system_prompt:
                formatted_messages.insert(0, {"role": "system", "content": system_prompt})

            # Create streaming request with retry logic
            response = await self._create_chat_completion(
                model=model, messages=formatted_messages, stream=stream
            )

            # Yield chunks
            async for chunk in response:
                # Check if this is a usage-only chunk (no choices)
                if not chunk.choices:
                    if chunk.usage:
                        logger.info(
                            f"Stream usage: {chunk.usage.prompt_tokens} prompt + "
                            f"{chunk.usage.completion_tokens} completion = "
                            f"{chunk.usage.total_tokens} total tokens"
                        )
                        # Log reasoning tokens if present (Grok reasoning models)
                        if hasattr(chunk.usage, "completion_tokens_details"):
                            details = chunk.usage.completion_tokens_details
                            if hasattr(details, "reasoning_tokens"):
                                logger.info(f"Reasoning tokens: {details.reasoning_tokens}")
                    continue

                # Check for content
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content

                # Check finish reason for edge cases
                if chunk.choices[0].finish_reason:
                    finish_reason = chunk.choices[0].finish_reason
                    if finish_reason == "length":
                        logger.warning("Response truncated due to max_tokens limit")
                    elif finish_reason == "content_filter":
                        logger.warning("Response filtered due to content policy")
                        yield "\n[Response was filtered due to content policy]"

        except AuthenticationError as e:
            logger.error(f"Authentication failed: {e}")
            raise
        except BadRequestError as e:
            logger.error(f"Bad request (check parameters, unsupported features): {e}")
            raise
        except (
            APIConnectionError,
            RateLimitError,
            APITimeoutError,
            InternalServerError,
        ) as e:
            # These are handled by retry decorator, but if all retries fail:
            logger.error(f"API error after retries: {type(e).__name__}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {type(e).__name__}: {e}")
            raise

    async def get_full_response(
        self, messages: list[dict], model: str, system_prompt: str | None = None
    ) -> tuple[str, dict]:
        """Get full response from Grok."""
        try:
            formatted_messages = self.format_messages(messages)

            if system_prompt:
                formatted_messages.insert(0, {"role": "system", "content": system_prompt})

            # Create non-streaming request with retry logic
            response = await self._create_chat_completion(
                model=model, messages=formatted_messages, stream=False
            )

            # Extract response
            content = response.choices[0].message.content or ""

            # Check finish reason for edge cases
            finish_reason = response.choices[0].finish_reason
            if finish_reason == "length":
                logger.warning("Response truncated due to max_tokens limit")
                content += "\n[Response was truncated due to length limit]"
            elif finish_reason == "content_filter":
                logger.warning("Response filtered due to content policy")
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

            # Add cached tokens if available
            if response.usage and hasattr(response.usage, "prompt_tokens_details"):
                if hasattr(response.usage.prompt_tokens_details, "cached_tokens"):
                    metadata["usage"]["cached_tokens"] = (
                        response.usage.prompt_tokens_details.cached_tokens
                    )

            # Add reasoning tokens if available (for Grok reasoning models)
            if response.usage and hasattr(response.usage, "completion_tokens_details"):
                if hasattr(response.usage.completion_tokens_details, "reasoning_tokens"):
                    metadata["usage"]["reasoning_tokens"] = (
                        response.usage.completion_tokens_details.reasoning_tokens
                    )
                    logger.info(f"Reasoning tokens used: {metadata['usage']['reasoning_tokens']}")

            logger.info(
                f"Response: {metadata['usage']['total_tokens']} tokens, "
                f"finish_reason={finish_reason}"
            )

            return content, metadata

        except AuthenticationError as e:
            logger.error(f"Authentication failed: {e}")
            raise
        except BadRequestError as e:
            logger.error(f"Bad request (check parameters, unsupported features): {e}")
            raise
        except (
            APIConnectionError,
            RateLimitError,
            APITimeoutError,
            InternalServerError,
        ) as e:
            # These are handled by retry decorator, but if all retries fail:
            logger.error(f"API error after retries: {type(e).__name__}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {type(e).__name__}: {e}")
            raise
