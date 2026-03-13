"""Emoji detection and risk classification.

Wraps the ``emoji`` package and ``unicodedata`` to detect emoji sequences in
text, extract metadata, and classify rendering risk. Knows nothing about files,
directories, or HTML.
"""

from __future__ import annotations

import unicodedata

import emoji as emoji_pkg

from .models import EmojiMetadata, RiskLevel

# Skin tone modifier codepoints (Fitzpatrick scale)
_SKIN_TONE_RANGE = range(0x1F3FB, 0x1F400)  # U+1F3FB through U+1F3FF

# Emoji version threshold for YELLOW classification
EMOJI_VERSION_THRESHOLD = 14.0


class EmojiAnalyzer:
    """Detects emojis in text and classifies their rendering risk."""

    def analyze_line(self, line: str) -> list[EmojiMetadata]:
        """Extract all emoji sequences from a single line of text.

        Returns one EmojiMetadata per unique emoji occurrence found.
        Variation selectors trailing a matched emoji are detected even if the
        ``emoji`` package does not include them in its match.
        """
        results: list[EmojiMetadata] = []
        matches = emoji_pkg.emoji_list(line)

        for match in matches:
            matched_emoji: str = match["emoji"]
            match_end: int = match["match_end"]

            # Check for a trailing variation selector that emoji_list may have
            # excluded from the match (e.g., ⚡ followed by FE0F).
            has_trailing_vs = False
            if match_end < len(line) and ord(line[match_end]) in (0xFE0E, 0xFE0F):
                has_trailing_vs = True
                # Include the variation selector in the emoji string for
                # accurate code-point reporting.
                matched_emoji = matched_emoji + line[match_end]

            metadata = self._build_metadata(matched_emoji, has_trailing_vs)
            results.append(metadata)

        return results

    def get_all_known_emojis(self) -> list[EmojiMetadata]:
        """Enumerate all emojis known to the ``emoji`` package.

        Returns a list sorted by code-point string for deterministic catalog
        output.
        """
        results: list[EmojiMetadata] = []
        for char, data in emoji_pkg.EMOJI_DATA.items():
            # Skip component entries (status 1) — these are modifiers like
            # skin tones and hair styles that are not standalone emojis.
            if data.get("status") == 1:
                continue
            metadata = self._build_metadata(char, has_trailing_vs=False)
            results.append(metadata)

        results.sort(key=lambda m: m.code_points)
        return results

    def _build_metadata(self, char: str, has_trailing_vs: bool) -> EmojiMetadata:
        """Build an EmojiMetadata from an emoji string."""
        code_points = _format_code_points(char)
        name = _get_emoji_name(char)
        emoji_version = _get_emoji_version(char)

        has_vs = has_trailing_vs or _contains_variation_selector(char)
        is_zwj = "\u200D" in char
        has_skin_tone = _contains_skin_tone_modifier(char)
        presentation = _is_emoji_presentation_default(char)

        risk_level, risk_reasons = _classify_risk(
            has_variation_selector=has_vs,
            emoji_presentation=presentation,
            is_zwj=is_zwj,
            has_skin_tone=has_skin_tone,
            emoji_version=emoji_version,
        )

        return EmojiMetadata(
            char=char,
            code_points=code_points,
            name=name,
            unicode_version=emoji_version,
            risk_level=risk_level,
            risk_reasons=risk_reasons,
            emoji_presentation=presentation,
            is_zwj=is_zwj,
            has_variation_selector=has_vs,
            has_skin_tone_modifier=has_skin_tone,
        )


def _format_code_points(char: str) -> str:
    """Format a string as space-separated hex code points."""
    return " ".join(f"U+{ord(c):04X}" for c in char)


def _get_emoji_name(char: str) -> str:
    """Get the best available name for an emoji.

    Tries the ``emoji`` package CLDR short name first, then falls back to
    ``unicodedata.name()`` for single codepoints.
    """
    # Try the emoji package data (handles multi-codepoint sequences)
    # Strip variation selectors for lookup since EMOJI_DATA may not have them
    lookup_char = char.replace("\uFE0F", "").replace("\uFE0E", "")
    data = emoji_pkg.EMOJI_DATA.get(char) or emoji_pkg.EMOJI_DATA.get(lookup_char)
    if data:
        cldr_name = str(data.get("en", ""))
        if cldr_name:
            # Remove surrounding colons and replace underscores
            return cldr_name.strip(":").replace("_", " ")

    # Fall back to unicodedata for single codepoints
    if len(char) == 1:
        return unicodedata.name(char, "unknown")

    return "unknown"


