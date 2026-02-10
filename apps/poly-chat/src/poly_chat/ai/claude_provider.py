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
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception_type,
    before_sleep_log,
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

        # Disable SDK retries - we handle retries explicitly with tenacity
        self.client = AsyncAnthropic(
            api_key=api_key, timeout=timeout_config, max_retries=0
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

    @retry(
        retry=retry_if_exception_type(
            (APIConnectionError, RateLimitError, APITimeoutError, InternalServerError)
        ),
        wait=wait_exponential_jitter(initial=1, max=60),
        stop=stop_after_attempt(4),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def _create_message(self, **kwargs):
        """Create message with retry logic.

        Args:
            **kwargs: Arguments to pass to client.messages.create()

        Returns:
            API response
        """
        return await self.client.messages.create(**kwargs)

    @retry(
        retry=retry_if_exception_type(
            (APIConnectionError, RateLimitError, APITimeoutError, InternalServerError)
        ),
        wait=wait_exponential_jitter(initial=1, max=60),
        stop=stop_after_attempt(4),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def _create_message_stream(self, **kwargs):
        """Create message stream with retry logic.

        Args:
            **kwargs: Arguments to pass to client.messages.stream()

        Returns:
            Stream context manager
        """
        return self.client.messages.stream(**kwargs)

    async def send_message(
        self,
        messages: list[dict],
        model: str,
        system_prompt: str | None = None,
        stream: bool = True,
        search: bool = False,
        max_tokens: int = 4096,
        metadata: dict | None = None,
    ) -> AsyncIterator[str]:
        """Send message to Claude and yield response chunks.

        Args:
            messages: Chat messages in PolyChat format
            model: Model name
            system_prompt: Optional system prompt
            stream: Whether to stream the response
            search: Whether to enable web search
            max_tokens: Maximum tokens in response (default 4096, increased to 8192 for search)
            metadata: Optional dict to populate with usage info after streaming

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
                "max_tokens": 8192 if search else max_tokens,
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            if search:
                kwargs["tools"] = [{"type": "web_search_20250305", "name": "web_search"}]

            # Create streaming request with retry logic
            async with await self._create_message_stream(**kwargs) as response_stream:
                async for text in response_stream.text_stream:
                    yield text

                # After stream completes, check stop reason and extract usage
                final_message = await response_stream.get_final_message()

                # Populate metadata with usage info if provided
                if metadata is not None:
                    metadata["usage"] = {
                        "prompt_tokens": final_message.usage.input_tokens,
                        "completion_tokens": final_message.usage.output_tokens,
                        "total_tokens": final_message.usage.input_tokens
                        + final_message.usage.output_tokens,
                    }

                # Extract citations from final_message if search was enabled
                if search and metadata is not None:
                    citations = []
                    trace_citations = []
                    for block in final_message.content:
                        if hasattr(block, "citations"):
                            for citation in (block.citations or []):
                                citations.append({
                                    "url": citation.url,
                                    "title": getattr(citation, "title", None)
                                })
                                trace_citations.append(
                                    {
                                        "url": citation.url,
                                        "title": getattr(citation, "title", None),
                                        "cited_text": getattr(citation, "cited_text", None),
                                    }
                                )
                    if citations:
                        metadata["citations"] = citations
                    metadata["search_raw"] = {
                        "provider": "claude",
                        "id": getattr(final_message, "id", None),
                        "stop_reason": getattr(final_message, "stop_reason", None),
                        "content": getattr(final_message, "content", None),
                        "citations": trace_citations,
                    }

                if final_message.stop_reason == "max_tokens":
                    logger.warning("Response truncated due to max_tokens limit")
                    yield "\n[Response was truncated due to token limit]"
                elif final_message.stop_reason in ("end_turn", "pause_turn"):
                    # Normal completion or search pause
                    pass

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
        search: bool = False,
        max_tokens: int = 4096,
    ) -> tuple[str, dict]:
        """Get full response from Claude.

        Args:
            messages: Chat messages in PolyChat format
            model: Model name
            system_prompt: Optional system prompt
            search: Whether to enable web search
            max_tokens: Maximum tokens in response (default 4096, increased to 8192 for search)

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
                "max_tokens": 8192 if search else max_tokens,
            }

            if search:
                kwargs["tools"] = [{"type": "web_search_20250305", "name": "web_search"}]

            if system_prompt:
                kwargs["system"] = system_prompt

            # Create non-streaming request with retry logic
            response = await self._create_message(**kwargs)

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

            # Extract citations if search was enabled
            if search:
                citations = []
                trace_citations = []
                for block in response.content:
                    if hasattr(block, "citations"):
                        for citation in (block.citations or []):
                            citations.append({
                                "url": citation.url,
                                "title": getattr(citation, "title", None)
                            })
                            trace_citations.append(
                                {
                                    "url": citation.url,
                                    "title": getattr(citation, "title", None),
                                    "cited_text": getattr(citation, "cited_text", None),
                                }
                            )
                if citations:
                    metadata["citations"] = citations
                metadata["search_raw"] = {
                    "provider": "claude",
                    "id": getattr(response, "id", None),
                    "stop_reason": getattr(response, "stop_reason", None),
                    "content": getattr(response, "content", None),
                    "citations": trace_citations,
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
