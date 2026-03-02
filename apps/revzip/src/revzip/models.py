"""Dataclasses shared across revzip layers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from re import Pattern


@dataclass(frozen=True)
class ResolvedPaths:
    source_arg_raw: str
    source_dir_abs: Path
    dest_arg_raw: str
    dest_dir_abs: Path
    ignore_arg_raw: str | None
    ignore_file_abs: Path | None


@dataclass(frozen=True)
class IgnoreRuleSet:
    patterns_raw: list[str]
    compiled_patterns: list[Pattern[str]]


@dataclass(frozen=True)
class ArchiveInventory:
    archived_files_rel: list[Path]
    empty_directories_rel: list[Path]
    skipped_symlinks_rel: list[Path]
    scanned_directories_count: int
    scanned_files_count: int

    @property
    def archived_file_count(self) -> int:
        return len(self.archived_files_rel)

    @property
    def empty_directory_count(self) -> int:
        return len(self.empty_directories_rel)


@dataclass(frozen=True)
class SnapshotMetadata:
    created_utc: str
    created_at: str
    comment: str
    comment_filename_segment: str
    zip_filename: str
    archived_files: list[str]
    empty_directories: list[str]


@dataclass(frozen=True)
class SnapshotRecord:
    metadata_path: Path
    zip_path: Path
    metadata: SnapshotMetadata
    created_utc_dt: datetime


@dataclass(frozen=True)
class SnapshotWarning:
    metadata_path: Path
    message: str


@dataclass(frozen=True)
class ArchiveResult:
    zip_path: Path
    metadata_path: Path
    archived_file_count: int
    empty_directory_count: int
    created_utc: str
    skipped_symlinks_rel: list[Path]


@dataclass(frozen=True)
class RestoreResult:
    selected_zip_path: Path
    restored_file_count: int
    restored_empty_directory_count: int
