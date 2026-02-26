"""HTML check-page renderer.

Generates one file per group from the --check base path.
File naming: {stem}-{slugify(group_name)}{suffix}
"""

from __future__ import annotations

import html
from collections.abc import Sequence
from pathlib import Path

from .constants import (
    DATE_PART_INDEX,
    DATE_PART_SEPARATOR,
    HTML_COL_CREATED,
    HTML_COL_TASK,
    HTML_DEFAULT_SUFFIX,
    HTML_DOC_TYPE,
    HTML_EMPTY_GROUP_TEXT,
    HTML_META_CHARSET,
    HTML_ROW_CLOSE,
    HTML_ROW_OPEN,
    HTML_STATUS_SYMBOL_NAH,
    HTML_STATUS_SYMBOL_OK,
    HTML_STATUS_SYMBOL_PENDING,
    HTML_STYLE_LINES,
    HTML_TABLE_CLOSE,
    HTML_TABLE_OPEN,
    HTML_TAG_BODY_CLOSE,
    HTML_TAG_BODY_OPEN,
    HTML_TAG_HEAD_CLOSE,
    HTML_TAG_HEAD_OPEN,
    HTML_TAG_HTML_CLOSE,
    HTML_TAG_HTML_OPEN,
    HTML_TBODY_CLOSE,
    HTML_TBODY_OPEN,
    HTML_THEAD_CLOSE,
    HTML_THEAD_OPEN,
    HTML_TITLE_PREFIX,
)
from .formatter import format_local_time
from .models import (
    Assignment,
    AssignmentStatus,
    Database,
    Group,
    Project,
    ProjectState,
    Task,
    assignment_key,
)
from .path_mapping import slugify


def render_check_pages(
    db: Database,
    check_base: Path,
    group_ids: set[int] | None = None,
) -> list[Path]:
    """Generate one HTML file per group.

    Each file is written to check_base.parent with the name pattern:
    {check_base.stem}-{slugify(group.name)}{check_base.suffix}
    """
    groups = _select_groups(db, group_ids)
    written_paths: list[Path] = []

    for group in groups:
        out_path = check_page_path(check_base, group.name)
        content = _render_group_page(db, group.id, group.name)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if out_path.exists():
            current = out_path.read_text(encoding="utf-8")
            if current == content:
                continue
        out_path.write_text(content, encoding="utf-8")
        written_paths.append(out_path)

    return written_paths


def remove_check_page(check_base: Path, group_name: str) -> None:
    """Delete a check page for a group name if the file exists."""
    path = check_page_path(check_base, group_name)
    try:
        path.unlink()
    except FileNotFoundError:
        return


def check_page_path(check_base: Path, group_name: str) -> Path:
    """Return the check-page path for one group name."""
    out_dir = check_base.parent
    stem = check_base.stem
    suffix = check_base.suffix or HTML_DEFAULT_SUFFIX
    slug = slugify(group_name)
    return out_dir / f"{stem}-{slug}{suffix}"


def _render_group_page(db: Database, group_id: int, group_name: str) -> str:
    # Projects for this group: exclude DEPRECATED, sort by name
    projects: list[Project] = sorted(
        [
            p
            for p in db.projects
            if p.group_id == group_id and p.state != ProjectState.DEPRECATED
        ],
        key=lambda p: p.name.lower(),
    )

    # Tasks for this group (target group_id or all groups): sort newest first
    tasks = sorted(
        [t for t in db.tasks if t.group_id is None or t.group_id == group_id],
        key=lambda t: t.created_utc,
        reverse=True,
    )

    title = html.escape(group_name)

    lines: list[str] = [
        HTML_DOC_TYPE,
        HTML_TAG_HTML_OPEN,
        HTML_TAG_HEAD_OPEN,
        f'  <meta charset="{HTML_META_CHARSET}">',
        f"  <title>{HTML_TITLE_PREFIX}{title}</title>",
        "  <style>",
        *HTML_STYLE_LINES,
        "  </style>",
        HTML_TAG_HEAD_CLOSE,
        HTML_TAG_BODY_OPEN,
        f"  <h1>{title}</h1>",
    ]

    if not projects and not tasks:
        lines += [HTML_EMPTY_GROUP_TEXT]
    else:
        lines += _render_table(db, projects, tasks)

    lines += [HTML_TAG_BODY_CLOSE, HTML_TAG_HTML_CLOSE, ""]
    return "\n".join(lines)


def _render_table(
    db: Database, projects: list[Project], tasks: Sequence[Task]
) -> list[str]:
    lines: list[str] = [HTML_TABLE_OPEN, HTML_THEAD_OPEN, HTML_ROW_OPEN]
    lines.append(HTML_COL_TASK)
    lines.append(HTML_COL_CREATED)

    for p in projects:
        label = html.escape(p.name)
        if p.state == ProjectState.SUSPENDED:
            label += " <em>(suspended)</em>"
        lines.append(f"        <th>{label}</th>")

    lines += [HTML_ROW_CLOSE, HTML_THEAD_CLOSE, HTML_TBODY_OPEN]

    for task in tasks:
        created = format_local_time(task.created_utc).split(DATE_PART_SEPARATOR)[DATE_PART_INDEX]
        desc = html.escape(task.description)
        lines.append(HTML_ROW_OPEN)
        lines.append(f'        <td class="task-desc">{desc}</td>')
        lines.append(f"        <td>{html.escape(created)}</td>")

        for project in projects:
            key = assignment_key(project.id, task.id)
            a: Assignment | None = db.assignments.get(key)
            if a is None:
                lines.append('        <td class="gap"></td>')
            else:
                cell_class, symbol = _cell_for_status(a.status)
                lines.append(f'        <td class="{cell_class}">{symbol}</td>')

        lines.append(HTML_ROW_CLOSE)

    lines += [HTML_TBODY_CLOSE, HTML_TABLE_CLOSE]
    return lines


def _cell_for_status(status: AssignmentStatus) -> tuple[str, str]:
    if status == AssignmentStatus.OK:
        return "ok", HTML_STATUS_SYMBOL_OK
    if status == AssignmentStatus.NAH:
        return "nah", HTML_STATUS_SYMBOL_NAH
    return "pending", HTML_STATUS_SYMBOL_PENDING


def _select_groups(db: Database, group_ids: set[int] | None) -> list[Group]:
    group_map = {g.id: g for g in db.groups}
    if group_ids is None:
        return list(db.groups)
    selected: list[Group] = []
    for gid in sorted(group_ids):
        group = group_map.get(gid)
        if group is None:
            continue
        selected.append(group)
    return selected
