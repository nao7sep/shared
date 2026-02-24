from __future__ import annotations

import pytest

from revzip.comment_sanitizer import validate_and_sanitize_comment
from revzip.errors import ArchiveError


def test_validate_and_sanitize_comment_multiline() -> None:
    comment, filename_segment = validate_and_sanitize_comment(
        "  first line\nsecond line  "
    )
    assert comment == "first line\nsecond line"
    assert filename_segment == "first-line-second-line"


def test_validate_and_sanitize_comment_requires_visible_character() -> None:
    with pytest.raises(ArchiveError):
        validate_and_sanitize_comment("   \n  ")


def test_validate_and_sanitize_comment_trims_edge_hyphens() -> None:
    comment, filename_segment = validate_and_sanitize_comment('  :hello? world:  ')
    assert comment == ":hello? world:"
    assert filename_segment == "hello-world"


def test_validate_and_sanitize_comment_fails_if_sanitized_segment_is_empty() -> None:
    with pytest.raises(ArchiveError):
        validate_and_sanitize_comment("  ///???***  ")
