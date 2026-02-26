"""HTML check-page renderer.

Generates one file per group from the --check base path.
File naming: {stem}-{slugify(group_name)}{suffix}
"""

from __future__ import annotations

import html
from collections.abc import Sequence
from pathlib import Path

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
    suffix = check_base.suffix or ".html"
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
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '  <meta charset="UTF-8">',
        f"  <title>Viber Check — {title}</title>",
        "  <style>",
        "    body { font-family: sans-serif; font-size: 14px; }",
        "    table { border-collapse: collapse; }",
        "    th, td { border: 1px solid #ccc; padding: 4px 8px;"
        " text-align: center; vertical-align: top; }",
        "    th { background: #f5f5f5; font-weight: bold; }",
        "    td.task-desc { text-align: left; max-width: 300px; word-break: break-word; }",
        "    td.gap { background: #ccc; }",
        "    td.pending { }",
        "    td.ok { }",
        "    td.nah { }",
        "  </style>",
        "</head>",
        "<body>",
        f"  <h1>{title}</h1>",
    ]

    if not projects and not tasks:
        lines += ["  <p>No projects or tasks in this group.</p>"]
    else:
        lines += _render_table(db, projects, tasks)

    lines += ["</body>", "</html>", ""]
    return "\n".join(lines)


def _render_table(
    db: Database, projects: list[Project], tasks: Sequence[Task]
) -> list[str]:
    lines: list[str] = ["  <table>", "    <thead>", "      <tr>"]
    lines.append("        <th>Task</th>")
    lines.append("        <th>Created</th>")

    for p in projects:
        label = html.escape(p.name)
        if p.state == ProjectState.SUSPENDED:
            label += " <em>(suspended)</em>"
        lines.append(f"        <th>{label}</th>")

    lines += ["      </tr>", "    </thead>", "    <tbody>"]

    for task in tasks:
        created = format_local_time(task.created_utc).split(" ")[0]
        desc = html.escape(task.description)
        lines.append("      <tr>")
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

        lines.append("      </tr>")

    lines += ["    </tbody>", "  </table>"]
    return lines


def _cell_for_status(status: AssignmentStatus) -> tuple[str, str]:
    if status == AssignmentStatus.OK:
        return "ok", "✅"
    if status == AssignmentStatus.NAH:
        return "nah", "❌"
    # Keep pending visually neutral and unobtrusive in tables.
    return "pending", "&nbsp;"


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
