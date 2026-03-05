from dataclasses import dataclass, field
from enum import Enum


class RiskLevel(Enum):
    RED = "red"
    YELLOW = "yellow"
    NONE = "none"


RISK_SORT_ORDER = {RiskLevel.RED: 0, RiskLevel.YELLOW: 1, RiskLevel.NONE: 2}


@dataclass(frozen=True)
class EmojiEntry:
    sequence: str
    name: str
    code_points: str
    emoji_version: float
    unicode_version: str
    group: str
    subgroup: str
    qualification: str
    has_variation_selector: bool
    has_zwj: bool
    has_skin_tone_modifier: bool
    is_text_default: bool
    risk_level: RiskLevel
    risk_reasons: tuple[str, ...]

    @property
    def sort_key_code_points(self) -> tuple[int, ...]:
        """Canonical code point sequence for deterministic ordering."""
        return tuple(ord(c) for c in self.sequence)


@dataclass
class ScanFinding:
    entry: EmojiEntry
    count: int

    @property
    def sort_key(self) -> tuple[int, int, tuple[int, ...]]:
        """Risk severity, then occurrence count descending, then code points."""
        return (
            RISK_SORT_ORDER[self.entry.risk_level],
            -self.count,
            self.entry.sort_key_code_points,
        )


@dataclass
class ScanResult:
    findings: list[ScanFinding] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
