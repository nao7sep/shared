from __future__ import annotations

from pathlib import Path

from revzip.ignore_rules import load_ignore_rule_set, matches_ignore_rules


def test_load_ignore_rule_set_skips_blank_and_comment_lines(tmp_path: Path) -> None:
    ignore_file = tmp_path / "ignore.txt"
    ignore_file.write_text(
        "\n".join(
            (
                "  # comment",
                "",
                "foo",
                "bar  ",
            )
        ),
        encoding="utf-8",
    )

    ignore_rule_set = load_ignore_rule_set(ignore_file)
    assert ignore_rule_set.patterns_raw == ["foo", "bar"]


def test_matches_ignore_rules_uses_partial_search_without_auto_anchors() -> None:
    ignore_rule_set = load_ignore_rule_set_from_patterns(["docs"])
    assert matches_ignore_rules(
        rel_path=Path("nested/docs/file.txt"),
        raw_source_argument="/tmp/source",
        ignore_rule_set=ignore_rule_set,
    )


def load_ignore_rule_set_from_patterns(patterns: list[str]):
    from re import compile

    from revzip.models import IgnoreRuleSet

    return IgnoreRuleSet(
        patterns_raw=patterns,
        compiled_patterns=[compile(pattern) for pattern in patterns],
    )
