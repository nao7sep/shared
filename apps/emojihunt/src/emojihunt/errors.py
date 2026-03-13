"""Custom exception types for emojihunt."""

from __future__ import annotations


class EmojihuntError(Exception):
    """Base class for all emojihunt errors."""


class PathMappingError(EmojihuntError):
    """Raised when a path argument cannot be safely mapped."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class IgnoreFileError(EmojihuntError):
    """Raised when the ignore file cannot be loaded or contains invalid patterns."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class ScanError(EmojihuntError):
    """Raised for fatal errors during directory scanning."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
