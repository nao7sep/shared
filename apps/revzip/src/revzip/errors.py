"""Typed exceptions for revzip."""


class RevzipError(Exception):
    """Base exception for revzip failures."""


class PathMappingError(RevzipError):
    """Raised when a path argument cannot be safely mapped."""


class StartupValidationError(RevzipError):
    """Raised when startup arguments are invalid."""


class IgnorePatternError(RevzipError):
    """Raised when the ignore pattern file is invalid."""


class ArchiveError(RevzipError):
    """Raised for archive workflow failures."""


class ArchiveCollisionError(ArchiveError):
    """Raised when the target snapshot file names already exist."""


class ArchiveEmptyError(ArchiveError):
    """Raised when there is nothing to archive."""


class MetadataError(RevzipError):
    """Raised when metadata cannot be read or written."""


class ExtractError(RevzipError):
    """Raised for extract workflow failures."""


class ZipIntegrityError(ExtractError):
    """Raised when zip integrity checks fail."""
