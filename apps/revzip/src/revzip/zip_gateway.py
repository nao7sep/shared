"""Zip read/write/verify helpers."""

from __future__ import annotations

from collections.abc import Callable
import zipfile
from pathlib import Path, PurePosixPath
from typing import Iterable

from .errors import ArchiveError, ExtractError, ZipIntegrityError


def write_snapshot_zip(
    *,
    source_dir_abs: Path,
    zip_path_abs: Path,
    archived_files_rel: Iterable[Path],
    empty_directories_rel: Iterable[Path],
    on_file_archived: Callable[[int, int], None] | None = None,
) -> None:
    file_entries = [(rel_path, rel_path.as_posix()) for rel_path in archived_files_rel]
    directory_entries = [
        (rel_path, f"{rel_path.as_posix().rstrip('/')}/")
        for rel_path in empty_directories_rel
    ]
    _assert_no_duplicate_entries(
        [entry_name for _, entry_name in file_entries + directory_entries]
    )

    try:
        with zipfile.ZipFile(zip_path_abs, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            total_files = len(file_entries)
            archived_files_count = 0
            for rel_path, entry_name in file_entries:
                file_abs = source_dir_abs / rel_path
                if not file_abs.is_file():
                    raise ArchiveError(f"File disappeared while archiving: {file_abs}")
                zf.write(file_abs, arcname=entry_name)
                archived_files_count += 1
                if on_file_archived is not None:
                    on_file_archived(archived_files_count, total_files)

            for rel_path, entry_name in directory_entries:
                dir_abs = source_dir_abs / rel_path
                if not dir_abs.is_dir():
                    raise ArchiveError(f"Directory disappeared while archiving: {dir_abs}")
                zf.writestr(entry_name, data=b"")
    except OSError as exc:
        raise ArchiveError(f"Failed to write zip archive: {zip_path_abs}") from exc


def verify_zip_integrity(zip_path_abs: Path) -> None:
    try:
        with zipfile.ZipFile(zip_path_abs, mode="r") as zf:
            corrupt_member = zf.testzip()
            if corrupt_member is not None:
                raise ZipIntegrityError(
                    f"Zip integrity check failed for member: {corrupt_member}"
                )
    except zipfile.BadZipFile as exc:
        raise ZipIntegrityError(f"Invalid zip archive: {zip_path_abs}") from exc
    except OSError as exc:
        raise ZipIntegrityError(f"Failed to read zip archive: {zip_path_abs}") from exc


def extract_snapshot_zip(*, zip_path_abs: Path, target_dir_abs: Path) -> None:
    try:
        with zipfile.ZipFile(zip_path_abs, mode="r") as zf:
            _validate_members_safe_for_extract(zf.infolist())
            zf.extractall(target_dir_abs)
    except zipfile.BadZipFile as exc:
        raise ExtractError(f"Invalid zip archive: {zip_path_abs}") from exc
    except OSError as exc:
        raise ExtractError(f"Failed to extract zip archive: {zip_path_abs}") from exc


def _assert_no_duplicate_entries(entry_names: list[str]) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for entry_name in entry_names:
        if entry_name in seen:
            duplicates.add(entry_name)
        seen.add(entry_name)

    if duplicates:
        ordered_duplicates = ", ".join(sorted(duplicates))
        raise ArchiveError(f"Duplicate zip entry paths detected: {ordered_duplicates}")


def _validate_members_safe_for_extract(members: list[zipfile.ZipInfo]) -> None:
    for member in members:
        entry_name = member.filename
        if entry_name.startswith("/") or entry_name.startswith("\\"):
            raise ExtractError(f"Unsafe zip entry path: {entry_name}")

        normalised = entry_name.replace("\\", "/")
        entry_parts = PurePosixPath(normalised).parts
        if ".." in entry_parts:
            raise ExtractError(f"Unsafe zip entry path: {entry_name}")
