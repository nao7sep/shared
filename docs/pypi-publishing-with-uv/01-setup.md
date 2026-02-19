# Setup

One-time setup for publishing to PyPI.

## Prerequisites

- uv installed (`brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Python 3.9+
- A package with `pyproject.toml`

## Create Accounts

**TestPyPI** and **PyPI** are separate databases with separate accounts.

| | Register | Tokens |
|---|----------|--------|
| TestPyPI | https://test.pypi.org/account/register/ | https://test.pypi.org/manage/account/token/ |
| PyPI | https://pypi.org/account/register/ | https://pypi.org/manage/account/token/ |

After registering each: **enable 2FA** (Settings → Account Security). Save recovery codes.

## Create API Tokens

1. Account Settings → API tokens → "Add API token"
2. Name: your app name
3. Scope: "Entire account" (first time — scope to project after first upload)
4. Copy token immediately (starts with `pypi-`, can't view again)

Do this for both TestPyPI and PyPI.

### Token Scoping (After First Upload)

After first successful publish to a given index:

1. Delete the "entire account" token
2. Create new token scoped to "Project: your-app"
3. More secure — limits blast radius if leaked

## Configure Token for Publishing

```bash
# Environment variable (preferred)
export UV_PUBLISH_TOKEN=<your-token>

# Or pass inline
uv publish --token <your-token>

# Or omit — uv will prompt
```

## Security Checklist

- 2FA on both accounts
- Tokens scoped to project (after first upload)
- Tokens in password manager or encrypted secrets repo — never in git
- Rotate periodically, revoke immediately if compromised
