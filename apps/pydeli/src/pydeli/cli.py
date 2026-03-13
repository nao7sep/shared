from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from getpass import getpass
from pathlib import Path

if sys.platform != "win32":
    import readline  # noqa: F401  # enables line-editing and arrow keys in input()
    readline.set_auto_history(False)

from .archiver import archive
from .auditor import audit_versions
from .builder import build
from .config import get_token, load_config, save_config, set_token
from .errors import PydeliError
from .models import RegistryTarget, RunMode
from .output_segments import start_segment
from .publisher import publish
from .registry import check_version_exists
from .verifier import verify

WINDOWS_DRIVE_RELATIVE_PATTERN = re.compile(r"^[A-Za-z]:(?![\\/])")

TOKEN_URLS = {
    RegistryTarget.TESTPYPI: "https://test.pypi.org/manage/account/token/",
    RegistryTarget.PYPI: "https://pypi.org/manage/account/token/",
}

TOKEN_ROTATION_MESSAGE = (
    "If you haven't already, consider switching from an account-wide token "
    "to a project-scoped token for this app on {target_name}. "
    "Project-scoped tokens limit the blast radius if the token is ever compromised."
)


def run() -> None:
    """Main workflow orchestrator."""
    args = _parse_args()

    # Collect all parameters (from CLI args or interactive prompts).
    target = _resolve_target(args.target)
    mode = _resolve_mode(args.dry_run, args.wet_run)
    app_dir = _resolve_app_dir(args.app_dir)
    archive_dir = _resolve_archive_dir(args.archive_dir)

    # Audit version consistency.
    start_segment()
    print("Auditing versions...")
    version, sources = audit_versions(app_dir)
    max_label_len = max(len(str(s.file_path)) for s in sources) + 1
    for source in sources:
        label = f"{source.file_path}:"
        print(f"  {label:<{max_label_len}}  {source.version_string}")
    print(f"Local version: {version}")

    # Read package name from pyproject.toml for registry queries.
    package_name = _read_package_name(app_dir)
    entry_point_name = _read_entry_point_name(app_dir)

    # Check version against target registry.
    start_segment()
    print(f"Checking {target.display_name} for {package_name} {version}...")
    if check_version_exists(package_name, version, target):
        raise PydeliError(
            f"Version {version} already exists on {target.display_name}. "
            "Bump the version in your source files and run again."
        )
    print(f"Version {version} is available on {target.display_name}.")

    # Token management.
    start_segment()
    config = load_config()
    token = get_token(config, package_name, target)
    if token is None:
        token = _guide_token_setup(config, package_name, target)
    else:
        print(f"Using stored {target.display_name} token for {package_name}.")
        print(TOKEN_ROTATION_MESSAGE.format(target_name=target.display_name))

    # Build.
    start_segment()
    print(f"Building {package_name}...")
    artifacts = build(app_dir)
    for artifact in artifacts:
        print(f"  {artifact.file_path.name}")
    print("Build succeeded.")

    # Archive.
    start_segment()
    dest = archive(artifacts, archive_dir, package_name)
    print(f"Archived to {dest}")

    # Publish (wet-run only).
    if mode is RunMode.DRY:
        start_segment()
        print("Dry run complete. No upload performed.")
        return

    start_segment()
    print(f"Publishing to {target.display_name}...")
    publish(artifacts, target, token)
    print(f"Published {package_name} {version} to {target.display_name}.")

    # Verification (wet-run, optional).
    start_segment()
    if _prompt_yes_no(f"Test-install {package_name} from {target.display_name}?"):
        start_segment()
        print("Setting up verification environment...")
        verify(package_name, str(version), entry_point_name, target)
        start_segment()
        print("Verification complete. Temporary environment cleaned up.")


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="pydeli",
        description="Python package release helper.",
    )
    parser.add_argument(
        "app_dir",
        nargs="?",
        default=None,
        help="Path to the app directory to publish.",
    )
    parser.add_argument(
        "--archive-dir",
        default=None,
        help="Root directory for archived build artifacts.",
    )
    parser.add_argument(
        "--target",
        choices=["testpypi", "pypi"],
        default=None,
        help="Target registry (testpypi or pypi).",
    )

    run_group = parser.add_mutually_exclusive_group()
    run_group.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Perform all steps except uploading.",
    )
    run_group.add_argument(
        "--wet-run",
        action="store_true",
        default=False,
        help="Perform all steps including uploading.",
    )

    return parser.parse_args()


# ---------------------------------------------------------------------------
# Parameter resolution (CLI arg or interactive prompt)
# ---------------------------------------------------------------------------


