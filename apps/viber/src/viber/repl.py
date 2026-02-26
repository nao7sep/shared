"""REPL command loop, parser, and interactive flows."""

from __future__ import annotations

import shlex
from collections.abc import Callable
from pathlib import Path

from .errors import AssignmentNotFoundError, ViberError
from .formatter import (
    format_group,
    format_local_time,
    format_project,
    format_task,
    print_blank,
    print_segment,
)
from .models import AssignmentStatus, Database, ProjectState, assignment_key
from .queries import pending_all, pending_by_project, pending_by_task
from .renderer import render_check_pages
from .service import (
    create_group,
    create_project,
    create_task,
    delete_group,
    delete_project,
    delete_task,
    get_group,
    get_project,
    get_task,
    list_groups,
    list_projects,
    list_tasks,
    resolve_assignment,
    set_project_state,
    update_task_description,
)
from .store import save_database

_PROMPT = "> Command: "

_FULL_COMMANDS = {
    "create", "read", "update", "delete", "view",
    "ok", "nah", "work", "help", "exit", "quit",
}
_ALIASES = {
    "c": "create",
    "r": "read",
    "u": "update",
    "d": "delete",
    "v": "view",
    "o": "ok",
    "n": "nah",
    "w": "work",
}

_HELP_TEXT = """\
Viber — cross-project maintenance tracker

Commands (full-word / alias):
  create group <name>                    c g <name>
  create project <name> g<ID>            c p <name> g<ID>
  create task <description> [g<ID>]      c t <description> [g<ID>]

  read groups                            r groups
  read projects                          r projects
  read tasks                             r tasks
  read g<ID>                             r g<ID>
  read p<ID>                             r p<ID>
  read t<ID>                             r t<ID>

  update p<ID> active|suspended|deprecated   u p<ID> <state>
  update t<ID>                               u t<ID>   (prompts for new description)

  delete g<ID>                           d g<ID>
  delete p<ID>                           d p<ID>
  delete t<ID>                           d t<ID>

  view                                   v       (all pending)
  view p<ID>                             v p<ID> (pending tasks for project)
  view t<ID>                             v t<ID> (pending projects for task)

  ok p<ID> t<ID>                         o p<ID> t<ID>
  ok t<ID> p<ID>                         o t<ID> p<ID>
  nah p<ID> t<ID>                        n p<ID> t<ID>

  work p<ID>                             w p<ID> (iterate pending tasks for project)
  work t<ID>                             w t<ID> (iterate pending projects for task)

  help
  exit | quit"""


def run_repl(
    db: Database,
    data_path: Path,
    check_path: Path | None,
) -> None:
    """Run the interactive REPL loop until exit/quit."""

    def after_mutation() -> None:
        save_database(db, data_path)
        if check_path is not None:
            render_check_pages(db, check_path)

    print("Viber is ready. Type 'help' for commands, 'exit' or 'quit' to leave.")

    while True:
        try:
            raw = input(_PROMPT)
        except (EOFError, KeyboardInterrupt):
            print()
            continue

        line = raw.strip()
        if not line:
            continue

        try:
            tokens = shlex.split(line)
        except ValueError as exc:
            print_segment([f"Parse error: {exc}"])
            continue

        if not tokens:
            continue

        verb = tokens[0].lower()
        verb = _ALIASES.get(verb, verb)
        args = tokens[1:]

        if verb in ("exit", "quit"):
            print_blank()
            print("Goodbye.")
            break

        try:
            _dispatch(verb, args, db, after_mutation)
        except ViberError as exc:
            print_segment([f"Error: {exc}"])
        except Exception as exc:  # noqa: BLE001
            print_segment([f"Unexpected error: {exc}"])


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


