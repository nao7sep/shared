"""Ignore pattern loading and matching."""

from __future__ import annotations

import re
from pathlib import Path

from .errors import IgnorePatternError
from .models import IgnoreRuleSet

_DEFAULT_IGNORE_NAMES = frozenset(
    {
        ".git",
        ".DS_Store",
        "Thumbs.db",
        "desktop.ini",
    }
)


def load_ignore_rule_set(ignore_file_abs: Path | None) -> IgnoreRuleSet:
    if ignore_file_abs is None:
        return IgnoreRuleSet(patterns_raw=[], compiled_patterns=[])

    try:
        lines = ignore_file_abs.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise IgnorePatternError(f"Failed to read ignore file: {ignore_file_abs}") from exc

    patterns_raw: list[str] = []
    compiled_patterns: list[re.Pattern[str]] = []

    for line_number, raw_line in enumerate(lines, start=1):
        pattern_text = raw_line.strip()
        if pattern_text == "" or pattern_text.startswith("#"):
            continue

        try:
            compiled = re.compile(pattern_text)
        except re.error as exc:
            raise IgnorePatternError(
                f"Invalid regex at {ignore_file_abs}:{line_number}: {exc}"
            ) from exc

        patterns_raw.append(pattern_text)
        compiled_patterns.append(compiled)

    return IgnoreRuleSet(patterns_raw=patterns_raw, compiled_patterns=compiled_patterns)


def is_default_ignored_name(name: str) -> bool:
    return name in _DEFAULT_IGNORE_NAMES


def matches_ignore_rules(
    *,
    rel_path: Path,
    raw_source_argument: str,
    ignore_rule_set: IgnoreRuleSet,
) -> bool:
    if not ignore_rule_set.compiled_patterns:
        return False

    target = f"{raw_source_argument}/{rel_path.as_posix()}"
    return any(pattern.search(target) for pattern in ignore_rule_set.compiled_patterns)
