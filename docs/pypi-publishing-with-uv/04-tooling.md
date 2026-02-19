# Tooling

`uv tool` for installation, and a publish script for automation.

## Installing uv

```bash
# macOS
brew install uv

# macOS/Linux (official)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## uv tool Commands

`uv tool` installs Python CLI apps into isolated venvs with commands on PATH. Solves the "externally managed environment" error from system Python.

```bash
# Install
uv tool install your-app
uv tool install your-app==0.2.0    # specific version

# Upgrade
uv tool upgrade your-app
uv tool upgrade --all

# Reinstall (force)
uv tool install --force your-app

# List installed
uv tool list

# Uninstall
uv tool uninstall your-app
```

### Troubleshooting

**"Command not found"** after install:
```bash
export PATH="$HOME/.local/bin:$PATH"
```
Add to shell profile (`.zshrc` / `.bashrc`) to persist.

**"Module not found"**: check `[project.scripts]` in pyproject.toml points to a valid `package.module:function`.

## Publish Script

Optional `scripts/publish.py` to automate the build/publish workflow. Key features:

- Interactive mode: 4 choices (TestPyPI, PyPI, Both, Exit)
- CLI flags: `--test`, `--prod`, `--build-only`, `--setup`
- Validates `pyproject.toml` exists
- Warns about uncommitted git changes
- Extracts version from `pyproject.toml`
- Cleans `dist/` before building
- Shows built file sizes
- Confirmation prompt before production publish

### Usage

```bash
# Interactive (recommended)
uv run python scripts/publish.py

# CLI flags
uv run python scripts/publish.py --build-only   # build only
uv run python scripts/publish.py --test          # TestPyPI
uv run python scripts/publish.py --prod          # PyPI (with confirmation)
uv run python scripts/publish.py --setup         # show credential help
```

### Minimal Template

```python
#!/usr/bin/env python3
"""Publish helper — build and upload to TestPyPI/PyPI."""

import argparse
import subprocess
import sys
import tomllib
from pathlib import Path

TESTPYPI_URL = "https://test.pypi.org/legacy/"

def get_version() -> str:
    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]

def clean_dist():
    import shutil
    dist = Path("dist")
    if dist.exists():
        shutil.rmtree(dist)

def build():
    clean_dist()
    subprocess.run(["uv", "build"], check=True)
    for f in Path("dist").iterdir():
        size = f.stat().st_size
        print(f"  {f.name}  ({size:,} bytes)")

def publish(test: bool = False):
    cmd = ["uv", "publish"]
    if test:
        cmd += ["--publish-url", TESTPYPI_URL]
    subprocess.run(cmd, check=True)

def check_git():
    result = subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True
    )
    if result.stdout.strip():
        print("⚠  Uncommitted changes detected.")

def main():
    parser = argparse.ArgumentParser(description="Build and publish to PyPI.")
    parser.add_argument("--test", action="store_true", help="Publish to TestPyPI")
    parser.add_argument("--prod", action="store_true", help="Publish to PyPI")
    parser.add_argument("--build-only", action="store_true", help="Build without publishing")
    parser.add_argument("--setup", action="store_true", help="Show credential setup help")
    args = parser.parse_args()

    if args.setup:
        print("Set UV_PUBLISH_TOKEN env var or pass --token to uv publish.")
        print("TestPyPI tokens: https://test.pypi.org/manage/account/token/")
        print("PyPI tokens:     https://pypi.org/manage/account/token/")
        return

    if not Path("pyproject.toml").exists():
        print("No pyproject.toml found.", file=sys.stderr)
        sys.exit(1)

    version = get_version()
    print(f"Version: {version}")
    check_git()

    if args.build_only:
        build()
        return

    if args.test or args.prod:
        build()
        if args.test:
            publish(test=True)
        if args.prod:
            confirm = input(f"Publish {version} to PyPI? [y/N] ")
            if confirm.lower() == "y":
                publish(test=False)
        return

    # Interactive mode
    build()
    print("\n1) Publish to TestPyPI")
    print("2) Publish to PyPI")
    print("3) Publish to Both")
    print("4) Exit")
    choice = input("Choice [1-4]: ")
    if choice == "1":
        publish(test=True)
    elif choice == "2":
        confirm = input(f"Publish {version} to PyPI? [y/N] ")
        if confirm.lower() == "y":
            publish(test=False)
    elif choice == "3":
        publish(test=True)
        confirm = input(f"Also publish {version} to PyPI? [y/N] ")
        if confirm.lower() == "y":
            publish(test=False)

if __name__ == "__main__":
    main()
```

## Reference Links

- [uv docs](https://docs.astral.sh/uv/)
- [PyPI help](https://pypi.org/help/)
- [Python Packaging Guide](https://packaging.python.org/)
- [PEP 440 (version specifiers)](https://peps.python.org/pep-0440/)
- [Semantic Versioning](https://semver.org/)