def _dispatch(
    verb: str,
    args: list[str],
    db: Database,
    after_mutation: Callable[[], None],
) -> None:
    if verb == "help":
        _cmd_help()
    elif verb == "create":
        _cmd_create(args, db, after_mutation)
    elif verb == "read":
        _cmd_read(args, db)
    elif verb == "update":
        _cmd_update(args, db, after_mutation)
    elif verb == "delete":
        _cmd_delete(args, db, after_mutation)
    elif verb == "view":
        _cmd_view(args, db)
    elif verb == "ok":
        _cmd_resolve(args, db, AssignmentStatus.OK, after_mutation)
    elif verb == "nah":
        _cmd_resolve(args, db, AssignmentStatus.NAH, after_mutation)
    elif verb == "work":
        _cmd_work(args, db, after_mutation)
    else:
        print_segment([f"Unknown command: '{verb}'. Type 'help' for available commands."])


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


def _cmd_help() -> None:
    print_segment(_HELP_TEXT.splitlines())


def _cmd_create(
    args: list[str], db: Database, after_mutation: Callable[[], None]
) -> None:
    if not args:
        print_segment([
            "Usage: create group <name> | create project <name> g<ID>"
            " | create task <description> [g<ID>]"
        ])
        return

    kind = args[0].lower()

    if kind in ("group", "g"):
        if len(args) < 2:
            print_segment(["Usage: create group <name>"])
            return
        name = " ".join(args[1:])
        group = create_group(db, name)
        after_mutation()
        print_segment([f"Created: {format_group(group)}"])

    elif kind in ("project", "p"):
        if len(args) < 3:
            print_segment(["Usage: create project <name> g<ID>"])
            return
        group_token = args[-1]
        group_id = _parse_id_token(group_token, "g")
        if group_id is None:
            print_segment([f"Invalid group reference '{group_token}'. Expected g<ID>."])
            return
        name = " ".join(args[1:-1])
        group = get_group(db, group_id)
        project = create_project(db, name, group_id)
        after_mutation()
        print_segment([f"Created: {format_project(project, group)}"])

    elif kind in ("task", "t"):
        if len(args) < 2:
            print_segment(["Usage: create task <description> [g<ID>]"])
            return
        task_group_id: int | None = None
        desc_tokens = args[1:]
        # Check if last token is a group reference
        if desc_tokens and _parse_id_token(desc_tokens[-1], "g") is not None:
            task_group_id = _parse_id_token(desc_tokens[-1], "g")
            desc_tokens = desc_tokens[:-1]
        if not desc_tokens:
            print_segment(["Task description cannot be empty."])
            return
        description = " ".join(desc_tokens)
        task = create_task(db, description, task_group_id)
        after_mutation()
        print_segment([f"Created: t{task.id}: {task.description}"])

    else:
        print_segment([f"Unknown entity type '{kind}'. Use 'group', 'project', or 'task'."])


def _cmd_read(args: list[str], db: Database) -> None:
    if not args:
        print_segment(["Usage: read groups|projects|tasks | read g<ID>|p<ID>|t<ID>"])
        return

    token = args[0].lower()

    if token in ("groups", "g"):
        groups = list_groups(db)
        if not groups:
            print_segment(["No groups."])
        else:
            print_segment([format_group(g) for g in groups])

    elif token in ("projects", "p"):
        projects = list_projects(db)
        if not projects:
            print_segment(["No projects."])
        else:
            group_map = {g.id: g for g in db.groups}
            lines = []
            for p in projects:
                g = group_map.get(p.group_id)
                if g:
                    lines.append(format_project(p, g))
                else:
                    lines.append(f"p{p.id}: {p.name} [{p.state.value}] (group: ?)")
            print_segment(lines)

    elif token in ("tasks", "t"):
        tasks = list_tasks(db)
        if not tasks:
            print_segment(["No tasks."])
        else:
            print_segment([format_task(t, db) for t in tasks])

    elif token.startswith("g"):
        gid = _parse_id_token(token, "g")
        if gid is None:
            print_segment([f"Invalid group reference '{token}'."])
            return
        group = get_group(db, gid)
        print_segment([format_group(group)])

    elif token.startswith("p"):
        pid = _parse_id_token(token, "p")
        if pid is None:
            print_segment([f"Invalid project reference '{token}'."])
            return
        project = get_project(db, pid)
        group_map = {g.id: g for g in db.groups}
        maybe_group = group_map.get(project.group_id)
        if maybe_group is not None:
            print_segment([format_project(project, maybe_group)])
        else:
            print_segment([f"p{project.id}: {project.name} [{project.state.value}]"])

    elif token.startswith("t"):
        tid = _parse_id_token(token, "t")
        if tid is None:
            print_segment([f"Invalid task reference '{token}'."])
            return
        task = get_task(db, tid)
        print_segment([format_task(task, db)])

    else:
        print_segment([
            f"Unknown target '{token}'."
            " Expected groups/projects/tasks or g<ID>/p<ID>/t<ID>."
        ])


