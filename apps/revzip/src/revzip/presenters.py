"""User-facing text rendering."""

from __future__ import annotations

from .models import IgnoreRuleSet, ResolvedPaths, SnapshotRecord, SnapshotWarning

_MAIN_MENU_TEXT = "\n".join(
    (
        "1. Archive",
        "2. Extract",
        "3. Exit",
    )
)
_LIST_SEPARATOR = " | "
_WARNING_PREFIX = "WARNING:"
_ERROR_PREFIX = "ERROR:"


def render_app_banner() -> str:
    return "revzip"


def render_loaded_parameters(
    *, resolved_paths: ResolvedPaths, ignore_rule_set: IgnoreRuleSet
) -> list[str]:
    ignore_file = (
        str(resolved_paths.ignore_file_abs)
        if resolved_paths.ignore_file_abs is not None
        else "(none)"
    )
    return [
        "Loaded parameters:",
        f"Source: {resolved_paths.source_dir_abs}",
        f"Destination: {resolved_paths.dest_dir_abs}",
        f"Ignore file: {ignore_file}",
        f"Ignore patterns: {len(ignore_rule_set.patterns_raw)}",
    ]


def render_main_menu() -> str:
    return _MAIN_MENU_TEXT


def render_error(message: str) -> str:
    return f"{_ERROR_PREFIX} {message}"


def render_warning(message: str) -> str:
    return f"{_WARNING_PREFIX} {message}"


def render_snapshot_warning_lines(warnings: list[SnapshotWarning]) -> list[str]:
    return [render_warning(warning.message) for warning in warnings]


def render_snapshot_rows(snapshot_records: list[SnapshotRecord]) -> list[str]:
    if not snapshot_records:
        return []

    width = len(str(len(snapshot_records)))
    rows: list[str] = []
    for index, record in enumerate(snapshot_records, start=1):
        row = _LIST_SEPARATOR.join(
            (
                f"{index:>{width}}",
                record.metadata.created_at,
                record.metadata.comment.replace("\n", "\\n"),
            )
        )
        rows.append(row)

    return rows
