"""Snapshot discovery and validation for extract listing."""

from __future__ import annotations

from pathlib import Path

from .errors import MetadataError
from .metadata_gateway import read_snapshot_metadata
from .models import SnapshotRecord, SnapshotWarning
from .timestamps import parse_created_utc


def discover_snapshots(
    *, dest_dir_abs: Path
) -> tuple[list[SnapshotRecord], list[SnapshotWarning]]:
    snapshot_records: list[SnapshotRecord] = []
    warnings: list[SnapshotWarning] = []

    metadata_files = sorted(dest_dir_abs.glob("*.json"), key=lambda p: p.name)
    for metadata_path in metadata_files:
        try:
            snapshot_metadata = read_snapshot_metadata(metadata_path_abs=metadata_path)
        except MetadataError as exc:
            warnings.append(
                SnapshotWarning(
                    metadata_path=metadata_path,
                    message=f"Invalid metadata JSON ({metadata_path.name}): {exc}",
                )
            )
            continue

        expected_zip_path = metadata_path.with_suffix(".zip")
        if snapshot_metadata.zip_filename != expected_zip_path.name:
            warnings.append(
                SnapshotWarning(
                    metadata_path=metadata_path,
                    message=(
                        "Metadata zip filename mismatch "
                        f"({metadata_path.name}: expected {expected_zip_path.name}, "
                        f"found {snapshot_metadata.zip_filename})"
                    ),
                )
            )
            continue

        if not expected_zip_path.exists() or not expected_zip_path.is_file():
            warnings.append(
                SnapshotWarning(
                    metadata_path=metadata_path,
                    message=(
                        "Missing corresponding zip for metadata "
                        f"({metadata_path.name} -> {expected_zip_path.name})"
                    ),
                )
            )
            continue

        try:
            created_utc_dt = parse_created_utc(snapshot_metadata.created_utc)
        except ValueError as exc:
            warnings.append(
                SnapshotWarning(
                    metadata_path=metadata_path,
                    message=f"Invalid created_utc value ({metadata_path.name}): {exc}",
                )
            )
            continue

        snapshot_records.append(
            SnapshotRecord(
                metadata_path=metadata_path,
                zip_path=expected_zip_path,
                metadata=snapshot_metadata,
                created_utc_dt=created_utc_dt,
            )
        )

    snapshot_records.sort(key=lambda record: record.created_utc_dt, reverse=True)
    return snapshot_records, warnings
