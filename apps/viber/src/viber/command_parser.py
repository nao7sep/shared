"""Command parsing and validation for REPL verbs."""

from __future__ import annotations

from dataclasses import dataclass

from .models import AssignmentStatus, ProjectState


class CommandParseError(ValueError):
    """User-facing command parse error with one or more output lines."""

    def __init__(self, lines: str | list[str]) -> None:
        if isinstance(lines, str):
            self.lines = [lines]
        else:
            self.lines = lines
        super().__init__("\n".join(self.lines))


@dataclass(frozen=True)
class ParsedCommand:
    pass


@dataclass(frozen=True)
class HelpCommand(ParsedCommand):
    pass


@dataclass(frozen=True)
class CreateGroupCommand(ParsedCommand):
    name: str


@dataclass(frozen=True)
class CreateProjectCommand(ParsedCommand):
    name: str
    group_id: int


@dataclass(frozen=True)
class CreateTaskCommand(ParsedCommand):
    description: str
    group_id: int | None


@dataclass(frozen=True)
class ReadCollectionCommand(ParsedCommand):
    kind: str  # groups | projects | tasks


@dataclass(frozen=True)
class ReadEntityCommand(ParsedCommand):
    kind: str  # group | project | task
    entity_id: int


@dataclass(frozen=True)
class UpdateGroupNameCommand(ParsedCommand):
    group_id: int
    new_name: str


@dataclass(frozen=True)
class UpdateProjectNameCommand(ParsedCommand):
    project_id: int
    new_name: str


@dataclass(frozen=True)
class UpdateProjectStateCommand(ParsedCommand):
    project_id: int
    new_state: ProjectState


@dataclass(frozen=True)
class UpdateAssignmentCommentCommand(ParsedCommand):
    project_id: int
    task_id: int
    comment: str | None


@dataclass(frozen=True)
class UpdateTaskDescriptionCommand(ParsedCommand):
    task_id: int
    new_description: str


@dataclass(frozen=True)
class UpdateTaskDescriptionPromptCommand(ParsedCommand):
    task_id: int


@dataclass(frozen=True)
class DeleteEntityCommand(ParsedCommand):
    kind: str  # group | project | task
    entity_id: int


@dataclass(frozen=True)
class ViewAllCommand(ParsedCommand):
    pass


@dataclass(frozen=True)
class ViewEntityCommand(ParsedCommand):
    kind: str  # project | task
    entity_id: int


@dataclass(frozen=True)
class ResolveAssignmentCommand(ParsedCommand):
    project_id: int
    task_id: int
    status: AssignmentStatus


@dataclass(frozen=True)
class WorkEntityCommand(ParsedCommand):
    kind: str  # project | task
    entity_id: int


@dataclass(frozen=True)
class UndoAssignmentCommand(ParsedCommand):
    project_id: int
    task_id: int


@dataclass(frozen=True)
class UndoEntityCommand(ParsedCommand):
    kind: str  # group | project | task
    entity_id: int


def parse_command(verb: str, args: list[str]) -> ParsedCommand:
    if verb == "help":
        if args:
            raise CommandParseError("Usage: help")
        return HelpCommand()
    if verb == "create":
        return _parse_create(args)
    if verb == "read":
        return _parse_read(args)
    if verb == "update":
        return _parse_update(args)
    if verb == "delete":
        return _parse_delete(args)
    if verb == "view":
        return _parse_view(args)
    if verb == "ok":
        return _parse_resolve(args, AssignmentStatus.OK)
    if verb == "nah":
        return _parse_resolve(args, AssignmentStatus.NAH)
    if verb == "work":
        return _parse_work(args)
    if verb == "undo":
        return _parse_undo(args)
    raise CommandParseError(f"Unknown command: '{verb}'. Type 'help' for available commands.")


def _parse_create(args: list[str]) -> ParsedCommand:
    if not args:
        raise CommandParseError(
            "Usage: create group <name> | create project <name> g<ID>"
            " | create task <description> <all|g<ID>>"
        )

    kind = args[0].lower()

    if kind in ("group", "g"):
        if len(args) < 2:
            raise CommandParseError("Usage: create group <name>")
        name = _join_tokens(args[1:])
        if not name:
            raise CommandParseError("Group name cannot be empty.")
        return CreateGroupCommand(name=name)

    if kind in ("project", "p"):
        if len(args) < 3:
            raise CommandParseError("Usage: create project <name> g<ID>")
        group_token = args[-1]
        group_id = _parse_id_token(group_token, "g")
        if group_id is None:
            raise CommandParseError(
                f"Invalid group reference '{group_token}'. Expected g<ID>."
            )
        name = _join_tokens(args[1:-1])
        if not name:
            raise CommandParseError("Project name cannot be empty.")
        return CreateProjectCommand(name=name, group_id=group_id)

    if kind in ("task", "t"):
        if len(args) < 3:
            raise CommandParseError("Usage: create task <description> <all|g<ID>>")
        scope_token = args[-1].lower()
        if scope_token == "all":
            task_group_id: int | None = None
        else:
            task_group_id = _parse_id_token(scope_token, "g")
            if task_group_id is None:
                raise CommandParseError(
                    f"Invalid task scope '{args[-1]}'. Expected all or g<ID>."
                )
        desc_tokens = args[1:-1]
        description = _join_tokens(desc_tokens)
        if not description:
            raise CommandParseError("Task description cannot be empty.")
        return CreateTaskCommand(description=description, group_id=task_group_id)

    raise CommandParseError(
        f"Unknown entity type '{kind}'. Use 'group', 'project', or 'task'."
    )


