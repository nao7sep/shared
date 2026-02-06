"""Tests for streaming module."""

import pytest
from io import StringIO
from unittest.mock import patch
from poly_chat.streaming import (
    display_streaming_response,
    accumulate_stream,
    print_with_prefix,
)


async def async_generator(items):
    """Helper to create async generator from list."""
    for item in items:
        yield item


async def async_generator_with_error(items, error_at):
    """Helper to create async generator that raises error at specific index."""
    for i, item in enumerate(items):
        if i == error_at:
            raise ValueError("Stream error")
        yield item


@pytest.mark.asyncio
async def test_display_streaming_response_basic():
    """Test basic streaming response display."""
    chunks = ["Hello", " ", "World", "!"]
    stream = async_generator(chunks)

    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        result = await display_streaming_response(stream)

    assert result == "Hello World!"
    output = mock_stdout.getvalue()
    assert "Hello World!" in output


@pytest.mark.asyncio
async def test_display_streaming_response_with_prefix():
    """Test streaming with prefix."""
    chunks = ["Test", " ", "message"]
    stream = async_generator(chunks)

    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        result = await display_streaming_response(stream, prefix="Assistant: ")

    assert result == "Test message"
    output = mock_stdout.getvalue()
    assert "Assistant: " in output
    assert "Test message" in output


@pytest.mark.asyncio
async def test_display_streaming_response_empty():
    """Test streaming with empty chunks."""
    stream = async_generator([])

    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        result = await display_streaming_response(stream)

    assert result == ""


@pytest.mark.asyncio
async def test_display_streaming_response_single_chunk():
    """Test streaming with single chunk."""
    stream = async_generator(["Single"])

    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        result = await display_streaming_response(stream)

    assert result == "Single"


@pytest.mark.asyncio
async def test_display_streaming_response_multiline():
    """Test streaming with newlines."""
    chunks = ["Line 1\n", "Line 2\n", "Line 3"]
    stream = async_generator(chunks)

    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        result = await display_streaming_response(stream)

    assert result == "Line 1\nLine 2\nLine 3"


@pytest.mark.asyncio
async def test_display_streaming_response_error():
    """Test error handling during streaming."""
    chunks = ["Hello", " ", "World"]
    stream = async_generator_with_error(chunks, error_at=2)

    with patch("sys.stdout", new_callable=StringIO):
        with pytest.raises(ValueError, match="Stream error"):
            await display_streaming_response(stream)


@pytest.mark.asyncio
async def test_accumulate_stream_basic():
    """Test basic stream accumulation without display."""
    chunks = ["Hello", " ", "World", "!"]
    stream = async_generator(chunks)

    result = await accumulate_stream(stream)

    assert result == "Hello World!"


@pytest.mark.asyncio
async def test_accumulate_stream_empty():
    """Test accumulating empty stream."""
    stream = async_generator([])

    result = await accumulate_stream(stream)

    assert result == ""


@pytest.mark.asyncio
async def test_accumulate_stream_large():
    """Test accumulating many chunks."""
    chunks = [str(i) for i in range(100)]
    stream = async_generator(chunks)

    result = await accumulate_stream(stream)

    expected = "".join(str(i) for i in range(100))
    assert result == expected


@pytest.mark.asyncio
async def test_accumulate_stream_preserves_content():
    """Test that accumulation preserves exact content."""
    chunks = ["Hello\n", "  ", "World  ", "\n", "!"]
    stream = async_generator(chunks)

    result = await accumulate_stream(stream)

    assert result == "Hello\n  World  \n!"


def test_print_with_prefix_basic():
    """Test printing with prefix."""
    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        print_with_prefix("Test message", prefix="User: ")

    output = mock_stdout.getvalue()
    assert output == "User: Test message\n"


def test_print_with_prefix_no_prefix():
    """Test printing without prefix."""
    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        print_with_prefix("Test message")

    output = mock_stdout.getvalue()
    assert output == "Test message\n"


def test_print_with_prefix_empty():
    """Test printing with empty prefix."""
    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        print_with_prefix("Test message", prefix="")

    output = mock_stdout.getvalue()
    assert output == "Test message\n"


def test_print_with_prefix_multiline():
    """Test printing multiline text with prefix."""
    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        print_with_prefix("Line 1\nLine 2\nLine 3", prefix=">>> ")

    output = mock_stdout.getvalue()
    assert output == ">>> Line 1\nLine 2\nLine 3\n"


@pytest.mark.asyncio
async def test_display_streaming_accumulation_correctness():
    """Test that display_streaming_response accumulates correctly."""
    # Test with various chunk sizes
    chunks = ["a", "bb", "ccc", "dddd", "eeeee"]
    stream = async_generator(chunks)

    with patch("sys.stdout", new_callable=StringIO):
        result = await display_streaming_response(stream)

    assert result == "abbcccddddeeeee"
    assert len(result) == sum(len(c) for c in chunks)


@pytest.mark.asyncio
async def test_accumulate_vs_display_same_result():
    """Test that accumulate_stream and display_streaming_response return same result."""
    chunks = ["Test", " ", "stream", " ", "content"]

    stream1 = async_generator(chunks)
    result1 = await accumulate_stream(stream1)

    stream2 = async_generator(chunks)
    with patch("sys.stdout", new_callable=StringIO):
        result2 = await display_streaming_response(stream2)

    assert result1 == result2
