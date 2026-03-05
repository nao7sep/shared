"""Load and classify the full emoji dataset from the upstream emoji library."""

import emoji as emoji_lib

from .models import EmojiEntry, RiskLevel

_SKIN_TONE_MODIFIERS = frozenset(range(0x1F3FB, 0x1F400))
_VARIATION_SELECTORS = frozenset({0xFE0E, 0xFE0F})
_ZWJ = 0x200D

_QUALIFICATION_MAP = {
    0: "component",
    1: "minimally-qualified",
    2: "fully-qualified",
    3: "unqualified",
}

_EMOJI_TO_UNICODE: dict[float, str] = {
    0.6: "6.0",
    0.7: "7.0",
    1.0: "8.0",
    2.0: "8.0",
    3.0: "9.0",
    4.0: "9.0",
    5.0: "10.0",
    11.0: "11.0",
    12.0: "12.0",
    12.1: "12.1",
    13.0: "13.0",
    13.1: "13.0",
    14.0: "14.0",
    15.0: "15.0",
    15.1: "15.1",
    16.0: "16.0",
}

# Pre-compute set of base sequences that need FE0F for emoji presentation.
# If an emoji string in EMOJI_DATA contains U+FE0F, its FE0F-stripped form
# has text-default or ambiguous presentation.
_text_default_bases: frozenset[str] | None = None


def _get_text_default_bases() -> frozenset[str]:
    global _text_default_bases
    if _text_default_bases is None:
        bases: set[str] = set()
        for seq in emoji_lib.EMOJI_DATA:
            if "\uFE0F" in seq:
                bases.add(seq.replace("\uFE0F", ""))
        _text_default_bases = frozenset(bases)
    return _text_default_bases


def load_emoji_dataset(*, fully_qualified_only: bool = False) -> dict[str, EmojiEntry]:
    """Load emoji sequences from the upstream library and classify each one.

    When fully_qualified_only is True, only includes status=2 entries (for catalog).
    When False, includes all entries (for scan matching).
    """
    text_default_bases = _get_text_default_bases()
    entries: dict[str, EmojiEntry] = {}

    for emoji_str, data in emoji_lib.EMOJI_DATA.items():
        status_code = data.get("status", 2)
        if fully_qualified_only and status_code != 2:
            continue

        name = data.get("en", "").strip(":").replace("_", " ")
        emoji_version = float(data.get("E", 0))
        unicode_version = _EMOJI_TO_UNICODE.get(emoji_version, f"{emoji_version:.1f}")
        group = data.get("group", "")
        subgroup = data.get("subgroup", "")
        qualification = _QUALIFICATION_MAP.get(status_code, "unknown")

        code_point_ints = tuple(ord(c) for c in emoji_str)
        code_points_str = " ".join(f"U+{cp:04X}" for cp in code_point_ints)

        has_vs = any(cp in _VARIATION_SELECTORS for cp in code_point_ints)
        has_zwj = _ZWJ in code_point_ints
        has_skin_tone = any(cp in _SKIN_TONE_MODIFIERS for cp in code_point_ints)

        # Text-default: sequence contains FE0F, or its base form is known to need FE0F
        stripped = emoji_str.replace("\uFE0F", "")
        is_text_default = has_vs or (stripped in text_default_bases)

        risk_level, risk_reasons = _classify_risk(
            has_vs=has_vs,
            is_text_default=is_text_default,
            has_zwj=has_zwj,
            has_skin_tone=has_skin_tone,
            emoji_version=emoji_version,
        )

        entries[emoji_str] = EmojiEntry(
            sequence=emoji_str,
            name=name,
            code_points=code_points_str,
            emoji_version=emoji_version,
            unicode_version=unicode_version,
            group=group,
            subgroup=subgroup,
            qualification=qualification,
            has_variation_selector=has_vs,
            has_zwj=has_zwj,
            has_skin_tone_modifier=has_skin_tone,
            is_text_default=is_text_default,
            risk_level=risk_level,
            risk_reasons=risk_reasons,
        )

    return entries


def _classify_risk(
    *,
    has_vs: bool,
    is_text_default: bool,
    has_zwj: bool,
    has_skin_tone: bool,
    emoji_version: float,
) -> tuple[RiskLevel, tuple[str, ...]]:
    reasons: list[str] = []
    has_red = False
    has_yellow = False

    if has_vs:
        reasons.append("variation selector")
        has_red = True
    if is_text_default:
        reasons.append("text-default presentation")
        has_red = True
    if has_zwj:
        reasons.append("zero width joiner")
        has_yellow = True
    if has_skin_tone:
        reasons.append("skin tone modifier")
        has_yellow = True
    if emoji_version >= 14.0:
        reasons.append(f"Unicode {_EMOJI_TO_UNICODE.get(emoji_version, f'{emoji_version:.1f}')}+")
        has_yellow = True

    if has_red:
        level = RiskLevel.RED
    elif has_yellow:
        level = RiskLevel.YELLOW
    else:
        level = RiskLevel.NONE

    return level, tuple(reasons)
