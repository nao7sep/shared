"""Tests for interactive setup wizard behavior."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from polychat import setup_wizard


def _configure_setup_paths(monkeypatch, tmp_path) -> tuple[str, str]:
    data_dir = tmp_path / ".polychat"
    profile_path = data_dir / "profile.json"
    api_keys_path = data_dir / "api-keys.json"
    chats_dir = data_dir / "chats"
    logs_dir = data_dir / "logs"

    monkeypatch.setattr(setup_wizard, "USER_DATA_DIR", str(data_dir))
    monkeypatch.setattr(setup_wizard, "SETUP_PROFILE_PATH", str(profile_path))
    monkeypatch.setattr(setup_wizard, "SETUP_API_KEYS_PATH", str(api_keys_path))
    monkeypatch.setattr(setup_wizard, "SETUP_CHATS_DIR", str(chats_dir))
    monkeypatch.setattr(setup_wizard, "SETUP_LOGS_DIR", str(logs_dir))

    return str(profile_path), str(api_keys_path)


def test_build_profile_uses_provider_order_and_shared_key_file() -> None:
    profile = setup_wizard._build_profile(
        {"mistral": "mistral-key", "openai": "openai-key"}
    )

    assert profile["default_ai"] == "openai"
    assert profile["models"] == {
        "openai": "gpt-5-mini",
        "mistral": "mistral-small-latest",
    }
    assert profile["api_keys"] == {
        "openai": {
            "type": "json",
            "path": setup_wizard.SETUP_API_KEYS_PATH,
            "key": "openai",
        },
        "mistral": {
            "type": "json",
            "path": setup_wizard.SETUP_API_KEYS_PATH,
            "key": "mistral",
        },
    }


def test_run_setup_wizard_returns_none_when_no_keys_are_provided(
    monkeypatch,
    tmp_path,
) -> None:
    profile_path, api_keys_path = _configure_setup_paths(monkeypatch, tmp_path)
    responses = iter([""] * len(setup_wizard.PROVIDER_INFO))
    monkeypatch.setattr(setup_wizard, "pt_prompt", lambda _prompt: next(responses))

    result = setup_wizard.run_setup_wizard()

    assert result is None
    assert not tmp_path.joinpath(".polychat").exists()
    assert not tmp_path.joinpath(profile_path).exists()
    assert not tmp_path.joinpath(api_keys_path).exists()


def test_run_setup_wizard_writes_profile_and_api_keys(monkeypatch, tmp_path) -> None:
    profile_path, api_keys_path = _configure_setup_paths(monkeypatch, tmp_path)
    responses = iter(
        [
            "sk-test-openai-1234567890",
            "",
            "",
            "",
            "",
            "",
            "",
            "y",
        ]
    )
    monkeypatch.setattr(setup_wizard, "pt_prompt", lambda _prompt: next(responses))

    result = setup_wizard.run_setup_wizard()

    assert result == profile_path
    assert tmp_path.joinpath(".polychat").exists()

    with open(api_keys_path, "r", encoding="utf-8") as f:
        saved_keys = json.load(f)
    assert saved_keys == {"openai": "sk-test-openai-1234567890"}

    with open(profile_path, "r", encoding="utf-8") as f:
        saved_profile = json.load(f)
    assert saved_profile["default_ai"] == "openai"
    assert saved_profile["models"] == {"openai": "gpt-5-mini"}
    assert saved_profile["api_keys"]["openai"] == {
        "type": "json",
        "path": api_keys_path,
        "key": "openai",
    }
    assert saved_profile["chats_dir"] == str(tmp_path / ".polychat" / "chats")
    assert saved_profile["logs_dir"] == str(tmp_path / ".polychat" / "logs")


def test_atomic_write_json_cleans_up_temp_file_on_replace_failure(
    monkeypatch,
    tmp_path,
) -> None:
    target_path = tmp_path / "profile.json"
    target_path.write_text('{"existing": true}', encoding="utf-8")
    before_entries = set(tmp_path.iterdir())

    def fail_replace(_src: Path | str, _dst: Path | str) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(setup_wizard.os, "replace", fail_replace)

    with pytest.raises(OSError, match="disk full"):
        setup_wizard._atomic_write_json(target_path, {"new": "payload"})

    assert json.loads(target_path.read_text(encoding="utf-8")) == {"existing": True}
    assert set(tmp_path.iterdir()) == before_entries


def test_run_setup_wizard_profile_write_failure_leaves_no_partial_profile(
    monkeypatch,
    tmp_path,
) -> None:
    profile_path, api_keys_path = _configure_setup_paths(monkeypatch, tmp_path)
    responses = iter(
        [
            "sk-test-openai-1234567890",
            "",
            "",
            "",
            "",
            "",
            "",
            "y",
        ]
    )
    monkeypatch.setattr(setup_wizard, "pt_prompt", lambda _prompt: next(responses))
    original_replace = setup_wizard.os.replace
    replace_count = 0

    def fail_on_profile_replace(src: str | Path, dst: str | Path) -> None:
        nonlocal replace_count
        if Path(dst) in {Path(api_keys_path), Path(profile_path)}:
            replace_count += 1
            if replace_count == 2:
                raise OSError("profile write failed")
        original_replace(src, dst)

    monkeypatch.setattr(setup_wizard.os, "replace", fail_on_profile_replace)

    with pytest.raises(OSError, match="profile write failed"):
        setup_wizard.run_setup_wizard()

    assert not Path(api_keys_path).exists()
    assert not Path(profile_path).exists()


def test_write_json_transaction_restores_original_files_on_failure(
    monkeypatch,
    tmp_path,
) -> None:
    api_keys_path = tmp_path / "api-keys.json"
    profile_path = tmp_path / "profile.json"
    api_keys_path.write_text('{"old":"keys"}', encoding="utf-8")
    profile_path.write_text('{"old":"profile"}', encoding="utf-8")

    original_replace = setup_wizard.os.replace
    replace_count = 0

    def fail_on_second_target(src: str | Path, dst: str | Path) -> None:
        nonlocal replace_count
        if Path(dst) in {api_keys_path, profile_path}:
            replace_count += 1
            if replace_count == 2:
                raise OSError("replace failed")
        original_replace(src, dst)

    monkeypatch.setattr(setup_wizard.os, "replace", fail_on_second_target)

    with pytest.raises(OSError, match="replace failed"):
        setup_wizard._write_json_transaction(
            [
                (api_keys_path, {"new": "keys"}),
                (profile_path, {"new": "profile"}),
            ]
        )

    assert json.loads(api_keys_path.read_text(encoding="utf-8")) == {"old": "keys"}
    assert json.loads(profile_path.read_text(encoding="utf-8")) == {"old": "profile"}


@pytest.mark.parametrize(
    ("existing_api_keys", "existing_profile"),
    [
        (True, False),
        (False, True),
    ],
)
def test_write_json_transaction_restores_mixed_old_and_new_files_on_failure(
    monkeypatch,
    tmp_path,
    existing_api_keys: bool,
    existing_profile: bool,
) -> None:
    api_keys_path = tmp_path / "api-keys.json"
    profile_path = tmp_path / "profile.json"

    if existing_api_keys:
        api_keys_path.write_text('{"old":"keys"}', encoding="utf-8")
    if existing_profile:
        profile_path.write_text('{"old":"profile"}', encoding="utf-8")

    original_replace = setup_wizard.os.replace
    replace_count = 0

    def fail_on_second_target(src: str | Path, dst: str | Path) -> None:
        nonlocal replace_count
        if Path(dst) in {api_keys_path, profile_path}:
            replace_count += 1
            if replace_count == 2:
                raise OSError("replace failed")
        original_replace(src, dst)

    monkeypatch.setattr(setup_wizard.os, "replace", fail_on_second_target)

    with pytest.raises(OSError, match="replace failed"):
        setup_wizard._write_json_transaction(
            [
                (api_keys_path, {"new": "keys"}),
                (profile_path, {"new": "profile"}),
            ]
        )

    if existing_api_keys:
        assert json.loads(api_keys_path.read_text(encoding="utf-8")) == {"old": "keys"}
    else:
        assert not api_keys_path.exists()

    if existing_profile:
        assert json.loads(profile_path.read_text(encoding="utf-8")) == {"old": "profile"}
    else:
        assert not profile_path.exists()
