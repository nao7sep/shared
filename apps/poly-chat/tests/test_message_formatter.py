"""Tests for text_formatting module."""

import pytest
from poly_chat.text_formatting import text_to_lines, lines_to_text


def test_text_to_lines_simple():
    """Test basic text to lines conversion."""
    text = "Hello\nWorld"
    lines = text_to_lines(text)
    assert lines == ["Hello", "World"]


def test_text_to_lines_with_leading_whitespace():
    """Test trimming leading whitespace-only lines."""
    text = "\n\n\nHello\nWorld"
    lines = text_to_lines(text)
    assert lines == ["Hello", "World"]


def test_text_to_lines_with_trailing_whitespace():
    """Test trimming trailing whitespace-only lines."""
    text = "Hello\nWorld\n\n\n"
    lines = text_to_lines(text)
    assert lines == ["Hello", "World"]


def test_text_to_lines_with_both():
    """Test trimming both leading and trailing whitespace."""
    text = "\n\nHello\nWorld\n\n"
    lines = text_to_lines(text)
    assert lines == ["Hello", "World"]


def test_text_to_lines_preserves_empty_lines_within():
    """Test that empty lines within content are preserved."""
    text = "Hello\n\nWorld"
    lines = text_to_lines(text)
    assert lines == ["Hello", "", "World"]


def test_text_to_lines_all_whitespace():
    """Test all whitespace-only text."""
    text = "\n\n\n"
    lines = text_to_lines(text)
    assert lines == []


def test_text_to_lines_empty():
    """Test empty string."""
    text = ""
    lines = text_to_lines(text)
    assert lines == []


def test_lines_to_text():
    """Test lines to text conversion."""
    lines = ["Hello", "World"]
    text = lines_to_text(lines)
    assert text == "Hello\nWorld"


def test_lines_to_text_with_empty_lines():
    """Test lines to text with empty lines."""
    lines = ["Hello", "", "World"]
    text = lines_to_text(lines)
    assert text == "Hello\n\nWorld"


def test_roundtrip():
    """Test that text -> lines -> text roundtrip works."""
    original = "Hello\n\nWorld\nTest"
    lines = text_to_lines(original)
    result = lines_to_text(lines)
    assert result == original
