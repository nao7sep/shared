"""Tests for explicit command dependency context wiring."""

from polychat.commands.chat_files import ChatFileCommandHandlers
from polychat.commands.meta_generation import MetadataGenerationCommandHandlers
from polychat.commands.meta_inspection import MetadataInspectionCommandHandlers
from polychat.commands.misc import MiscCommandHandlers
from polychat.commands.runtime_models import RuntimeModelCommandHandlers
from polychat.commands.runtime_mutation import RuntimeMutationCommandHandlers
from polychat.commands.runtime_modes import RuntimeModeCommandHandlers


def test_command_handler_exposes_command_context(
    command_handler,
    mock_session_manager,
) -> None:
    assert command_handler.context.manager is mock_session_manager
    assert command_handler.manager is command_handler.context.manager
    assert command_handler.interaction is command_handler.context.interaction


def test_command_handler_wires_explicit_command_handlers(command_handler) -> None:
    groups = command_handler._handler_groups
    assert isinstance(groups["runtime_model"], RuntimeModelCommandHandlers)
    assert isinstance(groups["runtime_mode"], RuntimeModeCommandHandlers)
    assert isinstance(groups["runtime_mutation"], RuntimeMutationCommandHandlers)
    assert isinstance(groups["meta_generation"], MetadataGenerationCommandHandlers)
    assert isinstance(groups["meta_inspection"], MetadataInspectionCommandHandlers)
    assert isinstance(groups["chat_files"], ChatFileCommandHandlers)
    assert isinstance(groups["misc"], MiscCommandHandlers)
