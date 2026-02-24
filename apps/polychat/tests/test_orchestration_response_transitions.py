"""Tests for response-mode transition policy helpers."""

from typing import cast

import pytest

from polychat.orchestrator_types import ActionMode
from polychat.orchestration.response_handlers import (
    build_transition_state,
    can_mutate_normal_chat,
    has_trailing_user_message,
    should_release_for_cancel,
    should_release_for_error,
    should_release_for_rollback,
    should_rollback_pre_send,
)


def test_build_transition_state_tracks_context_and_hex() -> None:
    state = build_transition_state(
        "normal",
        chat_path="/tmp/chat.json",
        chat_data={"messages": []},
        assistant_hex_id="abc123",
    )
    assert state.mode == "normal"
    assert state.has_chat_context is True
    assert state.has_assistant_hex_id is True


def test_build_transition_state_without_context_or_hex() -> None:
    state = build_transition_state(
        "normal",
        chat_path=None,
        chat_data=None,
        assistant_hex_id=None,
    )
    assert state.has_chat_context is False
    assert state.has_assistant_hex_id is False


@pytest.mark.parametrize(
    ("mode", "chat_path", "chat_data", "expected"),
    [
        ("normal", "/tmp/chat.json", {"messages": []}, True),
        ("normal", None, {"messages": []}, False),
        ("retry", "/tmp/chat.json", {"messages": []}, False),
        ("secret", "/tmp/chat.json", {"messages": []}, False),
    ],
)
def test_can_mutate_normal_chat_requires_normal_mode_and_context(
    mode: ActionMode,
    chat_path: str | None,
    chat_data: dict | None,
    expected: bool,
) -> None:
    state = build_transition_state(
        cast(ActionMode, mode),
        chat_path=chat_path,
        chat_data=chat_data,
        assistant_hex_id=None,
    )
    assert can_mutate_normal_chat(state) is expected


def test_should_release_for_error_normal_mode_requires_context() -> None:
    with_context = build_transition_state(
        "normal",
        chat_path="/tmp/chat.json",
        chat_data={"messages": []},
        assistant_hex_id="abc",
    )
    no_context = build_transition_state(
        "normal",
        chat_path=None,
        chat_data=None,
        assistant_hex_id="abc",
    )

    assert should_release_for_error(with_context) is True
    assert should_release_for_error(no_context) is False


@pytest.mark.parametrize("mode", ["retry", "secret"])
def test_should_release_for_error_non_normal_requires_only_hex(mode: ActionMode) -> None:
    with_hex = build_transition_state(
        cast(ActionMode, mode),
        chat_path=None,
        chat_data=None,
        assistant_hex_id="abc",
    )
    without_hex = build_transition_state(
        cast(ActionMode, mode),
        chat_path=None,
        chat_data=None,
        assistant_hex_id=None,
    )

    assert should_release_for_error(with_hex) is True
    assert should_release_for_error(without_hex) is False


def test_should_release_for_cancel_matches_mode_policy() -> None:
    normal_no_context = build_transition_state(
        "normal",
        chat_path=None,
        chat_data=None,
        assistant_hex_id="abc",
    )
    retry_with_hex = build_transition_state(
        "retry",
        chat_path=None,
        chat_data=None,
        assistant_hex_id="abc",
    )

    assert should_release_for_cancel(normal_no_context) is False
    assert should_release_for_cancel(retry_with_hex) is True


def test_should_release_for_rollback_depends_only_on_hex_presence() -> None:
    with_hex = build_transition_state(
        "normal",
        chat_path=None,
        chat_data=None,
        assistant_hex_id="abc",
    )
    without_hex = build_transition_state(
        "normal",
        chat_path="/tmp/chat.json",
        chat_data={"messages": []},
        assistant_hex_id=None,
    )

    assert should_release_for_rollback(with_hex) is True
    assert should_release_for_rollback(without_hex) is False


def test_has_trailing_user_message_detection() -> None:
    trailing_user = {"messages": [{"role": "assistant"}, {"role": "user"}]}
    trailing_assistant = {"messages": [{"role": "user"}, {"role": "assistant"}]}

    assert has_trailing_user_message(trailing_user) is True
    assert has_trailing_user_message(trailing_assistant) is False
    assert has_trailing_user_message({"messages": []}) is False
    assert has_trailing_user_message(None) is False


def test_should_rollback_pre_send_requires_normal_context_and_trailing_user() -> None:
    normal_state = build_transition_state(
        "normal",
        chat_path="/tmp/chat.json",
        chat_data={"messages": [{"role": "user"}]},
        assistant_hex_id=None,
    )
    retry_state = build_transition_state(
        "retry",
        chat_path="/tmp/chat.json",
        chat_data={"messages": [{"role": "user"}]},
        assistant_hex_id=None,
    )
    trailing_user = {"messages": [{"role": "assistant"}, {"role": "user"}]}
    trailing_assistant = {"messages": [{"role": "assistant"}]}

    assert should_rollback_pre_send(normal_state, trailing_user) is True
    assert should_rollback_pre_send(normal_state, trailing_assistant) is False
    assert should_rollback_pre_send(retry_state, trailing_user) is False
