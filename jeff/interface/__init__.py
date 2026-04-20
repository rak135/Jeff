"""CLI-first truthful operator surface."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .commands import CommandResult, InterfaceContext, assemble_live_context_package, execute_command
from .session import CliSession, SessionScope

if TYPE_CHECKING:
    from .cli import JeffCLI

__all__ = [
    "CliSession",
    "CommandResult",
    "InterfaceContext",
    "JeffCLI",
    "SessionScope",
    "assemble_live_context_package",
    "execute_command",
]


def __getattr__(name: str):
    if name != "JeffCLI":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from .cli import JeffCLI

    return JeffCLI
