"""Claude (Anthropic) provider implementation for PolyChat."""

from typing import AsyncIterator
from anthropic import AsyncAnthropic

from ..message_formatter import lines_to_text


class ClaudeProvider:
    """Claude (Anthropic) provider implementation."""

    def __init__(self, api_key: str, timeout: float = 30.0):
        """Initialize Claude provider.

        Args:
            api_key: Anthropic API key
            timeout: Request timeout in seconds (0 = no timeout, default: 30.0)
        """
        timeout_value = timeout if timeout > 0 else None
        self.client = AsyncAnthropic(api_key=api_key, timeout=timeout_value)
        self.api_key = api_key
        self.timeout = timeout

    def format_messages(self, conversation_messages: list[dict]) -> list[dict]:
        """Convert conversation format to Claude format.

        Args:
            conversation_messages: Messages in PolyChat format

        Returns:
            Messages in Claude format
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
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """Send message to Claude and yield response chunks.

        Args:
            messages: Conversation messages in PolyChat format
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

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"\n[ERROR] {error_msg}")
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
            messages: Conversation messages in PolyChat format
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

            # Extract metadata
            metadata = {
                "model": response.model,
                "stop_reason": response.stop_reason,
                "usage": {
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens
                    + response.usage.output_tokens,
                },
            }

            return content, metadata

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"\n[ERROR] {error_msg}")
            raise
