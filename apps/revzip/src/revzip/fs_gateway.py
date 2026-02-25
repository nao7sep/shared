"""Filesystem traversal and restore helpers."""

from __future__ import annotations

from collections.abc import Callable
import shutil
from pathlib import Path

from .errors import ArchiveError, ExtractError
from .ignore_rules import is_default_ignored_name, matches_ignore_rules
from .models import ArchiveInventory, IgnoreRuleSet


def collect_archive_inventory(
    *,
    source_dir_abs: Path,
    raw_source_argument: str,
    ignore_rule_set: IgnoreRuleSet,
    on_directory_scanned: Callable[[int, int], None] | None = None,
) -> ArchiveInventory:
    archived_files_rel: list[Path] = []
    empty_directories_rel: list[Path] = []
    skipped_symlinks_rel: list[Path] = []
    scanned_directories_count = 0
    scanned_files_count = 0

    def walk_dir(current_dir_abs: Path, current_rel: Path | None) -> bool:
        nonlocal scanned_directories_count
        nonlocal scanned_files_count

        has_archivable_entries = False
        try:
            children = sorted(current_dir_abs.iterdir(), key=lambda p: p.name)
        except OSError as exc:
            raise ArchiveError(f"Failed to read directory: {current_dir_abs}") from exc

        for child_abs in children:
            child_rel = (
                Path(child_abs.name)
                if current_rel is None
                else current_rel / child_abs.name
            )
            if is_default_ignored_name(child_abs.name):
                continue
            if matches_ignore_rules(
                rel_path=child_rel,
                raw_source_argument=raw_source_argument,
                ignore_rule_set=ignore_rule_set,
            ):
                continue
            if child_abs.is_symlink():
                skipped_symlinks_rel.append(child_rel)
                continue

            if child_abs.is_file():
                archived_files_rel.append(child_rel)
                scanned_files_count += 1
                has_archivable_entries = True
                continue

            if child_abs.is_dir():
                child_has_entries = walk_dir(child_abs, child_rel)
                if not child_has_entries:
                    empty_directories_rel.append(child_rel)
                has_archivable_entries = True
                continue

        scanned_directories_count += 1
        if on_directory_scanned is not None:
            on_directory_scanned(scanned_directories_count, scanned_files_count)

        return has_archivable_entries

    walk_dir(source_dir_abs, current_rel=None)

    archived_files_rel.sort(key=lambda p: p.as_posix())
    empty_directories_rel.sort(key=lambda p: p.as_posix())
    skipped_symlinks_rel.sort(key=lambda p: p.as_posix())

    return ArchiveInventory(
        archived_files_rel=archived_files_rel,
        empty_directories_rel=empty_directories_rel,
        skipped_symlinks_rel=skipped_symlinks_rel,
        scanned_directories_count=scanned_directories_count,
        scanned_files_count=scanned_files_count,
    )


def clear_and_recreate_directory(directory_abs: Path) -> None:
    if directory_abs.exists() and not directory_abs.is_dir():
        raise ExtractError(f"Restore target is not a directory: {directory_abs}")

    if not directory_abs.exists():
        try:
            directory_abs.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ExtractError(f"Failed to create directory: {directory_abs}") from exc
        return

    try:
        children = list(directory_abs.iterdir())
    except OSError as exc:
        raise ExtractError(f"Failed to list directory: {directory_abs}") from exc

    for child_abs in children:
        try:
            if child_abs.is_symlink() or child_abs.is_file():
                child_abs.unlink()
            elif child_abs.is_dir():
                shutil.rmtree(child_abs)
            else:
                child_abs.unlink()
        except OSError as exc:
            raise ExtractError(f"Failed to remove path during restore: {child_abs}") from exc

    try:
        directory_abs.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ExtractError(f"Failed to recreate directory: {directory_abs}") from exc


def count_regular_files_and_empty_directories(root_dir_abs: Path) -> tuple[int, int]:
    file_count = 0
    empty_directory_count = 0

    def walk_dir(current_dir_abs: Path) -> bool:
        nonlocal file_count
        nonlocal empty_directory_count

        has_entries = False
        try:
            children = sorted(current_dir_abs.iterdir(), key=lambda p: p.name)
        except OSError as exc:
            raise ExtractError(f"Failed to read directory: {current_dir_abs}") from exc

        for child_abs in children:
            if child_abs.is_symlink():
                continue
            if child_abs.is_file():
                file_count += 1
                has_entries = True
                continue
            if child_abs.is_dir():
                child_has_entries = walk_dir(child_abs)
                if not child_has_entries:
                    empty_directory_count += 1
                has_entries = True
                continue

        return has_entries

    walk_dir(root_dir_abs)
    return file_count, empty_directory_count
