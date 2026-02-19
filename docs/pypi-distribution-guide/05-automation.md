# Automation: Publishing Helper Script

Creating a Python script to automate and streamline the publishing workflow with safety checks and guidance.

## Why Automate?

Manual publishing is error-prone:
- Forgetting to clean `dist/`
- Publishing without building
- Typos in commands
- No verification steps
- Easy to publish to wrong target

**A helper script provides:**
- ✅ Consistent workflow
- ✅ Built-in safety checks
- ✅ Clear prompts and feedback
- ✅ Error handling
- ✅ Guidance for common tasks

## The Publishing Script

Create `scripts/publish.py` in your app directory:

```python
#!/usr/bin/env python3
"""Manual PyPI distribution tool.

Automates building and publishing packages with safety checks.

Usage:
    python scripts/publish.py          # Interactive mode
    python scripts/publish.py --test   # Publish to TestPyPI
    python scripts/publish.py --prod   # Publish to PyPI
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], check: bool = True, capture: bool = True):
    """Run command and return result."""
    print(f"→ Running: {' '.join(cmd)}")
    if capture:
        return subprocess.run(cmd, check=check, capture_output=True, text=True)
    else:
        return subprocess.run(cmd, check=check)


def get_version() -> str:
    """Extract version from pyproject.toml."""
    pyproject = Path("pyproject.toml")
    if not pyproject.exists():
        print("Error: pyproject.toml not found. Run from project root.")
        sys.exit(1)
    
    content = pyproject.read_text()
    match = re.search(r'^version = "(.+?)"', content, re.MULTILINE)
    if not match:
        print("Error: Could not find version in pyproject.toml")
        sys.exit(1)
    
    return match.group(1)


def check_git_status() -> None:
    """Warn about uncommitted changes."""
    result = run(["git", "status", "--porcelain"], check=True)
    if result.stdout.strip():
        print("⚠ Warning: Uncommitted changes in git workspace")
        response = input("Continue anyway? [y/N] ").strip().lower()
        if response not in ('y', 'yes'):
            print("Cancelled.")
            sys.exit(0)
    else:
        print("✓ Git workspace clean")


def build_package() -> None:
    """Build package with uv."""
    print("\n=== Building Package ===")

    # Clean dist/
    dist_dir = Path("dist")
    if dist_dir.exists():
        print("Cleaning dist/ directory...")
        for file in dist_dir.glob("*"):
            file.unlink()

    # Build
    run(["uv", "build"], capture=False)
    print("✓ Package built")
    
    # Show files
    if dist_dir.exists():
        files = list(dist_dir.glob("*"))
        print("\nBuilt files:")
        for file in files:
            print(f"  - {file.name} ({file.stat().st_size:,} bytes)")


def publish_testpypi() -> None:
    """Publish to TestPyPI."""
    print("\n=== Publishing to TestPyPI ===")

    print("Publishing (you may be prompted for token)...")
    run(["uv", "publish", "--publish-url", "https://test.pypi.org/legacy/"],
        capture=False, check=False)

    print("\n✓ Published to TestPyPI!")
    print("\nTest installation:")
    print("  uv tool install --index-url https://test.pypi.org/simple/ \\")
    print("    --extra-index-url https://pypi.org/simple/ your-app")


def publish_pypi() -> None:
    """Publish to PyPI (production)."""
    print("\n=== Publishing to PyPI (Production) ===")

    print("⚠ This will publish to PRODUCTION PyPI!")
    response = input("Type 'yes' to confirm: ").strip()
    if response != 'yes':
        print("Cancelled.")
        sys.exit(0)

    print("Publishing (you may be prompted for token)...")
    run(["uv", "publish"], capture=False, check=False)

    print("\n✓ Published to PyPI!")
    print("\nInstall with:")
    print("  uv tool install your-app")


def main():
    parser = argparse.ArgumentParser(description="Publish package to PyPI")
    parser.add_argument('--test', action='store_true', 
                       help='Publish to TestPyPI')
    parser.add_argument('--prod', action='store_true',
                       help='Publish to PyPI (production)')
    parser.add_argument('--build-only', action='store_true',
                       help='Build without publishing')
    
    args = parser.parse_args()
    
    print("=== PyPI Publisher ===\n")
    
    # Check environment
    if not Path("pyproject.toml").exists():
        print("Error: Must run from project root")
        sys.exit(1)

    # Show version
    version = get_version()
    print(f"\nCurrent version: {version}")
    
    # Check git
    check_git_status()
    
    # Build
    build_package()
    
    if args.build_only:
        print("\n✓ Build complete")
        return
    
    # Publish
    if not args.test and not args.prod:
        # Interactive mode
        print("\n=== Choose Target ===")
        print("1. TestPyPI (safe, for testing)")
        print("2. PyPI (production)")
        print("3. Exit")
        
        choice = input("\nChoice [1-3]: ").strip()
        
        if choice == '1':
            publish_testpypi()
        elif choice == '2':
            publish_pypi()
        else:
            print("Cancelled.")
    else:
        if args.test:
            publish_testpypi()
        if args.prod:
            publish_pypi()
    
    print("\n✓ Done!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelled.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"\nError: Command failed: {' '.join(e.cmd)}")
        sys.exit(1)
```