def _parse_read(args: list[str]) -> ParsedCommand:
    if not args or len(args) != 1:
        raise CommandParseError("Usage: read groups|projects|tasks | read g<ID>|p<ID>|t<ID>")

    token = args[0].lower()
    if token in ("groups", "g"):
        return ReadCollectionCommand(kind="groups")
    if token in ("projects", "p"):
        return ReadCollectionCommand(kind="projects")
    if token in ("tasks", "t"):
        return ReadCollectionCommand(kind="tasks")

    gid = _parse_id_token(token, "g")
    if gid is not None:
        return ReadEntityCommand(kind="group", entity_id=gid)

    pid = _parse_id_token(token, "p")
    if pid is not None:
        return ReadEntityCommand(kind="project", entity_id=pid)

    tid = _parse_id_token(token, "t")
    if tid is not None:
        return ReadEntityCommand(kind="task", entity_id=tid)

    raise CommandParseError(
        f"Unknown target '{token}'. Expected groups/projects/tasks or g<ID>/p<ID>/t<ID>."
    )


def _parse_update(args: list[str]) -> ParsedCommand:
    if not args:
        raise CommandParseError([
            "Usage:",
            "  update g<ID> <new-name>",
            "  update p<ID> name <new-name>",
            "  update p<ID> state <active|suspended|deprecated>",
            "  update p<ID> t<ID> [comment]",
            "  update t<ID> <new-description>",
            "  update t<ID> p<ID> [comment]",
        ])

    token = args[0].lower()

    gid = _parse_id_token(token, "g")
    if gid is not None:
        if len(args) < 2:
            raise CommandParseError("Usage: update g<ID> <new-name>")
        new_name = _join_tokens(args[1:])
        if not new_name:
            raise CommandParseError("Group name cannot be empty.")
        return UpdateGroupNameCommand(group_id=gid, new_name=new_name)

    pid = _parse_id_token(token, "p")
    if pid is not None:
        if len(args) < 2:
            raise CommandParseError([
                "Usage:",
                "  update p<ID> name <new-name>",
                "  update p<ID> state <active|suspended|deprecated>",
                "  update p<ID> t<ID> [comment]",
            ])

        second = args[1].lower()
        assignment_tid = _parse_id_token(second, "t")
        if assignment_tid is not None:
            comment = _join_tokens(args[2:]) or None
            return UpdateAssignmentCommentCommand(
                project_id=pid, task_id=assignment_tid, comment=comment
            )

        if second == "name":
            if len(args) < 3:
                raise CommandParseError("Usage: update p<ID> name <new-name>")
            new_name = _join_tokens(args[2:])
            if not new_name:
                raise CommandParseError("Project name cannot be empty.")
            return UpdateProjectNameCommand(project_id=pid, new_name=new_name)

        if second == "state":
            if len(args) < 3:
                raise CommandParseError(
                    "Usage: update p<ID> state <active|suspended|deprecated>"
                )
            if len(args) > 3:
                raise CommandParseError(
                    "Usage: update p<ID> state <active|suspended|deprecated>"
                )
            new_state = _parse_state_token(args[2].lower())
            if new_state is None:
                raise CommandParseError(
                    "Usage: update p<ID> state <active|suspended|deprecated>"
                )
            return UpdateProjectStateCommand(project_id=pid, new_state=new_state)

        raise CommandParseError([
            "Usage:",
            "  update p<ID> name <new-name>",
            "  update p<ID> state <active|suspended|deprecated>",
            "  update p<ID> t<ID> [comment]",
        ])

    tid = _parse_id_token(token, "t")
    if tid is not None:
        if len(args) >= 2:
            maybe_pid = _parse_id_token(args[1].lower(), "p")
            if maybe_pid is not None:
                comment = _join_tokens(args[2:]) or None
                return UpdateAssignmentCommentCommand(
                    project_id=maybe_pid, task_id=tid, comment=comment
                )
            new_desc = _join_tokens(args[1:])
            if not new_desc:
                raise CommandParseError("Task description cannot be empty.")
            return UpdateTaskDescriptionCommand(task_id=tid, new_description=new_desc)
        return UpdateTaskDescriptionPromptCommand(task_id=tid)

    raise CommandParseError(
        f"Unknown target '{token}'. Expected g<ID>, p<ID>, or t<ID>."
    )


