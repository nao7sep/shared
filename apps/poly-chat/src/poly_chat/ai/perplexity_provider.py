"""Perplexity provider implementation for PolyChat.

Note: Perplexity uses OpenAI-compatible API.
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
)
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception_type,
    before_sleep_log,
)

from ..message_formatter import lines_to_text
from ..timeouts import (
    DEFAULT_PROFILE_TIMEOUT_SEC,
    RETRY_BACKOFF_INITIAL_SEC,
    RETRY_BACKOFF_MAX_SEC,
    STANDARD_RETRY_ATTEMPTS,
    build_ai_httpx_timeout,
)
from .types import AIResponseMetadata

logger = logging.getLogger(__name__)


class PerplexityProvider:
    """Perplexity provider implementation.

    Perplexity uses OpenAI-compatible API.
    """

    def __init__(self, api_key: str, timeout: float = DEFAULT_PROFILE_TIMEOUT_SEC):
        """Initialize Perplexity provider.

        Args:
            api_key: Perplexity API key
            timeout: Request timeout in seconds (0 = no timeout, default: 30.0)
        """
        from openai import AsyncOpenAI

        timeout_config = build_ai_httpx_timeout(timeout)

        self.api_key = api_key
        self.timeout = timeout

        # Disable SDK retries - we handle retries explicitly with tenacity
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.perplexity.ai",
            timeout=timeout_config,
            max_retries=0,
        )

    def format_messages(self, chat_messages: list[dict]) -> list[dict]:
        """Convert Chat format to Perplexity format.

        IMPORTANT: Perplexity API requires messages to strictly alternate between
        user and assistant roles. If the original conversation contains consecutive
        messages with the same role, this method merges them to satisfy the API
        requirement.

        Behavior:
        - Consecutive same-role messages are merged with double newline separator
        - Original chat_messages list is NOT modified (read-only)
        - Merge operation is logged as a warning
        - Example:
            Input:  [user: "Hello", user: "How are you?"]
            Output: [user: "Hello\\n\\nHow are you?"]

        Args:
            chat_messages: Messages in PolyChat format (not modified)

        Returns:
            Messages in Perplexity format with role alternation enforced
        """
        formatted = []
        for msg in chat_messages:
            content = lines_to_text(msg["content"])
            new_msg = {"role": msg["role"], "content": content}

            # If this message has the same role as the previous one, merge them
            if formatted and formatted[-1]["role"] == new_msg["role"]:
                # Merge content with double newline separator
                formatted[-1]["content"] += "\n\n" + new_msg["content"]
                logger.warning(
                    f"Merged consecutive {new_msg['role']} messages for Perplexity API "
                    f"(Perplexity requires strict role alternation)"
                )
            else:
                formatted.append(new_msg)

        return formatted

    @staticmethod
    def _mark_search_executed(metadata: AIResponseMetadata | None, evidence: str) -> None:
        if metadata is None:
            return
        metadata["search_executed"] = True
        evidence_list = metadata.setdefault("search_evidence", [])
        if isinstance(evidence_list, list) and evidence not in evidence_list:
            evidence_list.append(evidence)

    @staticmethod
    def _extract_search_results(payload: object) -> list[dict]:
        """Extract Perplexity search_results into normalized citation-like records."""
        results = getattr(payload, "search_results", None) or []
        normalized = []
        for item in results:
            if isinstance(item, dict):
                url = item.get("url")
                title = item.get("title")
                date = item.get("date")
            else:
                url = getattr(item, "url", None)
                title = getattr(item, "title", None)
                date = getattr(item, "date", None)
            if url:
                normalized.append({"url": url, "title": title, "date": date})
        return normalized

    @classmethod
    def _extract_citations(cls, payload: object) -> list[dict]:
        """Extract citations with best available title information."""
        # Prefer search_results, which include titles in current Perplexity API.
        search_results = cls._extract_search_results(payload)
        if search_results:
            return [{"url": r.get("url"), "title": r.get("title")} for r in search_results if r.get("url")]

        # Fallback to legacy citations field.
        citations = getattr(payload, "citations", None) or []
        normalized = []
        for c in citations:
            if isinstance(c, dict):
                url = c.get("url")
                title = c.get("title")
            else:
                url = c
                title = None
            if url:
                normalized.append({"url": url, "title": title})
        return normalized

    @retry(
        retry=retry_if_exception_type(
            (APIConnectionError, RateLimitError, APITimeoutError, InternalServerError)
        ),
        wait=wait_exponential_jitter(
            initial=RETRY_BACKOFF_INITIAL_SEC,
            max=RETRY_BACKOFF_MAX_SEC,
        ),
        stop=stop_after_attempt(STANDARD_RETRY_ATTEMPTS),
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
        # Perplexity supports stream_options like OpenAI
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
        search: bool = False,
        thinking: bool = False,
        max_output_tokens: int | None = None,
        thinking_budget_tokens: int | None = None,
        metadata: AIResponseMetadata | None = None,
    ) -> AsyncIterator[str]:
        """Send message to Perplexity and yield response chunks.

        Args:
            messages: Chat messages in PolyChat format
            model: Model name
            system_prompt: Optional system prompt
            stream: Whether to stream the response
            search: Whether to enable web search (Perplexity has search always on for Sonar models)
            metadata: Optional dict to populate with usage info after streaming

        Yields:
            Response text chunks
        """
        try:
            formatted_messages = self.format_messages(messages)
            if metadata is not None and "sonar" in model.lower():
                self._mark_search_executed(metadata, "native_search_model")

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
                    # Extract citations/search results if available (final chunk without choices)
                    if metadata is not None:
                        citations = self._extract_citations(chunk)
                        if citations:
                            metadata["citations"] = citations
                            self._mark_search_executed(metadata, "citations")
                        search_results = self._extract_search_results(chunk)
                        if search_results:
                            metadata["search_results"] = search_results
                            self._mark_search_executed(metadata, "search_results")
                    continue

                # Check for content
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content

                # Check finish reason for edge cases
                if chunk.choices[0].finish_reason:
                    finish_reason = chunk.choices[0].finish_reason

                    # Extract citations/search_results from finish chunk
                    if metadata is not None:
                        citations = self._extract_citations(chunk)
                        if citations:
                            metadata["citations"] = citations
                            self._mark_search_executed(metadata, "citations")
                        search_results = self._extract_search_results(chunk)
                        if search_results:
                            metadata["search_results"] = search_results
                            self._mark_search_executed(metadata, "search_results")
                    if finish_reason == "length":
                        logger.warning("Response truncated due to max_tokens limit")
                    elif finish_reason == "content_filter":
                        logger.warning("Response filtered due to content policy")
                        yield "\n[Response was filtered due to content policy]"

        except APITimeoutError as e:
            # Special handling for timeouts - common with long search operations
            logger.error(f"Timeout error (Perplexity search took too long): {e}")
            logger.error("Consider increasing timeout for search-heavy models like sonar-pro")
            raise
        except AuthenticationError as e:
            logger.error(f"Authentication failed: {e}")
            raise
        except BadRequestError as e:
            logger.error(f"Bad request (check parameters): {e}")
            raise
        except (
            APIConnectionError,
            RateLimitError,
            InternalServerError,
        ) as e:
            # These are handled by retry decorator, but if all retries fail:
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
        thinking: bool = False,
        max_output_tokens: int | None = None,
        thinking_budget_tokens: int | None = None,
    ) -> tuple[str, dict]:
        """Get full response from Perplexity."""
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

            citations = self._extract_citations(response)
            search_results = self._extract_search_results(response)

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

            # Add citations/search results if available.
            if citations:
                metadata["citations"] = citations
                logger.info(f"Response included {len(citations)} citations")
                self._mark_search_executed(metadata, "citations")
            if search_results:
                metadata["search_results"] = search_results
                self._mark_search_executed(metadata, "search_results")

            logger.info(
                f"Response: {metadata['usage']['total_tokens']} tokens, "
                f"finish_reason={finish_reason}"
            )

            return content, metadata

        except APITimeoutError as e:
            # Special handling for timeouts - common with long search operations
            logger.error(f"Timeout error (Perplexity search took too long): {e}")
            logger.error("Consider increasing timeout for search-heavy models like sonar-pro")
            raise
        except AuthenticationError as e:
            logger.error(f"Authentication failed: {e}")
            raise
        except BadRequestError as e:
            logger.error(f"Bad request (check parameters): {e}")
            raise
        except (
            APIConnectionError,
            RateLimitError,
            InternalServerError,
        ) as e:
            # These are handled by retry decorator, but if all retries fail:
            logger.error(f"API error after retries: {type(e).__name__}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {type(e).__name__}: {e}")
            raise
