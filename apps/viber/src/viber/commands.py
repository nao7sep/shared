"""Command execution layer for parsed REPL commands."""

from __future__ import annotations

from collections.abc import Callable

from .command_parser import (
    CreateGroupCommand,
    CreateProjectCommand,
    CreateTaskCommand,
    DeleteEntityCommand,
    HelpCommand,
    ParsedCommand,
    ReadCollectionCommand,
    ReadEntityCommand,
    ResolveAssignmentCommand,
    UndoAssignmentCommand,
    UndoEntityCommand,
    UpdateAssignmentCommentCommand,
    UpdateGroupNameCommand,
    UpdateProjectNameCommand,
    UpdateProjectStateCommand,
    UpdateTaskDescriptionCommand,
    UpdateTaskDescriptionPromptCommand,
    ViewAllCommand,
    ViewEntityCommand,
    WorkEntityCommand,
)
from .errors import AssignmentNotFoundError
from .formatter import (
    format_group,
    format_group_ref,
    format_project,
    format_project_ref,
    format_task,
    format_task_ref,
    print_segment,
)
from .models import Assignment, AssignmentStatus, Database, assignment_key
from .queries import pending_all, pending_by_project, pending_by_task
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
    undo_assignment,
    update_assignment_comment,
    update_group_name,
    update_project_name,
    update_task_description,
)

MutationHook = Callable[[set[int] | None, set[str] | None], None]

_HELP_TEXT = """\
create group <name>                                c g <name>
create project <name> g<ID>                        c p <name> g<ID>
create task <description> <all|g<ID>>              c t <description> <all|g<ID>>

read groups                                        r groups
read projects                                      r projects
read tasks                                         r tasks
read g<ID>                                         r g<ID>
read p<ID>                                         r p<ID>
read t<ID>                                         r t<ID>

update g<ID> <new-name>                            u g<ID> <new-name>
update p<ID> name <new-name>                       u p<ID> name <new-name>
update p<ID> state <active|suspended|deprecated>   u p<ID> state <state>
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
nah t<ID> p<ID>                                    n t<ID> p<ID>

undo p<ID> t<ID>                                   z p<ID> t<ID>
undo t<ID> p<ID>                                   z t<ID> p<ID>
undo g<ID>                                         z g<ID>
undo p<ID>                                         z p<ID>
undo t<ID>                                         z t<ID>

work p<ID>                                         w p<ID> (iterate pending tasks)
work t<ID>                                         w t<ID> (iterate pending projects)

help
exit | quit"""


