"""Documentation drift checks for user-facing README content."""

from pathlib import Path

from polychat.profile import create_profile


def _readme_text() -> str:
    """Load project README text."""
    readme_path = Path(__file__).resolve().parents[1] / "README.md"
    return readme_path.read_text(encoding="utf-8")


def test_readme_mentions_generated_default_directories(tmp_path):
    """README should document the same chats/logs defaults as profile template."""
    profile_path = tmp_path / "profile.json"
    generated_profile, _messages = create_profile(str(profile_path))

    readme = _readme_text()

    assert generated_profile["chats_dir"] in readme
    assert generated_profile["logs_dir"] in readme


def test_readme_covers_generated_api_key_types(tmp_path):
    """README should cover every API key type used by generated profile template."""
    profile_path = tmp_path / "profile.json"
    generated_profile, _messages = create_profile(str(profile_path))

    readme = _readme_text()
    api_key_types = {
        config["type"]
        for config in generated_profile["api_keys"].values()
        if isinstance(config, dict) and "type" in config
    }

    for key_type in sorted(api_key_types):
        assert f'"type": "{key_type}"' in readme
