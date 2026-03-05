"""Pydeli user-facing error hierarchy."""


class PydeliError(Exception):
    """Base error for all user-facing pydeli failures.

    Caught at the CLI boundary and displayed without a traceback.
    """


class PathError(PydeliError):
    """Invalid or unresolvable path."""


class VersionError(PydeliError):
    """Version inconsistency or policy violation."""


class RegistryError(PydeliError):
    """Problem communicating with or interpreting a package registry."""


class BuildError(PydeliError):
    """Build subprocess failure."""


class PublishError(PydeliError):
    """Upload failure."""


class VerificationError(PydeliError):
    """Post-upload verification failure."""


class StateError(PydeliError):
    """Corrupt or missing local state."""


class BootstrapError(PydeliError):
    """First-release bootstrap flow failure."""
