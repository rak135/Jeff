"""CLI facade with shared one-shot and interactive command semantics."""

from __future__ import annotations

from collections.abc import Iterable

from .commands import CommandResult, InterfaceContext, execute_command
from .session import CliSession


class JeffCLI:
    def __init__(
        self,
        *,
        context: InterfaceContext,
        session: CliSession | None = None,
    ) -> None:
        self._context = context
        self._session = session or CliSession()

    @property
    def session(self) -> CliSession:
        return self._session

    @property
    def prompt(self) -> str:
        return self._session.prompt

    def run_one_shot(self, command_line: str, *, json_output: bool | None = None) -> str:
        result = self.execute(command_line, json_output=json_output)
        return result.text

    def run_interactive(self, command_lines: Iterable[str]) -> list[str]:
        outputs: list[str] = []
        for command_line in command_lines:
            result = self.execute(command_line)
            outputs.append(result.text)
        return outputs

    def execute(self, command_line: str, *, json_output: bool | None = None) -> CommandResult:
        result = execute_command(
            command_line=command_line,
            session=self._session,
            context=self._context,
            json_output=json_output,
        )
        self._session = result.session
        return result
