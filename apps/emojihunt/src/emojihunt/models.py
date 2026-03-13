"""Data models for emojihunt.

All structured data uses dataclasses. No raw dicts for multi-field data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class RiskLevel(str, Enum):
    """Emoji rendering risk classification."""

    RED = "RED"
    YELLOW = "YELLOW"
    SAFE = "SAFE"


class HandledPathStatus(str, Enum):
    """Status of a file encountered during scanning."""

    OK = "OK"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"


@dataclass
class EmojiMetadata:
    """Metadata for a single emoji or emoji sequence."""

    char: str
    code_points: str  # space-separated hex, e.g. "U+26A1 U+FE0F"
    name: str
    unicode_version: str  # e.g. "14.0", "E2.0", or "unknown"
    risk_level: RiskLevel
    risk_reasons: list[str] = field(default_factory=list)
    emoji_presentation: bool = True  # True if Emoji_Presentation=Yes
    is_zwj: bool = False
    has_variation_selector: bool = False
    has_skin_tone_modifier: bool = False


@dataclass
class ScanFinding:
    """An emoji found during scanning, with its occurrence count."""

    metadata: EmojiMetadata
    occurrence_count: int


@dataclass
class HandledPath:
    """A file path encountered during scanning, with its processing status."""

    path: str  # full absolute path
    status: HandledPathStatus
    error_message: str | None = None

    def format_line(self) -> str:
        """Format as a single line for the handled-path list file."""
        if self.status == HandledPathStatus.OK:
            return self.path
        if self.status == HandledPathStatus.SKIPPED:
            return f"{self.path} | SKIPPED"
        if self.error_message:
            return f"{self.path} | ERROR: {self.error_message}"
        return f"{self.path} | ERROR"


@dataclass
class ScanContext:
    """Metadata about a scan run, used for report headers."""

    targets: list[str]
    ignore_file: str | None
    started_utc: str  # ISO 8601 with Z
    finished_utc: str  # ISO 8601 with Z
    started_local: str  # human-readable local time
    finished_local: str  # human-readable local time
    duration_seconds: float
    files_scanned: int
    files_skipped: int
    files_errored: int
    unique_emojis_found: int
    total_occurrences: int
