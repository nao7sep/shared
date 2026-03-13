"""Ignore-pattern filter for directory and file paths.

Loads regex patterns from a user-provided ignore file and matches them against
relative paths from target roots. Knows nothing about scanning or emojis.
"""

from __future__ import annotations

import re
from pathlib import Path

from .errors import IgnoreFileError


class PathFilter:
    """Compiled ignore-pattern matcher.

    Each pattern is matched against the relative path (from the scan target root)
    of a directory or file. A match means the path should be ignored.
    """

    def __init__(self, patterns: list[re.Pattern[str]]) -> None:
        self._patterns = patterns

    @classmethod
    def from_file(cls, path: Path) -> PathFilter:
        """Load and compile patterns from an ignore file.

        File format:
        - One regex pattern per line.
        - Blank lines are skipped.
        - Lines starting with # are comments.
        - Invalid regex causes an immediate error with line number.
        """
        if not path.is_file():
            raise IgnoreFileError(f"Ignore file not found: {path}")

        patterns: list[re.Pattern[str]] = []
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            raise IgnoreFileError(f"Cannot read ignore file: {exc}") from exc

        for line_number, raw_line in enumerate(lines, start=1):
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                compiled = re.compile(stripped)
            except re.error as exc:
                raise IgnoreFileError(
                    f"Invalid regex on line {line_number}: {stripped!r} ({exc})"
                ) from exc
            patterns.append(compiled)

        return cls(patterns)

    @classmethod
    def empty(cls) -> PathFilter:
        """Create a filter that ignores nothing."""
        return cls([])

    def is_ignored(self, relative_path: str) -> bool:
        """Test whether a relative path matches any ignore pattern.

        Uses forward slashes for the match regardless of platform.
        """
        # Normalize to forward slashes for consistent matching
        normalized = relative_path.replace("\\", "/")
        return any(pattern.search(normalized) is not None for pattern in self._patterns)
