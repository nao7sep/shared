"""DeepSeek provider implementation for PolyChat.

Note: DeepSeek uses OpenAI-compatible API.
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
    APIStatusError,
)
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from ..message_formatter import lines_to_text

logger = logging.getLogger(__name__)


class DeepSeekProvider:
    """DeepSeek provider implementation.

    DeepSeek uses OpenAI-compatible API.
    """

    def __init__(self, api_key: str, timeout: float = 300.0):
        """Initialize DeepSeek provider.

        Args:
            api_key: DeepSeek API key
            timeout: Request timeout in seconds (0 = no timeout, default: 300.0)
                    NOTE: DeepSeek reasoning models (R1/deepseek-reasoner) perform
                    extensive "thinking" that can take several minutes.
                    Default increased to 300s (5 minutes) for reasoning models.
        """
        from openai import AsyncOpenAI

        # CRITICAL: DeepSeek reasoning models have long "thinking" phases
        # R1 models can take 1-5+ minutes for complex reasoning
        # Documentation recommends 300s (5 minutes) read timeout minimum
        if timeout > 0:
            # Ensure read timeout is at least 300s for reasoning models
            read_timeout = max(timeout, 300.0)
            timeout_config = httpx.Timeout(
                connect=10.0,  # 10s to establish connection
                read=read_timeout,  # MUST be 300s+ for R1/reasoning models
                write=30.0,  # 30s to send payload
                pool=10.0,  # 10s to wait for connection from pool
            )
        else:
            timeout_config = None

        self.api_key = api_key
        self.timeout = timeout

        # DeepSeek has NO default retries in client - we handle explicitly
        # 503 errors are common during peak times, need aggressive retries
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
            timeout=timeout_config,
            max_retries=0,  # We handle retries explicitly with tenacity
        )

    def format_messages(self, conversation_messages: list[dict]) -> list[dict]:
        """Convert conversation format to DeepSeek format."""
        formatted = []
        for msg in conversation_messages:
            content = lines_to_text(msg["content"])
            formatted.append({"role": msg["role"], "content": content})
        return formatted

    @retry(
        retry=retry_if_exception_type(
            (APIConnectionError, RateLimitError, APITimeoutError, InternalServerError, APIStatusError)
        ),
        # DeepSeek 503 errors can last 30-60s during peak load
        # Aggressive exponential backoff: 1s, 2s, 4s, 8s... up to 60s
        wait=wait_exponential(multiplier=1, min=1, max=60),
        stop=stop_after_attempt(10),  # More attempts for DeepSeek's 503 issues
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def _create_chat_completion(self, model: str, messages: list[dict], stream: bool):
        """Create chat completion with aggressive retry logic for DeepSeek's 503 errors.

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
        """Send message to DeepSeek and yield response chunks."""
        try:
            formatted_messages = self.format_messages(messages)

            if system_prompt:
                formatted_messages.insert(0, {"role": "system", "content": system_prompt})

            # Create streaming request with aggressive retry logic
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
                        # Log reasoning tokens if present (R1/reasoning models)
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

        except APIStatusError as e:
            # DeepSeek-specific error handling
            if e.status_code == 503:
                # Most common DeepSeek error - server overloaded
                logger.error(f"DeepSeek server overloaded (503) after retries: {e}")
                logger.error("Peak load on DeepSeek infrastructure - consider retry or fallback")
            elif e.status_code == 402:
                # Payment required - prepaid balance exhausted
                logger.error(f"DeepSeek account balance exhausted (402): {e}")
                logger.error("Top up DeepSeek prepaid balance")
            else:
                logger.error(f"DeepSeek API error ({e.status_code}) after retries: {e}")
            raise
        except APITimeoutError as e:
            logger.error(f"Timeout error (reasoning model took too long): {e}")
            logger.error("Consider increasing timeout for R1/reasoning models")
            raise
        except BadRequestError as e:
            # 400 often means reasoning_content was included in history
            logger.error(f"Bad request (check if reasoning_content in history): {e}")
            raise
        except AuthenticationError as e:
            logger.error(f"Authentication failed: {e}")
            raise
        except (APIConnectionError, RateLimitError, InternalServerError) as e:
            # These are handled by retry decorator, but if all retries fail:
            logger.error(f"API error after retries: {type(e).__name__}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {type(e).__name__}: {e}")
            raise

    async def get_full_response(
        self, messages: list[dict], model: str, system_prompt: str | None = None
    ) -> tuple[str, dict]:
        """Get full response from DeepSeek."""
        try:
            formatted_messages = self.format_messages(messages)

            if system_prompt:
                formatted_messages.insert(0, {"role": "system", "content": system_prompt})

            # Create non-streaming request with aggressive retry logic
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

            # Extract reasoning_content if available (for R1/reasoning models)
            # NOTE: Do NOT feed reasoning_content back to the model in multi-turn conversations!
            reasoning_content = getattr(
                response.choices[0].message, "reasoning_content", None
            )

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

            # Add reasoning content if available (R1 thinking traces)
            if reasoning_content:
                metadata["reasoning_content"] = reasoning_content
                logger.info(f"Reasoning model generated thinking traces")

            # Add reasoning tokens if available (for cost tracking)
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

        except APIStatusError as e:
            # DeepSeek-specific error handling
            if e.status_code == 503:
                # Most common DeepSeek error - server overloaded
                logger.error(f"DeepSeek server overloaded (503) after retries: {e}")
                logger.error("Peak load on DeepSeek infrastructure - consider retry or fallback")
            elif e.status_code == 402:
                # Payment required - prepaid balance exhausted
                logger.error(f"DeepSeek account balance exhausted (402): {e}")
                logger.error("Top up DeepSeek prepaid balance")
            else:
                logger.error(f"DeepSeek API error ({e.status_code}) after retries: {e}")
            raise
        except APITimeoutError as e:
            logger.error(f"Timeout error (reasoning model took too long): {e}")
            logger.error("Consider increasing timeout for R1/reasoning models")
            raise
        except BadRequestError as e:
            # 400 often means reasoning_content was included in history
            logger.error(f"Bad request (check if reasoning_content in history): {e}")
            raise
        except AuthenticationError as e:
            logger.error(f"Authentication failed: {e}")
            raise
        except (APIConnectionError, RateLimitError, InternalServerError) as e:
            # These are handled by retry decorator, but if all retries fail:
            logger.error(f"API error after retries: {type(e).__name__}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {type(e).__name__}: {e}")
            raise
