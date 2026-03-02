"""Tests for HTML check-page renderer."""

from pathlib import Path

from viber.models import AssignmentStatus, Database, ProjectState
from viber.renderer import remove_check_page, render_check_pages
from viber.service import (
    create_group,
    create_project,
    create_task,
    resolve_assignment,
    set_project_state,
)


def make_db_with_content() -> Database:
    db = Database()
    g1 = create_group(db, "Backend")
    p1 = create_project(db, "api-server", g1.id)
    _p2 = create_project(db, "auth-service", g1.id)
    t1 = create_task(db, "Update deps", None)
    _t2 = create_task(db, "Fix lint", g1.id)
    resolve_assignment(db, p1.id, t1.id, AssignmentStatus.OK, None)
    # _p2/t1 and p1/_t2 and _p2/_t2 remain pending
    return db


def test_render_creates_files(tmp_path: Path) -> None:
    db = make_db_with_content()
    check_base = tmp_path / "check.html"
    render_check_pages(db, check_base)
    files = list(tmp_path.glob("check-*.html"))
    assert len(files) == 1
    assert files[0].name == "check-backend.html"


def test_render_excludes_deprecated_projects(tmp_path: Path) -> None:
    db = Database()
    g = create_group(db, "Backend")
    _p1 = create_project(db, "api", g.id)
    p2 = create_project(db, "deprecated-service", g.id)
    create_task(db, "Task", None)
    set_project_state(db, p2.id, ProjectState.DEPRECATED)

    check_base = tmp_path / "check.html"
    render_check_pages(db, check_base)
    content = (tmp_path / "check-backend.html").read_text(encoding="utf-8")
    assert "api" in content
    assert "deprecated-service" not in content


def test_render_shows_suspended_project_with_label(tmp_path: Path) -> None:
    db = Database()
    g = create_group(db, "Backend")
    p = create_project(db, "sleepy-service", g.id)
    create_task(db, "Task", None)
    set_project_state(db, p.id, ProjectState.SUSPENDED)

    check_base = tmp_path / "check.html"
    render_check_pages(db, check_base)
    content = (tmp_path / "check-backend.html").read_text(encoding="utf-8")
    assert "sleepy-service" in content
    assert "suspended" in content


def test_render_gray_cell_for_lifecycle_gap(tmp_path: Path) -> None:
    """Project added AFTER task creation → gap cell (gray)."""
    db = Database()
    g = create_group(db, "Backend")
    # Create task first
    create_task(db, "Old task", None)
    # Then create project (no assignment generated)
    create_project(db, "new-project", g.id)

    check_base = tmp_path / "check.html"
    render_check_pages(db, check_base)
    content = (tmp_path / "check-backend.html").read_text(encoding="utf-8")
    assert 'class="gap"' in content


def test_render_status_symbols(tmp_path: Path) -> None:
    db = Database()
    g = create_group(db, "Backend")
    p1 = create_project(db, "ok-project", g.id)
    p2 = create_project(db, "nah-project", g.id)
    _p3 = create_project(db, "pending-project", g.id)
    t = create_task(db, "Task", None)
    resolve_assignment(db, p1.id, t.id, AssignmentStatus.OK, None)
    resolve_assignment(db, p2.id, t.id, AssignmentStatus.NAH, None)
    # _p3 remains pending

    check_base = tmp_path / "check.html"
    render_check_pages(db, check_base)
    content = (tmp_path / "check-backend.html").read_text(encoding="utf-8")
    assert "✅" in content
    assert "❌" in content
    assert "&nbsp;" in content


def test_render_tasks_newest_first(tmp_path: Path) -> None:
    db = Database()
    g = create_group(db, "Backend")
    create_project(db, "api", g.id)
    create_task(db, "First task", None)
    create_task(db, "Second task", None)

    check_base = tmp_path / "check.html"
    render_check_pages(db, check_base)
    content = (tmp_path / "check-backend.html").read_text(encoding="utf-8")
    # Second task (newer) should appear before first task
    pos_first = content.find("First task")
    pos_second = content.find("Second task")
    assert pos_second < pos_first, "Newer task should appear first in HTML"


