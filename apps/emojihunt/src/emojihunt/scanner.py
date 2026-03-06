"""Scan files and directories for emoji sequences."""

import os
import re
from collections import Counter
from pathlib import Path

import emoji as emoji_lib

from .errors import EmojihuntError
from .models import EmojiEntry, ScanFinding, ScanResult

IgnorePatterns = list[re.Pattern[str]]


def scan_targets(
    targets: list[Path],
    ignore_file: Path | None,
    dataset: dict[str, EmojiEntry],
) -> ScanResult:
    """Scan targets for emoji and return aggregated findings with warnings."""
    counts: Counter[str] = Counter()
    scanned_files: list[Path] = []
    warnings: list[str] = []
    ignore_patterns = _load_ignore_patterns(ignore_file)

    for target in targets:
        if _is_ignored(target, ignore_patterns):
            warnings.append(f"Target is ignored by ignore patterns: {target}")
        elif target.is_file():
            _scan_file(target, counts, scanned_files, warnings)
        elif target.is_dir():
            _scan_directory(target, counts, scanned_files, ignore_patterns, warnings)
        else:
            warnings.append(f"Target not found or not a file/directory: {target}")

    findings = [
        ScanFinding(entry=dataset[emoji_str], count=count)
        for emoji_str, count in counts.items()
        if emoji_str in dataset
    ]

    return ScanResult(findings=findings, scanned_files=scanned_files, warnings=warnings)


def _scan_file(path: Path, counts: Counter[str], scanned_files: list[Path], warnings: list[str]) -> None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError) as e:
        warnings.append(f"Cannot read {path}: {e}")
        return

    scanned_files.append(path)
    for match in emoji_lib.emoji_list(text):
        counts[match["emoji"]] += 1


def _scan_directory(
    directory: Path,
    counts: Counter[str],
    scanned_files: list[Path],
    ignore_patterns: IgnorePatterns,
    warnings: list[str],
) -> None:
    """Lazy directory traversal: check each entry before entering."""
    try:
        entries = sorted(os.scandir(directory), key=lambda e: e.name)
    except (OSError, PermissionError) as e:
        warnings.append(f"Cannot scan directory {directory}: {e}")
        return

    for entry in entries:
        entry_path = Path(entry.path)
        is_dir = entry.is_dir(follow_symlinks=False)

        if _is_ignored(entry_path, ignore_patterns):
            continue

        if is_dir:
            _scan_directory(entry_path, counts, scanned_files, ignore_patterns, warnings)
        elif entry.is_file(follow_symlinks=False):
            _scan_file(entry_path, counts, scanned_files, warnings)


def _is_ignored(path: Path, patterns: IgnorePatterns) -> bool:
    path_str = str(path)
    return any(p.search(path_str) for p in patterns)


def _load_ignore_patterns(ignore_file: Path | None) -> IgnorePatterns:
    """Load regex ignore patterns from file. Each non-empty, non-comment line is a pattern."""
    if ignore_file is None:
        return []
    try:
        text = ignore_file.read_text(encoding="utf-8")
    except (OSError, PermissionError) as e:
        raise EmojihuntError(f"Cannot read ignore file {ignore_file}: {e}") from e

    patterns: IgnorePatterns = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        try:
            patterns.append(re.compile(stripped))
        except re.error as e:
            raise EmojihuntError(
                f"Invalid regex on line {lineno} of {ignore_file}: {e}"
            ) from e
    return patterns