def execute_command(
    command: ParsedCommand,
    db: Database,
    after_mutation: MutationHook,
) -> None:
    if isinstance(command, HelpCommand):
        print_segment(_HELP_TEXT.splitlines())
        return

    if isinstance(command, CreateGroupCommand):
        group = create_group(db, command.name)
        after_mutation({group.id}, None)
        print_segment([f"Created group: {group.name} (g{group.id})"])
        return

    if isinstance(command, CreateProjectCommand):
        group = get_group(db, command.group_id)
        project = create_project(db, command.name, command.group_id)
        after_mutation({group.id}, None)
        print_segment([
            f"Created project: {project.name} (p{project.id}) in group {group.name} (g{group.id})"
        ])
        return

    if isinstance(command, CreateTaskCommand):
        task = create_task(db, command.description, command.group_id)
        after_mutation(_task_affected_group_ids(db, task.group_id), None)
        if task.group_id is None:
            scope = "all groups"
        else:
            scope_group = get_group(db, task.group_id)
            scope = f"group {scope_group.name} (g{scope_group.id})"
        print_segment([f"Created task: {task.description} (t{task.id}) for {scope}"])
        return

    if isinstance(command, ReadCollectionCommand):
        _exec_read_collection(command, db)
        return

    if isinstance(command, ReadEntityCommand):
        _exec_read_entity(command, db)
        return

    if isinstance(command, UpdateGroupNameCommand):
        old_name = get_group(db, command.group_id).name
        group = update_group_name(db, command.group_id, command.new_name)
        removed_names = {old_name} if old_name != group.name else None
        after_mutation({group.id}, removed_names)
        if old_name == group.name:
            print_segment([f"Group name unchanged: {group.name} (g{group.id})"])
        else:
            print_segment([
                f"Renamed group: {old_name} (g{group.id}) -> "
                f"{group.name} (g{group.id})"
            ])
        return

    if isinstance(command, UpdateProjectNameCommand):
        old_name = get_project(db, command.project_id).name
        project = update_project_name(db, command.project_id, command.new_name)
        after_mutation({project.group_id}, None)
        if old_name == project.name:
            print_segment([f"Project name unchanged: {project.name} (p{project.id})"])
        else:
            print_segment([
                f"Renamed project: {old_name} (p{project.id}) -> "
                f"{project.name} (p{project.id})"
            ])
        return

    if isinstance(command, UpdateProjectStateCommand):
        project = set_project_state(db, command.project_id, command.new_state)
        after_mutation({project.group_id}, None)
        print_segment([
            f"Updated project state: {project.name} (p{project.id}) -> {command.new_state.value}"
        ])
        return

    if isinstance(command, UpdateAssignmentCommentCommand):
        update_assignment_comment(db, command.project_id, command.task_id, command.comment)
        after_mutation(set(), None)
        if command.comment:
            print_segment([
                "Updated assignment comment for "
                f"p{command.project_id} | t{command.task_id}: {command.comment}"
            ])
        else:
            print_segment([
                f"Cleared assignment comment for p{command.project_id} | t{command.task_id}"
            ])
        return

    if isinstance(command, UpdateTaskDescriptionCommand):
        task = update_task_description(db, command.task_id, command.new_description)
        after_mutation(_task_affected_group_ids(db, task.group_id), None)
        print_segment([f"Updated task: {format_task_ref(task)}"])
        return

    if isinstance(command, UpdateTaskDescriptionPromptCommand):
        task = get_task(db, command.task_id)
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
        task = update_task_description(db, command.task_id, new_desc)
        after_mutation(_task_affected_group_ids(db, task.group_id), None)
        print_segment([f"Updated task: {format_task_ref(task)}"])
        return

    if isinstance(command, DeleteEntityCommand):
        _exec_delete(command, db, after_mutation)
        return

    if isinstance(command, ViewAllCommand):
        entries = pending_all(db)
        if not entries:
            print_segment(["Vibe is good. No pending assignments."])
        else:
            lines = [
                (
                    f"{format_project_ref(e.project)}"
                    f" | {format_group_ref(e.group)}"
                    f" | {format_task_ref(e.task)}"
                )
                for e in entries
            ]
            print_segment(lines)
        return

    if isinstance(command, ViewEntityCommand):
        _exec_view_entity(command, db)
        return

    if isinstance(command, ResolveAssignmentCommand):
        _exec_resolve(command, db, after_mutation)
        return

    if isinstance(command, WorkEntityCommand):
        _exec_work(command, db, after_mutation)
        return

    if isinstance(command, UndoAssignmentCommand):
        _exec_undo_assignment(command, db, after_mutation)
        return

    if isinstance(command, UndoEntityCommand):
        _exec_undo_entity(command, db, after_mutation)
        return

    print_segment(["Unsupported command."])


def _exec_read_collection(command: ReadCollectionCommand, db: Database) -> None:
    if command.kind == "groups":
        groups = list_groups(db)
        if not groups:
            print_segment(["No groups."])
        else:
            print_segment([format_group(g) for g in groups])
        return

    if command.kind == "projects":
        projects = list_projects(db)
        if not projects:
            print_segment(["No projects."])
            return
        lines = [format_project(project, get_group(db, project.group_id)) for project in projects]
        print_segment(lines)
        return

    tasks = list_tasks(db)
    if not tasks:
        print_segment(["No tasks."])
    else:
        print_segment([format_task(t, db) for t in tasks])


