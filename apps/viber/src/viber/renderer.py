"""HTML check-page renderer.

Generates one file per group from the --check base path.
File naming: {stem}-{slugify(group_name)}{suffix}
"""

from __future__ import annotations

import html
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from .formatter import format_local_time
from .models import (
    Assignment,
    AssignmentStatus,
    Database,
    Project,
    ProjectState,
    Task,
    assignment_key,
)
from .path_mapping import slugify

# HTML status symbols
_SYMBOL_OK = "✅"
_SYMBOL_NAH = "❌"
_SYMBOL_PENDING = "·"


def render_check_pages(db: Database, check_base: Path) -> None:
    """Generate one HTML file per group.

    Each file is written to check_base.parent with the name pattern:
    {check_base.stem}-{slugify(group.name)}{check_base.suffix}
    """
    out_dir = check_base.parent
    stem = check_base.stem
    suffix = check_base.suffix or ".html"

    for group in db.groups:
        slug = slugify(group.name)
        out_path = out_dir / f"{stem}-{slug}{suffix}"
        content = _render_group_page(db, group.id, group.name)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")


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

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
        f"  <p>Generated: {html.escape(generated_at)}</p>",
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
        created = format_local_time(task.created_utc).split(" ")[0]  # date only
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
        return "ok", _SYMBOL_OK
    if status == AssignmentStatus.NAH:
        return "nah", _SYMBOL_NAH
    return "pending", _SYMBOL_PENDING
