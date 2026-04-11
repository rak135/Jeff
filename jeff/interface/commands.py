"""Small explicit command handlers over backend read surfaces and flow outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import shlex
from typing import Mapping

from jeff.core.containers.models import Project, Run, WorkUnit
from jeff.core.state.models import GlobalState
from jeff.orchestrator import FlowRunResult

from .json_views import (
    lifecycle_json,
    project_list_json,
    request_receipt_json,
    run_show_json,
    session_scope_json,
    trace_json,
    work_unit_list_json,
)
from .render import (
    render_help,
    render_lifecycle,
    render_project_list,
    render_request_receipt,
    render_run_show,
    render_scope,
    render_trace,
    render_work_unit_list,
)
from .session import CliSession


@dataclass(frozen=True, slots=True)
class InterfaceContext:
    state: GlobalState
    flow_runs: Mapping[str, FlowRunResult] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CommandResult:
    session: CliSession
    text: str
    json_payload: dict[str, object] | None = None


def execute_command(
    *,
    command_line: str,
    session: CliSession,
    context: InterfaceContext,
    json_output: bool | None = None,
) -> CommandResult:
    tokens = _parse(command_line)
    if not tokens:
        return CommandResult(session=session, text="")

    if tokens[0] == "help":
        return CommandResult(session=session, text=render_help())

    if tokens[0] == "project":
        return _project_command(tokens=tokens, session=session, context=context)
    if tokens[0] == "work":
        return _work_command(tokens=tokens, session=session, context=context)
    if tokens[0] == "run":
        return _run_command(tokens=tokens, session=session, context=context)
    if tokens[0] == "scope":
        return _scope_command(tokens=tokens, session=session)
    if tokens[0] == "mode":
        return _mode_command(tokens=tokens, session=session)
    if tokens[0] == "json":
        return _json_command(tokens=tokens, session=session)
    if tokens[0] in {"inspect", "show"}:
        result = _show_command(tokens=tokens, session=session, context=context)
        return _apply_json_mode(result, json_output=json_output)
    if tokens[0] == "trace":
        result = _trace_command(tokens=tokens, session=session, context=context)
        return _apply_json_mode(result, json_output=json_output)
    if tokens[0] == "lifecycle":
        result = _lifecycle_command(tokens=tokens, session=session, context=context)
        return _apply_json_mode(result, json_output=json_output)
    if tokens[0] in {"approve", "reject", "retry", "revalidate", "recover"}:
        return _request_command(tokens=tokens, session=session, context=context)

    raise ValueError(f"unsupported command: {' '.join(tokens)}")


def _parse(command_line: str) -> list[str]:
    normalized = command_line.strip()
    if not normalized:
        return []
    if normalized.startswith("/"):
        normalized = normalized[1:]
    return shlex.split(normalized)


def _project_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    if len(tokens) < 2:
        raise ValueError("project command requires list or use")
    if tokens[1] == "list":
        projects = tuple(context.state.projects.values())
        payload = project_list_json(projects)
        return CommandResult(session=session, text=render_project_list(payload), json_payload=payload)
    if tokens[1] == "use" and len(tokens) == 3:
        project = _get_project(context, tokens[2])
        next_session = session.with_scope(project_id=str(project.project_id), work_unit_id=None, run_id=None)
        return CommandResult(
            session=next_session,
            text=f"session scope updated: project_id={project.project_id}",
        )
    raise ValueError("project command must be 'project list' or 'project use <project_id>'")


def _work_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    project = _require_scoped_project(session, context)
    if len(tokens) < 2:
        raise ValueError("work command requires list or use")
    if tokens[1] == "list":
        payload = work_unit_list_json(project)
        return CommandResult(session=session, text=render_work_unit_list(payload), json_payload=payload)
    if tokens[1] == "use" and len(tokens) == 3:
        work_unit = _get_work_unit(project, tokens[2])
        next_session = session.with_scope(
            project_id=str(project.project_id),
            work_unit_id=str(work_unit.work_unit_id),
            run_id=None,
        )
        return CommandResult(
            session=next_session,
            text=f"session scope updated: project_id={project.project_id} work_unit_id={work_unit.work_unit_id}",
        )
    raise ValueError("work command must be 'work list' or 'work use <work_unit_id>'")


def _run_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    if len(tokens) != 3 or tokens[1] != "use":
        raise ValueError("run command must be 'run use <run_id>'")
    project = _require_scoped_project(session, context)
    work_unit = _require_scoped_work_unit(session, project)
    run = _get_run(work_unit, tokens[2])
    next_session = session.with_scope(
        project_id=str(project.project_id),
        work_unit_id=str(work_unit.work_unit_id),
        run_id=str(run.run_id),
    )
    return CommandResult(
        session=next_session,
        text=(
            f"session scope updated: project_id={project.project_id} "
            f"work_unit_id={work_unit.work_unit_id} run_id={run.run_id}"
        ),
    )


def _scope_command(*, tokens: list[str], session: CliSession) -> CommandResult:
    if len(tokens) != 2:
        raise ValueError("scope command must be 'scope show' or 'scope clear'")
    if tokens[1] == "show":
        payload = session_scope_json(session)
        return CommandResult(session=session, text=render_scope(payload), json_payload=payload)
    if tokens[1] == "clear":
        next_session = session.clear_scope()
        return CommandResult(session=next_session, text="session scope cleared")
    raise ValueError("scope command must be 'scope show' or 'scope clear'")


def _mode_command(*, tokens: list[str], session: CliSession) -> CommandResult:
    if len(tokens) != 2 or tokens[1] not in {"compact", "debug"}:
        raise ValueError("mode command must be 'mode compact' or 'mode debug'")
    next_session = session.with_mode(tokens[1])  # type: ignore[arg-type]
    return CommandResult(session=next_session, text=f"output mode set to {tokens[1]}")


def _json_command(*, tokens: list[str], session: CliSession) -> CommandResult:
    if len(tokens) != 2 or tokens[1] not in {"on", "off"}:
        raise ValueError("json command must be 'json on' or 'json off'")
    enabled = tokens[1] == "on"
    next_session = session.with_json_output(enabled)
    return CommandResult(session=next_session, text=f"json_output set to {enabled}")


def _show_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    run = _resolve_run_from_tokens(tokens=tokens, session=session, context=context)
    project = _require_project_for_run(context, run.project_id)
    work_unit = project.work_units[run.work_unit_id]
    flow_run = context.flow_runs.get(str(run.run_id))
    payload = run_show_json(project=project, work_unit=work_unit, run=run, flow_run=flow_run)
    return CommandResult(session=session, text=render_run_show(payload), json_payload=payload)


def _trace_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    run = _resolve_run_from_tokens(tokens=tokens, session=session, context=context)
    flow_run = _require_flow_run(context, str(run.run_id))
    payload = trace_json(flow_run)
    return CommandResult(session=session, text=render_trace(payload), json_payload=payload)


def _lifecycle_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    run = _resolve_run_from_tokens(tokens=tokens, session=session, context=context)
    flow_run = _require_flow_run(context, str(run.run_id))
    payload = lifecycle_json(flow_run)
    return CommandResult(session=session, text=render_lifecycle(payload), json_payload=payload)


def _request_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    request_type = tokens[0]
    target_run = _resolve_run_from_tokens(tokens=tokens, session=session, context=context)
    flow_run = _require_flow_run(context, str(target_run.run_id))
    routed_outcome = None if flow_run.routing_decision is None else flow_run.routing_decision.routed_outcome

    allowed_outcomes = {
        "approve": {"approval_required"},
        "reject": {"approval_required"},
        "retry": {"retry"},
        "revalidate": {"revalidate"},
        "recover": {"recover"},
    }
    if routed_outcome not in allowed_outcomes[request_type]:
        raise ValueError(
            f"{request_type} is not currently available for run {target_run.run_id}; "
            f"current routed_outcome is {routed_outcome or 'none'}"
        )

    note = (
        f"{request_type} request accepted for run {target_run.run_id}; "
        "this records request entry only and does not imply apply, completion, or truth mutation."
    )
    payload = request_receipt_json(
        request_type=request_type,
        target=str(target_run.run_id),
        accepted=True,
        scope={
            "project_id": session.scope.project_id,
            "work_unit_id": session.scope.work_unit_id,
            "run_id": session.scope.run_id,
        },
        note=note,
    )
    return CommandResult(session=session, text=render_request_receipt(payload), json_payload=payload)


def _apply_json_mode(result: CommandResult, *, json_output: bool | None) -> CommandResult:
    if not (result.json_payload and (json_output is True or (json_output is None and result.session.json_output))):
        return result
    return CommandResult(
        session=result.session,
        text=json.dumps(result.json_payload, sort_keys=True),
        json_payload=result.json_payload,
    )


def _get_project(context: InterfaceContext, project_id: str) -> Project:
    try:
        return context.state.projects[project_id]
    except KeyError as exc:
        raise ValueError(f"unknown project_id: {project_id}") from exc


def _require_scoped_project(session: CliSession, context: InterfaceContext) -> Project:
    if session.scope.project_id is None:
        raise ValueError("current session scope has no project_id")
    return _get_project(context, session.scope.project_id)


def _get_work_unit(project: Project, work_unit_id: str) -> WorkUnit:
    try:
        return project.work_units[work_unit_id]
    except KeyError as exc:
        raise ValueError(f"unknown work_unit_id: {work_unit_id}") from exc


def _require_scoped_work_unit(session: CliSession, project: Project) -> WorkUnit:
    if session.scope.work_unit_id is None:
        raise ValueError("current session scope has no work_unit_id")
    return _get_work_unit(project, session.scope.work_unit_id)


def _get_run(work_unit: WorkUnit, run_id: str) -> Run:
    try:
        return work_unit.runs[run_id]
    except KeyError as exc:
        raise ValueError(f"unknown run_id: {run_id}") from exc


def _resolve_run_from_tokens(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> Run:
    run_id = tokens[1] if len(tokens) > 1 else session.scope.run_id
    if run_id is None:
        raise ValueError("no run_id was provided and the session scope has no current run")
    if session.scope.project_id is not None and session.scope.work_unit_id is not None:
        project = _get_project(context, session.scope.project_id)
        work_unit = _get_work_unit(project, session.scope.work_unit_id)
        return _get_run(work_unit, run_id)

    for project in context.state.projects.values():
        for work_unit in project.work_units.values():
            if run_id in work_unit.runs:
                return work_unit.runs[run_id]
    raise ValueError(f"unknown run_id: {run_id}")


def _require_project_for_run(context: InterfaceContext, project_id: str) -> Project:
    return _get_project(context, str(project_id))


def _require_flow_run(context: InterfaceContext, run_id: str) -> FlowRunResult:
    try:
        return context.flow_runs[run_id]
    except KeyError as exc:
        raise ValueError(f"no orchestrator flow result is available for run {run_id}") from exc