def _exec_read_entity(command: ReadEntityCommand, db: Database) -> None:
    if command.kind == "group":
        group = get_group(db, command.entity_id)
        print_segment([format_group(group)])
        return

    if command.kind == "project":
        project = get_project(db, command.entity_id)
        group = get_group(db, project.group_id)
        print_segment([format_project(project, group)])
        return

    task = get_task(db, command.entity_id)
    print_segment([format_task(task, db)])


def _exec_delete(command: DeleteEntityCommand, db: Database, after_mutation: MutationHook) -> None:
    if command.kind == "group":
        group = get_group(db, command.entity_id)
        if not _confirm_action([format_group(group)]):
            return
        group = delete_group(db, command.entity_id)
        after_mutation(None, {group.name})
        print_segment([f"Deleted group: {group.name} (g{group.id})"])
        return

    if command.kind == "project":
        project = get_project(db, command.entity_id)
        group = get_group(db, project.group_id)
        summary = format_project(project, group)
        if not _confirm_action([summary]):
            return
        project = delete_project(db, command.entity_id)
        after_mutation(None, None)
        print_segment([f"Deleted project: {project.name} (p{project.id})"])
        return

    task = get_task(db, command.entity_id)
    if not _confirm_action([format_task(task, db)]):
        return
    task = delete_task(db, command.entity_id)
    after_mutation(_task_affected_group_ids(db, task.group_id), None)
    print_segment([f"Deleted task: {task.description} (t{task.id})"])


def _exec_view_entity(command: ViewEntityCommand, db: Database) -> None:
    if command.kind == "project":
        project = get_project(db, command.entity_id)
        group = get_group(db, project.group_id)
        header = f"{format_project_ref(project)} | {format_group_ref(group)}"
        results = pending_by_project(db, command.entity_id)
        if not results:
            print_segment([header, "No pending tasks."])
            return
        lines: list[str] = [header]
        for task, _assignment in results:
            lines.append(format_task_ref(task))
        print_segment(lines)
        return

    task = get_task(db, command.entity_id)
    task_results = pending_by_task(db, command.entity_id)
    header = format_task_ref(task)
    if not task_results:
        print_segment([header, "No pending projects."])
        return
    lines = [header]
    for project, group, _assignment in task_results:
        lines.append(f"{format_project_ref(project)} | {format_group_ref(group)}")
    print_segment(lines)


