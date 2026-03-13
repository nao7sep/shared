from __future__ import annotations


class PydeliError(Exception):
    """Base exception for user-facing pydeli errors."""


class ConfigError(PydeliError):
    """Raised when configuration is missing or invalid."""


class AuditError(PydeliError):
    """Raised when version consistency checks fail."""


class RegistryError(PydeliError):
    """Raised when registry communication fails or version already exists."""


class BuildError(PydeliError):
    """Raised when uv build fails."""


class PublishError(PydeliError):
    """Raised when uv publish fails."""


class VerificationError(PydeliError):
    """Raised when test-install verification fails."""
