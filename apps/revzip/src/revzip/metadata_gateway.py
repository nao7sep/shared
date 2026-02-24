"""Metadata JSON serialization and parsing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import MetadataError
from .models import SnapshotMetadata
from .timestamps import parse_created_utc


def write_snapshot_metadata(
    *, metadata_path_abs: Path, snapshot_metadata: SnapshotMetadata
) -> None:
    payload = {
        "created_utc": snapshot_metadata.created_utc,
        "created_at": snapshot_metadata.created_at,
        "comment": snapshot_metadata.comment,
        "comment_filename_segment": snapshot_metadata.comment_filename_segment,
        "zip_filename": snapshot_metadata.zip_filename,
        "archived_files": snapshot_metadata.archived_files,
        "empty_directories": snapshot_metadata.empty_directories,
    }
    try:
        metadata_path_abs.write_text(
            f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise MetadataError(f"Failed to write metadata: {metadata_path_abs}") from exc


def read_snapshot_metadata(*, metadata_path_abs: Path) -> SnapshotMetadata:
    try:
        raw_text = metadata_path_abs.read_text(encoding="utf-8")
    except OSError as exc:
        raise MetadataError(f"Failed to read metadata: {metadata_path_abs}") from exc

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise MetadataError(f"Invalid metadata JSON: {metadata_path_abs}") from exc

    if not isinstance(payload, dict):
        raise MetadataError(f"Metadata JSON must be an object: {metadata_path_abs}")

    created_utc = _get_required_str(payload, "created_utc", metadata_path_abs)
    try:
        parse_created_utc(created_utc)
    except ValueError as exc:
        raise MetadataError(
            f"Invalid created_utc timestamp in metadata: {metadata_path_abs}"
        ) from exc

    created_at = _get_required_str(payload, "created_at", metadata_path_abs)
    comment = _get_required_str(payload, "comment", metadata_path_abs)
    comment_filename_segment = _get_required_str(
        payload, "comment_filename_segment", metadata_path_abs
    )
    zip_filename = _get_required_str(payload, "zip_filename", metadata_path_abs)
    archived_files = _get_required_str_list(payload, "archived_files", metadata_path_abs)
    empty_directories = _get_required_str_list(
        payload, "empty_directories", metadata_path_abs
    )

    return SnapshotMetadata(
        created_utc=created_utc,
        created_at=created_at,
        comment=comment,
        comment_filename_segment=comment_filename_segment,
        zip_filename=zip_filename,
        archived_files=archived_files,
        empty_directories=empty_directories,
    )


def _get_required_str(payload: dict[str, Any], key: str, metadata_path_abs: Path) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise MetadataError(f"Metadata key '{key}' must be a string: {metadata_path_abs}")
    return value


def _get_required_str_list(
    payload: dict[str, Any], key: str, metadata_path_abs: Path
) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise MetadataError(f"Metadata key '{key}' must be a list: {metadata_path_abs}")
    if not all(isinstance(item, str) for item in value):
        raise MetadataError(
            f"Metadata key '{key}' must be a list of strings: {metadata_path_abs}"
        )
    return value
