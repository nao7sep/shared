"""Typed models for command documentation metadata."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CommandDocEntry:
    """One documented command entry shared by help and README output."""

    command_names: tuple[str, ...]
    help_signature: str
    help_description: str
    readme_signature: str
    readme_description: str
    help_continuations: tuple[str, ...] = ()
    readme_continuations: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CommandDocSection:
    """One command documentation section."""

    title: str
    entries: tuple[CommandDocEntry, ...]
