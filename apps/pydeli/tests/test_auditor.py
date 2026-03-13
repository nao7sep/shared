from __future__ import annotations

import pytest
from packaging.version import Version

from pydeli.auditor import VERSION_PATTERN, audit_versions
from pydeli.errors import AuditError


# ---------------------------------------------------------------------------
# VERSION_PATTERN regex edge cases
# ---------------------------------------------------------------------------


class TestVersionPattern:
    """Verify the regex handles real-world __version__ variations."""

    def test_double_quotes(self) -> None:
        match = VERSION_PATTERN.search('__version__ = "1.2.3"')
        assert match and match.group(1) == "1.2.3"

    def test_single_quotes(self) -> None:
        match = VERSION_PATTERN.search("__version__ = '0.1.0'")
        assert match and match.group(1) == "0.1.0"

    def test_no_spaces_around_equals(self) -> None:
        match = VERSION_PATTERN.search('__version__="2.0.0"')
        assert match and match.group(1) == "2.0.0"

    def test_extra_spaces(self) -> None:
        match = VERSION_PATTERN.search('__version__   =   "3.0.0"')
        assert match and match.group(1) == "3.0.0"

    def test_pep440_dev_suffix(self) -> None:
        match = VERSION_PATTERN.search('__version__ = "1.0.0.dev1"')
        assert match and match.group(1) == "1.0.0.dev1"

    def test_pep440_rc_suffix(self) -> None:
        match = VERSION_PATTERN.search('__version__ = "2.1.0rc3"')
        assert match and match.group(1) == "2.1.0rc3"

    def test_pep440_post_suffix(self) -> None:
        match = VERSION_PATTERN.search('__version__ = "1.0.0.post2"')
        assert match and match.group(1) == "1.0.0.post2"

    def test_ignores_commented_line(self) -> None:
        text = '# __version__ = "0.0.1"\n__version__ = "0.0.2"'
        match = VERSION_PATTERN.search(text)
        assert match and match.group(1) == "0.0.2"

    def test_no_match_on_similar_variable(self) -> None:
        match = VERSION_PATTERN.search('_version_ = "1.0.0"')
        assert match is None

    def test_version_buried_in_multiline_file(self) -> None:
        text = (
            '"""Module docstring."""\n'
            "\n"
            "import sys\n"
            "\n"
            '__version__ = "4.5.6"\n'
            "\n"
            "def main(): pass\n"
        )
        match = VERSION_PATTERN.search(text)
        assert match and match.group(1) == "4.5.6"


# ---------------------------------------------------------------------------
# audit_versions integration tests
# ---------------------------------------------------------------------------


