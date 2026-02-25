"""Comment validation and filename sanitization."""

from __future__ import annotations

from os.path import splitext
import re
import unicodedata

from .errors import ArchiveError

_VISIBLE_CHAR_PATTERN = re.compile(r"\S", flags=re.UNICODE)
_HYPHEN_RUN_PATTERN = re.compile(r"-+")
_PRESERVED_SYMBOLS = frozenset({"_", "-", "."})


def validate_and_sanitize_comment(raw_comment: str) -> tuple[str, str]:
    trimmed_comment = raw_comment.strip()
    if not _VISIBLE_CHAR_PATTERN.search(trimmed_comment):
        raise ArchiveError("Comment must include at least one visible character.")

    base_raw, extension_raw = splitext(trimmed_comment)
    base_sanitized = _slugify_fragment(base_raw).strip("-.")
    extension_sanitized = _slugify_fragment(extension_raw)
    sanitized = f"{base_sanitized}{extension_sanitized}"
    if sanitized == "":
        raise ArchiveError("Comment cannot be converted to a valid filename segment.")

    return trimmed_comment, sanitized


def _slugify_fragment(fragment: str) -> str:
    replaced = "".join(
        ch if _is_preserved_slug_char(ch) else "-"
        for ch in fragment
    )
    lowered = replaced.lower()
    return _HYPHEN_RUN_PATTERN.sub("-", lowered)


def _is_preserved_slug_char(ch: str) -> bool:
    if ch in _PRESERVED_SYMBOLS:
        return True

    category = unicodedata.category(ch)
    return category.startswith("L") or category.startswith("N")
