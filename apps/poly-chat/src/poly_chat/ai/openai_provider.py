"""OpenAI provider implementation for PolyChat."""

from typing import AsyncIterator
from openai import AsyncOpenAI

from ..message_formatter import lines_to_text


class OpenAIProvider:
    """OpenAI (GPT) provider implementation."""

    def __init__(self, api_key: str, timeout: float = 30.0):
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            timeout: Request timeout in seconds (0 = no timeout, default: 30.0)
        """
        timeout_value = timeout if timeout > 0 else None
        self.client = AsyncOpenAI(api_key=api_key, timeout=timeout_value)
        self.api_key = api_key
        self.timeout = timeout

    def format_messages(self, conversation_messages: list[dict]) -> list[dict]:
        """Convert conversation format to OpenAI format.

        Args:
            conversation_messages: Messages in PolyChat format

        Returns:
            Messages in OpenAI format
        """
        formatted = []
        for msg in conversation_messages:
            content = lines_to_text(msg["content"])
            formatted.append({"role": msg["role"], "content": content})
        return formatted

    async def send_message(
        self,
        messages: list[dict],
        model: str,
        system_prompt: str | None = None,
        stream: bool = True,
    ) -> AsyncIterator[str]:
        """Send message to OpenAI and yield response chunks.

        Args:
            messages: Conversation messages in PolyChat format
            model: Model name
            system_prompt: Optional system prompt
            stream: Whether to stream the response

        Yields:
            Response text chunks
        """
        try:
            # Format messages
            formatted_messages = self.format_messages(messages)

            # Add system prompt if provided
            if system_prompt:
                formatted_messages.insert(0, {"role": "system", "content": system_prompt})

            # Create streaming request
            response = await self.client.chat.completions.create(
                model=model, messages=formatted_messages, stream=stream
            )

            # Yield chunks
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"\n[ERROR] {error_msg}")
            raise

    async def get_full_response(
        self, messages: list[dict], model: str, system_prompt: str | None = None
    ) -> tuple[str, dict]:
        """Get full response from OpenAI.

        Args:
            messages: Conversation messages in PolyChat format
            model: Model name
            system_prompt: Optional system prompt

        Returns:
            Tuple of (response_text, metadata)
        """
        try:
            # Format messages
            formatted_messages = self.format_messages(messages)

            # Add system prompt if provided
            if system_prompt:
                formatted_messages.insert(0, {"role": "system", "content": system_prompt})

            # Create non-streaming request
            response = await self.client.chat.completions.create(
                model=model, messages=formatted_messages, stream=False
            )

            # Extract response
            content = response.choices[0].message.content or ""

            # Extract metadata
            metadata = {
                "model": response.model,
                "finish_reason": response.choices[0].finish_reason,
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

            # Add reasoning tokens if available (for o1/o3 models)
            if response.usage and hasattr(response.usage, "completion_tokens_details"):
                if hasattr(response.usage.completion_tokens_details, "reasoning_tokens"):
                    metadata["usage"]["reasoning_tokens"] = (
                        response.usage.completion_tokens_details.reasoning_tokens
                    )

            return content, metadata

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"\n[ERROR] {error_msg}")
            raise
