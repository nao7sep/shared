"""Claude (Anthropic) provider implementation for PolyChat."""

import logging
from typing import AsyncIterator
import httpx
from anthropic import AsyncAnthropic
from anthropic import (
    RateLimitError,
    BadRequestError,
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    PermissionDeniedError,
    InternalServerError,
    APIStatusError,
)

from ..message_formatter import lines_to_text

logger = logging.getLogger(__name__)


class ClaudeProvider:
    """Claude (Anthropic) provider implementation."""

    def __init__(self, api_key: str, timeout: float = 30.0):
        """Initialize Claude provider.

        Args:
            api_key: Anthropic API key
            timeout: Request timeout in seconds (0 = no timeout, default: 30.0)
        """
        # Configure granular timeouts for better error handling
        if timeout > 0:
            timeout_config = httpx.Timeout(
                connect=5.0,  # Fast fail on connection issues
                read=timeout,  # Allow model time to generate
                write=10.0,  # Should be quick to send request
                pool=2.0,  # Fast fail if connection pool exhausted
            )
        else:
            timeout_config = None

        # Configure retries - SDK default is 2, we use 3 for better resilience
        self.client = AsyncAnthropic(
            api_key=api_key, timeout=timeout_config, max_retries=3
        )
        self.api_key = api_key
        self.timeout = timeout

    def format_messages(self, chat_messages: list[dict]) -> list[dict]:
        """Convert Chat format to Claude format.

        Args:
            chat_messages: Messages in PolyChat format

        Returns:
            Messages in Claude format
        """
        formatted = []
        for msg in chat_messages:
            content = lines_to_text(msg["content"])
            formatted.append({"role": msg["role"], "content": content})
        return formatted

    async def send_message(
        self,
        messages: list[dict],
        model: str,
        system_prompt: str | None = None,
        stream: bool = True,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """Send message to Claude and yield response chunks.

        Args:
            messages: Chat messages in PolyChat format
            model: Model name
            system_prompt: Optional system prompt
            stream: Whether to stream the response
            max_tokens: Maximum tokens in response (default 4096)

        Yields:
            Response text chunks
        """
        try:
            # Format messages
            formatted_messages = self.format_messages(messages)

            # Claude handles system prompt separately
            kwargs = {
                "model": model,
                "messages": formatted_messages,
                "max_tokens": max_tokens,
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            # Create streaming request (stream parameter not needed in .stream() method)
            async with self.client.messages.stream(**kwargs) as response_stream:
                async for text in response_stream.text_stream:
                    yield text

                # After stream completes, check stop reason
                final_message = await response_stream.get_final_message()
                if final_message.stop_reason == "max_tokens":
                    logger.warning("Response truncated due to max_tokens limit")
                    yield "\n[Response was truncated due to token limit]"

        except APIStatusError as e:
            # Check for 529 - System overloaded (critical error)
            if e.status_code == 529:
                logger.error(f"Anthropic system overloaded (529): {e}")
                logger.error(
                    "System is under heavy load. Consider implementing backoff or fallback."
                )
            else:
                logger.error(f"API status error ({e.status_code}): {e}")
            raise
        except RateLimitError as e:
            # 429 - Rate limit exceeded, SDK will retry but if all retries fail:
            logger.error(f"Rate limit exceeded after retries: {e}")
            raise
        except BadRequestError as e:
            # 400 - Invalid request, don't retry
            logger.error(f"Bad request: {e}")
            raise
        except AuthenticationError as e:
            # 401 - Invalid API key
            logger.error(f"Authentication failed: {e}")
            raise
        except PermissionDeniedError as e:
            # 403 - No access to resource
            logger.error(f"Permission denied: {e}")
            raise
        except (APIConnectionError, APITimeoutError, InternalServerError) as e:
            # Network/timeout/server errors - SDK will retry, but if all fail:
            logger.error(f"API error after retries: {type(e).__name__}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {type(e).__name__}: {e}")
            raise

    async def get_full_response(
        self,
        messages: list[dict],
        model: str,
        system_prompt: str | None = None,
        max_tokens: int = 4096,
    ) -> tuple[str, dict]:
        """Get full response from Claude.

        Args:
            messages: Chat messages in PolyChat format
            model: Model name
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens in response (default 4096)

        Returns:
            Tuple of (response_text, metadata)
        """
        try:
            # Format messages
            formatted_messages = self.format_messages(messages)

            # Claude handles system prompt separately
            kwargs = {
                "model": model,
                "messages": formatted_messages,
                "max_tokens": max_tokens,
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            # Create non-streaming request
            response = await self.client.messages.create(**kwargs)

            # Extract response
            content = ""
            for block in response.content:
                if hasattr(block, "text"):
                    content += block.text

            # Check stop reason for edge cases
            stop_reason = response.stop_reason
            if stop_reason == "max_tokens":
                logger.warning("Response truncated due to max_tokens limit")
                content += "\n[Response was truncated due to token limit]"

            # Extract metadata
            metadata = {
                "model": response.model,
                "stop_reason": stop_reason,
                "usage": {
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens
                    + response.usage.output_tokens,
                },
            }

            logger.info(
                f"Response: {metadata['usage']['total_tokens']} tokens, "
                f"stop_reason={stop_reason}"
            )

            return content, metadata

        except APIStatusError as e:
            # Check for 529 - System overloaded (critical error)
            if e.status_code == 529:
                logger.error(f"Anthropic system overloaded (529): {e}")
                logger.error(
                    "System is under heavy load. Consider implementing backoff or fallback."
                )
            else:
                logger.error(f"API status error ({e.status_code}): {e}")
            raise
        except RateLimitError as e:
            # 429 - Rate limit exceeded, SDK will retry but if all retries fail:
            logger.error(f"Rate limit exceeded after retries: {e}")
            raise
        except BadRequestError as e:
            # 400 - Invalid request, don't retry
            logger.error(f"Bad request: {e}")
            raise
        except AuthenticationError as e:
            # 401 - Invalid API key
            logger.error(f"Authentication failed: {e}")
            raise
        except PermissionDeniedError as e:
            # 403 - No access to resource
            logger.error(f"Permission denied: {e}")
            raise
        except (APIConnectionError, APITimeoutError, InternalServerError) as e:
            # Network/timeout/server errors - SDK will retry, but if all fail:
            logger.error(f"API error after retries: {type(e).__name__}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {type(e).__name__}: {e}")
            raise