class TestAuditVersions:
    """Test version auditing against real filesystem layouts."""

    def test_src_layout_consistent(self, tmp_path: pytest.TempPathFactory) -> None:
        """Two sources match — should return the version and both sources."""
        _write_pyproject(tmp_path, "my-app", "1.2.3")
        _write_src_init(tmp_path, "my_app", "1.2.3")

        version, sources = audit_versions(tmp_path)
        assert version == Version("1.2.3")
        assert len(sources) == 2

    def test_flat_layout_consistent(self, tmp_path: pytest.TempPathFactory) -> None:
        """Flat layout (no src/) with matching versions."""
        _write_pyproject(tmp_path, "myapp", "0.5.0")
        pkg = tmp_path / "myapp"
        pkg.mkdir()
        (pkg / "__init__.py").write_text('__version__ = "0.5.0"\n')

        version, sources = audit_versions(tmp_path)
        assert version == Version("0.5.0")
        assert len(sources) == 2

    def test_src_layout_preferred_over_flat(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        """When both src/ and flat layouts exist, src/ is found first."""
        _write_pyproject(tmp_path, "myapp", "1.0.0")
        _write_src_init(tmp_path, "myapp", "1.0.0")
        # Also create flat layout with same version
        flat = tmp_path / "myapp"
        flat.mkdir()
        (flat / "__init__.py").write_text('__version__ = "1.0.0"\n')

        version, sources = audit_versions(tmp_path)
        assert version == Version("1.0.0")
        # src/ version should be found; flat may or may not be (src/ comes first)
        src_paths = [s for s in sources if "src" in str(s.file_path)]
        assert len(src_paths) >= 1

    def test_mismatch_raises(self, tmp_path: pytest.TempPathFactory) -> None:
        """Different versions across files should raise AuditError."""
        _write_pyproject(tmp_path, "my-app", "1.0.0")
        _write_src_init(tmp_path, "my_app", "0.9.0")

        with pytest.raises(AuditError, match="Version mismatch detected"):
            audit_versions(tmp_path)

    def test_three_way_mismatch(self, tmp_path: pytest.TempPathFactory) -> None:
        """Three files, three different versions."""
        _write_pyproject(tmp_path, "my-app", "1.0.0")
        _write_src_init(tmp_path, "my_app", "1.0.1")
        _write_src_main(tmp_path, "my_app", "1.0.2")

        with pytest.raises(AuditError, match="Version mismatch detected"):
            audit_versions(tmp_path)

    def test_no_sources_raises(self, tmp_path: pytest.TempPathFactory) -> None:
        """No pyproject.toml and no Python files should raise."""
        with pytest.raises(AuditError, match="No version strings found"):
            audit_versions(tmp_path)

    def test_pyproject_only_warns(
        self, tmp_path: pytest.TempPathFactory, capsys: pytest.CaptureFixture
    ) -> None:
        """Single source (pyproject.toml only) should warn but succeed."""
        _write_pyproject(tmp_path, "my-app", "2.0.0")

        version, sources = audit_versions(tmp_path)
        assert version == Version("2.0.0")
        assert len(sources) == 1
        assert "WARNING" in capsys.readouterr().out

    def test_invalid_pep440_version_raises(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        """A version like 'banana' should fail PEP 440 validation."""
        _write_pyproject(tmp_path, "my-app", "banana")

        with pytest.raises(AuditError, match="not PEP 440 compliant"):
            audit_versions(tmp_path)

    def test_hyphenated_package_name_maps_to_underscore(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        """Package 'my-cool-app' should find module 'my_cool_app'."""
        _write_pyproject(tmp_path, "my-cool-app", "0.1.0")
        _write_src_init(tmp_path, "my_cool_app", "0.1.0")

        version, sources = audit_versions(tmp_path)
        assert version == Version("0.1.0")
        assert len(sources) == 2

    def test_pyproject_missing_version_field(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        """pyproject.toml exists but has no version — only __init__.py counts."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "myapp"\n', encoding="utf-8"
        )
        _write_src_init(tmp_path, "myapp", "1.0.0")

        version, sources = audit_versions(tmp_path)
        assert version == Version("1.0.0")
        assert len(sources) == 1

    def test_malformed_toml_raises(self, tmp_path: pytest.TempPathFactory) -> None:
        """Corrupt pyproject.toml should raise AuditError, not crash."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("this is not valid toml [[[", encoding="utf-8")

        with pytest.raises(AuditError, match="Failed to parse"):
            audit_versions(tmp_path)

    def test_all_three_files_consistent(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        """pyproject.toml + __init__.py + __main__.py all matching."""
        _write_pyproject(tmp_path, "my-app", "3.0.0a1")
        _write_src_init(tmp_path, "my_app", "3.0.0a1")
        _write_src_main(tmp_path, "my_app", "3.0.0a1")

        version, sources = audit_versions(tmp_path)
        assert version == Version("3.0.0a1")
        assert len(sources) == 3


# ---------------------------------------------------------------------------
# Helpers for building fake app directories
# ---------------------------------------------------------------------------


def _write_pyproject(tmp_path, name: str, version: str) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        f'[project]\nname = "{name}"\nversion = "{version}"\n',
        encoding="utf-8",
    )


def _write_src_init(tmp_path, module_name: str, version: str) -> None:
    pkg = tmp_path / "src" / module_name
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text(f'__version__ = "{version}"\n')


def _write_src_main(tmp_path, module_name: str, version: str) -> None:
    pkg = tmp_path / "src" / module_name
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__main__.py").write_text(f'__version__ = "{version}"\n')
