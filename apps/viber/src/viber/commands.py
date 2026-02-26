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
    format_local_time,
    format_project,
    format_project_ref,
    format_task,
    format_task_ref,
    print_blank,
    print_segment,
)
from .models import AssignmentStatus, Database, assignment_key
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
    update_assignment_comment,
    update_group_name,
    update_project_name,
    update_task_description,
)

MutationHook = Callable[[set[int] | None, set[str] | None], None]

HELP_TEXT = """\
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


def execute_command(
    command: ParsedCommand,
    db: Database,
    after_mutation: MutationHook,
) -> None:
    if isinstance(command, HelpCommand):
        print_segment(HELP_TEXT.splitlines())
        return

    if isinstance(command, CreateGroupCommand):
        group = create_group(db, command.name)
        after_mutation({group.id}, None)
        print_segment([f"Created group: {group.name} (g{group.id})."])
        return

    if isinstance(command, CreateProjectCommand):
        group = get_group(db, command.group_id)
        project = create_project(db, command.name, command.group_id)
        after_mutation({group.id}, None)
        print_segment([
            f"Created project: {project.name} (p{project.id}) in group {group.name} (g{group.id})."
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
        print_segment([f"Created task: {task.description} (t{task.id}) for {scope}."])
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
            print_segment([f"Group name unchanged: {group.name} (g{group.id})."])
        else:
            print_segment([
                f"Renamed group: {old_name} (g{group.id}) -> "
                f"{group.name} (g{group.id})."
            ])
        return

    if isinstance(command, UpdateProjectNameCommand):
        old_name = get_project(db, command.project_id).name
        project = update_project_name(db, command.project_id, command.new_name)
        after_mutation({project.group_id}, None)
        if old_name == project.name:
            print_segment([f"Project name unchanged: {project.name} (p{project.id})."])
        else:
            print_segment([
                f"Renamed project: {old_name} (p{project.id}) -> "
                f"{project.name} (p{project.id})."
            ])
        return

    if isinstance(command, UpdateProjectStateCommand):
        project = set_project_state(db, command.project_id, command.new_state)
        after_mutation({project.group_id}, None)
        print_segment([
            f"Updated project state: {project.name} (p{project.id}) -> {command.new_state.value}."
        ])
        return

    if isinstance(command, UpdateAssignmentCommentCommand):
        update_assignment_comment(db, command.project_id, command.task_id, command.comment)
        after_mutation(set(), None)
        if command.comment:
            print_segment([
                "Updated assignment comment for "
                f"p{command.project_id} + t{command.task_id}: {command.comment}"
            ])
        else:
            print_segment([
                f"Cleared assignment comment for p{command.project_id} + t{command.task_id}."
            ])
        return

    if isinstance(command, UpdateTaskDescriptionCommand):
        task = update_task_description(db, command.task_id, command.new_description)
        after_mutation(_task_affected_group_ids(db, task.group_id), None)
        print_segment([f"Updated task: {format_task_ref(task)}."])
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
        print_segment([f"Updated task: {format_task_ref(task)}."])
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
                f"{format_project_ref(e.project)} + {format_task_ref(e.task)}"
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
        group_map = {g.id: g for g in db.groups}
        lines: list[str] = []
        for project in projects:
            group = group_map.get(project.group_id)
            if group is not None:
                lines.append(format_project(project, group))
            else:
                created = format_local_time(project.created_utc)
                lines.append(
                    f"{project.name} (p{project.id}) [{project.state.value}] (group: ?)"
                    f" [created: {created}]"
                )
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
        group_map = {g.id: g for g in db.groups}
        maybe_group = group_map.get(project.group_id)
        if maybe_group is not None:
            print_segment([format_project(project, maybe_group)])
        else:
            created = format_local_time(project.created_utc)
            print_segment(
                [f"{project.name} (p{project.id}) [{project.state.value}] [created: {created}]"]
            )
        return

    task = get_task(db, command.entity_id)
    print_segment([format_task(task, db)])


def _exec_delete(command: DeleteEntityCommand, db: Database, after_mutation: MutationHook) -> None:
    if command.kind == "group":
        group = delete_group(db, command.entity_id)
        after_mutation(set(), {group.name})
        print_segment([f"Deleted group: {group.name} (g{group.id})."])
        return

    if command.kind == "project":
        project = delete_project(db, command.entity_id)
        after_mutation({project.group_id}, None)
        print_segment([f"Deleted project: {project.name} (p{project.id})."])
        return

    task = delete_task(db, command.entity_id)
    after_mutation(_task_affected_group_ids(db, task.group_id), None)
    print_segment([f"Deleted task: {task.description} (t{task.id})."])


def _exec_view_entity(command: ViewEntityCommand, db: Database) -> None:
    if command.kind == "project":
        project = get_project(db, command.entity_id)
        results = pending_by_project(db, command.entity_id)
        if not results:
            print_segment([f"No pending tasks for {format_project_ref(project)}."])
            return
        lines = [f"Pending tasks for {format_project_ref(project)}:"]
        for task, _assignment in results:
            created = format_local_time(task.created_utc).split(" ")[0]
            lines.append(f"  {format_task_ref(task)} ({created})")
        print_segment(lines)
        return

    task = get_task(db, command.entity_id)
    task_results = pending_by_task(db, command.entity_id)
    if not task_results:
        print_segment([f"No pending projects for {format_task_ref(task)}."])
        return
    lines = [f"Pending projects for {format_task_ref(task)}:"]
    for project, group, _assignment in task_results:
        lines.append(f"  {format_project_ref(project)} (group: {group.name})")
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
    resolve_assignment(db, command.project_id, command.task_id, command.status, comment)
    after_mutation({project.group_id}, None)
    print_segment([
        f"Updated assignment: {project.name} (p{project.id}) + {task.description} (t{task.id})"
        f" -> {verb_label}."
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

    results = pending_by_project(db, project.id)
    if not results:
        print_segment([f"No pending tasks for {format_project_ref(project)}."])
        return

    print_segment([
        f"Work loop: {project.name} (p{project.id}) has {len(results)} pending task(s)."
    ], trailing_blank=False)
    print_blank()

    for i, (task, _assignment) in enumerate(results, 1):
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
            verb_label = "ok" if status == AssignmentStatus.OK else "nah"
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

    for i, (project, group, _assignment) in enumerate(results, 1):
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
            verb_label = "ok" if status == AssignmentStatus.OK else "nah"
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


def _task_affected_group_ids(db: Database, group_id: int | None) -> set[int]:
    if group_id is None:
        return {g.id for g in db.groups}
    return {group_id}
