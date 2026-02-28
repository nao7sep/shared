"""Integration tests for chat `updated_at` persistence behavior."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from polychat.chat import load_chat, save_chat
from polychat.commands import CommandHandler
from polychat.domain.chat import ChatDocument
from polychat.domain.profile import RuntimeProfile
from polychat.orchestrator import ChatOrchestrator
from polychat.session_manager import SessionManager


async def _build_session(tmp_path: Path) -> tuple[SessionManager, CommandHandler, ChatOrchestrator, str]:
    chat_path = tmp_path / "chat.json"
    profile = RuntimeProfile(
        default_ai="openai",
        models={"openai": "gpt-5-mini"},
        chats_dir=str(tmp_path),
        logs_dir=str(tmp_path),
        api_keys={},
        timeout=300,
    )
    chat_data = ChatDocument.from_raw({
        "metadata": {
            "title": None,
            "summary": None,
            "system_prompt": None,
            "created_utc": None,
            "updated_utc": None,
        },
        "messages": [
            {"role": "user", "content": ["hello"]},
            {"role": "assistant", "content": ["hi"], "model": "gpt-5-mini"},
        ],
    })

    await save_chat(str(chat_path), chat_data)
    manager = SessionManager(
        profile=profile,
        current_ai="openai",
        current_model="gpt-5-mini",
        chat=load_chat(str(chat_path)),
        chat_path=str(chat_path),
    )
    handler = CommandHandler(manager)
    orchestrator = ChatOrchestrator(manager)
    return manager, handler, orchestrator, str(chat_path)


@pytest.mark.asyncio
async def test_runtime_only_commands_do_not_bump_updated_at(tmp_path: Path) -> None:
    manager, handler, orchestrator, chat_path = await _build_session(tmp_path)
    before = manager.chat.metadata.updated_utc

    for command in ("/search on", "/search", "/retry", "/help", "/status", "/history 1"):
        response = await handler.execute_command(command)
        await orchestrator.handle_command_response(response)

    after = manager.chat.metadata.updated_utc
    assert after == before
    assert load_chat(chat_path).metadata.updated_utc == before


@pytest.mark.asyncio
async def test_mutating_commands_bump_updated_at_only_on_real_changes(tmp_path: Path) -> None:
    manager, handler, orchestrator, _chat_path = await _build_session(tmp_path)
    initial = manager.chat.metadata.updated_utc

    response = await handler.execute_command("/title First title")
    await orchestrator.handle_command_response(response)
    updated_after_title = manager.chat.metadata.updated_utc
    assert updated_after_title != initial

    await asyncio.sleep(0.001)
    response = await handler.execute_command("/title First title")
    await orchestrator.handle_command_response(response)
    unchanged_after_same_title = manager.chat.metadata.updated_utc
    assert unchanged_after_same_title == updated_after_title

    await asyncio.sleep(0.001)
    response = await handler.execute_command("/summary New summary")
    await orchestrator.handle_command_response(response)
    updated_after_summary = manager.chat.metadata.updated_utc
    assert updated_after_summary != unchanged_after_same_title

