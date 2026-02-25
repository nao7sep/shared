"""Comment validation and filename sanitization."""

from __future__ import annotations

import re

from .constants import COMMENT_FILENAME_SANITIZE_REGEX
from .errors import ArchiveError

_VISIBLE_CHAR_PATTERN = re.compile(r"\S", flags=re.UNICODE)
_SANITIZE_PATTERN = re.compile(COMMENT_FILENAME_SANITIZE_REGEX)
_HYPHEN_RUN_PATTERN = re.compile(r"-+")


def validate_and_sanitize_comment(raw_comment: str) -> tuple[str, str]:
    trimmed_comment = raw_comment.strip()
    if not _VISIBLE_CHAR_PATTERN.search(trimmed_comment):
        raise ArchiveError("Comment must include at least one visible character.")

    sanitized = _SANITIZE_PATTERN.sub("-", trimmed_comment)
    # Existing '-' runs are valid input, so collapse them after invalid-char replacement.
    sanitized = _HYPHEN_RUN_PATTERN.sub("-", sanitized).strip("-")
    if sanitized == "":
        raise ArchiveError("Comment cannot be converted to a valid filename segment.")

    return trimmed_comment, sanitized
