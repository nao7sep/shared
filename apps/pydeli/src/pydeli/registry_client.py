"""PyPI and TestPyPI JSON API client.

Queries the public JSON API to determine which versions of a project
already exist on each registry. The remote registry is the source of truth.
"""

from __future__ import annotations

import httpx
from packaging.version import InvalidVersion, Version

from .errors import RegistryError
from .models import Registry, RegistryVersionInfo

_TIMEOUT = 15.0


def _json_api_url(registry: Registry, project_name: str) -> str:
    base = registry.url.rstrip("/")
    return f"{base}/pypi/{project_name}/json"


def query_registry(
    registry: Registry, project_name: str
) -> RegistryVersionInfo:
    """Query a registry for all known versions of a project.

    Returns RegistryVersionInfo with an empty version list if the project
    does not exist on the registry (HTTP 404).
    """
    url = _json_api_url(registry, project_name)
    try:
        response = httpx.get(url, timeout=_TIMEOUT, follow_redirects=True)
    except httpx.HTTPError as e:
        raise RegistryError(
            f"Failed to query {registry.display_name} for {project_name}: {e}"
        ) from e

    if response.status_code == 404:
        return RegistryVersionInfo(
            registry=registry,
            project_name=project_name,
            versions=[],
            latest_version=None,
        )

    if response.status_code != 200:
        raise RegistryError(
            f"{registry.display_name} returned HTTP {response.status_code} for {project_name}"
        )

    try:
        data = response.json()
    except ValueError as e:
        raise RegistryError(
            f"Invalid JSON from {registry.display_name} for {project_name}: {e}"
        ) from e

    releases = data.get("releases", {})
    versions: list[Version] = []
    for ver_str in releases:
        try:
            versions.append(Version(ver_str))
        except InvalidVersion:
            continue  # skip unparseable versions

    versions.sort()
    latest = versions[-1] if versions else None

    return RegistryVersionInfo(
        registry=registry,
        project_name=project_name,
        versions=versions,
        latest_version=latest,
    )


def check_version_publishable(
    version: Version,
    testpypi_info: RegistryVersionInfo,
    pypi_info: RegistryVersionInfo,
) -> list[str]:
    """Check whether a version can be published.

    Returns a list of problems. Empty list means publishable.
    """
    problems: list[str] = []

    if testpypi_info.contains(version):
        problems.append(
            f"Version {version} already exists on {testpypi_info.registry.display_name}."
        )

    if pypi_info.contains(version):
        problems.append(
            f"Version {version} already exists on {pypi_info.registry.display_name}."
        )

    if testpypi_info.latest_version is not None and version <= testpypi_info.latest_version:
        problems.append(
            f"Version {version} is not newer than the latest TestPyPI version ({testpypi_info.latest_version})."
        )

    if pypi_info.latest_version is not None and version <= pypi_info.latest_version:
        problems.append(
            f"Version {version} is not newer than the latest PyPI version ({pypi_info.latest_version})."
        )

    return problems