def _resolve_target(cli_value: str | None) -> RegistryTarget:
    if cli_value is not None:
        return RegistryTarget(cli_value)

    start_segment()
    print("Select target registry:")
    print("  1) TestPyPI")
    print("  2) PyPI")

    while True:
        choice = input("Choice [1/2]: ").strip()
        if choice == "1":
            return RegistryTarget.TESTPYPI
        if choice == "2":
            return RegistryTarget.PYPI
        print("Invalid choice. Enter 1 or 2.")


def _resolve_mode(dry_run: bool, wet_run: bool) -> RunMode:
    if dry_run:
        return RunMode.DRY
    if wet_run:
        return RunMode.WET

    start_segment()
    print("Select run mode:")
    print("  1) Dry run (build and archive only, no upload)")
    print("  2) Wet run (build, archive, and upload)")

    while True:
        choice = input("Choice [1/2]: ").strip()
        if choice == "1":
            return RunMode.DRY
        if choice == "2":
            return RunMode.WET
        print("Invalid choice. Enter 1 or 2.")


def _resolve_app_dir(cli_value: str | None) -> Path:
    if cli_value is not None:
        return _validate_app_dir(_map_user_path(cli_value))

    start_segment()
    while True:
        raw = input("App directory path: ").strip()
        if not raw:
            print("Input cannot be empty.")
            continue
        try:
            path = _map_user_path(raw)
            return _validate_app_dir(path)
        except PydeliError as exc:
            print(f"Error: {exc}")


def _resolve_archive_dir(cli_value: str | None) -> Path:
    if cli_value is not None:
        return _map_user_path(cli_value)

    start_segment()
    while True:
        raw = input("Archive root directory: ").strip()
        if not raw:
            print("Input cannot be empty.")
            continue
        try:
            return _map_user_path(raw)
        except PydeliError as exc:
            print(f"Error: {exc}")


def _validate_app_dir(path: Path) -> Path:
    if not path.is_dir():
        raise PydeliError(f"Directory not found: {path}")
    if not (path / "pyproject.toml").is_file():
        raise PydeliError(f"No pyproject.toml found in {path}")
    return path


# ---------------------------------------------------------------------------
# Path mapping
# ---------------------------------------------------------------------------


def _map_user_path(raw: str) -> Path:
    """Map user path input to an absolute Path.

    Supports absolute paths, ~ (home), and basic relative paths.
    Rejects ambiguous Windows forms.
    """
    normalized = unicodedata.normalize("NFC", raw.strip())
    if not normalized:
        raise PydeliError("Path input cannot be empty.")
    if "\0" in normalized:
        raise PydeliError("Path input cannot contain NUL.")

    normalized = normalized.replace("\\", "/")

    if WINDOWS_DRIVE_RELATIVE_PATTERN.match(normalized):
        raise PydeliError(
            "Windows rooted path forms like '\\temp' and 'C:temp' are not supported."
        )

    if normalized.startswith("~"):
        return Path(normalized).expanduser().resolve()

    candidate = Path(normalized)
    if candidate.is_absolute():
        return candidate.resolve()

    # Allow simple relative paths resolved from cwd as a convenience.
    return candidate.resolve()


# ---------------------------------------------------------------------------
# Token setup
# ---------------------------------------------------------------------------


def _guide_token_setup(
    config: dict, package_name: str, target: RegistryTarget
) -> str:
    """Walk the user through creating and saving a token."""
    url = TOKEN_URLS[target]

    print(f"No {target.display_name} token found for '{package_name}'.")
    print("To create a token:")
    print(f"  1. Go to: {url}")
    print("  2. Create a token (account-wide for first-time, or project-scoped).")
    print("  3. Paste the token below.")

    while True:
        token = getpass("Token: ").strip()
        if token:
            break
        print("Token cannot be empty.")

    set_token(config, package_name, target, token)
    save_config(config)
    print(f"Token saved for {package_name} on {target.display_name}.")
    print(TOKEN_ROTATION_MESSAGE.format(target_name=target.display_name))
    return token


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _prompt_yes_no(question: str) -> bool:
    """Ask a yes/no question and return True for yes."""
    while True:
        answer = input(f"{question} (y/n): ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("Please answer y or n.")


def _read_package_name(app_dir: Path) -> str:
    """Read the package name from pyproject.toml."""
    import tomllib

    pyproject_path = app_dir / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    name = data.get("project", {}).get("name")
    if not isinstance(name, str) or not name:
        raise PydeliError(f"No [project].name found in {pyproject_path}")
    return name


def _read_entry_point_name(app_dir: Path) -> str:
    """Read the first console script entry point name from pyproject.toml.

    Falls back to the package name if no entry point is defined.
    """
    import tomllib

    pyproject_path = app_dir / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    scripts = data.get("project", {}).get("scripts", {})
    if scripts:
        return next(iter(scripts))

    name = data.get("project", {}).get("name", "")
    return name.replace("-", "_") if name else "app"
