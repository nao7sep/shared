"""Custom exception hierarchy for tk."""


class AppError(Exception):
    """Base exception for app-specific failures."""


class UsageError(ValueError, AppError):
    """Command usage or user-input errors."""


class ValidationError(ValueError, AppError):
    """Domain validation errors."""


class ConfigError(ValueError, AppError):
    """Profile/configuration validation errors."""


class StorageError(AppError):
    """Storage load/save failures."""
