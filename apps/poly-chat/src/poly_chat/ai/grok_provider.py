"""Grok (xAI) provider implementation for PolyChat.

Note: Grok uses OpenAI-compatible API.
"""

import logging
from typing import AsyncIterator
import httpx
from openai import (
    AsyncOpenAI,
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

    def format_messages(self, chat_messages: list[dict]) -> list[dict]:
        """Convert Chat format to Grok format."""
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
    async def _create_chat_completion(self, model: str, messages: list[dict], stream: bool, search: bool = False):
        """Create chat completion with retry logic.

        Args:
            model: Model name
            messages: Formatted messages
            stream: Whether to stream
            search: Whether to enable web search

        Returns:
            API response
        """
        stream_options = {"include_usage": True} if stream else None
        tools = [{"type": "web_search"}] if search else None
        return await self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=stream,
            stream_options=stream_options,
            tools=tools,
        )

    @retry(
        retry=retry_if_exception_type(
            (APIConnectionError, RateLimitError, APITimeoutError, InternalServerError)
        ),
        wait=wait_exponential_jitter(initial=1, max=60),
        stop=stop_after_attempt(4),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def _create_response(self, model: str, input_items: list[dict], stream: bool, search: bool = False):
        """Create response via Responses API with retry logic."""
        tools = [{"type": "web_search"}] if search else None
        return await self.client.responses.create(
            model=model,
            input=input_items,
            stream=stream,
            tools=tools,
        )

    async def send_message(
        self,
        messages: list[dict],
        model: str,
        system_prompt: str | None = None,
        stream: bool = True,
        search: bool = False,
        metadata: dict | None = None,
    ) -> AsyncIterator[str]:
        """Send message to Grok and yield response chunks.

        Args:
            messages: Chat messages in PolyChat format
            model: Model name
            system_prompt: Optional system prompt
            stream: Whether to stream the response
            search: Whether to enable web search
            metadata: Optional dict to populate with usage info after streaming

        Yields:
            Response text chunks
        """
        try:
            formatted_messages = self.format_messages(messages)

            if system_prompt:
                formatted_messages.insert(0, {"role": "system", "content": system_prompt})

            if search:
                # xAI web search is available via Responses API.
                response = await self._create_response(
                    model=model, input_items=formatted_messages, stream=stream, search=True
                )

                async for event in response:
                    if event.type == "response.output_text.delta":
                        if event.delta:
                            yield event.delta
                    elif event.type == "response.completed":
                        if event.response and event.response.usage and metadata is not None:
                            usage = event.response.usage
                            metadata["usage"] = {
                                "prompt_tokens": usage.input_tokens,
                                "completion_tokens": usage.output_tokens,
                                "total_tokens": usage.total_tokens,
                            }

                        if event.response and metadata is not None:
                            citations = []
                            raw_citations = getattr(event.response, "citations", None) or []
                            for c in raw_citations:
                                if isinstance(c, dict):
                                    citations.append(
                                        {"url": c.get("url"), "title": c.get("title")}
                                    )
                                else:
                                    citations.append(
                                        {
                                            "url": getattr(c, "url", None),
                                            "title": getattr(c, "title", None),
                                        }
                                    )
                            if not citations and getattr(event.response, "output", None):
                                for item in event.response.output:
                                    if getattr(item, "type", None) == "message":
                                        for content in getattr(item, "content", []):
                                            for annotation in getattr(content, "annotations", []):
                                                if getattr(annotation, "type", None) == "url_citation":
                                                    citations.append(
                                                        {
                                                            "url": getattr(annotation, "url", None),
                                                            "title": getattr(annotation, "title", None),
                                                        }
                                                    )
                            citations = [c for c in citations if c.get("url")]
                            if citations:
                                metadata["citations"] = citations
                            metadata["search_raw"] = {
                                "provider": "grok",
                                "response_id": getattr(event.response, "id", None),
                                "raw_citations": raw_citations,
                                "output": getattr(event.response, "output", None),
                            }
                return

            # Non-search path: chat completions API
            response = await self._create_chat_completion(
                model=model, messages=formatted_messages, stream=stream, search=False
            )

            # Yield chunks
            async for chunk in response:
                # Check if this is a usage-only chunk (no choices)
                if not chunk.choices:
                    if chunk.usage:
                        # Populate metadata with usage info if provided
                        if metadata is not None:
                            metadata["usage"] = {
                                "prompt_tokens": chunk.usage.prompt_tokens,
                                "completion_tokens": chunk.usage.completion_tokens,
                                "total_tokens": chunk.usage.total_tokens,
                            }
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
                    # Extract citations if available (final chunk)
                    citations = getattr(chunk, "citations", None)
                    if citations and metadata is not None:
                        # Normalize to standard format
                        metadata["citations"] = [
                            {"url": c.get("url", c), "title": c.get("title")}
                            if isinstance(c, dict) else {"url": c, "title": None}
                            for c in citations
                        ]
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
        self, messages: list[dict], model: str, system_prompt: str | None = None, search: bool = False
    ) -> tuple[str, dict]:
        """Get full response from Grok."""
        try:
            formatted_messages = self.format_messages(messages)

            if system_prompt:
                formatted_messages.insert(0, {"role": "system", "content": system_prompt})

            if search:
                response = await self._create_response(
                    model=model, input_items=formatted_messages, stream=False, search=True
                )
                content = response.output_text or ""
                metadata = {
                    "model": getattr(response, "model", model),
                    "finish_reason": "completed",
                    "usage": {
                        "prompt_tokens": response.usage.input_tokens if response.usage else 0,
                        "completion_tokens": response.usage.output_tokens if response.usage else 0,
                        "total_tokens": response.usage.total_tokens if response.usage else 0,
                    },
                }

                citations = []
                raw_citations = getattr(response, "citations", None) or []
                for c in raw_citations:
                    if isinstance(c, dict):
                        citations.append({"url": c.get("url"), "title": c.get("title")})
                    else:
                        citations.append(
                            {"url": getattr(c, "url", None), "title": getattr(c, "title", None)}
                        )
                if not citations and getattr(response, "output", None):
                    for item in response.output:
                        if getattr(item, "type", None) == "message":
                            for part in getattr(item, "content", []):
                                for annotation in getattr(part, "annotations", []):
                                    if getattr(annotation, "type", None) == "url_citation":
                                        citations.append(
                                            {
                                                "url": getattr(annotation, "url", None),
                                                "title": getattr(annotation, "title", None),
                                            }
                                        )
                citations = [c for c in citations if c.get("url")]
                if citations:
                    metadata["citations"] = citations
                metadata["search_raw"] = {
                    "provider": "grok",
                    "response_id": getattr(response, "id", None),
                    "raw_citations": raw_citations,
                    "output": getattr(response, "output", None),
                }

                return content, metadata

            # Non-search path: chat completions API
            response = await self._create_chat_completion(
                model=model, messages=formatted_messages, stream=False, search=False
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

            # Extract citations if available
            citations = getattr(response, "citations", None)
            if citations:
                # Normalize to standard format
                metadata["citations"] = [
                    {"url": c.get("url", c), "title": c.get("title")}
                    if isinstance(c, dict) else {"url": c, "title": None}
                    for c in citations
                ]

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
