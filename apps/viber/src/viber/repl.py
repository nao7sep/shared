"""REPL command loop, parser, and interactive flows."""

from __future__ import annotations

import shlex
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .errors import AssignmentNotFoundError, ViberError
from .formatter import (
    format_group,
    format_local_time,
    format_project,
    format_project_ref,
    format_task,
    format_task_ref,
    print_banner,
    print_blank,
    print_segment,
)
from .models import AssignmentStatus, Database, ProjectState, assignment_key
from .queries import pending_all, pending_by_project, pending_by_task
from .renderer import remove_check_page, render_check_pages
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
    update_assignment_comment,
    update_group_name,
    update_project_name,
    update_task_description,
)
from .store import save_database

_PROMPT = "> "
_BANNER_LINES = (
    "Viber — cross-project maintenance tracker",
    "Type 'help' for commands. Type 'exit' or 'quit' to leave.",
)
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
_COMMAND_EXIT = "exit"
_COMMAND_QUIT = "quit"
_VERB_OK = "ok"
_VERB_NAH = "nah"
_COMMAND_CANCEL_CONFIRM = "y"
_COMMAND_CANCEL_CONFIRM_LONG = "yes"
_READLINE_BIND_ENABLE_KEYPAD = "set enable-keypad on"
_READLINE_BIND_EMACS = "set editing-mode emacs"
_REPL_HISTORY_SUFFIX = ".history"

_TOKEN_GROUP_PREFIX = "g"
_TOKEN_PROJECT_PREFIX = "p"
_TOKEN_TASK_PREFIX = "t"
_PROJECT_STATE_ACTIVE = "active"
_PROJECT_STATE_SUSPENDED = "suspended"
_PROJECT_STATE_DEPRECATED = "deprecated"

_HELP_TEXT = """\
create group <name>                                c g <name>
create project <name> g<ID>                        c p <name> g<ID>
create task <description> [g<ID>]                  c t <description> [g<ID>]

read groups                                        r groups
read projects                                      r projects
read tasks                                         r tasks
read g<ID>                                         r g<ID>
read p<ID>                                         r p<ID>
read t<ID>                                         r t<ID>

update g<ID> <new-name>                            u g<ID> <new-name>
update p<ID> name <new-name>                       u p<ID> name <new-name>
update p<ID> state <active|suspended|deprecated>   u p<ID> state <state>
update p<ID> <active|suspended|deprecated>         u p<ID> <state>
update t<ID> <new-description>                     u t<ID> <new-description>
update p<ID> t<ID> [comment]                       u p<ID> t<ID> [comment]
update t<ID> p<ID> [comment]                       u t<ID> p<ID> [comment]

delete g<ID>                                       d g<ID>
delete p<ID>                                       d p<ID>
delete t<ID>                                       d t<ID>

view                                               v       (all pending)
view p<ID>                                         v p<ID> (pending tasks for project)
view t<ID>                                         v t<ID> (pending projects for task)

ok p<ID> t<ID>                                     o p<ID> t<ID>
ok t<ID> p<ID>                                     o t<ID> p<ID>
nah p<ID> t<ID>                                    n p<ID> t<ID>

work p<ID>                                         w p<ID> (iterate pending tasks)
work t<ID>                                         w t<ID> (iterate pending projects)

help
exit | quit"""

readline_module: Any
try:
    import readline as readline_module
except ImportError:  # pragma: no cover - platform-dependent
    readline_module = None
readline: Any = readline_module

MutationHook = Callable[[set[int] | None, set[str] | None], None]


def run_repl(
    db: Database,
    data_path: Path,
    check_path: Path | None,
) -> None:
    """Run the interactive REPL loop until exit/quit."""

    history_path = data_path.with_suffix(f"{data_path.suffix}{_REPL_HISTORY_SUFFIX}")
    _configure_line_editor(history_path)

    def after_mutation(
        affected_group_ids: set[int] | None,
        removed_group_names: set[str] | None,
    ) -> None:
        save_database(db, data_path)
        if check_path is None:
            return
        if removed_group_names:
            for group_name in sorted(removed_group_names):
                remove_check_page(check_path, group_name)
        if affected_group_ids is None:
            render_check_pages(db, check_path)
            return
        if affected_group_ids:
            render_check_pages(db, check_path, affected_group_ids)

    print_banner(_BANNER_LINES)

    try:
        while True:
            try:
                raw = input(_PROMPT)
            except (EOFError, KeyboardInterrupt):
                print()
                continue

            line = raw.strip()
            if not line:
                continue
            _record_history_entry(line)

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

            if verb in (_COMMAND_EXIT, _COMMAND_QUIT):
                print_segment(["Goodbye."], trailing_blank=False)
                break

            try:
                _dispatch(verb, args, db, after_mutation)
            except ViberError as exc:
                print_segment([f"Error: {exc}"])
            except Exception as exc:  # noqa: BLE001
                print_segment([f"Unexpected error: {exc}"])
    finally:
        _save_line_editor_history(history_path)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


