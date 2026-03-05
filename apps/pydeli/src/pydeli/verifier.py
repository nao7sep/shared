"""Post-publish verification in an ephemeral environment.

Creates a temporary venv, installs the exact uploaded version from TestPyPI
(with PyPI as fallback for dependencies), and runs a basic smoke test.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from packaging.version import Version

from .errors import VerificationError
from .models import Registry, VerificationResult


def verify_testpypi_install(
    project_name: str,
    version: Version,
    entry_point: str | None = None,
) -> VerificationResult:
    """Install the package from TestPyPI in an isolated temp environment and smoke-test it.

    Uses TestPyPI as the primary index and PyPI as fallback for dependencies.
    If entry_point is provided, runs `<entry_point> --version` as the smoke test.
    Otherwise runs `python -c "import <module>"`.
    """
    with tempfile.TemporaryDirectory(prefix="pydeli-verify-") as tmp:
        venv_dir = Path(tmp) / ".venv"

        # Create isolated venv
        try:
            subprocess.run(
                ["uv", "venv", str(venv_dir)],
                capture_output=True,
                text=True,
                timeout=60,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise VerificationError(f"Failed to create verification venv: {e.stderr}")
        except FileNotFoundError:
            raise VerificationError("uv is not installed or not on PATH.")

        # Install from TestPyPI with PyPI fallback
        install_spec = f"{project_name}=={version}"
        try:
            result = subprocess.run(
                [
                    "uv", "pip", "install",
                    "--python", str(venv_dir / "bin" / "python"),
                    "--index-url", Registry.TESTPYPI.simple_url,
                    "--extra-index-url", Registry.PYPI.simple_url,
                    install_spec,
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            raise VerificationError("Install from TestPyPI timed out after 120 seconds.")

        if result.returncode != 0:
            return VerificationResult(
                success=False,
                message=f"Failed to install {install_spec} from TestPyPI.",
                command_output=result.stderr.strip(),
            )

        # Smoke test
        python_bin = str(venv_dir / "bin" / "python")
        if entry_point:
            smoke_cmd = [str(venv_dir / "bin" / entry_point), "--version"]
        else:
            module_name = project_name.replace("-", "_")
            smoke_cmd = [python_bin, "-c", f"import {module_name}; print({module_name}.__version__)"]

        try:
            smoke_result = subprocess.run(
                smoke_cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            return VerificationResult(
                success=False,
                message="Smoke test timed out after 30 seconds.",
            )

        if smoke_result.returncode != 0:
            return VerificationResult(
                success=False,
                message="Smoke test failed.",
                command_output=(smoke_result.stderr or smoke_result.stdout).strip(),
            )

        return VerificationResult(
            success=True,
            message=f"Verification passed for {project_name} {version}.",
            command_output=smoke_result.stdout.strip(),
        )
