"""Scan files and directories for emoji sequences."""

import os
from collections import Counter
from pathlib import Path

import emoji as emoji_lib
import pathspec

from .errors import EmojihuntError
from .models import EmojiEntry, ScanFinding, ScanResult

_ALWAYS_SKIP_DIRS = frozenset({".git", ".hg", ".svn", "__pycache__", "node_modules"})


def scan_targets(
    targets: list[Path],
    ignore_file: Path | None,
    dataset: dict[str, EmojiEntry],
) -> ScanResult:
    """Scan targets for emoji and return aggregated findings with warnings."""
    counts: Counter[str] = Counter()
    warnings: list[str] = []
    custom_ignore = _load_custom_ignore(ignore_file)

    for target in targets:
        if target.is_file():
            _scan_file(target, counts, warnings)
        elif target.is_dir():
            _scan_directory(target, counts, [], custom_ignore, target, warnings)
        else:
            warnings.append(f"Target not found or not a file/directory: {target}")

    findings = [
        ScanFinding(entry=dataset[emoji_str], count=count)
        for emoji_str, count in counts.items()
        if emoji_str in dataset
    ]

    return ScanResult(findings=findings, warnings=warnings)


def _scan_file(path: Path, counts: Counter[str], warnings: list[str]) -> None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError) as e:
        warnings.append(f"Cannot read {path}: {e}")
        return

    for match in emoji_lib.emoji_list(text):
        counts[match["emoji"]] += 1


def _scan_directory(
    directory: Path,
    counts: Counter[str],
    inherited_gitignores: list[tuple[Path, pathspec.PathSpec]],
    custom_ignore: pathspec.PathSpec | None,
    scan_root: Path,
    warnings: list[str],
) -> None:
    """Lazy directory traversal: inspect each entry before entering."""
    gitignores = list(inherited_gitignores)
    local_gi = _load_gitignore(directory)
    if local_gi is not None:
        gitignores.append((directory, local_gi))

    try:
        entries = sorted(os.scandir(directory), key=lambda e: e.name)
    except (OSError, PermissionError) as e:
        warnings.append(f"Cannot scan directory {directory}: {e}")
        return

    for entry in entries:
        entry_path = Path(entry.path)
        is_dir = entry.is_dir(follow_symlinks=False)

        if is_dir and entry.name in _ALWAYS_SKIP_DIRS:
            continue

        if _should_ignore(entry_path, is_dir, gitignores, custom_ignore, scan_root):
            continue

        if is_dir:
            _scan_directory(
                entry_path, counts, gitignores, custom_ignore, scan_root, warnings
            )
        elif entry.is_file(follow_symlinks=False):
            _scan_file(entry_path, counts, warnings)


def _should_ignore(
    path: Path,
    is_dir: bool,
    gitignores: list[tuple[Path, pathspec.PathSpec]],
    custom_ignore: pathspec.PathSpec | None,
    scan_root: Path,
) -> bool:
    for gi_dir, gi_spec in gitignores:
        try:
            rel = str(path.relative_to(gi_dir))
        except ValueError:
            continue
        check = rel + "/" if is_dir else rel
        if gi_spec.match_file(check):
            return True

    if custom_ignore is not None:
        try:
            rel = str(path.relative_to(scan_root))
        except ValueError:
            rel = path.name
        check = rel + "/" if is_dir else rel
        if custom_ignore.match_file(check):
            return True

    return False


def _load_custom_ignore(ignore_file: Path | None) -> pathspec.PathSpec | None:
    if ignore_file is None:
        return None
    try:
        text = ignore_file.read_text(encoding="utf-8")
        return pathspec.PathSpec.from_lines("gitwildmatch", text.splitlines())
    except (OSError, PermissionError) as e:
        raise EmojihuntError(f"Cannot read ignore file {ignore_file}: {e}") from e


def _load_gitignore(directory: Path) -> pathspec.PathSpec | None:
    gitignore_path = directory / ".gitignore"
    if not gitignore_path.is_file():
        return None
    try:
        text = gitignore_path.read_text(encoding="utf-8")
        return pathspec.PathSpec.from_lines("gitwildmatch", text.splitlines())
    except (OSError, PermissionError):
        return None