def _get_emoji_version(char: str) -> str:
    """Get the emoji version string from the ``emoji`` package.

    Returns the 'E' field value as a string (e.g., "14.0", "0.6").
    """
    lookup_char = char.replace("\uFE0F", "").replace("\uFE0E", "")
    data = emoji_pkg.EMOJI_DATA.get(char) or emoji_pkg.EMOJI_DATA.get(lookup_char)
    if data and "E" in data:
        version = data["E"]
        # Ensure it's formatted with a decimal point
        version_str = str(version)
        if "." not in version_str:
            version_str = f"{version}.0"
        return version_str
    return "unknown"


def _contains_variation_selector(char: str) -> bool:
    """Check if the emoji string contains a variation selector."""
    return "\uFE0E" in char or "\uFE0F" in char


def _contains_skin_tone_modifier(char: str) -> bool:
    """Check if the emoji string contains a Fitzpatrick skin tone modifier."""
    return any(ord(c) in _SKIN_TONE_RANGE for c in char)


def _is_emoji_presentation_default(char: str) -> bool:
    """Determine if the emoji defaults to emoji (color) presentation.

    Returns True if the emoji defaults to color rendering, False if it
    defaults to text rendering (Emoji_Presentation=No).

    Heuristic: emojis with ``variant=True`` in the emoji package data are
    presentation-ambiguous. Among those, characters in the lower Unicode
    ranges (below U+1F000) typically default to text presentation.
    Additionally, status 4 (unqualified) entries default to text.
    """
    lookup_char = char.replace("\uFE0F", "").replace("\uFE0E", "")
    data = emoji_pkg.EMOJI_DATA.get(char) or emoji_pkg.EMOJI_DATA.get(lookup_char)

    if not data:
        return True  # Unknown — assume safe

    # Status 4 (unqualified) entries are text-presentation defaults
    if data.get("status") == 4:
        return False

    # Entries with variant=True that have base codepoints < U+1F000
    # are typically Emoji_Presentation=No (text default)
    if data.get("variant"):
        base_codepoints = [
            ord(c)
            for c in lookup_char
            if ord(c) not in (0x200D, 0xFE0E, 0xFE0F)
            and ord(c) not in _SKIN_TONE_RANGE
        ]
        if base_codepoints and all(cp < 0x1F000 for cp in base_codepoints):
            return False

    return True


def _classify_risk(
    *,
    has_variation_selector: bool,
    emoji_presentation: bool,
    is_zwj: bool,
    has_skin_tone: bool,
    emoji_version: str,
) -> tuple[RiskLevel, list[str]]:
    """Classify risk and collect reasons.

    RED takes precedence over YELLOW. The first matching rule wins for level,
    but all applicable reasons are collected.
    """
    reasons: list[str] = []
    level = RiskLevel.SAFE

    # RED conditions
    if has_variation_selector:
        reasons.append("Contains variation selector")
        level = RiskLevel.RED
    if not emoji_presentation:
        reasons.append("Emoji_Presentation=No (defaults to text)")
        level = RiskLevel.RED

    # YELLOW conditions (only upgrade from SAFE, never downgrade from RED)
    if is_zwj:
        reasons.append("ZWJ sequence (may fragment)")
        if level == RiskLevel.SAFE:
            level = RiskLevel.YELLOW
    if has_skin_tone:
        reasons.append("Skin tone modifier (may fragment)")
        if level == RiskLevel.SAFE:
            level = RiskLevel.YELLOW

    try:
        version_float = float(emoji_version)
        if version_float >= EMOJI_VERSION_THRESHOLD:
            reasons.append(f"Emoji version {emoji_version} (may show as missing glyph)")
            if level == RiskLevel.SAFE:
                level = RiskLevel.YELLOW
    except ValueError:
        pass

    return level, reasons
