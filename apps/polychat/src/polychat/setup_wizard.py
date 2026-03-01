"""Setup wizard for PolyChat.

Interactive wizard that configures PolyChat with API keys and creates
profile and key files in ~/.polychat/.
"""

import os
import json
import tempfile
from pathlib import Path
from typing import Any, Optional

from prompt_toolkit import prompt as pt_prompt

from .constants import (
    BUILTIN_PROMPT_SYSTEM_DEFAULT,
    BUILTIN_PROMPT_TITLE,
    BUILTIN_PROMPT_SUMMARY,
    BUILTIN_PROMPT_SAFETY,
    USER_DATA_DIR,
)
from .formatting.constants import BORDERLINE_CHAR, BORDERLINE_WIDTH
from .timeouts import DEFAULT_PROFILE_TIMEOUT_SEC

# Fixed paths for setup wizard
SETUP_PROFILE_PATH = f"{USER_DATA_DIR}/profile.json"
SETUP_API_KEYS_PATH = f"{USER_DATA_DIR}/api-keys.json"
SETUP_CHATS_DIR = f"{USER_DATA_DIR}/chats"
SETUP_LOGS_DIR = f"{USER_DATA_DIR}/logs"

# Provider info: (id, display_name, default_model)
PROVIDER_INFO = [
    ("openai", "OpenAI", "gpt-5-mini"),
    ("claude", "Anthropic Claude", "claude-haiku-4-5"),
    ("gemini", "Google Gemini", "gemini-3-flash-preview"),
    ("grok", "xAI Grok", "grok-4-1-fast-non-reasoning"),
    ("perplexity", "Perplexity", "sonar"),
    ("mistral", "Mistral", "mistral-small-latest"),
    ("deepseek", "DeepSeek", "deepseek-chat"),
]


def _mask_key(key: str) -> str:
    """Mask an API key for display, showing first 4 and last 4 characters."""
    if len(key) > 12:
        return key[:4] + "..." + key[-4:]
    return "***"


def _atomic_write_json(path: Path, payload: Any) -> None:
    """Write JSON via a temp file and atomically replace the destination."""
    path.parent.mkdir(parents=True, exist_ok=True)

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            json.dump(payload, temp_file, indent=2, ensure_ascii=False)
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_path = Path(temp_file.name)

        os.replace(temp_path, path)
    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise


def _write_json_transaction(entries: list[tuple[Path, Any]]) -> None:
    """Write multiple JSON files with rollback so setup is all-or-nothing."""
    temp_paths: dict[Path, Path] = {}
    backup_paths: dict[Path, Path] = {}
    had_original: dict[Path, bool] = {}
    replaced_targets: list[Path] = []

    try:
        for path, payload in entries:
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                json.dump(payload, temp_file, indent=2, ensure_ascii=False)
                temp_file.flush()
                os.fsync(temp_file.fileno())
                temp_paths[path] = Path(temp_file.name)

        for path, _payload in entries:
            had_original[path] = path.exists()
            if path.exists():
                backup_path = Path(
                    tempfile.mkstemp(
                        dir=path.parent,
                        prefix=f".{path.name}.",
                        suffix=".bak",
                    )[1]
                )
                backup_path.unlink()
                os.replace(path, backup_path)
                backup_paths[path] = backup_path

        for path, _payload in entries:
            os.replace(temp_paths[path], path)
            replaced_targets.append(path)

    except Exception:
        for path in reversed(replaced_targets):
            if not had_original.get(path, False) and path.exists():
                path.unlink(missing_ok=True)

        for path, backup_path in backup_paths.items():
            os.replace(backup_path, path)

        for path, temp_path in temp_paths.items():
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)

        for backup_path in backup_paths.values():
            backup_path.unlink(missing_ok=True)
        raise

    for backup_path in backup_paths.values():
        backup_path.unlink(missing_ok=True)


def run_setup_wizard() -> Optional[str]:
    """Run the interactive setup wizard.

    Returns:
        Mapped profile path string on success, or None on failure/cancellation.
    """
    borderline = BORDERLINE_CHAR * BORDERLINE_WIDTH

    print(borderline)
    print("PolyChat Setup")
    print(borderline)
    print()
    print("PolyChat supports 7 AI providers:")
    for i, (_, display_name, _) in enumerate(PROVIDER_INFO, 1):
        print(f"  {i}. {display_name}")
    print()
    print("Enter your API key for each provider, or press Enter to skip.")
    print()

    # Collect API keys
    api_keys: dict[str, str] = {}
    for provider_id, display_name, _ in PROVIDER_INFO:
        try:
            key = pt_prompt(f"  {display_name} API key: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            print("Setup cancelled.")
            return None
        if key:
            api_keys[provider_id] = key

    print()

    # Check if any keys were provided
    if not api_keys:
        print("No API keys were provided.")
        print("At least one API key is required to use PolyChat.")
        print()
        print("You can run 'polychat setup' again at any time.")
        return None

    # Show summary
    print("Configured providers:")
    for provider_id, display_name, _ in PROVIDER_INFO:
        if provider_id in api_keys:
            print(f"  \u2713 {display_name}: {_mask_key(api_keys[provider_id])}")
        else:
            print(f"  - {display_name}: (skipped)")
    print()

    # Ask for confirmation
    try:
        confirm = pt_prompt("Save and start PolyChat? (y/N): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        print("Setup cancelled.")
        return None

    if confirm not in ("y", "yes"):
        print("Setup cancelled.")
        return None

    # Build profile
    profile = _build_profile(api_keys)

    # Write files
    from .path_utils import map_path

    api_keys_path = Path(map_path(SETUP_API_KEYS_PATH))
    profile_path = Path(map_path(SETUP_PROFILE_PATH))

    _write_json_transaction(
        [
            (api_keys_path, api_keys),
            (profile_path, profile),
        ]
    )

    print()
    print(f"Profile:  {profile_path}")
    print(f"API keys: {api_keys_path}")
    print()  # Banner owns no leading blank, so wizard emits trailing separation

    return str(profile_path)


def _build_profile(api_keys: dict[str, str]) -> dict[str, Any]:
    """Build profile from collected API keys."""
    # Only include providers that have keys
    configured_providers = [
        (pid, dname, model)
        for pid, dname, model in PROVIDER_INFO
        if pid in api_keys
    ]

    # First configured provider is the default
    default_ai = configured_providers[0][0]

    # Models section: only configured providers
    models = {pid: model for pid, _, model in configured_providers}

    # API keys section: all point to the shared api-keys.json
    api_keys_config = {}
    for pid, _, _ in configured_providers:
        api_keys_config[pid] = {
            "type": "json",
            "path": SETUP_API_KEYS_PATH,
            "key": pid,
        }

    profile = {
        "default_ai": default_ai,
        "models": models,
        "timeout": DEFAULT_PROFILE_TIMEOUT_SEC,
        "input_mode": "quick",
        "system_prompt": BUILTIN_PROMPT_SYSTEM_DEFAULT,
        "title_prompt": BUILTIN_PROMPT_TITLE,
        "summary_prompt": BUILTIN_PROMPT_SUMMARY,
        "safety_prompt": BUILTIN_PROMPT_SAFETY,
        "chats_dir": SETUP_CHATS_DIR,
        "logs_dir": SETUP_LOGS_DIR,
        "api_keys": api_keys_config,
        "ai_limits": {
            "default": {
                "max_output_tokens": None,
                "search_max_output_tokens": None,
            },
            "providers": {},
            "helper": {
                "max_output_tokens": None,
                "search_max_output_tokens": None,
            },
        },
    }

    return profile
