# Setup: Accounts and Credentials

One-time setup for publishing to PyPI. Once configured, you won't need to repeat these steps.

## Prerequisites

- uv installed (`brew install uv` on macOS)
- Python 3.9+ (check with `python3 --version`)
- A Python package ready to publish (with `pyproject.toml`)

## Step 1: Create PyPI Accounts

### TestPyPI Account

1. Go to https://test.pypi.org/account/register/
2. Fill out registration form
3. Verify email
4. **Enable 2FA** (Settings → Account Security → Two Factor Authentication)
   - Use authenticator app (Authy, Google Authenticator, etc.)
   - Save recovery codes securely

### PyPI Account

1. Go to https://pypi.org/account/register/
2. Fill out registration form
3. Verify email
4. **Enable 2FA** (Settings → Account Security → Two Factor Authentication)

**Important**: These are separate accounts with separate databases. You need both.

## Step 2: Create API Tokens

### Why Tokens?

- Required for publishing
- More secure than passwords
- Can be scoped to specific projects
- Can be revoked without changing your password

### TestPyPI Token

1. Log in to https://test.pypi.org
2. Go to Account Settings → API tokens: https://test.pypi.org/manage/account/token/
3. Click "Add API token"
4. **Token name**: Your app name (e.g., `my-app`)
5. **Scope**: Choose "Entire account" (will scope to project after first upload)
6. Click "Add token"
7. **Copy the token** - starts with `pypi-` and is very long
8. **Save immediately** - you can't view it again

### PyPI Token

Same process as TestPyPI:

1. Log in to https://pypi.org
2. Go to Account Settings → API tokens: https://pypi.org/manage/account/token/
3. Create token with same settings
4. Copy and save

### Storing Tokens Securely

**Recommended: Keep in a secrets repository**

Create a file for Python-related secrets:

```bash
# Example: secrets/python/pypi-tokens.txt
TestPyPI Token:
pypi-AgEIcHlwaS5vcmcC...

PyPI Token:
pypi-AgEIcHlwaS5vcmcC...
```

Store this in a private, encrypted git repository or password manager.

**Never commit tokens to your public repository!**

## Step 3: Configure Token for Publishing

Set the token as an environment variable before publishing:

```bash
export UV_PUBLISH_TOKEN=<your-token>
```

Or pass it directly to `uv publish`:

```bash
uv publish --token <your-token>
```

If omitted, `uv publish` will prompt for username and password.

### Token Scoping (After First Upload)

After successfully publishing version 1 to PyPI:

1. Go to https://pypi.org/manage/project/your-app/settings/
2. Delete the "entire account" token
3. Create a new token scoped to "Project: your-app"
4. Update your stored token

This limits the token's access to just your app (more secure).

**Do the same for TestPyPI** after your first TestPyPI upload.

## Step 4: Verify uv Setup

Check that uv is properly installed:

```bash
uv --version
# Should show: uv X.Y.Z
```

## Security Best Practices

1. **Enable 2FA** on both PyPI accounts
2. **Scope tokens** to projects after first upload
3. **Store tokens securely** (password manager or encrypted repo)
4. **Never commit** tokens to git
5. **Rotate tokens** periodically (every 6-12 months)
6. **Revoke tokens** immediately if compromised

## Summary

You now have:
- ✅ TestPyPI and PyPI accounts with 2FA enabled
- ✅ API tokens for both services stored securely
- ✅ uv installed and ready

Next: [03-publishing.md](03-publishing.md) - Learn the publishing workflow