def test_render_multiple_groups(tmp_path: Path) -> None:
    db = Database()
    g1 = create_group(db, "Backend")
    g2 = create_group(db, "Frontend")
    create_project(db, "api", g1.id)
    create_project(db, "ui", g2.id)
    create_task(db, "Task", None)

    check_base = tmp_path / "check.html"
    render_check_pages(db, check_base)
    files = sorted(f.name for f in tmp_path.glob("check-*.html"))
    assert "check-backend.html" in files
    assert "check-frontend.html" in files


def test_render_selected_groups_only(tmp_path: Path) -> None:
    db = Database()
    g1 = create_group(db, "Backend")
    g2 = create_group(db, "Frontend")
    create_project(db, "api", g1.id)
    create_project(db, "ui", g2.id)
    create_task(db, "Task", None)

    check_base = tmp_path / "check.html"
    render_check_pages(db, check_base)
    frontend_path = tmp_path / "check-frontend.html"
    before_stat = frontend_path.stat().st_mtime_ns

    create_project(db, "billing", g1.id)
    render_check_pages(db, check_base, {g1.id})
    after_stat = frontend_path.stat().st_mtime_ns

    assert before_stat == after_stat


def test_remove_check_page(tmp_path: Path) -> None:
    db = Database()
    g = create_group(db, "Backend")
    create_project(db, "api", g.id)
    create_task(db, "Task", None)

    check_base = tmp_path / "check.html"
    render_check_pages(db, check_base)
    page = tmp_path / "check-backend.html"
    assert page.exists()

    remove_check_page(check_base, "Backend")
    assert not page.exists()


def test_render_slug_collisions_share_filename(tmp_path: Path) -> None:
    """Groups whose names produce the same slug map to the same file; last writer wins."""
    db = Database()
    g1 = create_group(db, "Backend Team")
    g2 = create_group(db, "Backend-Team")
    create_project(db, "api", g1.id)
    create_project(db, "worker", g2.id)
    create_task(db, "Task", None)

    check_base = tmp_path / "check.html"
    render_check_pages(db, check_base)

    files = list(tmp_path.glob("check-*.html"))
    assert len(files) == 1
    assert files[0].name == "check-backend-team.html"


def test_render_group_name_with_empty_slug_uses_fallback_filename(tmp_path: Path) -> None:
    db = Database()
    g = create_group(db, "!!!")
    create_project(db, "api", g.id)
    create_task(db, "Task", None)

    check_base = tmp_path / "check.html"
    written = render_check_pages(db, check_base)

    assert [path.name for path in written] == ["check-group.html"]
    content = written[0].read_text(encoding="utf-8")
    assert "<h1>!!! | viber</h1>" in content


def test_render_escapes_all_user_supplied_text(tmp_path: Path) -> None:
    db = Database()
    group_name = 'Back<end>&"Team"'
    project_name = 'api<script>alert(1)</script>&"x"'
    task_desc = 'Fix <b>markup</b> & "quotes"'
    g = create_group(db, group_name)
    p = create_project(db, project_name, g.id)
    create_task(db, task_desc, g.id)
    set_project_state(db, p.id, ProjectState.SUSPENDED)

    check_base = tmp_path / "check.html"
    written = render_check_pages(db, check_base)
    assert len(written) == 1
    content = written[0].read_text(encoding="utf-8")

    # Group name in title/h1 must be escaped.
    assert "Back&lt;end&gt;&amp;&quot;Team&quot;" in content
    # Project name must be escaped, while static suspended markup is preserved.
    assert "api&lt;script&gt;alert(1)&lt;/script&gt;&amp;&quot;x&quot;" in content
    assert "<em>(suspended)</em>" in content
    # Task description must be escaped.
    assert "Fix &lt;b&gt;markup&lt;/b&gt; &amp; &quot;quotes&quot;" in content
    # Raw tag injection should not appear.
    assert "<script>alert(1)</script>" not in content
    assert "<b>markup</b>" not in content
