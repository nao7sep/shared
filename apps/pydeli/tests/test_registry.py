from __future__ import annotations

import json
import urllib.error

import pytest
from packaging.version import Version

from pydeli.errors import RegistryError
from pydeli.models import RegistryTarget
from pydeli.registry import check_version_exists


class TestCheckVersionExists:
    """Registry API interaction with mocked HTTP responses."""

    def test_version_exists(self, monkeypatch) -> None:
        """Known version in releases dict should return True."""
        response_data = {"releases": {"1.0.0": [], "1.1.0": []}}
        monkeypatch.setattr(
            "pydeli.registry.urllib.request.urlopen",
            _mock_urlopen(response_data),
        )
        assert check_version_exists("myapp", Version("1.0.0"), RegistryTarget.PYPI) is True

    def test_version_does_not_exist(self, monkeypatch) -> None:
        """Version not in releases dict should return False."""
        response_data = {"releases": {"1.0.0": []}}
        monkeypatch.setattr(
            "pydeli.registry.urllib.request.urlopen",
            _mock_urlopen(response_data),
        )
        assert check_version_exists("myapp", Version("2.0.0"), RegistryTarget.PYPI) is False

    def test_package_not_found_returns_false(self, monkeypatch) -> None:
        """HTTP 404 means first-time publication — version is available."""
        monkeypatch.setattr(
            "pydeli.registry.urllib.request.urlopen",
            _mock_urlopen_http_error(404),
        )
        assert check_version_exists("myapp", Version("1.0.0"), RegistryTarget.TESTPYPI) is False

    def test_server_error_raises(self, monkeypatch) -> None:
        """HTTP 500 should raise RegistryError, not silently pass."""
        monkeypatch.setattr(
            "pydeli.registry.urllib.request.urlopen",
            _mock_urlopen_http_error(500),
        )
        with pytest.raises(RegistryError, match="HTTP 500"):
            check_version_exists("myapp", Version("1.0.0"), RegistryTarget.PYPI)

    def test_network_failure_raises(self, monkeypatch) -> None:
        """URLError (DNS failure, timeout) should raise RegistryError."""
        def raise_url_error(*args, **kwargs):
            raise urllib.error.URLError("Name resolution failed")

        monkeypatch.setattr(
            "pydeli.registry.urllib.request.urlopen",
            raise_url_error,
        )
        with pytest.raises(RegistryError, match="Name resolution failed"):
            check_version_exists("myapp", Version("1.0.0"), RegistryTarget.PYPI)

    def test_normalized_version_string_lookup(self, monkeypatch) -> None:
        """PEP 440 normalizes '1.0.0.dev01' to '1.0.0.dev1' — the releases
        dict key must match the normalized form."""
        response_data = {"releases": {"1.0.0.dev1": []}}
        monkeypatch.setattr(
            "pydeli.registry.urllib.request.urlopen",
            _mock_urlopen(response_data),
        )
        # packaging.version.Version normalizes dev01 -> dev1
        assert check_version_exists("myapp", Version("1.0.0.dev01"), RegistryTarget.PYPI) is True

    def test_empty_releases_dict(self, monkeypatch) -> None:
        """Package exists but has no releases — version is available."""
        response_data = {"releases": {}}
        monkeypatch.setattr(
            "pydeli.registry.urllib.request.urlopen",
            _mock_urlopen(response_data),
        )
        assert check_version_exists("myapp", Version("1.0.0"), RegistryTarget.PYPI) is False

    def test_uses_testpypi_url(self, monkeypatch) -> None:
        """Verify TestPyPI target hits the correct host."""
        captured_urls: list[str] = []

        original_urlopen = _mock_urlopen({"releases": {}})

        def capturing_urlopen(request, **kwargs):
            captured_urls.append(request.full_url)
            return original_urlopen(request, **kwargs)

        monkeypatch.setattr(
            "pydeli.registry.urllib.request.urlopen",
            capturing_urlopen,
        )
        check_version_exists("myapp", Version("1.0.0"), RegistryTarget.TESTPYPI)
        assert captured_urls[0].startswith("https://test.pypi.org/")


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


class _MockResponse:
    def __init__(self, data: dict) -> None:
        self._data = json.dumps(data).encode("utf-8")

    def read(self) -> bytes:
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def _mock_urlopen(response_data: dict):
    def urlopen(request, **kwargs):
        return _MockResponse(response_data)
    return urlopen


def _mock_urlopen_http_error(code: int):
    def urlopen(request, **kwargs):
        raise urllib.error.HTTPError(
            url=request.full_url,
            code=code,
            msg=f"HTTP {code}",
            hdrs=None,  # type: ignore[arg-type]
            fp=None,
        )
    return urlopen
