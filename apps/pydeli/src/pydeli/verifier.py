from __future__ import annotations

import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .errors import VerificationError
from .models import RegistryTarget

TESTPYPI_INDEX_URL = "https://test.pypi.org/simple/"
PYPI_INDEX_URL = "https://pypi.org/simple/"

VERIFICATION_CONFIRM_STRING = "ok"


def verify(
    package_name: str,
    version_string: str,
    entry_point_name: str,
    target: RegistryTarget,
) -> None:
    """Test-install the published package in a temporary venv and let the user try it.

    Creates a temp venv, installs the package from the target registry, opens a
    separate terminal window for the user to interact with the app, waits for
    confirmation, then cleans up.
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="pydeli-verify-"))

    try:
        _create_venv(tmp_dir)
        _install_package(tmp_dir, package_name, version_string, target)
        _run_in_terminal(tmp_dir, entry_point_name)
        _wait_for_confirmation()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _create_venv(tmp_dir: Path) -> None:
    """Create a virtual environment in the temp directory."""
    venv_dir = tmp_dir / "venv"
    try:
        subprocess.run(
            ["uv", "venv", str(venv_dir)],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else "No error output."
        raise VerificationError(f"Failed to create virtual environment:\n{stderr}") from exc

    if not venv_dir.exists():
        raise VerificationError(f"Virtual environment was not created: {venv_dir}")


def _install_package(
    tmp_dir: Path,
    package_name: str,
    version_string: str,
    target: RegistryTarget,
) -> None:
    """Install the package from the target registry into the temp venv."""
    venv_dir = tmp_dir / "venv"
    python_path = _get_venv_python(venv_dir)

    cmd = [
        "uv",
        "pip",
        "install",
        "--python",
        str(python_path),
        f"{package_name}=={version_string}",
    ]

    if target is RegistryTarget.TESTPYPI:
        cmd.extend(["--index-url", TESTPYPI_INDEX_URL])
        cmd.extend(["--extra-index-url", PYPI_INDEX_URL])

    try:
        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else "No error output."
        raise VerificationError(
            f"Failed to install {package_name}=={version_string} from "
            f"{target.display_name}:\n{stderr}"
        ) from exc


def _run_in_terminal(tmp_dir: Path, entry_point_name: str) -> None:
    """Open the installed app in a separate terminal window for user testing."""
    venv_dir = tmp_dir / "venv"
    bin_dir = _get_venv_bin_dir(venv_dir)
    app_path = bin_dir / entry_point_name

    if not app_path.exists():
        raise VerificationError(
            f"Entry point not found in venv: {app_path}\n"
            f"The package may not define a console script named '{entry_point_name}'."
        )

    system = platform.system()

    if system == "Darwin":
        _open_macos_terminal(venv_dir, entry_point_name)
    elif system == "Windows":
        _open_windows_terminal(venv_dir, entry_point_name)
    elif system == "Linux":
        _open_linux_terminal(venv_dir, entry_point_name)
    else:
        _print_manual_instructions(venv_dir, entry_point_name)


def _open_macos_terminal(venv_dir: Path, entry_point_name: str) -> None:
    """Open a new Terminal.app window with the venv activated and the app running."""
    bin_dir = venv_dir / "bin"
    script = f'source "{bin_dir}/activate" && "{bin_dir}/{entry_point_name}" ; echo "\\nApp exited. You can close this window." && read'

    try:
        subprocess.Popen(
            [
                "osascript",
                "-e",
                f'tell application "Terminal" to do script "{script}"',
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        _print_manual_instructions(venv_dir, entry_point_name)
        return

    print(f"Opened a new Terminal window running '{entry_point_name}'.")
    print("Test the app in that window.")


def _open_windows_terminal(venv_dir: Path, entry_point_name: str) -> None:
    """Open a new cmd window with the venv activated and the app running."""
    scripts_dir = venv_dir / "Scripts"
    cmd = f'"{scripts_dir}\\activate.bat" && "{scripts_dir}\\{entry_point_name}.exe" && echo. && echo App exited. You can close this window. && pause'

    try:
        subprocess.Popen(
            ["cmd", "/c", "start", "cmd", "/k", cmd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        _print_manual_instructions(venv_dir, entry_point_name)
        return

    print(f"Opened a new command prompt running '{entry_point_name}'.")
    print("Test the app in that window.")


def _open_linux_terminal(venv_dir: Path, entry_point_name: str) -> None:
    """Try to open a terminal emulator on Linux."""
    bin_dir = venv_dir / "bin"
    shell_cmd = f'source "{bin_dir}/activate" && "{bin_dir}/{entry_point_name}" ; echo "App exited. Press Enter to close." && read'

    terminals = [
        ["gnome-terminal", "--", "bash", "-c", shell_cmd],
        ["xfce4-terminal", "-e", f"bash -c '{shell_cmd}'"],
        ["konsole", "-e", "bash", "-c", shell_cmd],
        ["xterm", "-e", f"bash -c '{shell_cmd}'"],
    ]

    for terminal_cmd in terminals:
        try:
            subprocess.Popen(
                terminal_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print(f"Opened a terminal window running '{entry_point_name}'.")
            print("Test the app in that window.")
            return
        except OSError:
            continue

    _print_manual_instructions(venv_dir, entry_point_name)


def _print_manual_instructions(venv_dir: Path, entry_point_name: str) -> None:
    """Print instructions for manual testing when no terminal can be opened."""
    bin_dir = _get_venv_bin_dir(venv_dir)
    print("Could not open a separate terminal window automatically.")
    print("To test the app manually, open a new terminal and run:")
    print(f"  source \"{bin_dir}/activate\"")
    print(f"  {entry_point_name}")


def _wait_for_confirmation() -> None:
    """Wait for the user to type the confirmation string."""
    print()
    print(f"Type '{VERIFICATION_CONFIRM_STRING}' and press Enter when you are done testing.")

    while True:
        try:
            response = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            raise VerificationError("Verification canceled.")
        if response == VERIFICATION_CONFIRM_STRING:
            return
        print(f"Please type '{VERIFICATION_CONFIRM_STRING}' to continue.")


def _get_venv_python(venv_dir: Path) -> Path:
    """Return the path to the Python executable in the venv."""
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _get_venv_bin_dir(venv_dir: Path) -> Path:
    """Return the bin/Scripts directory of the venv."""
    if sys.platform == "win32":
        return venv_dir / "Scripts"
    return venv_dir / "bin"
