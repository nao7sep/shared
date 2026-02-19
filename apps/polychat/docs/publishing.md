# Publishing to PyPI

Simple manual process for publishing polychat to PyPI.

## One-Time Setup

### 1. Get API Tokens

Create accounts and tokens:
- **TestPyPI**: https://test.pypi.org/account/register/ → https://test.pypi.org/manage/account/token/
- **PyPI**: https://pypi.org/account/register/ → https://pypi.org/manage/account/token/

### 2. Configure Tokens (Optional)

Set as environment variable before publishing:

```bash
export UV_PUBLISH_TOKEN=<your-token>
```

Or pass directly via `uv publish --token <your-token>`. If omitted, uv will prompt.

## Publishing Workflow

### Full Interactive Mode (Recommended)

```bash
cd shared/apps/polychat

# 1. Update version in pyproject.toml manually
#    Edit: version = "0.2.0"

# 2. Run publish script
uv run python scripts/publish.py

# 3. Follow the interactive prompts:
#    - Choose TestPyPI (for testing) or PyPI (production)
#    - Script will build and publish
```

### Command-Line Mode

```bash
# Build only (no publishing)
uv run python scripts/publish.py --build-only

# Publish to TestPyPI
uv run python scripts/publish.py --test

# Publish to PyPI (production)
uv run python scripts/publish.py --prod

# Show credential setup help
uv run python scripts/publish.py --setup
```

## What the Script Does

1. **Validates environment**
   - Verifies pyproject.toml exists
   - Warns about uncommitted git changes

2. **Extracts version** from `pyproject.toml`

3. **Builds package**
   - Cleans `dist/` directory
   - Runs `uv build`
   - Shows built file sizes

4. **Publishes** (based on your choice)
   - TestPyPI: Safe testing environment
   - PyPI: Production (requires confirmation)

## Testing After Publication

### From TestPyPI
```bash
uv tool install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  polychat

pc --version
```

### From PyPI
```bash
uv tool install polychat
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

```bash
# Build
uv build

# Publish to TestPyPI
uv publish --publish-url https://test.pypi.org/legacy/

# Publish to PyPI
uv publish
```

## Troubleshooting

### "Version already exists"
PyPI doesn't allow re-uploading. You must bump the version number in `pyproject.toml`.

### "Authentication failed"
Run `uv run python scripts/publish.py --setup` for credential instructions.

### Build contains wrong files
uv_build auto-detects the `src/` layout. Ensure `src/polychat/` exists and pyproject.toml has `name = "polychat"`.

## What Gets Published

From your local project:
- `src/polychat/` directory (the package)
- `README.md`
- `LICENSE`
- Generated: `PKG-INFO`, `METADATA`

NOT included:
- `tests/`, `docs/`, `scripts/`, `prompts/`
- `.venv/`, `.pytest_cache/`
- Development configs

## Best Practices

1. **Test on TestPyPI first** - Always do a test run before production
2. **Commit changes** - Commit version bumps before publishing
3. **Tag releases** - Optional but helps track what's published
4. **Verify installation** - Test install after publishing
5. **Keep tokens secret** - Never commit API tokens to git
