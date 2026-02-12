"""Streaming response handler for PolyChat.

This module handles displaying streaming responses in real-time,
accumulating the full response, and handling errors mid-stream.
"""

import time
from typing import AsyncIterator


async def display_streaming_response(
    stream: AsyncIterator[str], prefix: str = ""
) -> tuple[str, float | None]:
    """Display streaming response in real-time and accumulate full text.

    Args:
        stream: Async iterator of response chunks
        prefix: Optional prefix to display before response (e.g., "Assistant: ")

    Returns:
        Tuple of (full accumulated response text, first token timestamp or None)

    Raises:
        KeyboardInterrupt: If user presses Ctrl-C during streaming
        Exception: If stream encounters error
    """
    accumulated = []
    first_token_time = None

    try:
        # Print prefix if provided
        if prefix:
            print(prefix, end="", flush=True)

        # Stream and display chunks
        async for chunk in stream:
            # Track time of first token
            if first_token_time is None:
                first_token_time = time.perf_counter()

            print(chunk, end="", flush=True)
            accumulated.append(chunk)

        # Add newline at end
        print()

    except KeyboardInterrupt:
        # User cancelled streaming
        print("\n[Streaming cancelled by user]")
        raise

    except Exception as e:
        # Error during streaming
        print(f"\n[Error during streaming: {e}]")
        raise

    return "".join(accumulated), first_token_time


async def accumulate_stream(stream: AsyncIterator[str]) -> str:
    """Accumulate stream without displaying (for non-interactive use).

    Args:
        stream: Async iterator of response chunks

    Returns:
        Full accumulated response text
    """
    accumulated = []

    async for chunk in stream:
        accumulated.append(chunk)

    return "".join(accumulated)


def print_with_prefix(text: str, prefix: str = ""):
    """Print text with optional prefix.

    Args:
        text: Text to print
        prefix: Optional prefix (e.g., "User: ", "Assistant: ")
    """
    if prefix:
        print(f"{prefix}{text}")
    else:
        print(text)


def display_citations(citations: list[dict]) -> None:
    """Display search citations after response.

    Args:
        citations: List of citation dicts with "url" and optional "title" keys
    """
    if not citations:
        return
    print()
    print("Sources:")
    for i, citation in enumerate(citations, 1):
        number = citation.get("number", i)
        title = citation.get("title")
        url = citation.get("url")
        if title and url:
            print(f"  [{number}] {title}")
            print(f"      {url}")
        elif url:
            print(f"  [{number}] {url}")
        elif title:
            print(f"  [{number}] {title} (URL unavailable)")
        else:
            print(f"  [{number}] [source unavailable]")