def _exec_resolve(
    command: ResolveAssignmentCommand,
    db: Database,
    after_mutation: MutationHook,
) -> None:
    project = get_project(db, command.project_id)
    task = get_task(db, command.task_id)

    key = assignment_key(command.project_id, command.task_id)
    if key not in db.assignments:
        raise AssignmentNotFoundError(command.project_id, command.task_id)

    assignment = db.assignments[key]
    verb_label = "ok" if command.status == AssignmentStatus.OK else "nah"

    print_segment(
        [
            f"Resolving as '{verb_label}':",
            f"  Project: {format_project_ref(project)}",
            f"  Task:    {format_task_ref(task)}",
            f"  Current: {assignment.status.value}",
        ],
        trailing_blank=False,
    )

    try:
        comment_raw = input("Comment (optional, Enter to skip): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        print_segment(["Cancelled."])
        return

    comment = comment_raw if comment_raw else None
    resolve_assignment(db, command.project_id, command.task_id, command.status, comment)
    after_mutation({project.group_id}, None)
    print_segment([
        f"Updated assignment: {format_project_ref(project)} | {format_task_ref(task)}"
        f" | {verb_label}"
    ])


def _exec_work(command: WorkEntityCommand, db: Database, after_mutation: MutationHook) -> None:
    if command.kind == "project":
        project = get_project(db, command.entity_id)
        _work_by_project(db, project, after_mutation)
        return

    task = get_task(db, command.entity_id)
    _work_by_task(db, task, after_mutation)


def _work_by_project(
    db: Database, project: object, after_mutation: MutationHook
) -> None:
    from .models import Project  # local import for type

    if not isinstance(project, Project):
        return

    initial_results = pending_by_project(db, project.id)
    if not initial_results:
        print_segment([f"No pending tasks for {format_project_ref(project)}"])
        return

    while True:
        results = pending_by_project(db, project.id)
        if not results:
            print_segment(["Work loop complete."])
            return

        lines = [f"Work loop: {format_project_ref(project)}"]
        for i, (task, _assignment) in enumerate(results, 1):
            lines.append(f"{i}. {format_task(task, db)}")
        print_segment(lines, trailing_blank=False)

        selected = _prompt_work_item_selection(len(results))
        if selected is None:
            print_segment(["Work loop exited."])
            return

        task = results[selected - 1][0]
        status = _prompt_work_resolution_status()
        if status is None:
            print_segment(["Cancelled."])
            continue

        cancelled, comment = _prompt_optional_comment()
        if cancelled:
            print_segment(["Cancelled."])
            continue

        resolve_assignment(db, project.id, task.id, status, comment)
        after_mutation({project.group_id}, None)
        verb_label = "ok" if status == AssignmentStatus.OK else "nah"
        print_segment([
            (
                f"Updated assignment: {format_project_ref(project)}"
                f" | {format_task_ref(task)}"
                f" | {verb_label}"
            )
        ])


def _work_by_task(
    db: Database, task: object, after_mutation: MutationHook
) -> None:
    from .models import Task  # local import for type

    if not isinstance(task, Task):
        return

    initial_results = pending_by_task(db, task.id)
    if not initial_results:
        print_segment([f"No pending projects for {format_task_ref(task)}"])
        return

    while True:
        results = pending_by_task(db, task.id)
        if not results:
            print_segment(["Work loop complete."])
            return

        lines = [f"Work loop: {format_task_ref(task)}"]
        for i, (project, group, _assignment) in enumerate(results, 1):
            lines.append(f"{i}. {format_project(project, group)}")
        print_segment(lines, trailing_blank=False)

        selected = _prompt_work_item_selection(len(results))
        if selected is None:
            print_segment(["Work loop exited."])
            return

        project = results[selected - 1][0]
        status = _prompt_work_resolution_status()
        if status is None:
            print_segment(["Cancelled."])
            continue

        cancelled, comment = _prompt_optional_comment()
        if cancelled:
            print_segment(["Cancelled."])
            continue

        resolve_assignment(db, project.id, task.id, status, comment)
        after_mutation({project.group_id}, None)
        verb_label = "ok" if status == AssignmentStatus.OK else "nah"
        print_segment([
            (
                f"Updated assignment: {format_project_ref(project)}"
                f" | {format_task_ref(task)}"
                f" | {verb_label}"
            )
        ])


def _prompt_work_item_selection(total_items: int) -> int | None:
    """Prompt for item index or quit. Returns 1-based index or None (quit/cancel)."""
    while True:
        try:
            raw = input(f"Select item 1-{total_items} or q to quit: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        if raw in ("q", "quit"):
            return None
        if raw.isdigit():
            selected = int(raw)
            if 1 <= selected <= total_items:
                return selected
        print(f"Please enter a number between 1 and {total_items}, or q.")


def _prompt_work_resolution_status() -> AssignmentStatus | None:
    """Prompt for resolution action. Returns status or None for cancel."""
    while True:
        try:
            raw = input("Action [o]k / [n]ah / [c]ancel: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        if raw in ("o", "ok"):
            return AssignmentStatus.OK
        if raw in ("n", "nah"):
            return AssignmentStatus.NAH
        if raw in ("c", "cancel"):
            return None
        print("Please enter o, n, or c.")


def _prompt_optional_comment() -> tuple[bool, str | None]:
    """Prompt for optional comment. Returns (cancelled, comment)."""
    try:
        comment_raw = input("Comment (optional, Enter for none): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return True, None
    return False, (comment_raw if comment_raw else None)


def _confirm_action(lines: list[str]) -> bool:
    print_segment(lines, trailing_blank=False)
    try:
        confirm = input("Type 'yes' to confirm delete [N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        print_segment(["Cancelled."])
        return False
    if confirm != "yes":
        print_segment(["Cancelled."])
        return False
    return True


def _exec_undo_assignment(
    command: UndoAssignmentCommand,
    db: Database,
    after_mutation: MutationHook,
) -> None:
    project = get_project(db, command.project_id)
    task = get_task(db, command.task_id)

    key = assignment_key(command.project_id, command.task_id)
    if key not in db.assignments:
        raise AssignmentNotFoundError(command.project_id, command.task_id)

    assignment = db.assignments[key]
    if assignment.status == AssignmentStatus.PENDING:
        print_segment(["Assignment is already pending."])
        return

    undo_assignment(db, command.project_id, command.task_id)
    after_mutation({project.group_id}, None)
    print_segment([
        f"Undone: {format_project_ref(project)} | {format_task_ref(task)}"
    ])


def _exec_undo_entity(
    command: UndoEntityCommand,
    db: Database,
    after_mutation: MutationHook,
) -> None:
    targets: list[Assignment]
    label: str
    affected_group_ids: set[int]

    if command.kind == "group":
        group = get_group(db, command.entity_id)
        project_ids = {p.id for p in db.projects if p.group_id == group.id}
        targets = _find_resolved_assignments(db, project_ids=project_ids)
        label = f"group {format_group_ref(group)}"
        affected_group_ids = {group.id}
    elif command.kind == "project":
        project = get_project(db, command.entity_id)
        targets = _find_resolved_assignments(db, project_ids={project.id})
        label = f"project {format_project_ref(project)}"
        affected_group_ids = {project.group_id}
    else:
        task = get_task(db, command.entity_id)
        targets = _find_resolved_assignments(db, task_ids={task.id})
        label = f"task {format_task_ref(task)}"
        affected_group_ids = {
            get_project(db, a.project_id).group_id for a in targets
        }

    if not targets:
        print_segment([f"No resolved assignments for {label}."])
        return

    lines = [f"Undo {len(targets)} assignment(s) for {label}:"]
    for a in targets:
        p = get_project(db, a.project_id)
        t = get_task(db, a.task_id)
        lines.append(
            f"  {format_project_ref(p)} | {format_task_ref(t)} | {a.status.value}"
        )

    if not _confirm_undo(lines):
        return

    for a in targets:
        undo_assignment(db, a.project_id, a.task_id)
    after_mutation(affected_group_ids, None)
    print_segment([f"Undone {len(targets)} assignment(s)."])


def _find_resolved_assignments(
    db: Database,
    *,
    project_ids: set[int] | None = None,
    task_ids: set[int] | None = None,
) -> list[Assignment]:
    """Find non-pending assignments matching the given filters."""
    results: list[Assignment] = []
    for a in db.assignments.values():
        if a.status == AssignmentStatus.PENDING:
            continue
        if project_ids is not None and a.project_id not in project_ids:
            continue
        if task_ids is not None and a.task_id not in task_ids:
            continue
        results.append(a)
    return results


def _confirm_undo(lines: list[str]) -> bool:
    """Show undo details and ask for y/N confirmation."""
    print_segment(lines, trailing_blank=False)
    try:
        confirm = input("Confirm? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        print_segment(["Cancelled."])
        return False
    if confirm not in ("y", "yes"):
        print_segment(["Cancelled."])
        return False
    return True


def _task_affected_group_ids(db: Database, group_id: int | None) -> set[int]:
    if group_id is None:
        return {g.id for g in db.groups}
    return {group_id}
