"""Claude (Anthropic) provider implementation for PolyChat."""

import logging
from typing import AsyncIterator
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
)

from ..logging_utils import before_sleep_log_event, log_event
from ..text_formatting import lines_to_text
from ..timeouts import (
    DEFAULT_PROFILE_TIMEOUT_SEC,
    RETRY_BACKOFF_INITIAL_SEC,
    RETRY_BACKOFF_MAX_SEC,
    STANDARD_RETRY_ATTEMPTS,
    build_ai_httpx_timeout,
)
from .limits import claude_effective_max_output_tokens
from .tools import claude_web_search_tools
from .types import AIResponseMetadata


class ClaudeProvider:
    """Claude (Anthropic) provider implementation."""

    # Set to True to enable prompt caching.  When enabled, the system
    # prompt and the final conversation message each receive a
    # cache_control breakpoint, asking the API to cache those tokens.
    #
    # Caching is not free.  Cache reads cost 90% less than regular input,
    # but cache writes carry a surcharge: 25% more at the default 5-minute
    # TTL, or twice the regular rate at the maximum 1-hour TTL.  Savings
    # only materialize when the cached prefix is reused within the window.
    #
    # PolyChat is designed for deep, deliberate conversation.  Users often
    # spend more than five minutes composing a message, and it is common
    # to revisit a thread after more than an hour.  Under these conditions,
    # prompt caching rarely breaks even and may increase costs instead.
    # This flag is provided for testing only; the default is False, and
    # the TTL is not user-configurable here.  Other providers in the stack
    # serve different interaction styles where caching may be worthwhile.
    prompt_caching: bool = False

    def __init__(self, api_key: str, timeout: float = DEFAULT_PROFILE_TIMEOUT_SEC):
        """Initialize Claude provider.

        Args:
            api_key: Anthropic API key
            timeout: Request timeout in seconds (0 = no timeout, default: 30.0)
        """
        timeout_config = build_ai_httpx_timeout(timeout)

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
        wait=wait_exponential_jitter(
            initial=RETRY_BACKOFF_INITIAL_SEC,
            max=RETRY_BACKOFF_MAX_SEC,
        ),
        stop=stop_after_attempt(STANDARD_RETRY_ATTEMPTS),
        before_sleep=before_sleep_log_event(
            provider="claude",
            operation="_create_message",
            level=logging.WARNING,
        ),
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
        wait=wait_exponential_jitter(
            initial=RETRY_BACKOFF_INITIAL_SEC,
            max=RETRY_BACKOFF_MAX_SEC,
        ),
        stop=stop_after_attempt(STANDARD_RETRY_ATTEMPTS),
        before_sleep=before_sleep_log_event(
            provider="claude",
            operation="_create_message_stream",
            level=logging.WARNING,
        ),
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
        max_output_tokens: int | None = None,
        metadata: AIResponseMetadata | None = None,
    ) -> AsyncIterator[str]:
        """Send message to Claude and yield response chunks.

        Args:
            messages: Chat messages in PolyChat format
            model: Model name
            system_prompt: Optional system prompt
            stream: Whether to stream the response
            search: Whether to enable web search
            max_output_tokens: Optional cap for provider output tokens
            metadata: Optional dict to populate with usage info after streaming

        Yields:
            Response text chunks
        """
        try:
            # Format messages
            formatted_messages = self.format_messages(messages)

            # Optionally add cache_control breakpoints for prompt caching
            if self.prompt_caching and formatted_messages:
                last_msg = formatted_messages[-1]
                last_msg["content"] = [
                    {
                        "type": "text",
                        "text": last_msg["content"],
                        "cache_control": {"type": "ephemeral"},
                    }
                ]

            # Claude handles system prompt separately
            kwargs = {
                "model": model,
                "messages": formatted_messages,
                "max_tokens": claude_effective_max_output_tokens(max_output_tokens),
            }

            if system_prompt:
                if self.prompt_caching:
                    kwargs["system"] = [
                        {
                            "type": "text",
                            "text": system_prompt,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ]
                else:
                    kwargs["system"] = system_prompt

            if search:
                kwargs["tools"] = claude_web_search_tools()

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
                    cache_read = getattr(final_message.usage, "cache_read_input_tokens", None)
                    if cache_read:
                        metadata["usage"]["cached_tokens"] = cache_read
                    cache_write = getattr(final_message.usage, "cache_creation_input_tokens", None)
                    if cache_write:
                        metadata["usage"]["cache_write_tokens"] = cache_write

                # Extract citations from final_message if search was enabled
                if search and metadata is not None:
                    citations = []
                    for block in final_message.content:
                        if hasattr(block, "citations"):
                            for citation in (block.citations or []):
                                citations.append({
                                    "url": citation.url,
                                    "title": getattr(citation, "title", None)
                                })
                    if citations:
                        metadata["citations"] = citations

                if final_message.stop_reason == "max_tokens":
                    log_event(
                        "provider_log",
                        level=logging.WARNING,
                        provider="claude",
                        message="Response truncated due to max_tokens limit",
                    )
                    yield "\n[Response was truncated due to token limit]"
                elif final_message.stop_reason in ("end_turn", "pause_turn"):
                    # Normal completion or search pause
                    pass

        except APIStatusError as e:
            # Check for 529 - System overloaded (critical error)
            if e.status_code == 529:
                log_event(
                    "provider_log",
                    level=logging.ERROR,
                    provider="claude",
                    message=(
                        f"Anthropic system overloaded (529): {e}. "
                        "System is under heavy load; consider backoff or fallback."
                    ),
                )
            else:
                log_event(
                    "provider_log",
                    level=logging.ERROR,
                    provider="claude",
                    message=f"API status error ({e.status_code}): {e}",
                )
            raise
        except RateLimitError as e:
            # 429 - Rate limit exceeded, SDK will retry but if all retries fail:
            log_event(
                "provider_log",
                level=logging.ERROR,
                provider="claude",
                message=f"Rate limit exceeded after retries: {e}",
            )
            raise
        except BadRequestError as e:
            # 400 - Invalid request, don't retry
            log_event(
                "provider_log",
                level=logging.ERROR,
                provider="claude",
                message=f"Bad request: {e}",
            )
            raise
        except AuthenticationError as e:
            # 401 - Invalid API key
            log_event(
                "provider_log",
                level=logging.ERROR,
                provider="claude",
                message=f"Authentication failed: {e}",
            )
            raise
        except PermissionDeniedError as e:
            # 403 - No access to resource
            log_event(
                "provider_log",
                level=logging.ERROR,
                provider="claude",
                message=f"Permission denied: {e}",
            )
            raise
        except (APIConnectionError, APITimeoutError, InternalServerError) as e:
            # Network/timeout/server errors - SDK will retry, but if all fail:
            log_event(
                "provider_log",
                level=logging.ERROR,
                provider="claude",
                message=f"API error after retries: {type(e).__name__}: {e}",
            )
            raise
        except Exception as e:
            log_event(
                "provider_log",
                level=logging.ERROR,
                provider="claude",
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
        """Get full response from Claude.

        Args:
            messages: Chat messages in PolyChat format
            model: Model name
            system_prompt: Optional system prompt
            search: Whether to enable web search
            max_output_tokens: Optional cap for provider output tokens

        Returns:
            Tuple of (response_text, metadata)
        """
        try:
            # Format messages
            formatted_messages = self.format_messages(messages)

            # Optionally add cache_control breakpoints for prompt caching
            if self.prompt_caching and formatted_messages:
                last_msg = formatted_messages[-1]
                last_msg["content"] = [
                    {
                        "type": "text",
                        "text": last_msg["content"],
                        "cache_control": {"type": "ephemeral"},
                    }
                ]

            # Claude handles system prompt separately
            kwargs = {
                "model": model,
                "messages": formatted_messages,
                "max_tokens": claude_effective_max_output_tokens(max_output_tokens),
            }

            if search:
                kwargs["tools"] = claude_web_search_tools()

            if system_prompt:
                if self.prompt_caching:
                    kwargs["system"] = [
                        {
                            "type": "text",
                            "text": system_prompt,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ]
                else:
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
                log_event(
                    "provider_log",
                    level=logging.WARNING,
                    provider="claude",
                    message="Response truncated due to max_tokens limit",
                )
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
                for block in response.content:
                    if hasattr(block, "citations"):
                        for citation in (block.citations or []):
                            citations.append({
                                "url": citation.url,
                                "title": getattr(citation, "title", None)
                            })
                if citations:
                    metadata["citations"] = citations

            log_event(
                "provider_log",
                level=logging.INFO,
                provider="claude",
                message=(
                    f"Response: {metadata['usage']['total_tokens']} tokens, "
                    f"stop_reason={stop_reason}"
                ),
            )

            return content, metadata

        except APIStatusError as e:
            # Check for 529 - System overloaded (critical error)
            if e.status_code == 529:
                log_event(
                    "provider_log",
                    level=logging.ERROR,
                    provider="claude",
                    message=(
                        f"Anthropic system overloaded (529): {e}. "
                        "System is under heavy load; consider backoff or fallback."
                    ),
                )
            else:
                log_event(
                    "provider_log",
                    level=logging.ERROR,
                    provider="claude",
                    message=f"API status error ({e.status_code}): {e}",
                )
            raise
        except RateLimitError as e:
            # 429 - Rate limit exceeded, SDK will retry but if all retries fail:
            log_event(
                "provider_log",
                level=logging.ERROR,
                provider="claude",
                message=f"Rate limit exceeded after retries: {e}",
            )
            raise
        except BadRequestError as e:
            # 400 - Invalid request, don't retry
            log_event(
                "provider_log",
                level=logging.ERROR,
                provider="claude",
                message=f"Bad request: {e}",
            )
            raise
        except AuthenticationError as e:
            # 401 - Invalid API key
            log_event(
                "provider_log",
                level=logging.ERROR,
                provider="claude",
                message=f"Authentication failed: {e}",
            )
            raise
        except PermissionDeniedError as e:
            # 403 - No access to resource
            log_event(
                "provider_log",
                level=logging.ERROR,
                provider="claude",
                message=f"Permission denied: {e}",
            )
            raise
        except (APIConnectionError, APITimeoutError, InternalServerError) as e:
            # Network/timeout/server errors - SDK will retry, but if all fail:
            log_event(
                "provider_log",
                level=logging.ERROR,
                provider="claude",
                message=f"API error after retries: {type(e).__name__}: {e}",
            )
            raise
        except Exception as e:
            log_event(
                "provider_log",
                level=logging.ERROR,
                provider="claude",
                message=f"Unexpected error: {type(e).__name__}: {e}",
            )
            raise
