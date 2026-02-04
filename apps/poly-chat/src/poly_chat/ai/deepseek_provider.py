"""DeepSeek provider implementation for PolyChat.

Note: DeepSeek uses OpenAI-compatible API.
"""

from typing import AsyncIterator

from ..message_formatter import lines_to_text


class DeepSeekProvider:
    """DeepSeek provider implementation.

    DeepSeek uses OpenAI-compatible API.
    """

    def __init__(self, api_key: str, timeout: float = 30.0):
        """Initialize DeepSeek provider.

        Args:
            api_key: DeepSeek API key
            timeout: Request timeout in seconds (0 = no timeout, default: 30.0)
        """
        from openai import AsyncOpenAI

        timeout_value = timeout if timeout > 0 else None
        self.api_key = api_key
        self.timeout = timeout
        self.client = AsyncOpenAI(
            api_key=api_key, base_url="https://api.deepseek.com/v1", timeout=timeout_value
        )

    def format_messages(self, conversation_messages: list[dict]) -> list[dict]:
        """Convert conversation format to DeepSeek format."""
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
        """Send message to DeepSeek and yield response chunks."""
        try:
            formatted_messages = self.format_messages(messages)

            if system_prompt:
                formatted_messages.insert(0, {"role": "system", "content": system_prompt})

            response = await self.client.chat.completions.create(
                model=model, messages=formatted_messages, stream=stream
            )

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
        """Get full response from DeepSeek."""
        try:
            formatted_messages = self.format_messages(messages)

            if system_prompt:
                formatted_messages.insert(0, {"role": "system", "content": system_prompt})

            response = await self.client.chat.completions.create(
                model=model, messages=formatted_messages, stream=False
            )

            content = response.choices[0].message.content or ""

            # Extract reasoning_content if available (for R1/reasoning models)
            reasoning_content = getattr(
                response.choices[0].message, "reasoning_content", None
            )

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

            # Add reasoning content if available
            if reasoning_content:
                metadata["reasoning_content"] = reasoning_content

            # Add reasoning tokens if available
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
