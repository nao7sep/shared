"""Workflow orchestration: preflight-only and full publish flows.

Stage order (full publish):
1. Resolve and validate paths
2. Load local version evidence
3. Enforce version consistency
4. Query TestPyPI and PyPI for existing versions
5. Ensure the local version is publishable
6. Ensure required credentials and bootstrap state exist
7. Build artifacts
8. Archive artifacts locally
9. Publish to TestPyPI
10. Verify installed package in isolation
11. Ask whether to publish to PyPI
12. Publish to PyPI if approved

Preflight stops before any publish and may reuse the same archive paths.
"""

from __future__ import annotations

from pathlib import Path


from . import ui
from .archive_store import archive_artifacts
from .builder import build_app
from .errors import VersionError
from .models import (
    Registry,
    RegistryVersionInfo,
    ReleaseTarget,
    RunSummary,
    TokenScope,
    VersionEvidence,
    WorkflowMode,
)
from .publisher import publish_to_registry
from .registry_client import check_version_publishable, query_registry
from .state_store import load_credential, update_credential_token
from .verifier import verify_testpypi_install
from .version_audit import audit_versions, _discover_module_name


def _detect_project_name(app_dir: Path) -> str:
    """Read project name from pyproject.toml."""
    import tomllib

    try:
        with open(app_dir / "pyproject.toml", "rb") as f:
            data = tomllib.load(f)
        name = data.get("project", {}).get("name")
        if not name:
            raise ValueError("No project.name in pyproject.toml")
        return str(name)
    except Exception as e:
        raise VersionError(f"Failed to read project name from pyproject.toml: {e}") from e


def _detect_entry_point(app_dir: Path) -> str | None:
    """Read the first entry point name from pyproject.toml [project.scripts]."""
    import tomllib

    try:
        with open(app_dir / "pyproject.toml", "rb") as f:
            data = tomllib.load(f)
        scripts = data.get("project", {}).get("scripts", {})
        if scripts:
            return next(iter(scripts))
        return None
    except Exception:
        return None


def _show_version_evidence(evidence: VersionEvidence) -> None:
    rows = [(s.label, s.version_string) for s in evidence.sources]
    ui.version_table("Local Version Sources", rows, highlight_col=1)


def _show_registry_state(
    testpypi: RegistryVersionInfo, pypi: RegistryVersionInfo
) -> None:
    rows: list[tuple[str, str]] = []
    if testpypi.latest_version:
        rows.append(("TestPyPI latest", str(testpypi.latest_version)))
    else:
        rows.append(("TestPyPI", "No releases found"))
    if pypi.latest_version:
        rows.append(("PyPI latest", str(pypi.latest_version)))
    else:
        rows.append(("PyPI", "No releases found"))
    ui.key_value_block(rows)


def _ensure_credential(
    registry: Registry,
    project_name: str,
    testpypi_info: RegistryVersionInfo | None = None,
) -> str:
    """Ensure a credential exists for the registry, running bootstrap if needed."""
    cred = load_credential(registry, project_name)

    if cred and cred.token_value:
        # Check if rotation is needed
        if cred.needs_rotation:
            ui.warning(
                f"Your {registry.display_name} token for {project_name} is account-scoped "
                "and should be rotated to a project-scoped token."
            )
            rotate = ui.confirm("Would you like to rotate to a project-scoped token now?")
            if rotate:
                return _run_token_entry(registry, project_name, scope=TokenScope.PROJECT, needs_rotation=False)
        return cred.token_value

    # No credential — run bootstrap
    return _run_bootstrap(registry, project_name, testpypi_info)


def _run_bootstrap(
    registry: Registry,
    project_name: str,
    testpypi_info: RegistryVersionInfo | None = None,
) -> str:
    """Guide user through first-release token setup."""
    is_first_release = testpypi_info is not None and not testpypi_info.exists

    ui.info(f"No {registry.display_name} token found for {project_name}.")

    if is_first_release:
        ui.info_continuation(
            "This appears to be the first release. You will need an account-wide API token."
        )
        ui.info_continuation(
            f"\n1. Go to {registry.url}/manage/account/#api-tokens"
        )
        ui.info_continuation(
            "2. Create an API token with scope: Entire account"
        )
        ui.info_continuation(
            "3. Copy the token (starts with 'pypi-')"
        )
        token = ui.secret_input(f"Paste your {registry.display_name} account-wide API token")
        update_credential_token(
            registry, project_name, token,
            scope=TokenScope.ACCOUNT, needs_rotation=True,
        )
        return token
    else:
        ui.info_continuation(
            f"The project already exists on {registry.display_name}. "
            f"You can use a project-scoped token."
        )
        ui.info_continuation(
            f"\n1. Go to {registry.url}/manage/project/{project_name}/settings/"
        )
        ui.info_continuation(
            "2. Create an API token scoped to this project"
        )
        ui.info_continuation(
            "3. Copy the token (starts with 'pypi-')"
        )
        return _run_token_entry(registry, project_name, scope=TokenScope.PROJECT, needs_rotation=False)