def _cmd_update(
    args: list[str], db: Database, after_mutation: Callable[[], None]
) -> None:
    if not args:
        print_segment(["Usage: update p<ID> active|suspended|deprecated | update t<ID>"])
        return

    token = args[0].lower()

    if token.startswith("p"):
        pid = _parse_id_token(token, "p")
        if pid is None:
            print_segment([f"Invalid project reference '{token}'."])
            return
        if len(args) < 2:
            print_segment(["Usage: update p<ID> active|suspended|deprecated"])
            return
        state_str = args[1].lower()
        state_map = {
            "active": ProjectState.ACTIVE,
            "suspended": ProjectState.SUSPENDED,
            "deprecated": ProjectState.DEPRECATED,
        }
        if state_str not in state_map:
            print_segment([f"Unknown state '{state_str}'. Use: active, suspended, deprecated."])
            return
        project = set_project_state(db, pid, state_map[state_str])
        group_map = {g.id: g for g in db.groups}
        group = group_map.get(project.group_id)
        after_mutation()
        if group:
            print_segment([f"Updated: {format_project(project, group)}"])
        else:
            print_segment([f"Updated: p{project.id} state → {state_str}"])

    elif token.startswith("t"):
        tid = _parse_id_token(token, "t")
        if tid is None:
            print_segment([f"Invalid task reference '{token}'."])
            return
        task = get_task(db, tid)
        print_segment([
            f"Current description: {task.description}",
        ])
        try:
            new_desc = input("New description: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            print_segment(["Update cancelled."])
            return
        if not new_desc:
            print_segment(["Description cannot be empty. Update cancelled."])
            return
        task = update_task_description(db, tid, new_desc)
        after_mutation()
        print_segment([f"Updated: t{task.id}: {task.description}"])

    else:
        print_segment([f"Unknown target '{token}'. Expected p<ID> or t<ID>."])


def _cmd_delete(
    args: list[str], db: Database, after_mutation: Callable[[], None]
) -> None:
    if not args:
        print_segment(["Usage: delete g<ID>|p<ID>|t<ID>"])
        return

    token = args[0].lower()

    if token.startswith("g"):
        gid = _parse_id_token(token, "g")
        if gid is None:
            print_segment([f"Invalid group reference '{token}'."])
            return
        group = delete_group(db, gid)
        after_mutation()
        print_segment([f"Deleted: {format_group(group)}"])

    elif token.startswith("p"):
        pid = _parse_id_token(token, "p")
        if pid is None:
            print_segment([f"Invalid project reference '{token}'."])
            return
        project = delete_project(db, pid)
        after_mutation()
        print_segment([f"Deleted: p{project.id}: {project.name}"])

    elif token.startswith("t"):
        tid = _parse_id_token(token, "t")
        if tid is None:
            print_segment([f"Invalid task reference '{token}'."])
            return
        task = delete_task(db, tid)
        after_mutation()
        print_segment([f"Deleted: t{task.id}: {task.description}"])

    else:
        print_segment([f"Unknown target '{token}'. Expected g<ID>, p<ID>, or t<ID>."])


def _cmd_view(args: list[str], db: Database) -> None:
    if not args:
        # All pending
        entries = pending_all(db)
        if not entries:
            print_segment(["Vibe is good. No pending assignments."])
        else:
            lines = []
            for e in entries:
                lines.append(
                    f"p{e.project.id}/{e.project.name} + t{e.task.id}: {e.task.description}"
                )
            print_segment(lines)
        return

    token = args[0].lower()

    if token.startswith("p"):
        pid = _parse_id_token(token, "p")
        if pid is None:
            print_segment([f"Invalid project reference '{token}'."])
            return
        project = get_project(db, pid)
        results = pending_by_project(db, pid)
        if not results:
            print_segment([f"No pending tasks for p{pid}: {project.name}."])
        else:
            lines = [f"Pending tasks for p{pid}: {project.name}:"]
            for task, _a in results:
                created = format_local_time(task.created_utc).split(" ")[0]
                lines.append(f"  t{task.id}: {task.description} ({created})")
            print_segment(lines)

    elif token.startswith("t"):
        tid = _parse_id_token(token, "t")
        if tid is None:
            print_segment([f"Invalid task reference '{token}'."])
            return
        task = get_task(db, tid)
        task_results = pending_by_task(db, tid)
        if not task_results:
            print_segment([f"No pending projects for t{tid}: {task.description}."])
        else:
            lines = [f"Pending projects for t{tid}: {task.description}:"]
            for project, group, _a in task_results:
                lines.append(f"  p{project.id}: {project.name} (group: {group.name})")
            print_segment(lines)

    else:
        print_segment([f"Unknown target '{token}'. Expected p<ID> or t<ID>."])


def _cmd_resolve(
    args: list[str],
    db: Database,
    status: AssignmentStatus,
    after_mutation: Callable[[], None],
) -> None:
    """Handle ok/nah with either p<ID> t<ID> or t<ID> p<ID> token order."""
    if len(args) < 2:
        verb = "ok" if status == AssignmentStatus.OK else "nah"
        print_segment([f"Usage: {verb} p<ID> t<ID>"])
        return

    pid, tid = _parse_pt_tokens(args[0], args[1])
    if pid is None or tid is None:
        print_segment([f"Expected p<ID> and t<ID> in either order. Got: {args[0]} {args[1]}"])
        return

    project = get_project(db, pid)
    task = get_task(db, tid)

    key = assignment_key(pid, tid)
    if key not in db.assignments:
        raise AssignmentNotFoundError(pid, tid)

    assignment = db.assignments[key]
    verb_label = "ok" if status == AssignmentStatus.OK else "nah"

    print_segment([
        f"Resolving as '{verb_label}':",
        f"  Project: p{project.id}: {project.name}",
        f"  Task:    t{task.id}: {task.description}",
        f"  Current: {assignment.status.value}",
    ])

    try:
        confirm = input("Confirm? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        print_segment(["Cancelled."])
        return

    if confirm not in ("y", "yes"):
        print_segment(["Cancelled."])
        return

    try:
        comment_raw = input("Comment (optional, Enter to skip): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        comment_raw = ""

    comment = comment_raw if comment_raw else None
    resolve_assignment(db, pid, tid, status, comment)
    after_mutation()
    print_segment([
        f"Marked {verb_label}: p{project.id}/{project.name}"
        f" + t{task.id}/{task.description}"
    ])


def _cmd_work(
    args: list[str], db: Database, after_mutation: Callable[[], None]
) -> None:
    if not args:
        print_segment(["Usage: work p<ID> | work t<ID>"])
        return

    token = args[0].lower()

    if token.startswith("p"):
        pid = _parse_id_token(token, "p")
        if pid is None:
            print_segment([f"Invalid project reference '{token}'."])
            return
        project = get_project(db, pid)
        _work_by_project(db, project, after_mutation)

    elif token.startswith("t"):
        tid = _parse_id_token(token, "t")
        if tid is None:
            print_segment([f"Invalid task reference '{token}'."])
            return
        task = get_task(db, tid)
        _work_by_task(db, task, after_mutation)

    else:
        print_segment([f"Unknown target '{token}'. Expected p<ID> or t<ID>."])


def _work_by_project(
    db: Database, project: object, after_mutation: Callable[[], None]
) -> None:
    from .models import Project  # local import for type

    if not isinstance(project, Project):
        return

    results = pending_by_project(db, project.id)
    if not results:
        print_segment([f"No pending tasks for p{project.id}: {project.name}."])
        return

    print_segment([f"Work loop: p{project.id}: {project.name} — {len(results)} pending task(s)."])
    print_blank()

    for i, (task, _a) in enumerate(results, 1):
        created = format_local_time(task.created_utc).split(" ")[0]
        print(f"[{i}/{len(results)}] t{task.id}: {task.description} ({created})")

        action = _prompt_work_action()
        if action == "q":
            print_segment(["Work loop exited."])
            return
        if action == "s":
            continue
        if action in ("o", "n"):
            status = AssignmentStatus.OK if action == "o" else AssignmentStatus.NAH
            try:
                comment_raw = input("Comment (optional, Enter to skip): ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                comment_raw = ""
            comment = comment_raw if comment_raw else None
            resolve_assignment(db, project.id, task.id, status, comment)
            after_mutation()
            verb_label = "ok" if status == AssignmentStatus.OK else "nah"
            print(f"Marked {verb_label}.")
        print_blank()

    print_segment(["Work loop complete."])


def _work_by_task(
    db: Database, task: object, after_mutation: Callable[[], None]
) -> None:
    from .models import Task  # local import for type

    if not isinstance(task, Task):
        return

    results = pending_by_task(db, task.id)
    if not results:
        print_segment([f"No pending projects for t{task.id}: {task.description}."])
        return

    print_segment([
        f"Work loop: t{task.id}: {task.description}"
        f" — {len(results)} pending project(s)."
    ])
    print_blank()

    for i, (project, group, _a) in enumerate(results, 1):
        print(f"[{i}/{len(results)}] p{project.id}: {project.name} (group: {group.name})")

        action = _prompt_work_action()
        if action == "q":
            print_segment(["Work loop exited."])
            return
        if action == "s":
            continue
        if action in ("o", "n"):
            status = AssignmentStatus.OK if action == "o" else AssignmentStatus.NAH
            try:
                comment_raw = input("Comment (optional, Enter to skip): ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                comment_raw = ""
            comment = comment_raw if comment_raw else None
            resolve_assignment(db, project.id, task.id, status, comment)
            after_mutation()
            verb_label = "ok" if status == AssignmentStatus.OK else "nah"
            print(f"Marked {verb_label}.")
        print_blank()

    print_segment(["Work loop complete."])


def _prompt_work_action() -> str:
    """Prompt for work-loop action. Returns 'o', 'n', 's', or 'q'."""
    while True:
        try:
            raw = input("[o]k / [n]ah / [s]kip / [q]uit: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return "q"
        if raw in ("o", "ok"):
            return "o"
        if raw in ("n", "nah"):
            return "n"
        if raw in ("s", "skip"):
            return "s"
        if raw in ("q", "quit"):
            return "q"
        print("Please enter o, n, s, or q.")


# ---------------------------------------------------------------------------
# Token parsing helpers
# ---------------------------------------------------------------------------


def _parse_id_token(token: str, prefix: str) -> int | None:
    """Parse a token like 'g3', 'p12', 't7' → integer ID.

    Returns None if the token doesn't match the expected prefix+integer format.
    Also accepts bare prefix (e.g. 'g') with no digits → None.
    """
    token = token.lower()
    if not token.startswith(prefix):
        return None
    remainder = token[len(prefix):]
    if not remainder.isdigit():
        return None
    return int(remainder)


def _parse_pt_tokens(
    a: str, b: str
) -> tuple[int | None, int | None]:
    """Parse two tokens (in either order p<ID> t<ID> or t<ID> p<ID>).

    Returns (project_id, task_id).
    """
    a = a.lower()
    b = b.lower()

    if a.startswith("p") and b.startswith("t"):
        return _parse_id_token(a, "p"), _parse_id_token(b, "t")
    if a.startswith("t") and b.startswith("p"):
        return _parse_id_token(b, "p"), _parse_id_token(a, "t")
    return None, None
