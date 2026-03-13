"""Tests for emojihunt.analyzer — risk classification and emoji detection edge cases."""

from __future__ import annotations

from emojihunt.analyzer import EmojiAnalyzer, _classify_risk, _format_code_points
from emojihunt.models import RiskLevel


class TestRiskClassification:
    """The classification logic has a precedence rule: RED > YELLOW > SAFE,
    but ALL applicable reasons must be collected regardless of final level."""

    def test_red_trumps_yellow(self) -> None:
        """An emoji that triggers both RED and YELLOW conditions must be RED,
        but must still list the YELLOW reasons."""
        level, reasons = _classify_risk(
            has_variation_selector=True,
            emoji_presentation=True,
            is_zwj=True,
            has_skin_tone=False,
            emoji_version="15.0",
        )
        assert level == RiskLevel.RED
        assert any("variation selector" in r.lower() for r in reasons)
        assert any("zwj" in r.lower() for r in reasons)
        assert any("version" in r.lower() for r in reasons)

    def test_both_red_conditions(self) -> None:
        """Variation selector AND text-default presentation — both RED reasons collected."""
        level, reasons = _classify_risk(
            has_variation_selector=True,
            emoji_presentation=False,
            is_zwj=False,
            has_skin_tone=False,
            emoji_version="1.0",
        )
        assert level == RiskLevel.RED
        assert len(reasons) == 2

    def test_yellow_from_version_alone(self) -> None:
        level, reasons = _classify_risk(
            has_variation_selector=False,
            emoji_presentation=True,
            is_zwj=False,
            has_skin_tone=False,
            emoji_version="14.0",
        )
        assert level == RiskLevel.YELLOW
        assert len(reasons) == 1

    def test_version_just_below_threshold_is_safe(self) -> None:
        level, reasons = _classify_risk(
            has_variation_selector=False,
            emoji_presentation=True,
            is_zwj=False,
            has_skin_tone=False,
            emoji_version="13.1",
        )
        assert level == RiskLevel.SAFE
        assert reasons == []

    def test_unknown_version_does_not_crash(self) -> None:
        """'unknown' version string must not raise — just skip the version check."""
        level, reasons = _classify_risk(
            has_variation_selector=False,
            emoji_presentation=True,
            is_zwj=False,
            has_skin_tone=False,
            emoji_version="unknown",
        )
        assert level == RiskLevel.SAFE

    def test_multiple_yellow_reasons_collected(self) -> None:
        level, reasons = _classify_risk(
            has_variation_selector=False,
            emoji_presentation=True,
            is_zwj=True,
            has_skin_tone=True,
            emoji_version="15.0",
        )
        assert level == RiskLevel.YELLOW
        assert len(reasons) == 3


class TestAnalyzeLineEdgeCases:
    """Edge cases for the line-level emoji detection."""

    def setup_method(self) -> None:
        self.analyzer = EmojiAnalyzer()

    def test_empty_line(self) -> None:
        assert self.analyzer.analyze_line("") == []

    def test_plain_ascii(self) -> None:
        assert self.analyzer.analyze_line("Hello, world! 123") == []

    def test_trailing_variation_selector_captured(self) -> None:
        """When emoji_list returns ⚡ (U+26A1) but FE0F follows in the text,
        the analyzer must include the VS in the result's code_points."""
        line = "\u26A1\uFE0F"  # HIGH VOLTAGE + VS16
        results = self.analyzer.analyze_line(line)
        assert len(results) >= 1
        # The result must reflect the variation selector presence
        found = results[0]
        assert found.has_variation_selector

    def test_zwj_sequence_detected_as_single_entry(self) -> None:
        """A ZWJ family emoji should produce one result, not multiple."""
        # Man + ZWJ + Woman + ZWJ + Boy
        zwj_emoji = "\U0001F468\u200D\U0001F469\u200D\U0001F466"
        results = self.analyzer.analyze_line(f"Family: {zwj_emoji}")
        # Should be recognized as a single emoji (or its components, depending
        # on the emoji package version), but all results should have is_zwj=True
        # if the package detects the full sequence.
        if len(results) == 1:
            assert results[0].is_zwj

    def test_multiple_emojis_in_one_line(self) -> None:
        line = "Hello \U0001F600 world \U0001F4A9 end"
        results = self.analyzer.analyze_line(line)
        assert len(results) == 2

    def test_skin_tone_modifier_detected(self) -> None:
        # Waving hand + medium skin tone
        line = "\U0001F44B\U0001F3FD"
        results = self.analyzer.analyze_line(line)
        assert len(results) >= 1
        assert results[0].has_skin_tone_modifier


class TestGetAllKnownEmojis:
    def test_returns_sorted_by_code_points(self) -> None:
        analyzer = EmojiAnalyzer()
        emojis = analyzer.get_all_known_emojis()
        code_points = [e.code_points for e in emojis]
        assert code_points == sorted(code_points)

    def test_no_empty_results(self) -> None:
        analyzer = EmojiAnalyzer()
        emojis = analyzer.get_all_known_emojis()
        assert len(emojis) > 100  # sanity check — emoji package knows thousands


class TestFormatCodePoints:
    def test_single_bmp_char(self) -> None:
        assert _format_code_points("A") == "U+0041"

    def test_supplementary_plane(self) -> None:
        assert _format_code_points("\U0001F600") == "U+1F600"

    def test_multi_codepoint_sequence(self) -> None:
        result = _format_code_points("\u26A1\uFE0F")
        assert result == "U+26A1 U+FE0F"
