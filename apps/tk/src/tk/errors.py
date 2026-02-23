"""Custom exception hierarchy for tk."""


class TkError(Exception):
    """Base exception for tk-specific failures."""


class TkUsageError(ValueError, TkError):
    """Command usage or user-input errors."""


class TkValidationError(ValueError, TkError):
    """Domain validation errors."""


class TkConfigError(ValueError, TkError):
    """Profile/configuration validation errors."""


class TkStorageError(TkError):
    """Storage load/save failures."""
