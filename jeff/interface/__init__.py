"""CLI-first truthful operator surface."""

from .cli import JeffCLI
from .commands import CommandResult, InterfaceContext, execute_command
from .session import CliSession, SessionScope

__all__ = [
    "CliSession",
    "CommandResult",
    "InterfaceContext",
    "JeffCLI",
    "SessionScope",
    "execute_command",
]
