"""Perplexity provider implementation for PolyChat.

Note: Perplexity uses OpenAI-compatible API.
"""

from typing import AsyncIterator

from ..message_formatter import lines_to_text


class PerplexityProvider:
    """Perplexity provider implementation.

    Perplexity uses OpenAI-compatible API.
    """

    def __init__(self, api_key: str, timeout: float = 30.0):
        """Initialize Perplexity provider.

        Args:
            api_key: Perplexity API key
            timeout: Request timeout in seconds (0 = no timeout, default: 30.0)
        """
        from openai import AsyncOpenAI

        timeout_value = timeout if timeout > 0 else None
        self.api_key = api_key
        self.timeout = timeout
        self.client = AsyncOpenAI(
            api_key=api_key, base_url="https://api.perplexity.ai", timeout=timeout_value
        )

    def format_messages(self, conversation_messages: list[dict]) -> list[dict]:
        """Convert conversation format to Perplexity format.

        Perplexity requires messages to alternate between user and assistant.
        This method ensures alternation by keeping only the last message of
        consecutive same-role messages.
        """
        formatted = []
        for msg in conversation_messages:
            content = lines_to_text(msg["content"])
            new_msg = {"role": msg["role"], "content": content}

            # If this message has the same role as the previous one, replace the previous
            if formatted and formatted[-1]["role"] == new_msg["role"]:
                formatted[-1] = new_msg
            else:
                formatted.append(new_msg)

        return formatted

    async def send_message(
        self,
        messages: list[dict],
        model: str,
        system_prompt: str | None = None,
        stream: bool = True,
    ) -> AsyncIterator[str]:
        """Send message to Perplexity and yield response chunks."""
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
        """Get full response from Perplexity."""
        try:
            formatted_messages = self.format_messages(messages)

            if system_prompt:
                formatted_messages.insert(0, {"role": "system", "content": system_prompt})

            response = await self.client.chat.completions.create(
                model=model, messages=formatted_messages, stream=False
            )

            content = response.choices[0].message.content or ""

            # Extract citations if available
            citations = getattr(response, "citations", None)

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

            # Add citations if available
            if citations:
                metadata["citations"] = citations

            return content, metadata

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"\n[ERROR] {error_msg}")
            raise
