# Publishing to PyPI

Simple manual process for publishing poly-chat to PyPI.

## One-Time Setup

### 1. Get API Tokens

Create accounts and tokens:
- **TestPyPI**: https://test.pypi.org/account/register/ → https://test.pypi.org/manage/account/token/
- **PyPI**: https://pypi.org/account/register/ → https://pypi.org/manage/account/token/

### 2. Configure Tokens (Optional)

```bash
poetry config pypi-token.pypi <your-pypi-token>
poetry config pypi-token.testpypi <your-testpypi-token>
```

If you skip this, Poetry will prompt for tokens when publishing.

## Publishing Workflow

### Full Interactive Mode (Recommended)

```bash
cd shared/apps/poly-chat

# 1. Update version in pyproject.toml manually
#    Edit: version = "0.2.0"

# 2. Run publish script
python tools/publish.py

# 3. Follow the interactive prompts:
#    - Choose TestPyPI (for testing) or PyPI (production)
#    - Script will build and publish
```

### Command-Line Mode

```bash
# Build only (no publishing)
python tools/publish.py --build-only

# Publish to TestPyPI
python tools/publish.py --test

# Publish to PyPI (production)
python tools/publish.py --prod

# Show credential setup help
python tools/publish.py --setup
```

## What the Script Does

1. **Validates environment**
   - Checks Poetry is installed
   - Verifies pyproject.toml exists
   - Warns about uncommitted git changes

2. **Extracts version** from `pyproject.toml`

3. **Builds package**
   - Cleans `dist/` directory
   - Runs `poetry build`
   - Shows built file sizes

4. **Publishes** (based on your choice)
   - TestPyPI: Safe testing environment
   - PyPI: Production (requires confirmation)

## Testing After Publication

### From TestPyPI
```bash
pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  poly-chat

pc --version
```

### From PyPI
```bash
pip install poly-chat
pc --version
```

## Version Numbering

Use semantic versioning in `pyproject.toml`:
- `0.1.0` → `0.2.0` (minor - new features)
- `0.2.0` → `0.2.1` (patch - bug fixes)
- `0.9.0` → `1.0.0` (major - breaking changes)

## Git Tags (Optional)

If you want to tag releases in git:

```bash
# After successful PyPI publish
git tag v0.2.0
git push --tags
```

This is optional - tags are not required for PyPI publishing.

## Manual Publishing (Without Script)

If you prefer raw Poetry commands:

```bash
# Build
poetry build

# Publish to TestPyPI
poetry config repositories.testpypi https://test.pypi.org/legacy/
poetry publish -r testpypi

# Publish to PyPI
poetry publish
```

## Troubleshooting

### "Version already exists"
PyPI doesn't allow re-uploading. You must bump the version number in `pyproject.toml`.

### "Authentication failed"
Run `python tools/publish.py --setup` for credential instructions.

### "Poetry not found"
Install Poetry: `curl -sSL https://install.python-poetry.org | python3 -`

### Build contains wrong files
Check `packages` in `pyproject.toml`:
```toml
packages = [{include = "poly_chat", from = "src"}]
```

Only `src/poly_chat/` is included in the package.

## What Gets Published

From your local project:
- `src/poly_chat/` directory (the package)
- `README.md`
- `LICENSE`
- Generated: `PKG-INFO`, `METADATA`

NOT included:
- `tests/`, `docs/`, `tools/`, `prompts/`
- `.venv/`, `.pytest_cache/`
- Development configs

## Best Practices

1. **Test on TestPyPI first** - Always do a test run before production
2. **Commit changes** - Commit version bumps before publishing
3. **Tag releases** - Optional but helps track what's published
4. **Verify installation** - Test install after publishing
5. **Keep tokens secret** - Never commit API tokens to git