## Making the Script Executable

```bash
chmod +x scripts/publish.py
```

## Usage Examples

### Interactive Mode

```bash
cd /path/to/your/app
python3 scripts/publish.py
```

The script will:
1. Check Poetry is installed
2. Show current version
3. Check git status (warn about uncommitted changes)
4. Build the package
5. Prompt for target (TestPyPI/PyPI/Exit)
6. Publish and show installation instructions

### Build Only

```bash
python3 scripts/publish.py --build-only
```

Just builds the package without publishing. Useful for:
- Verifying package contents
- Testing the build process
- Checking file sizes

### Publish to TestPyPI

```bash
python3 scripts/publish.py --test
```

Automatically publishes to TestPyPI after building.

### Publish to PyPI

```bash
python3 scripts/publish.py --prod
```

Publishes to production PyPI with confirmation prompt.

## Script Features

### Safety Checks

- **Git status check**: Warns about uncommitted changes
- **Confirmation prompt**: For production PyPI publishing
- **Clean dist/**: Removes old builds automatically

### User Guidance

- **Clear output**: Shows what's happening at each step
- **Installation instructions**: Prints commands after publishing
- **File sizes**: Shows built file sizes
- **Error handling**: Catches and reports errors clearly

### Flexibility

- **Interactive mode**: Guided workflow with prompts
- **Command-line flags**: Scriptable automation
- **Build-only option**: Test builds without publishing

## Workflow Integration

### Full Release Workflow

```bash
# 1. Update version in pyproject.toml
# version = "0.1.0"

# 2. Test build
python3 scripts/publish.py --build-only

# 3. Check contents
tar -tzf dist/*.tar.gz

# 4. Publish to TestPyPI
python3 scripts/publish.py --test

# 5. Test installation
uv tool install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ your-app

# 6. If good, publish to PyPI
python3 scripts/publish.py --prod

# 7. Tag in git
git add pyproject.toml
git commit -m "Release v0.1.0"
git tag v0.1.0
git push --tags
```

## Customization

### Adding Version Validation

```python
def validate_version(version: str) -> bool:
    """Check version follows semantic versioning."""
    pattern = r'^\d+\.\d+\.\d+$'
    return bool(re.match(pattern, version))
```

### Adding Changelog Reminder

```python
def check_changelog() -> None:
    """Remind to update changelog."""
    changelog = Path("CHANGELOG.md")
    if changelog.exists():
        print("\n⚠ Remember to update CHANGELOG.md!")
        input("Press Enter to continue...")
```

### Adding README Check

```python
def verify_readme() -> None:
    """Check README mentions latest version."""
    readme = Path("README.md").read_text()
    version = get_version()
    if version not in readme:
        print(f"\n⚠ Warning: Version {version} not in README")
```

## Alternative: Simple Shell Script

If you prefer shell scripts:

```bash
#!/bin/bash
# scripts/publish.sh

set -e

echo "=== Building Package ==="
uv build

echo ""
echo "=== Choose Target ==="
echo "1. TestPyPI"
echo "2. PyPI"
read -p "Choice: " choice

if [ "$choice" == "1" ]; then
    uv publish --publish-url https://test.pypi.org/legacy/
elif [ "$choice" == "2" ]; then
    read -p "Publish to PRODUCTION PyPI? (yes/no): " confirm
    if [ "$confirm" == "yes" ]; then
        uv publish
    fi
fi
```

## Extending the Script

### Add Package Content Verification

```python
def verify_package_contents():
    """Check package includes expected files."""
    dist_files = list(Path("dist").glob("*.tar.gz"))
    if not dist_files:
        return
    
    import tarfile
    with tarfile.open(dist_files[0], 'r:gz') as tar:
        members = tar.getnames()
        
        # Check for expected files
        checks = {
            'README': any('README' in m for m in members),
            'LICENSE': any('LICENSE' in m for m in members),
            'Python files': any(m.endswith('.py') for m in members)
        }
        
        print("\nPackage contents:")
        for check, passed in checks.items():
            status = "✓" if passed else "✗"
            print(f"  {status} {check}")
```

### Add Test Running

```python
def run_tests():
    """Run tests before building."""
    print("\n=== Running Tests ===")
    result = subprocess.run(
        ["uv", "run", "pytest"],
        capture_output=False
    )
    if result.returncode != 0:
        print("\n✗ Tests failed!")
        sys.exit(1)
    print("✓ Tests passed")
```

## Summary

A publishing script provides:
- Consistent, repeatable workflow
- Safety checks and confirmations
- Clear guidance and feedback
- Error prevention
- Time savings

Start with the basic script and extend as needed for your specific workflow.

Next: [06-best-practices.md](06-best-practices.md) - Learn about dependency management and common pitfalls