def _dispatch(
    verb: str,
    args: list[str],
    db: Database,
    after_mutation: MutationHook,
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
    args: list[str], db: Database, after_mutation: MutationHook
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
        after_mutation({group.id}, None)
        print_segment([f"Created group: {group.name} (g{group.id})."])

    elif kind in ("project", "p"):
        if len(args) < 3:
            print_segment(["Usage: create project <name> g<ID>"])
            return
        group_token = args[-1]
        group_id = _parse_id_token(group_token, _TOKEN_GROUP_PREFIX)
        if group_id is None:
            print_segment([f"Invalid group reference '{group_token}'. Expected g<ID>."])
            return
        name = " ".join(args[1:-1])
        group = get_group(db, group_id)
        project = create_project(db, name, group_id)
        after_mutation({group.id}, None)
        print_segment([
            f"Created project: {project.name} (p{project.id}) in group {group.name} (g{group.id})."
        ])

    elif kind in ("task", "t"):
        if len(args) < 2:
            print_segment(["Usage: create task <description> [g<ID>]"])
            return
        task_group_id: int | None = None
        desc_tokens = args[1:]
        # Check if last token is a group reference
        if desc_tokens and _parse_id_token(desc_tokens[-1], _TOKEN_GROUP_PREFIX) is not None:
            task_group_id = _parse_id_token(desc_tokens[-1], _TOKEN_GROUP_PREFIX)
            desc_tokens = desc_tokens[:-1]
        if not desc_tokens:
            print_segment(["Task description cannot be empty."])
            return
        description = " ".join(desc_tokens)
        task = create_task(db, description, task_group_id)
        after_mutation(_task_affected_group_ids(db, task.group_id), None)
        if task.group_id is None:
            scope = "all groups"
        else:
            scope_group = get_group(db, task.group_id)
            scope = f"group {scope_group.name} (g{scope_group.id})"
        print_segment([f"Created task: {task.description} (t{task.id}) for {scope}."])

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
                    lines.append(f"{p.name} (p{p.id}) [{p.state.value}] (group: ?)")
            print_segment(lines)

    elif token in ("tasks", "t"):
        tasks = list_tasks(db)
        if not tasks:
            print_segment(["No tasks."])
        else:
            print_segment([format_task(t, db) for t in tasks])

    elif token.startswith("g"):
        gid = _parse_id_token(token, _TOKEN_GROUP_PREFIX)
        if gid is None:
            print_segment([f"Invalid group reference '{token}'."])
            return
        group = get_group(db, gid)
        print_segment([format_group(group)])

    elif token.startswith("p"):
        pid = _parse_id_token(token, _TOKEN_PROJECT_PREFIX)
        if pid is None:
            print_segment([f"Invalid project reference '{token}'."])
            return
        project = get_project(db, pid)
        group_map = {g.id: g for g in db.groups}
        maybe_group = group_map.get(project.group_id)
        if maybe_group is not None:
            print_segment([format_project(project, maybe_group)])
        else:
            print_segment([f"{project.name} (p{project.id}) [{project.state.value}]"])

    elif token.startswith("t"):
        tid = _parse_id_token(token, _TOKEN_TASK_PREFIX)
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
    args: list[str], db: Database, after_mutation: MutationHook
) -> None:
    if not args:
        print_segment([
            "Usage:",
            "  update g<ID> <new-name>",
            "  update p<ID> name <new-name>",
            "  update p<ID> state <active|suspended|deprecated>",
            "  update p<ID> t<ID> [comment]",
            "  update t<ID> <new-description>",
            "  update t<ID> p<ID> [comment]",
        ])
        return

    token = args[0].lower()

    if token.startswith("g"):
        gid = _parse_id_token(token, _TOKEN_GROUP_PREFIX)
        if gid is None:
            print_segment([f"Invalid group reference '{token}'."])
            return
        if len(args) < 2:
            print_segment(["Usage: update g<ID> <new-name>"])
            return
        new_name = " ".join(args[1:]).strip()
        if not new_name:
            print_segment(["Group name cannot be empty."])
            return
        old_name = get_group(db, gid).name
        group = update_group_name(db, gid, new_name)
        removed_names = {old_name} if old_name != group.name else None
        after_mutation({group.id}, removed_names)
        if old_name == group.name:
            print_segment([f"Group name unchanged: {group.name} (g{group.id})."])
        else:
            print_segment([
                f"Renamed group: {old_name} (g{group.id}) -> "
                f"{group.name} (g{group.id})."
            ])
        return

    if token.startswith("p"):
        pid = _parse_id_token(token, _TOKEN_PROJECT_PREFIX)
        if pid is None:
            print_segment([f"Invalid project reference '{token}'."])
            return
        if len(args) < 2:
            print_segment([
                "Usage:",
                "  update p<ID> name <new-name>",
                "  update p<ID> state <active|suspended|deprecated>",
                "  update p<ID> t<ID> [comment]",
            ])
            return
        second = args[1].lower()
        assignment_tid = _parse_id_token(second, _TOKEN_TASK_PREFIX)
        if assignment_tid is not None:
            comment = _join_tokens(args[2:])
            update_assignment_comment(db, pid, assignment_tid, comment or None)
            after_mutation(set(), None)
            if comment:
                print_segment([
                    f"Updated assignment comment for p{pid} + t{assignment_tid}: {comment}"
                ])
            else:
                print_segment([f"Cleared assignment comment for p{pid} + t{assignment_tid}."])
            return

        if second == "name":
            if len(args) < 3:
                print_segment(["Usage: update p<ID> name <new-name>"])
                return
            new_name = _join_tokens(args[2:])
            if not new_name:
                print_segment(["Project name cannot be empty."])
                return
            old_name = get_project(db, pid).name
            project = update_project_name(db, pid, new_name)
            after_mutation({project.group_id}, None)
            if old_name == project.name:
                print_segment([f"Project name unchanged: {project.name} (p{project.id})."])
            else:
                print_segment([
                    f"Renamed project: {old_name} (p{project.id}) -> "
                    f"{project.name} (p{project.id})."
                ])
            return

        if second == "state":
            if len(args) < 3:
                print_segment(["Usage: update p<ID> state <active|suspended|deprecated>"])
                return
            state_str = args[2].lower()
        else:
            state_str = second

        state_map = {
            _PROJECT_STATE_ACTIVE: ProjectState.ACTIVE,
            _PROJECT_STATE_SUSPENDED: ProjectState.SUSPENDED,
            _PROJECT_STATE_DEPRECATED: ProjectState.DEPRECATED,
        }
        if state_str in state_map:
            project = set_project_state(db, pid, state_map[state_str])
            after_mutation({project.group_id}, None)
            print_segment([
                f"Updated project state: {project.name} (p{project.id}) -> {state_str}."
            ])
            return

        # Fallback: treat update p<ID> <name...> as a rename command.
        new_name = _join_tokens(args[1:])
        if not new_name:
            print_segment(["Project name cannot be empty."])
            return
        old_name = get_project(db, pid).name
        project = update_project_name(db, pid, new_name)
        after_mutation({project.group_id}, None)
        if old_name == project.name:
            print_segment([f"Project name unchanged: {project.name} (p{project.id})."])
        else:
            print_segment([
                f"Renamed project: {old_name} (p{project.id}) -> "
                f"{project.name} (p{project.id})."
            ])
        return

    elif token.startswith("t"):
        tid = _parse_id_token(token, _TOKEN_TASK_PREFIX)
        if tid is None:
            print_segment([f"Invalid task reference '{token}'."])
            return
        if len(args) >= 2:
            maybe_pid = _parse_id_token(args[1].lower(), _TOKEN_PROJECT_PREFIX)
            if maybe_pid is not None:
                comment = _join_tokens(args[2:])
                update_assignment_comment(db, maybe_pid, tid, comment or None)
                after_mutation(set(), None)
                if comment:
                    print_segment([
                        f"Updated assignment comment for p{maybe_pid} + t{tid}: {comment}"
                    ])
                else:
                    print_segment([f"Cleared assignment comment for p{maybe_pid} + t{tid}."])
                return
            new_desc = _join_tokens(args[1:])
            if not new_desc:
                print_segment(["Task description cannot be empty."])
                return
            task = update_task_description(db, tid, new_desc)
            after_mutation(_task_affected_group_ids(db, task.group_id), None)
            print_segment([f"Updated task: {format_task_ref(task)}."])
            return

        task = get_task(db, tid)
        print_segment([f"Current task description: {task.description}"], trailing_blank=False)
        try:
            new_desc = input("New description: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            print_segment(["Update cancelled."])
            return
        if not new_desc:
            print_segment(["Task description cannot be empty. Update cancelled."])
            return
        task = update_task_description(db, tid, new_desc)
        after_mutation(_task_affected_group_ids(db, task.group_id), None)
        print_segment([f"Updated task: {format_task_ref(task)}."])

    else:
        print_segment([f"Unknown target '{token}'. Expected g<ID>, p<ID>, or t<ID>."])


def _cmd_delete(
    args: list[str], db: Database, after_mutation: MutationHook
) -> None:
    if not args:
        print_segment(["Usage: delete g<ID>|p<ID>|t<ID>"])
        return

    token = args[0].lower()

    if token.startswith("g"):
        gid = _parse_id_token(token, _TOKEN_GROUP_PREFIX)
        if gid is None:
            print_segment([f"Invalid group reference '{token}'."])
            return
        group = delete_group(db, gid)
        after_mutation(set(), {group.name})
        print_segment([f"Deleted group: {group.name} (g{group.id})."])

    elif token.startswith("p"):
        pid = _parse_id_token(token, _TOKEN_PROJECT_PREFIX)
        if pid is None:
            print_segment([f"Invalid project reference '{token}'."])
            return
        project = delete_project(db, pid)
        after_mutation({project.group_id}, None)
        print_segment([f"Deleted project: {project.name} (p{project.id})."])

    elif token.startswith("t"):
        tid = _parse_id_token(token, _TOKEN_TASK_PREFIX)
        if tid is None:
            print_segment([f"Invalid task reference '{token}'."])
            return
        task = delete_task(db, tid)
        after_mutation(_task_affected_group_ids(db, task.group_id), None)
        print_segment([f"Deleted task: {task.description} (t{task.id})."])

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
                    f"{format_project_ref(e.project)} + {format_task_ref(e.task)}"
                )
            print_segment(lines)
        return

    token = args[0].lower()

    if token.startswith("p"):
        pid = _parse_id_token(token, _TOKEN_PROJECT_PREFIX)
        if pid is None:
            print_segment([f"Invalid project reference '{token}'."])
            return
        project = get_project(db, pid)
        results = pending_by_project(db, pid)
        if not results:
            print_segment([f"No pending tasks for {format_project_ref(project)}."])
        else:
            lines = [f"Pending tasks for {format_project_ref(project)}:"]
            for task, _a in results:
                created = format_local_time(task.created_utc).split(" ")[0]
                lines.append(f"  {format_task_ref(task)} ({created})")
            print_segment(lines)

    elif token.startswith("t"):
        tid = _parse_id_token(token, _TOKEN_TASK_PREFIX)
        if tid is None:
            print_segment([f"Invalid task reference '{token}'."])
            return
        task = get_task(db, tid)
        task_results = pending_by_task(db, tid)
        if not task_results:
            print_segment([f"No pending projects for {format_task_ref(task)}."])
        else:
            lines = [f"Pending projects for {format_task_ref(task)}:"]
            for project, group, _a in task_results:
                lines.append(f"  {format_project_ref(project)} (group: {group.name})")
            print_segment(lines)

    else:
        print_segment([f"Unknown target '{token}'. Expected p<ID> or t<ID>."])