def _parse_delete(args: list[str]) -> ParsedCommand:
    if not args or len(args) != 1:
        raise CommandParseError("Usage: delete g<ID>|p<ID>|t<ID>")

    token = args[0].lower()
    gid = _parse_id_token(token, "g")
    if gid is not None:
        return DeleteEntityCommand(kind="group", entity_id=gid)
    pid = _parse_id_token(token, "p")
    if pid is not None:
        return DeleteEntityCommand(kind="project", entity_id=pid)
    tid = _parse_id_token(token, "t")
    if tid is not None:
        return DeleteEntityCommand(kind="task", entity_id=tid)
    raise CommandParseError(
        f"Unknown target '{token}'. Expected g<ID>, p<ID>, or t<ID>."
    )


def _parse_view(args: list[str]) -> ParsedCommand:
    if not args:
        return ViewAllCommand()
    if len(args) != 1:
        raise CommandParseError("Usage: view | view p<ID> | view t<ID>")

    token = args[0].lower()
    pid = _parse_id_token(token, "p")
    if pid is not None:
        return ViewEntityCommand(kind="project", entity_id=pid)
    tid = _parse_id_token(token, "t")
    if tid is not None:
        return ViewEntityCommand(kind="task", entity_id=tid)
    raise CommandParseError(
        f"Unknown target '{token}'. Expected p<ID> or t<ID>."
    )


def _parse_resolve(args: list[str], status: AssignmentStatus) -> ParsedCommand:
    if len(args) != 2:
        verb = "ok" if status == AssignmentStatus.OK else "nah"
        raise CommandParseError(f"Usage: {verb} p<ID> t<ID>")
    pid, tid = _parse_pt_tokens(args[0], args[1])
    if pid is None or tid is None:
        raise CommandParseError(
            f"Expected p<ID> and t<ID> in either order. Got: {args[0]} {args[1]}"
        )
    return ResolveAssignmentCommand(project_id=pid, task_id=tid, status=status)


def _parse_work(args: list[str]) -> ParsedCommand:
    if not args or len(args) != 1:
        raise CommandParseError("Usage: work p<ID> | work t<ID>")
    token = args[0].lower()
    pid = _parse_id_token(token, "p")
    if pid is not None:
        return WorkEntityCommand(kind="project", entity_id=pid)
    tid = _parse_id_token(token, "t")
    if tid is not None:
        return WorkEntityCommand(kind="task", entity_id=tid)
    raise CommandParseError(
        f"Unknown target '{token}'. Expected p<ID> or t<ID>."
    )


def _parse_undo(args: list[str]) -> ParsedCommand:
    if len(args) == 2:
        pid, tid = _parse_pt_tokens(args[0], args[1])
        if pid is not None and tid is not None:
            return UndoAssignmentCommand(project_id=pid, task_id=tid)
        raise CommandParseError(
            f"Expected p<ID> and t<ID> in either order. Got: {args[0]} {args[1]}"
        )
    if len(args) == 1:
        token = args[0].lower()
        gid = _parse_id_token(token, "g")
        if gid is not None:
            return UndoEntityCommand(kind="group", entity_id=gid)
        pid = _parse_id_token(token, "p")
        if pid is not None:
            return UndoEntityCommand(kind="project", entity_id=pid)
        tid = _parse_id_token(token, "t")
        if tid is not None:
            return UndoEntityCommand(kind="task", entity_id=tid)
        raise CommandParseError(
            f"Unknown target '{token}'. Expected g<ID>, p<ID>, or t<ID>."
        )
    raise CommandParseError(
        "Usage: undo p<ID> t<ID> | undo g<ID> | undo p<ID> | undo t<ID>"
    )


def _join_tokens(tokens: list[str]) -> str:
    return " ".join(tokens).strip()


def _parse_state_token(token: str) -> ProjectState | None:
    if token == "active":
        return ProjectState.ACTIVE
    if token == "suspended":
        return ProjectState.SUSPENDED
    if token == "deprecated":
        return ProjectState.DEPRECATED
    return None


def _parse_id_token(token: str, prefix: str) -> int | None:
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
    a = a.lower()
    b = b.lower()

    if a.startswith("p") and b.startswith("t"):
        return _parse_id_token(a, "p"), _parse_id_token(b, "t")
    if a.startswith("t") and b.startswith("p"):
        return _parse_id_token(b, "p"), _parse_id_token(a, "t")
    return None, None
