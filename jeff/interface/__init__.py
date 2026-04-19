"""CLI-first truthful operator surface."""

from .cli import JeffCLI
from .commands import CommandResult, InterfaceContext, assemble_live_context_package, execute_command
from .session import CliSession, SessionScope

__all__ = [
    "CliSession",
    "CommandResult",
    "InterfaceContext",
    "JeffCLI",
    "SessionScope",
    "assemble_live_context_package",
    "execute_command",
]
