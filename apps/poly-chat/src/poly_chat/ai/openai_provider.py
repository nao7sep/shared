"""OpenAI provider implementation for PolyChat.

This provider uses the OpenAI Responses API (recommended for all new projects).
See: https://platform.openai.com/docs/guides/text
"""

import logging
from typing import AsyncIterator
from openai import AsyncOpenAI
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
from .tools import openai_web_search_tools
from .types import AIResponseMetadata


class OpenAIProvider:
    """OpenAI (GPT) provider implementation using the Responses API."""

    def __init__(self, api_key: str, timeout: float = DEFAULT_PROFILE_TIMEOUT_SEC):
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            timeout: Request timeout in seconds (0 = no timeout, default: 30.0)
        """
        timeout_config = build_ai_httpx_timeout(timeout)

        # Disable default retries - we handle retries explicitly
        self.client = AsyncOpenAI(
            api_key=api_key, timeout=timeout_config, max_retries=0
        )
        self.api_key = api_key
        self.timeout = timeout

    def format_messages(self, chat_messages: list[dict]) -> list[dict]:
        """Convert Chat format to OpenAI Responses API input format.

        Args:
            chat_messages: Messages in PolyChat format

        Returns:
            Messages in OpenAI Responses API input format
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
            provider="openai",
            operation="_create_response",
            level=logging.WARNING,
        ),
    )
    async def _create_response(
        self,
        model: str,
        input_items: list[dict],
        stream: bool,
        search: bool = False,
        max_output_tokens: int | None = None,
    ):
        """Create response using Responses API with retry logic.

        Args:
            model: Model name
            input_items: Formatted input items (messages in Responses API format)
            stream: Whether to stream
            search: Whether to enable web search
            max_output_tokens: Optional output token cap

        Returns:
            API response
        """
        kwargs: dict[str, object] = {
            "model": model,
            "input": input_items,
            "stream": stream,
        }
        if search:
            kwargs["tools"] = openai_web_search_tools()
        if max_output_tokens is not None:
            kwargs["max_output_tokens"] = max_output_tokens
        return await self.client.responses.create(**kwargs)

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
        """Send message to OpenAI and yield response chunks.

        Args:
            messages: Chat messages in PolyChat format
            model: Model name
            system_prompt: Optional system prompt (uses 'developer' role)
            stream: Whether to stream the response
            search: Whether to enable web search
            metadata: Optional dict to populate with usage info after streaming

        Yields:
            Response text chunks
        """
        try:
            # Format messages
            formatted_messages = self.format_messages(messages)

            # Add system prompt if provided (using 'developer' role for Responses API)
            if system_prompt:
                formatted_messages.insert(0, {"role": "developer", "content": system_prompt})

            # Create streaming request with retry logic
            response = await self._create_response(
                model=model,
                input_items=formatted_messages,
                stream=stream,
                search=search,
                max_output_tokens=max_output_tokens,
            )

            # Yield chunks from streaming events
            async for event in response:
                # Handle text delta events
                if event.type == "response.output_text.delta":
                    if event.delta:
                        yield event.delta

                # Handle completion event (contains usage stats and citations)
                elif event.type == "response.completed":
                    if event.response and event.response.usage:
                        usage = event.response.usage
                        # Populate metadata with usage info if provided
                        # Note: Responses API uses input_tokens/output_tokens
                        if metadata is not None:
                            metadata["usage"] = {
                                "prompt_tokens": usage.input_tokens,
                                "completion_tokens": usage.output_tokens,
                                "total_tokens": usage.total_tokens,
                            }
                        log_event(
                            "provider_log",
                            level=logging.INFO,
                            provider="openai",
                            message=(
                                f"Stream usage: {usage.input_tokens} prompt + "
                                f"{usage.output_tokens} completion = "
                                f"{usage.total_tokens} total tokens"
                            ),
                        )

                    # Extract citations from response.output items
                    if search and event.response and metadata is not None:
                        citations = []
                        for item in event.response.output:
                            if item.type == "message":
                                for content in item.content:
                                    for annotation in getattr(content, "annotations", []):
                                        if annotation.type == "url_citation":
                                            citations.append({
                                                "url": annotation.url,
                                                "title": getattr(annotation, "title", None)
                                            })
                        if citations:
                            metadata["citations"] = citations

                # Handle output item completion (check for special finish reasons)
                elif event.type == "response.output_item.done":
                    if hasattr(event, 'item') and hasattr(event.item, 'status'):
                        status = event.item.status
                        if status == "incomplete":
                            log_event(
                                "provider_log",
                                level=logging.WARNING,
                                provider="openai",
                                message="Response incomplete (may be truncated)",
                            )
                        elif status == "failed":
                            log_event(
                                "provider_log",
                                level=logging.WARNING,
                                provider="openai",
                                message="Response generation failed",
                            )

        except AuthenticationError as e:
            log_event(
                "provider_log",
                level=logging.ERROR,
                provider="openai",
                message=f"Authentication failed: {e}",
            )
            raise
        except BadRequestError as e:
            log_event(
                "provider_log",
                level=logging.ERROR,
                provider="openai",
                message=f"Bad request (check context length, invalid params): {e}",
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
                provider="openai",
                message=f"API error after retries: {type(e).__name__}: {e}",
            )
            raise
        except Exception as e:
            log_event(
                "provider_log",
                level=logging.ERROR,
                provider="openai",
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
        """Get full response from OpenAI.

        Args:
            messages: Chat messages in PolyChat format
            model: Model name
            system_prompt: Optional system prompt (uses 'developer' role)
            search: Whether to enable web search

        Returns:
            Tuple of (response_text, metadata)
        """
        try:
            # Format messages
            formatted_messages = self.format_messages(messages)

            # Add system prompt if provided (using 'developer' role for Responses API)
            if system_prompt:
                formatted_messages.insert(0, {"role": "developer", "content": system_prompt})

            # Create non-streaming request with retry logic
            response = await self._create_response(
                model=model,
                input_items=formatted_messages,
                stream=False,
                search=search,
                max_output_tokens=max_output_tokens,
            )

            # Extract response text using convenience property
            content = response.output_text or ""

            # Check output items for status/completion info
            finish_status = "complete"
            for item in response.output:
                if hasattr(item, 'status'):
                    if item.status == "incomplete":
                        log_event(
                            "provider_log",
                            level=logging.WARNING,
                            provider="openai",
                            message="Response incomplete (may be truncated)",
                        )
                        content += "\n[Response was truncated due to length limit]"
                        finish_status = "incomplete"
                    elif item.status == "failed":
                        log_event(
                            "provider_log",
                            level=logging.WARNING,
                            provider="openai",
                            message="Response generation failed",
                        )
                        content = "[Response generation failed]"
                        finish_status = "failed"

            # Extract metadata
            # Note: Responses API uses input_tokens/output_tokens instead of prompt_tokens/completion_tokens
            metadata = {
                "model": response.model if hasattr(response, 'model') else model,
                "finish_status": finish_status,
                "usage": {
                    "prompt_tokens": response.usage.input_tokens if response.usage else 0,
                    "completion_tokens": (
                        response.usage.output_tokens if response.usage else 0
                    ),
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
            }

            # Add cached tokens if available
            if response.usage and hasattr(response.usage, "input_tokens_details"):
                if hasattr(response.usage.input_tokens_details, "cached_tokens"):
                    metadata["usage"]["cached_tokens"] = (
                        response.usage.input_tokens_details.cached_tokens
                    )

            # Add reasoning tokens if available (for o3/GPT-5 models)
            if response.usage and hasattr(response.usage, "output_tokens_details"):
                if hasattr(response.usage.output_tokens_details, "reasoning_tokens"):
                    metadata["usage"]["reasoning_tokens"] = (
                        response.usage.output_tokens_details.reasoning_tokens
                    )

            # Extract citations if search was enabled
            if search:
                citations = []
                for item in response.output:
                    if item.type == "message":
                        for content in item.content:
                            for annotation in getattr(content, "annotations", []):
                                if annotation.type == "url_citation":
                                    citations.append({
                                        "url": annotation.url,
                                        "title": getattr(annotation, "title", None)
                                    })
                if citations:
                    metadata["citations"] = citations

            log_event(
                "provider_log",
                level=logging.INFO,
                provider="openai",
                message=(
                    f"Response: {metadata['usage']['total_tokens']} tokens, "
                    f"status={finish_status}"
                ),
            )

            return content, metadata

        except AuthenticationError as e:
            log_event(
                "provider_log",
                level=logging.ERROR,
                provider="openai",
                message=f"Authentication failed: {e}",
            )
            raise
        except BadRequestError as e:
            log_event(
                "provider_log",
                level=logging.ERROR,
                provider="openai",
                message=f"Bad request (check context length, invalid params): {e}",
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
                provider="openai",
                message=f"API error after retries: {type(e).__name__}: {e}",
            )
            raise
        except Exception as e:
            log_event(
                "provider_log",
                level=logging.ERROR,
                provider="openai",
                message=f"Unexpected error: {type(e).__name__}: {e}",
            )
            raise
