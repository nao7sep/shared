"""HTML check-page renderer.

Generates one file per group from the --check base path.
File naming: {stem}-{safe-slug}-g{group_id}{suffix}
"""

from __future__ import annotations

import html
from collections.abc import Sequence
from pathlib import Path

from .errors import FilenameSanitizationError
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
    {check_base.stem}-{safe-slug}-g{group.id}{check_base.suffix}
    """
    groups = _select_groups(db, group_ids)
    written_paths: list[Path] = []

    for group in groups:
        out_path = check_page_path(check_base, group.id, group.name)
        content = _render_group_page(db, group.id, group.name)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if out_path.exists():
            current = out_path.read_text(encoding="utf-8")
            if current == content:
                continue
        out_path.write_text(content, encoding="utf-8")
        written_paths.append(out_path)

    return written_paths


def remove_check_page(check_base: Path, group_id: int, group_name: str) -> None:
    """Delete a check page for a group name if the file exists."""
    path = check_page_path(check_base, group_id, group_name)
    try:
        path.unlink()
    except FileNotFoundError:
        return


def check_page_path(check_base: Path, group_id: int, group_name: str) -> Path:
    """Return the check-page path for one group name."""
    out_dir = check_base.parent
    stem = check_base.stem
    suffix = check_base.suffix or ".html"
    slug = _safe_group_slug(group_name)
    return out_dir / f"{stem}-{slug}-g{group_id}{suffix}"


def _safe_group_slug(group_name: str) -> str:
    try:
        return slugify(group_name)
    except FilenameSanitizationError:
        return "group"


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

    group_label = html.escape(group_name)

    lines: list[str] = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '  <meta charset="UTF-8">',
        f"  <title>{group_label} | viber</title>",
        "  <style>",
        "    body { font-size: 1rem; }",
        "    h1 { text-align: center; }",
        "    table { border-collapse: collapse; margin: 0 auto; }",
        "    th, td { border: 1px solid gray; padding: 0.5em; text-align: center; }",
        "    th { background: black; color: white; font-weight: bold; }",
        "    td.task-desc { text-align: left; overflow-wrap: break-word; }",
        "    td.gap { background: silver; }",
        "  </style>",
        "</head>",
        "<body>",
        f"  <h1>{group_label} | viber</h1>",
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
    lines.append("        <th>Created</th>")
    lines.append("        <th>Task</th>")

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
        lines.append(f"        <td>{html.escape(created)}</td>")
        lines.append(f'        <td class="task-desc">{desc}</td>')

        for project in projects:
            key = assignment_key(project.id, task.id)
            a: Assignment | None = db.assignments.get(key)
            if a is None:
                lines.append('        <td class="gap"></td>')
            else:
                lines.append(f"        <td>{_status_symbol(a.status)}</td>")

        lines.append("      </tr>")

    lines += ["    </tbody>", "  </table>"]
    return lines


def _status_symbol(status: AssignmentStatus) -> str:
    if status == AssignmentStatus.OK:
        return "✅"
    if status == AssignmentStatus.NAH:
        return "❌"
    # Keep pending visually neutral and unobtrusive in tables.
    return "&nbsp;"


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
