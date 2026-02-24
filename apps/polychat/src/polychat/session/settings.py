"""Simple session setting mutations."""

from __future__ import annotations

from .state import SessionState


def switch_provider(state: SessionState, provider_name: str, model_name: str) -> None:
    """Switch active provider/model pair."""
    state.current_ai = provider_name
    state.current_model = model_name


def toggle_input_mode(state: SessionState) -> str:
    """Toggle input mode between quick and compose."""
    if state.input_mode == "quick":
        state.input_mode = "compose"
    else:
        state.input_mode = "quick"
    return state.input_mode

