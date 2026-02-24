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
    assert isinstance(command_handler._runtime_model_commands, RuntimeModelCommandHandlers)
    assert isinstance(command_handler._runtime_mode_commands, RuntimeModeCommandHandlers)
    assert isinstance(command_handler._runtime_mutation_commands, RuntimeMutationCommandHandlers)
    assert isinstance(command_handler._metadata_generation_commands, MetadataGenerationCommandHandlers)
    assert isinstance(command_handler._metadata_inspection_commands, MetadataInspectionCommandHandlers)
    assert isinstance(command_handler._chat_file_commands, ChatFileCommandHandlers)
    assert isinstance(command_handler._misc_commands, MiscCommandHandlers)
