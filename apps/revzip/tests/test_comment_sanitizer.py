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


def test_validate_and_sanitize_comment_merges_all_hyphen_runs() -> None:
    comment, filename_segment = validate_and_sanitize_comment(
        "   ^\\-\\-\\-\\^- adf aasd fasd   "
    )
    assert comment == "^\\-\\-\\-\\^- adf aasd fasd"
    assert filename_segment == "adf-aasd-fasd"


def test_validate_and_sanitize_comment_slugifies_connector_symbols() -> None:
    comment, filename_segment = validate_and_sanitize_comment("  revzip done & checked  ")
    assert comment == "revzip done & checked"
    assert filename_segment == "revzip-done-checked"


def test_validate_and_sanitize_comment_replaces_plus_and_at() -> None:
    _, filename_segment = validate_and_sanitize_comment("A+B@C")
    assert filename_segment == "a-b-c"


def test_validate_and_sanitize_comment_lowercases_base_and_extension() -> None:
    _, filename_segment = validate_and_sanitize_comment("MIXED.Name.TXT")
    assert filename_segment == "mixed.name.txt"
