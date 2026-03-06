import re
from pathlib import Path

import pytest

from emojihunt.path_mapping import map_user_path
from emojihunt.scanner import _load_ignore_patterns, _is_ignored
from emojihunt.errors import EmojihuntError


class TestMapUserPath:
    def test_absolute_path_accepted(self, tmp_path: Path) -> None:
        result = map_user_path(str(tmp_path))
        assert result == tmp_path.resolve()

    def test_tilde_path_accepted(self) -> None:
        result = map_user_path("~/code")
        assert result == (Path.home() / "code").resolve()

    def test_at_path_resolves_inside_app_root(self) -> None:
        result = map_user_path("@/data/foo.txt")
        assert result.is_absolute()
        assert result.name == "foo.txt"

    def test_at_escape_rejected(self) -> None:
        with pytest.raises(EmojihuntError, match="cannot escape"):
            map_user_path("@/../../../etc/passwd")

    def test_relative_path_rejected(self) -> None:
        with pytest.raises(EmojihuntError, match="Relative paths"):
            map_user_path("relative/path")

    def test_empty_path_rejected(self) -> None:
        with pytest.raises(EmojihuntError, match="empty"):
            map_user_path("   ")

    def test_nul_rejected(self) -> None:
        with pytest.raises(EmojihuntError, match="NUL"):
            map_user_path("/tmp/bad\x00path")

    def test_windows_rooted_rejected(self) -> None:
        with pytest.raises(EmojihuntError, match="Windows"):
            map_user_path("C:temp")

    def test_backslash_rooted_rejected(self) -> None:
        with pytest.raises(EmojihuntError, match="Windows"):
            map_user_path("\\temp")

    def test_repeated_separators_accepted(self, tmp_path: Path) -> None:
        result = map_user_path(str(tmp_path).replace("/", "//"))
        assert result == tmp_path.resolve()

    def test_nfc_normalization(self, tmp_path: Path) -> None:
        import unicodedata
        nfd = unicodedata.normalize("NFD", str(tmp_path))
        result = map_user_path(nfd)
        assert result == tmp_path.resolve()


class TestLoadIgnorePatterns:
    def test_empty_file_returns_no_patterns(self, tmp_path: Path) -> None:
        f = tmp_path / "ignore.txt"
        f.write_text("")
        assert _load_ignore_patterns(f) == []

    def test_comments_and_blank_lines_skipped(self, tmp_path: Path) -> None:
        f = tmp_path / "ignore.txt"
        f.write_text("# comment\n\n  \n")
        assert _load_ignore_patterns(f) == []

    def test_valid_pattern_loaded(self, tmp_path: Path) -> None:
        f = tmp_path / "ignore.txt"
        f.write_text(r"/\.venv/")
        patterns = _load_ignore_patterns(f)
        assert len(patterns) == 1

    def test_invalid_regex_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "ignore.txt"
        f.write_text("[invalid")
        with pytest.raises(EmojihuntError, match="line 1"):
            _load_ignore_patterns(f)

    def test_none_returns_empty(self) -> None:
        assert _load_ignore_patterns(None) == []


class TestIsIgnored:
    def test_matching_pattern_ignores_path(self) -> None:
        patterns = [re.compile(r"/\.venv/")]
        assert _is_ignored(Path("/home/user/project/.venv/lib"), patterns)

    def test_non_matching_pattern_does_not_ignore(self) -> None:
        patterns = [re.compile(r"/\.venv/")]
        assert not _is_ignored(Path("/home/user/project/src/main.py"), patterns)

    def test_no_patterns_never_ignores(self) -> None:
        assert not _is_ignored(Path("/any/path"), [])


class TestScanner:
    def test_scan_file_with_emoji(self, tmp_path: Path) -> None:
        from emojihunt.scanner import scan_targets
        from emojihunt.emoji_data import load_emoji_dataset

        f = tmp_path / "test.txt"
        f.write_text("Hello 😀 world 😀 and 🎉")
        dataset = load_emoji_dataset()
        result = scan_targets([f], None, dataset)

        counts = {finding.entry.sequence: finding.count for finding in result.findings}
        assert counts.get("😀") == 2
        assert counts.get("🎉") == 1

    def test_scan_file_no_emoji(self, tmp_path: Path) -> None:
        from emojihunt.scanner import scan_targets
        from emojihunt.emoji_data import load_emoji_dataset

        f = tmp_path / "plain.txt"
        f.write_text("No emoji here.")
        dataset = load_emoji_dataset()
        result = scan_targets([f], None, dataset)
        assert result.findings == []

    def test_ignored_directory_not_entered(self, tmp_path: Path) -> None:
        from emojihunt.scanner import scan_targets
        from emojihunt.emoji_data import load_emoji_dataset

        subdir = tmp_path / "skip_me"
        subdir.mkdir()
        (subdir / "emoji.txt").write_text("😀")

        ignore_file = tmp_path / "ignore.txt"
        ignore_file.write_text("/skip_me/")

        dataset = load_emoji_dataset()
        result = scan_targets([tmp_path], ignore_file, dataset)
        assert result.findings == []

    def test_missing_target_produces_warning(self, tmp_path: Path) -> None:
        from emojihunt.scanner import scan_targets
        from emojihunt.emoji_data import load_emoji_dataset

        dataset = load_emoji_dataset()
        result = scan_targets([tmp_path / "nonexistent.txt"], None, dataset)
        assert result.findings == []
        assert any("not found" in w for w in result.warnings)
