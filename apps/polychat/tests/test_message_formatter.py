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


def test_truncate_text_no_forward_search():
    """Algorithm only searches backward, never forward beyond target."""
    result = truncate_text("AlphaBeta,  gamma", 11)
    # Target is position 8 ('a'), no spaces backward, cuts exactly there
    assert result == "AlphaBet..."


def test_truncate_max_length_guarantee():
    """Result never exceeds max_length (hard guarantee)."""
    cases = [
        ("Hello world this is a very long string", 15),
        ("NoSpacesHereAtAllJustOneLongWord", 10),
        ("a" * 100, 25),
        ("Short", 20),
    ]
    
    for text, max_len in cases:
        result = truncate_text(text, max_len)
        assert len(result) <= max_len, f"Result '{result}' exceeds max_length {max_len}"


def test_truncate_removes_trailing_punctuation():
    """When breaking at boundary, removes trailing punctuation."""
    result = truncate_text("Hello world,  more text", 15)
    assert result == "Hello world..."


def test_truncate_removes_trailing_ellipsis():
    """Removes original ellipsis in text when truncating."""
    result = truncate_text("This is word...  and more text here", 18)
    assert result == "This is word..."


def test_truncate_custom_suffix():
    """Supports custom suffix and respects max_length."""
    result = truncate_text("Hello world", 10, suffix=">>")
    assert result == "Hello>>"
    assert len(result) <= 10


def test_truncate_empty_max_length():
    """Handles edge case of max_length <= 0."""
    result = truncate_text("Hello", 0)
    assert result == ""


def test_truncate_suffix_longer_than_max():
    """Handles edge case where suffix is longer than max_length."""
    result = truncate_text("Hello world", 2, suffix="...")
    assert result == ".."  # Returns truncated suffix


def test_truncate_exact_max_length():
    """Text exactly at max_length is not truncated."""
    result = truncate_text("Hello", 5)
    assert result == "Hello"
