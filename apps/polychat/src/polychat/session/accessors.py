"""Session access descriptors and state helpers for SessionManager."""

from __future__ import annotations

from typing import Any, Callable, Generic, Optional, TYPE_CHECKING, TypeVar, cast, overload

from .state import SessionState

if TYPE_CHECKING:
    from ..session_manager import SessionManager

T = TypeVar("T")


class StateField(Generic[T]):
    """Descriptor forwarding one SessionManager attribute to SessionState."""

    def __init__(
        self,
        field_name: str,
        *,
        readonly: bool = False,
        validator: Optional[Callable[[T], None]] = None,
        coerce: Optional[Callable[[T], T]] = None,
    ) -> None:
        self._field_name = field_name
        self._readonly = readonly
        self._validator = validator
        self._coerce = coerce

    @overload
    def __get__(
        self,
        instance: None,
        owner: type["SessionManager"],
    ) -> "StateField[T]":
        ...

    @overload
    def __get__(
        self,
        instance: "SessionManager",
        owner: type["SessionManager"],
    ) -> T:
        ...

    def __get__(
        self,
        instance: Optional["SessionManager"],
        owner: type["SessionManager"],
    ) -> Any:
        if instance is None:
            return self
        return cast(T, getattr(instance._state, self._field_name))

    def __set__(self, instance: "SessionManager", value: T) -> None:
        if self._readonly:
            raise AttributeError(f"'{self._field_name}' is read-only")
        if self._coerce is not None:
            value = self._coerce(value)
        if self._validator is not None:
            self._validator(value)
        setattr(instance._state, self._field_name, value)


def state_to_dict(
    state: SessionState,
    *,
    message_hex_ids: dict[int, str],
) -> dict[str, Any]:
    """Serialize SessionState for diagnostics."""
    return {
        "current_ai": state.current_ai,
        "current_model": state.current_model,
        "helper_ai": state.helper_ai,
        "helper_model": state.helper_model,
        "profile": state.profile.to_dict(),
        "chat": state.chat.to_dict(),
        "chat_path": state.chat_path,
        "profile_path": state.profile_path,
        "log_file": state.log_file,
        "system_prompt": state.system_prompt,
        "system_prompt_path": state.system_prompt_path,
        "input_mode": state.input_mode,
        "retry_mode": state.retry_mode,
        "secret_mode": state.secret_mode,
        "search_mode": state.search_mode,
        "message_hex_ids": message_hex_ids,
        "hex_id_set": state.hex_id_set,
    }
