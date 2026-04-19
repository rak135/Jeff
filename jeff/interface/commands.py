"""Small explicit command dispatcher over backend read surfaces and flow outputs."""

from __future__ import annotations

from collections.abc import Callable
import json
import shlex

from jeff.cognitive import ResearchOperatorSurfaceError, ResearchSynthesisRuntimeError

from .command_common import assemble_live_context_package
from .command_inspect import inspect_command, lifecycle_command, show_command, trace_command
from .command_models import CommandResult, InterfaceContext, SelectionReviewRecord
from .command_requests import request_command
from .command_research import research_command
from .command_scope import json_command, mode_command, project_command, run_command, scope_command, work_command
from .command_selection import selection_command
from .json_views import research_error_json
from .render import render_help
from .session import CliSession


def execute_command(
    *,
    command_line: str,
    session: CliSession,
    context: InterfaceContext,
    json_output: bool | None = None,
    live_debug_emitter: Callable[[str], None] | None = None,
) -> CommandResult:
    tokens = _parse(command_line)
    if not tokens:
        return CommandResult(context=context, session=session, text="")

    if tokens[0] == "help":
        return CommandResult(context=context, session=session, text=render_help())

    if tokens[0] == "project":
        return project_command(tokens=tokens, session=session, context=context)
    if tokens[0] == "work":
        return work_command(tokens=tokens, session=session, context=context)
    if tokens[0] == "run":
        return run_command(tokens=tokens, session=session, context=context)
    if tokens[0] == "scope":
        return scope_command(tokens=tokens, session=session, context=context)
    if tokens[0] == "mode":
        return mode_command(tokens=tokens, session=session, context=context)
    if tokens[0] == "json":
        return json_command(tokens=tokens, session=session, context=context)
    if tokens[0] == "inspect":
        result = inspect_command(
            tokens=tokens,
            session=session,
            context=context,
            assemble_live_context_package_fn=assemble_live_context_package,
        )
        return _apply_json_mode(result, json_output=json_output)
    if tokens[0] == "show":
        result = show_command(tokens=tokens, session=session, context=context)
        return _apply_json_mode(result, json_output=json_output)
    if tokens[0] == "selection":
        result = selection_command(tokens=tokens, session=session, context=context)
        return _apply_json_mode(result, json_output=json_output)
    if tokens[0] == "trace":
        result = trace_command(tokens=tokens, session=session, context=context)
        return _apply_json_mode(result, json_output=json_output)
    if tokens[0] == "lifecycle":
        result = lifecycle_command(tokens=tokens, session=session, context=context)
        return _apply_json_mode(result, json_output=json_output)
    if tokens[0] == "research":
        try:
            result = research_command(
                command_line=command_line,
                tokens=tokens,
                session=session,
                context=context,
                assemble_live_context_package_fn=assemble_live_context_package,
                live_debug_emitter=live_debug_emitter,
            )
        except ResearchOperatorSurfaceError as exc:
            if not (json_output is True or (json_output is None and session.json_output)):
                raise
            payload = research_error_json(
                project_id=exc.project_id,
                work_unit_id=exc.work_unit_id,
                run_id=exc.run_id,
                research_mode=exc.research_mode,
                error=exc,
                session=session,
                debug_events=tuple(getattr(exc, "debug_events", ())),
            )
            payload = _with_debug_payload(payload, debug_events=getattr(exc, "debug_events", ()), session=session)
            return CommandResult(
                context=context,
                session=session,
                text=json.dumps(payload, sort_keys=True),
                json_payload=payload,
                debug_events=tuple(getattr(exc, "debug_events", ())),
            )
        except ResearchSynthesisRuntimeError as exc:
            if not (json_output is True or (json_output is None and session.json_output)):
                raise
            payload = research_error_json(
                project_id=exc.project_id,
                work_unit_id=exc.work_unit_id,
                run_id=exc.run_id,
                research_mode=exc.research_mode,
                error=exc,
                session=session,
                debug_events=tuple(getattr(exc, "debug_events", ())),
            )
            payload = _with_debug_payload(payload, debug_events=getattr(exc, "debug_events", ()), session=session)
            return CommandResult(
                context=context,
                session=session,
                text=json.dumps(payload, sort_keys=True),
                json_payload=payload,
                debug_events=tuple(getattr(exc, "debug_events", ())),
            )
        return _apply_json_mode(result, json_output=json_output)
    if tokens[0] in {"approve", "reject", "retry", "revalidate", "recover"}:
        result = request_command(tokens=tokens, session=session, context=context)
        return _apply_json_mode(result, json_output=json_output)

    raise ValueError(
        f"unsupported command: {' '.join(tokens)}. "
        "Jeff CLI is command-driven; use /help to see supported slash commands."
    )


def _parse(command_line: str) -> list[str]:
    normalized = command_line.strip()
    if not normalized:
        return []
    if normalized.startswith("/"):
        normalized = normalized[1:]
    return shlex.split(normalized)


def _apply_json_mode(result: CommandResult, *, json_output: bool | None) -> CommandResult:
    if not (result.json_payload and (json_output is True or (json_output is None and result.session.json_output))):
        return result
    payload = _with_debug_payload(result.json_payload, debug_events=result.debug_events, session=result.session)
    return CommandResult(
        context=result.context,
        session=result.session,
        text=json.dumps(payload, sort_keys=True),
        json_payload=payload,
        debug_events=result.debug_events,
    )


def _with_debug_payload(
    payload: dict[str, object],
    *,
    debug_events: tuple[dict[str, object], ...],
    session: CliSession,
) -> dict[str, object]:
    if session.output_mode != "debug" or not debug_events:
        return payload
    return {**payload, "debug": {"events": [dict(event) for event in debug_events]}}
