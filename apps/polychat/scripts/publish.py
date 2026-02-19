#!/usr/bin/env python3
"""Manual PyPI distribution tool for polychat.

Usage:
    python scripts/publish.py          # Interactive mode
    python scripts/publish.py --test   # Publish to TestPyPI
    python scripts/publish.py --prod   # Publish to PyPI (production)
    python scripts/publish.py --setup  # Show credential setup instructions
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text: str) -> None:
    print(f"\n{Colors.BOLD}{text}{Colors.END}")


def print_success(text: str) -> None:
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_error(text: str) -> None:
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_info(text: str) -> None:
    print(f"{Colors.BLUE}→ {text}{Colors.END}")


def print_warning(text: str) -> None:
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def run(cmd: list[str], check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    print_info(f"Running: {' '.join(cmd)}")
    if capture:
        return subprocess.run(cmd, check=check, capture_output=True, text=True)
    else:
        return subprocess.run(cmd, check=check)


def get_version() -> str:
    pyproject = Path("pyproject.toml")
    if not pyproject.exists():
        print_error("pyproject.toml not found. Run from project root (apps/polychat).")
        sys.exit(1)

    content = pyproject.read_text()
    match = re.search(r'^version = "(.+?)"', content, re.MULTILINE)
    if not match:
        print_error("Could not find version in pyproject.toml")
        sys.exit(1)

    return match.group(1)


def check_git_status() -> None:
    result = run(["git", "status", "--porcelain"], check=True)
    if result.stdout.strip():
        print_warning("Git workspace has uncommitted changes.")
        print("Consider committing or stashing before publishing.")
        response = input(f"{Colors.YELLOW}Continue anyway? [y/N]{Colors.END} ").strip().lower()
        if response not in ('y', 'yes'):
            print("Cancelled.")
            sys.exit(0)
    else:
        print_success("Git workspace is clean")


def build_package() -> None:
    print_header("Building package...")

    dist_dir = Path("dist")
    if dist_dir.exists():
        print_info("Cleaning dist/ directory")
        for file in dist_dir.glob("*"):
            file.unlink()

    run(["uv", "build"], capture=False)
    print_success("Package built successfully")

    if dist_dir.exists():
        files = list(dist_dir.glob("*"))
        print("\nBuilt files:")
        for file in files:
            print(f"  - {file.name} ({file.stat().st_size:,} bytes)")


def publish_to_testpypi() -> None:
    print_header("Publishing to TestPyPI...")
    print_info("Publishing to TestPyPI (you may be prompted for token)")
    run(["uv", "publish", "--publish-url", "https://test.pypi.org/legacy/"], capture=False, check=False)
    print_success("Published to TestPyPI!")
    print("\nTest installation with:")
    print("  uv tool install --index-url https://test.pypi.org/simple/ \\")
    print("    --extra-index-url https://pypi.org/simple/ polychat")


def publish_to_pypi() -> None:
    print_header("Publishing to PyPI (Production)...")
    print_warning("This will publish to PRODUCTION PyPI!")
    response = input(f"{Colors.YELLOW}Are you sure? Type 'yes' to confirm:{Colors.END} ").strip()
    if response != 'yes':
        print("Cancelled.")
        sys.exit(0)

    print_info("Publishing to PyPI (you may be prompted for token)")
    run(["uv", "publish"], capture=False, check=False)
    print_success("Published to PyPI!")
    print("\nInstall with:")
    print("  uv tool install polychat")


def configure_credentials() -> None:
    print_header("Configure PyPI Credentials")
    print("\nGet API tokens from:")
    print("  TestPyPI: https://test.pypi.org/manage/account/token/")
    print("  PyPI:     https://pypi.org/manage/account/token/")
    print("\nSet them via environment variables:")
    print("  export UV_PUBLISH_TOKEN=<your-token>")
    print("\nOr pass directly:")
    print("  uv publish --token <your-token>")


def main():
    parser = argparse.ArgumentParser(description="Publish polychat to PyPI")
    parser.add_argument('--test', action='store_true', help='Publish to TestPyPI only')
    parser.add_argument('--prod', action='store_true', help='Publish to PyPI (production)')
    parser.add_argument('--build-only', action='store_true', help='Build package without publishing')
    parser.add_argument('--setup', action='store_true', help='Show credential setup instructions')

    args = parser.parse_args()

    print(f"{Colors.BOLD}=== polychat PyPI Publisher ==={Colors.END}")

    if args.setup:
        configure_credentials()
        return

    if not Path("pyproject.toml").exists():
        print_error("Must run from project root (apps/polychat)")
        sys.exit(1)

    version = get_version()
    print(f"\n{Colors.BOLD}Current version:{Colors.END} {version}")

    check_git_status()
    build_package()

    if args.build_only:
        print("\nBuild complete. Package is in dist/")
        return

    if not args.test and not args.prod:
        print_header("Choose publication target:")
        print("  1. TestPyPI (safe, for testing)")
        print("  2. PyPI (production)")
        print("  3. Both (TestPyPI first, then PyPI)")
        print("  4. Exit")

        choice = input(f"\n{Colors.BLUE}Choice [1-4]:{Colors.END} ").strip()

        if choice == '1':
            publish_to_testpypi()
        elif choice == '2':
            publish_to_pypi()
        elif choice == '3':
            publish_to_testpypi()
            print("\n" + "=" * 50)
            publish_to_pypi()
        else:
            print("Cancelled.")
            return
    else:
        if args.test:
            publish_to_testpypi()
        if args.prod:
            publish_to_pypi()

    print(f"\n{Colors.GREEN}{Colors.BOLD}Done!{Colors.END}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Cancelled.{Colors.END}")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed: {' '.join(e.cmd)}")
        if e.stderr:
            print(e.stderr)
        sys.exit(1)
