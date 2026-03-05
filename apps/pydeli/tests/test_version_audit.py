"""Tests for pydeli.version_audit module."""

import pytest

from packaging.version import Version

from pydeli.errors import VersionError
from pydeli.version_audit import audit_versions, collect_version_sources


def _write_pyproject(app_dir, version="0.1.0", name="testapp"):
    (app_dir / "pyproject.toml").write_text(
        f'[project]\nname = "{name}"\nversion = "{version}"\n'
    )


def _write_init(module_dir, version="0.1.0"):
    module_dir.mkdir(parents=True, exist_ok=True)
    (module_dir / "__init__.py").write_text(f'__version__ = "{version}"\n')


def _write_main(module_dir, version="0.1.0"):
    module_dir.mkdir(parents=True, exist_ok=True)
    (module_dir / "__main__.py").write_text(f'__version__ = "{version}"\n')


class TestCollectVersionSources:
    def test_pyproject_only(self, tmp_path):
        _write_pyproject(tmp_path)
        sources = collect_version_sources(tmp_path)
        assert len(sources) == 1
        assert sources[0].version_string == "0.1.0"
        assert "pyproject.toml" in sources[0].label

    def test_all_three_sources(self, tmp_path):
        _write_pyproject(tmp_path, name="testapp")
        mod = tmp_path / "src" / "testapp"
        _write_init(mod)
        _write_main(mod)
        sources = collect_version_sources(tmp_path)
        assert len(sources) == 3

    def test_flat_layout(self, tmp_path):
        _write_pyproject(tmp_path, name="testapp")
        mod = tmp_path / "testapp"
        _write_init(mod)
        sources = collect_version_sources(tmp_path)
        assert len(sources) == 2

    def test_single_quote_version(self, tmp_path):
        _write_pyproject(tmp_path, name="testapp")
        mod = tmp_path / "src" / "testapp"
        mod.mkdir(parents=True, exist_ok=True)
        (mod / "__init__.py").write_text("__version__ = '0.1.0'\n")
        sources = collect_version_sources(tmp_path)
        assert len(sources) == 2
        assert sources[1].version_string == "0.1.0"


class TestAuditVersions:
    def test_consistent_versions(self, tmp_path):
        _write_pyproject(tmp_path, name="testapp")
        mod = tmp_path / "src" / "testapp"
        _write_init(mod)
        _write_main(mod)
        evidence = audit_versions(tmp_path)
        assert evidence.resolved_version == Version("0.1.0")
        assert len(evidence.sources) == 3

    def test_inconsistent_versions_raises(self, tmp_path):
        _write_pyproject(tmp_path, version="0.1.0", name="testapp")
        mod = tmp_path / "src" / "testapp"
        _write_init(mod, version="0.2.0")
        with pytest.raises(VersionError, match="mismatch"):
            audit_versions(tmp_path)

    def test_no_sources_raises(self, tmp_path):
        with pytest.raises(VersionError, match="No version sources"):
            audit_versions(tmp_path)

    def test_invalid_pep440_raises(self, tmp_path):
        _write_pyproject(tmp_path, version="not-a-version", name="testapp")
        with pytest.raises(VersionError, match="not valid PEP 440"):
            audit_versions(tmp_path)

    def test_dev_version(self, tmp_path):
        _write_pyproject(tmp_path, version="0.1.0.dev1", name="testapp")
        mod = tmp_path / "src" / "testapp"
        _write_init(mod, version="0.1.0.dev1")
        evidence = audit_versions(tmp_path)
        assert evidence.resolved_version == Version("0.1.0.dev1")
        assert evidence.resolved_version.is_devrelease

    def test_prerelease_version(self, tmp_path):
        _write_pyproject(tmp_path, version="1.0.0a1", name="testapp")
        evidence = audit_versions(tmp_path)
        assert evidence.resolved_version.is_prerelease
