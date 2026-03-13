from __future__ import annotations

import json
import urllib.error
import urllib.request

from packaging.version import Version

from .errors import RegistryError
from .models import RegistryTarget

PYPI_API_URL = "https://pypi.org/pypi/{package}/json"
TESTPYPI_API_URL = "https://test.pypi.org/pypi/{package}/json"


def check_version_exists(
    package_name: str, version: Version, target: RegistryTarget
) -> bool:
    """Check whether a specific version of a package exists on the target registry.

    Returns True if the version already exists, False if it does not.
    Returns False if the package itself does not exist (first-time publication).
    Raises RegistryError on network or unexpected errors.
    """
    api_url = _get_api_url(target).format(package=package_name)

    try:
        request = urllib.request.Request(api_url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            # Package does not exist on the registry — first-time publication.
            return False
        raise RegistryError(
            f"Failed to query {target.display_name} for {package_name}: "
            f"HTTP {exc.code}"
        ) from exc
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        raise RegistryError(
            f"Failed to query {target.display_name} for {package_name}: {exc}"
        ) from exc

    releases = data.get("releases", {})
    return str(version) in releases


def _get_api_url(target: RegistryTarget) -> str:
    if target is RegistryTarget.TESTPYPI:
        return TESTPYPI_API_URL
    return PYPI_API_URL