def _cmd_resolve(
    args: list[str],
    db: Database,
    status: AssignmentStatus,
    after_mutation: MutationHook,
) -> None:
    """Handle ok/nah with either p<ID> t<ID> or t<ID> p<ID> token order."""
    if len(args) < 2:
        verb = _VERB_OK if status == AssignmentStatus.OK else _VERB_NAH
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
    verb_label = _VERB_OK if status == AssignmentStatus.OK else _VERB_NAH

    print_segment([
        f"Resolving as '{verb_label}':",
        f"  Project: {format_project_ref(project)}",
        f"  Task:    {format_task_ref(task)}",
        f"  Current: {assignment.status.value}",
    ], trailing_blank=False)

    try:
        confirm = input("Confirm? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        print_segment(["Cancelled."])
        return

    if confirm not in (_COMMAND_CANCEL_CONFIRM, _COMMAND_CANCEL_CONFIRM_LONG):
        print_segment(["Cancelled."])
        return

    try:
        comment_raw = input("Comment (optional, Enter to skip): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        comment_raw = ""

    comment = comment_raw if comment_raw else None
    resolve_assignment(db, pid, tid, status, comment)
    after_mutation({project.group_id}, None)
    print_segment([
        f"Updated assignment: {project.name} (p{project.id}) + {task.description} (t{task.id})"
        f" -> {verb_label}."
    ])


def _cmd_work(
    args: list[str], db: Database, after_mutation: MutationHook
) -> None:
    if not args:
        print_segment(["Usage: work p<ID> | work t<ID>"])
        return

    token = args[0].lower()

    if token.startswith("p"):
        pid = _parse_id_token(token, _TOKEN_PROJECT_PREFIX)
        if pid is None:
            print_segment([f"Invalid project reference '{token}'."])
            return
        project = get_project(db, pid)
        _work_by_project(db, project, after_mutation)

    elif token.startswith("t"):
        tid = _parse_id_token(token, _TOKEN_TASK_PREFIX)
        if tid is None:
            print_segment([f"Invalid task reference '{token}'."])
            return
        task = get_task(db, tid)
        _work_by_task(db, task, after_mutation)

    else:
        print_segment([f"Unknown target '{token}'. Expected p<ID> or t<ID>."])


def _work_by_project(
    db: Database, project: object, after_mutation: MutationHook
) -> None:
    from .models import Project  # local import for type

    if not isinstance(project, Project):
        return

    results = pending_by_project(db, project.id)
    if not results:
        print_segment([f"No pending tasks for {format_project_ref(project)}."])
        return

    print_segment([
        f"Work loop: {project.name} (p{project.id}) has {len(results)} pending task(s)."
    ], trailing_blank=False)
    print_blank()

    for i, (task, _a) in enumerate(results, 1):
        created = format_local_time(task.created_utc).split(" ")[0]
        print(f"[{i}/{len(results)}] {format_task_ref(task)} ({created})")

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
            after_mutation({project.group_id}, None)
            verb_label = _VERB_OK if status == AssignmentStatus.OK else _VERB_NAH
            print(f"Updated assignment to {verb_label}.")
        print_blank()

    print_segment(["Work loop complete."])


def _work_by_task(
    db: Database, task: object, after_mutation: MutationHook
) -> None:
    from .models import Task  # local import for type

    if not isinstance(task, Task):
        return

    results = pending_by_task(db, task.id)
    if not results:
        print_segment([f"No pending projects for {format_task_ref(task)}."])
        return

    print_segment([
        f"Work loop: {task.description} (t{task.id}) has {len(results)} pending project(s)."
    ], trailing_blank=False)
    print_blank()

    for i, (project, group, _a) in enumerate(results, 1):
        print(f"[{i}/{len(results)}] {format_project_ref(project)} (group: {group.name})")

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
            after_mutation({project.group_id}, None)
            verb_label = _VERB_OK if status == AssignmentStatus.OK else _VERB_NAH
            print(f"Updated assignment to {verb_label}.")
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
# Output and input helpers
# ---------------------------------------------------------------------------


def _join_tokens(tokens: list[str]) -> str:
    return " ".join(tokens).strip()


def _task_affected_group_ids(db: Database, group_id: int | None) -> set[int]:
    if group_id is None:
        return {g.id for g in db.groups}
    return {group_id}


def _configure_line_editor(history_path: Path) -> None:
    if readline is None:
        return
    try:
        readline.parse_and_bind(_READLINE_BIND_ENABLE_KEYPAD)
        readline.parse_and_bind(_READLINE_BIND_EMACS)
    except Exception:  # noqa: BLE001
        pass
    try:
        if history_path.exists():
            readline.read_history_file(str(history_path))
    except Exception:  # noqa: BLE001
        pass


def _record_history_entry(line: str) -> None:
    if readline is None:
        return
    try:
        last_index = readline.get_current_history_length()
        if last_index > 0 and readline.get_history_item(last_index) == line:
            return
        readline.add_history(line)
    except Exception:  # noqa: BLE001
        return


def _save_line_editor_history(history_path: Path) -> None:
    if readline is None:
        return
    try:
        history_path.parent.mkdir(parents=True, exist_ok=True)
        readline.write_history_file(str(history_path))
    except Exception:  # noqa: BLE001
        return


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

    if a.startswith(_TOKEN_PROJECT_PREFIX) and b.startswith(_TOKEN_TASK_PREFIX):
        return _parse_id_token(a, _TOKEN_PROJECT_PREFIX), _parse_id_token(b, _TOKEN_TASK_PREFIX)
    if a.startswith(_TOKEN_TASK_PREFIX) and b.startswith(_TOKEN_PROJECT_PREFIX):
        return _parse_id_token(b, _TOKEN_PROJECT_PREFIX), _parse_id_token(a, _TOKEN_TASK_PREFIX)
    return None, None
