"""Tests for text_formatting module."""

from poly_chat.text_formatting import lines_to_text, text_to_lines, truncate_text


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


def test_truncate_text_prefers_separator_near_cut_point():
    """Truncate should prefer semantic separators around target length."""
    result = truncate_text("Alpha beta gamma delta", 14)
    assert result == "Alpha beta..."


def test_truncate_text_fallback_hard_cut():
    """Truncate should fall back to hard cut when separators are unavailable."""
    result = truncate_text("abcdefghijklmno", 10)
    assert result == "abcdefg..."


def test_truncate_text_uses_unicode_punctuation_boundaries():
    """Unicode punctuation should be treated as semantic cut points."""
    result = truncate_text("alpha beta、gamma delta", 15)
    assert result == "alpha beta..."


def test_truncate_text_uses_boundary_run_start_on_left_search():
    """When boundary is at/before force cut, cut at run start."""
    result = truncate_text("Alpha, beta gamma", 8)
    assert result == "Alpha..."


def test_truncate_text_uses_first_boundary_on_right_search():
    """If no left boundary is found, use the first right boundary as-is."""
    result = truncate_text("AlphaBeta,  gamma", 11)
    assert result == "AlphaBeta..."
