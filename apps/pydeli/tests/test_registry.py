"""Tests for pydeli.registry_client module."""

from packaging.version import Version

from pydeli.models import Registry, RegistryVersionInfo
from pydeli.registry_client import check_version_publishable


class TestCheckVersionPublishable:
    def _make_info(self, registry, versions_str=None):
        versions = [Version(v) for v in (versions_str or [])]
        versions.sort()
        return RegistryVersionInfo(
            registry=registry,
            project_name="testpkg",
            versions=versions,
            latest_version=versions[-1] if versions else None,
        )

    def test_fresh_project_publishable(self):
        testpypi = self._make_info(Registry.TESTPYPI)
        pypi = self._make_info(Registry.PYPI)
        problems = check_version_publishable(Version("0.1.0"), testpypi, pypi)
        assert problems == []

    def test_version_exists_on_testpypi(self):
        testpypi = self._make_info(Registry.TESTPYPI, ["0.1.0"])
        pypi = self._make_info(Registry.PYPI)
        problems = check_version_publishable(Version("0.1.0"), testpypi, pypi)
        assert any("already exists on TestPyPI" in p for p in problems)

    def test_version_exists_on_pypi(self):
        testpypi = self._make_info(Registry.TESTPYPI)
        pypi = self._make_info(Registry.PYPI, ["0.1.0"])
        problems = check_version_publishable(Version("0.1.0"), testpypi, pypi)
        assert any("already exists on PyPI" in p for p in problems)

    def test_not_newer_than_testpypi(self):
        testpypi = self._make_info(Registry.TESTPYPI, ["0.2.0"])
        pypi = self._make_info(Registry.PYPI)
        problems = check_version_publishable(Version("0.1.0"), testpypi, pypi)
        assert any("not newer" in p for p in problems)

    def test_not_newer_than_pypi(self):
        testpypi = self._make_info(Registry.TESTPYPI)
        pypi = self._make_info(Registry.PYPI, ["1.0.0"])
        problems = check_version_publishable(Version("0.1.0"), testpypi, pypi)
        assert any("not newer" in p for p in problems)

    def test_newer_version_publishable(self):
        testpypi = self._make_info(Registry.TESTPYPI, ["0.1.0"])
        pypi = self._make_info(Registry.PYPI, ["0.1.0"])
        problems = check_version_publishable(Version("0.2.0"), testpypi, pypi)
        assert problems == []

    def test_pep440_ordering(self):
        """dev < alpha < beta < rc < final < post."""
        testpypi = self._make_info(Registry.TESTPYPI, ["1.0.0a1"])
        pypi = self._make_info(Registry.PYPI)
        # beta is newer than alpha
        problems = check_version_publishable(Version("1.0.0b1"), testpypi, pypi)
        assert problems == []
        # dev is older than alpha
        problems = check_version_publishable(Version("1.0.0.dev1"), testpypi, pypi)
        assert any("not newer" in p for p in problems)


class TestRegistryModel:
    def test_display_names(self):
        assert Registry.TESTPYPI.display_name == "TestPyPI"
        assert Registry.PYPI.display_name == "PyPI"

    def test_urls(self):
        assert "test.pypi.org" in Registry.TESTPYPI.url
        assert "pypi.org" in Registry.PYPI.url
        assert "test.pypi.org" not in Registry.PYPI.url

    def test_upload_urls(self):
        assert "legacy" in Registry.TESTPYPI.upload_url
        assert "legacy" in Registry.PYPI.upload_url
