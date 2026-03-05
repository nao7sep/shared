"""Local persistent state under platformdirs.user_data_dir("Pydeli").

Stores credential metadata and bootstrap state as JSON.
Never stores secrets in the state file — tokens are held only in memory
during the session and passed via environment variables to subprocesses.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import platformdirs

from .errors import StateError
from .models import CredentialState, Registry, TokenScope

_APP_NAME = "Pydeli"


def _state_dir() -> Path:
    return Path(platformdirs.user_data_dir(_APP_NAME))


def _state_file() -> Path:
    return _state_dir() / "state.json"


def ensure_state_dir() -> Path:
    """Create and return the state directory."""
    d = _state_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load_raw() -> dict:
    path = _state_file()
    if not path.exists():
        return {"credentials": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        raise StateError(f"Failed to read state file {path}: {e}") from e


def _save_raw(data: dict) -> None:
    ensure_state_dir()
    path = _state_file()
    try:
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    except OSError as e:
        raise StateError(f"Failed to write state file {path}: {e}") from e


def _credential_key(registry: Registry, project_name: str) -> str:
    return f"{registry.value}:{project_name}"


def load_credential(registry: Registry, project_name: str) -> CredentialState | None:
    """Load credential state for a registry+project pair, or None if not found."""
    data = _load_raw()
    creds = data.get("credentials", {})
    key = _credential_key(registry, project_name)
    entry = creds.get(key)
    if entry is None:
        return None
    return CredentialState(
        registry=Registry(entry["registry"]),
        project_name=entry["project_name"],
        token_value=entry.get("token_value", ""),
        token_scope=TokenScope(entry["token_scope"]),
        needs_rotation=entry.get("needs_rotation", False),
        created_utc=datetime.fromisoformat(entry["created_utc"]),
        updated_utc=datetime.fromisoformat(entry["updated_utc"]),
    )


def save_credential(cred: CredentialState) -> None:
    """Persist credential state for a registry+project pair."""
    data = _load_raw()
    creds = data.setdefault("credentials", {})
    key = _credential_key(cred.registry, cred.project_name)
    creds[key] = {
        "registry": cred.registry.value,
        "project_name": cred.project_name,
        "token_value": cred.token_value,
        "token_scope": cred.token_scope.value,
        "needs_rotation": cred.needs_rotation,
        "created_utc": cred.created_utc.isoformat(),
        "updated_utc": cred.updated_utc.isoformat(),
    }
    _save_raw(data)


def update_credential_token(
    registry: Registry,
    project_name: str,
    token_value: str,
    scope: TokenScope,
    needs_rotation: bool,
) -> CredentialState:
    """Update (or create) a credential with a new token value."""
    existing = load_credential(registry, project_name)
    now = datetime.now(timezone.utc)
    if existing:
        existing.token_value = token_value
        existing.token_scope = scope
        existing.needs_rotation = needs_rotation
        existing.updated_utc = now
        save_credential(existing)
        return existing

    cred = CredentialState(
        registry=registry,
        project_name=project_name,
        token_value=token_value,
        token_scope=scope,
        needs_rotation=needs_rotation,
        created_utc=now,
        updated_utc=now,
    )
    save_credential(cred)
    return cred


def delete_credential(registry: Registry, project_name: str) -> None:
    """Remove credential state for a registry+project pair."""
    data = _load_raw()
    creds = data.get("credentials", {})
    key = _credential_key(registry, project_name)
    creds.pop(key, None)
    _save_raw(data)
