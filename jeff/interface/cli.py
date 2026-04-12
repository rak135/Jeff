"""CLI facade with shared one-shot and interactive command semantics."""

from __future__ import annotations

from collections.abc import Iterable
import json
from collections.abc import Callable

from jeff.cognitive import ResearchSynthesisRuntimeError

from .json_views import research_error_json
from .commands import CommandResult, InterfaceContext, execute_command
from .render import render_research_debug_event
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
        return self._compose_result_output(result, json_output=json_output)

    def run_interactive(self, command_lines: Iterable[str]) -> list[str]:
        outputs: list[str] = []
        for command_line in command_lines:
            try:
                result = self.execute(command_line)
                outputs.append(self._compose_result_output(result, json_output=None))
            except Exception as exc:
                outputs.append(self._compose_exception_output(exc))
        return outputs

    def execute(
        self,
        command_line: str,
        *,
        json_output: bool | None = None,
        live_debug_emitter: Callable[[str], None] | None = None,
    ) -> CommandResult:
        result = execute_command(
            command_line=command_line,
            session=self._session,
            context=self._context,
            json_output=json_output,
            live_debug_emitter=live_debug_emitter,
        )
        self._session = result.session
        self._context = result.context
        return result

    def render_research_runtime_error(self, error: ResearchSynthesisRuntimeError) -> str:
        if self._session.json_output:
            payload = research_error_json(
                project_id=error.project_id,
                work_unit_id=error.work_unit_id,
                run_id=error.run_id,
                research_mode=error.research_mode,
                error=error,
                session=self._session,
            )
            debug_events = tuple(getattr(error, "debug_events", ()))
            if self._session.output_mode == "debug" and debug_events:
                payload = {**payload, "debug": {"events": [dict(event) for event in debug_events]}}
            return json.dumps(payload, sort_keys=True)
        return str(error)

    def _compose_result_output(self, result: CommandResult, *, json_output: bool | None) -> str:
        if json_output is True or (json_output is None and result.session.json_output):
            return result.text
        if result.session.output_mode != "debug" or not result.debug_events:
            return result.text
        debug_lines = [render_research_debug_event(event) for event in result.debug_events]
        return "\n".join([*debug_lines, result.text]) if result.text else "\n".join(debug_lines)

    def _compose_exception_output(self, exc: Exception) -> str:
        debug_events = tuple(getattr(exc, "debug_events", ()))
        if isinstance(exc, ResearchSynthesisRuntimeError):
            rendered_error = self.render_research_runtime_error(exc)
        else:
            rendered_error = str(exc)
        if self._session.output_mode != "debug" or not debug_events or self._session.json_output:
            return rendered_error
        debug_lines = [render_research_debug_event(event) for event in debug_events]
        return "\n".join([*debug_lines, rendered_error])
