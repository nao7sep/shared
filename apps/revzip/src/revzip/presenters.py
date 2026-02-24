"""User-facing text rendering."""

from __future__ import annotations

from .constants import ERROR_PREFIX, LIST_SEPARATOR, MAIN_MENU_TEXT, WARNING_PREFIX
from .models import SnapshotRecord, SnapshotWarning


def render_main_menu() -> str:
    return MAIN_MENU_TEXT


def render_error(message: str) -> str:
    return f"{ERROR_PREFIX} {message}"


def render_warning(message: str) -> str:
    return f"{WARNING_PREFIX} {message}"


def render_snapshot_warning_lines(warnings: list[SnapshotWarning]) -> list[str]:
    return [render_warning(warning.message) for warning in warnings]


def render_snapshot_rows(snapshot_records: list[SnapshotRecord]) -> list[str]:
    if not snapshot_records:
        return []

    width = len(str(len(snapshot_records)))
    rows: list[str] = []
    for index, record in enumerate(snapshot_records, start=1):
        row = LIST_SEPARATOR.join(
            (
                f"{index:>{width}}",
                record.metadata.created_at,
                f"files={len(record.metadata.archived_files)}",
                f"empty-dirs={len(record.metadata.empty_directories)}",
                record.metadata.comment.replace("\n", "\\n"),
            )
        )
        rows.append(row)

    return rows
