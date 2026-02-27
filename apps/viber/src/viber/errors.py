"""Custom exception types for viber."""

from __future__ import annotations


class ViberError(Exception):
    """Base class for all viber errors."""


class GroupNotFoundError(ViberError):
    def __init__(self, group_id: int) -> None:
        super().__init__(f"Group {group_id} not found.")


class ProjectNotFoundError(ViberError):
    def __init__(self, project_id: int) -> None:
        super().__init__(f"Project {project_id} not found.")


class TaskNotFoundError(ViberError):
    def __init__(self, task_id: int) -> None:
        super().__init__(f"Task {task_id} not found.")


class AssignmentNotFoundError(ViberError):
    def __init__(self, project_id: int, task_id: int) -> None:
        super().__init__(f"No assignment for p{project_id} / t{task_id}.")


class DuplicateNameError(ViberError):
    def __init__(self, name: str) -> None:
        super().__init__(f"Name '{name}' already exists.")


class InvalidStateTransitionError(ViberError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class PathMappingError(ViberError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class StartupValidationError(ViberError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class FilenameSanitizationError(ViberError):
    def __init__(self, segment: str) -> None:
        super().__init__(f"Sanitization of '{segment}' produced an empty result.")