def _run_token_entry(
    registry: Registry,
    project_name: str,
    scope: TokenScope,
    needs_rotation: bool,
) -> str:
    """Prompt for a token and persist it."""
    token = ui.secret_input(f"Paste your {registry.display_name} API token")
    update_credential_token(registry, project_name, token, scope=scope, needs_rotation=needs_rotation)
    ui.success_message(f"{registry.display_name} token saved.")
    return token


def run_wizard(app_dir: Path, archive_dir: Path) -> None:
    """Main wizard entry point."""

    # Step 1-2: Version audit
    ui.progress_message("Checking version sources...")
    evidence = audit_versions(app_dir)
    _show_version_evidence(evidence)
    version = evidence.resolved_version

    # Detect project/module info
    project_name = _detect_project_name(app_dir)
    module_name = _discover_module_name(app_dir) or project_name.replace("-", "_")
    entry_point = _detect_entry_point(app_dir)

    ui.key_value_block([
        ("Project", project_name),
        ("Module", module_name),
        ("Version", str(version)),
        ("App dir", str(app_dir)),
        ("Archive", str(archive_dir)),
    ])

    # Step 3: Choose workflow mode
    mode_choice = ui.select(
        "Select workflow mode:",
        ["Publish (TestPyPI → verify → PyPI)", "Preflight only (build and archive)"],
    )
    mode = WorkflowMode.PUBLISH if mode_choice.startswith("Publish") else WorkflowMode.PREFLIGHT

    target = ReleaseTarget(
        app_dir=app_dir,
        archive_dir=archive_dir,
        project_name=project_name,
        module_name=module_name,
        version=version,
        version_evidence=evidence,
    )

    summary = RunSummary(target=target, mode=mode)

    # Step 4: Query registries
    ui.progress_message("Querying registries...")
    testpypi_info = query_registry(Registry.TESTPYPI, project_name)
    pypi_info = query_registry(Registry.PYPI, project_name)
    _show_registry_state(testpypi_info, pypi_info)

    # Step 5: Check publishability (for publish mode)
    if mode == WorkflowMode.PUBLISH:
        problems = check_version_publishable(version, testpypi_info, pypi_info)
        if problems:
            for p in problems:
                ui.warning(p)
            ui.info("Update version strings in your source files and rerun pydeli.")
            return

        ui.success_message(f"Version {version} is publishable.")

    # Step 6: Build
    ui.progress_message("Building...")
    build_result = build_app(app_dir)
    summary.build_result = build_result

    for artifact in build_result.artifacts:
        ui.info_continuation(f"  Built: {artifact.filename}")

    # Step 7: Archive
    ui.progress_message("Archiving artifacts...")
    archive_version_dir = archive_artifacts(archive_dir, version, build_result.artifacts)
    ui.success_message(f"Archived to {archive_version_dir}")

    if mode == WorkflowMode.PREFLIGHT:
        ui.farewell(f"Preflight complete for {project_name} {version}.")
        return

    # Step 8: Ensure TestPyPI credentials
    testpypi_token = _ensure_credential(Registry.TESTPYPI, project_name, testpypi_info)

    # Step 9: Publish to TestPyPI
    if not ui.confirm(f"Publish {version} to TestPyPI?", default=True):
        ui.farewell("Publish canceled.")
        return

    ui.progress_message("Publishing to TestPyPI...")
    testpypi_result = publish_to_registry(
        Registry.TESTPYPI, build_result.artifacts, testpypi_token, version,
    )
    summary.testpypi_result = testpypi_result
    ui.success_message(testpypi_result.message)

    # Step 10: Verify
    ui.progress_message("Verifying installation from TestPyPI...")
    verification = verify_testpypi_install(project_name, version, entry_point)
    summary.verification_result = verification

    if verification.success:
        ui.success_message(verification.message)
        if verification.command_output:
            ui.info_continuation(f"  Output: {verification.command_output}")
    else:
        ui.warning(f"Verification failed: {verification.message}")
        if verification.command_output:
            ui.info_continuation(f"  Output: {verification.command_output}")
        proceed = ui.confirm("Verification failed. Proceed to PyPI anyway?", default=False)
        if not proceed:
            ui.farewell("Stopped after TestPyPI publish. PyPI publish skipped.")
            return

    # Step 11: Ensure PyPI credentials
    pypi_token = _ensure_credential(Registry.PYPI, project_name, pypi_info)

    # Step 12: Publish to PyPI
    if not ui.confirm(f"Publish {version} to PyPI?", default=True):
        ui.farewell("PyPI publish skipped.")
        return

    ui.progress_message("Publishing to PyPI...")
    pypi_result = publish_to_registry(
        Registry.PYPI, build_result.artifacts, pypi_token, version,
    )
    summary.pypi_result = pypi_result
    ui.success_message(pypi_result.message)

    ui.farewell(f"Release complete: {project_name} {version}")
