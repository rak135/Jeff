"""Read-oriented inspect and historical run command handlers."""

from __future__ import annotations

from collections.abc import Callable

from jeff.cognitive import ContextPackage
from jeff.core.containers.models import Project, Run, WorkUnit
from jeff.core.schemas import Scope

from .command_common import (
    ensure_selection_review_for_run,
    require_flow_run,
    require_project_for_run,
    require_scoped_project,
    require_scoped_work_unit,
    resolve_historical_run,
    resolve_or_create_active_run,
)
from .command_models import CommandResult, InterfaceContext
from .json_views import lifecycle_json, run_show_json, trace_json
from .render import render_lifecycle, render_run_show, render_trace
from .session import CliSession


def inspect_command(
    *,
    tokens: list[str],
    session: CliSession,
    context: InterfaceContext,
    assemble_live_context_package_fn: Callable[..., ContextPackage],
) -> CommandResult:
    if len(tokens) != 1:
        raise ValueError("inspect uses the current work_unit scope only. Use /show <run_id> for manual historical inspect.")
    project = require_scoped_project(session, context)
    work_unit = require_scoped_work_unit(session, project)
    run, next_session, next_context, notice = resolve_or_create_active_run(
        session=session,
        context=context,
        project=project,
        work_unit=work_unit,
    )
    flow_run = next_context.flow_runs.get(str(run.run_id))
    next_context, selection_review = ensure_selection_review_for_run(context=next_context, run=run, flow_run=flow_run)
    live_context_package = _build_inspect_live_context_package(
        context=next_context,
        project=project,
        work_unit=work_unit,
        run=run,
        assemble_live_context_package_fn=assemble_live_context_package_fn,
    )
    payload = run_show_json(
        project=project,
        work_unit=work_unit,
        run=run,
        flow_run=flow_run,
        selection_review=selection_review,
        live_context_package=live_context_package,
    )
    text = render_run_show(payload)
    if notice is not None:
        text = f"{notice}\n{text}"
    return CommandResult(context=next_context, session=next_session, text=text, json_payload=payload)


def show_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    run, next_session, notice = resolve_historical_run(
        tokens=tokens,
        session=session,
        context=context,
        command_name=tokens[0],
    )
    project = require_project_for_run(context, run.project_id)
    work_unit = project.work_units[run.work_unit_id]
    flow_run = context.flow_runs.get(str(run.run_id))
    next_context, selection_review = ensure_selection_review_for_run(context=context, run=run, flow_run=flow_run)
    payload = run_show_json(
        project=project,
        work_unit=work_unit,
        run=run,
        flow_run=flow_run,
        selection_review=selection_review,
    )
    text = render_run_show(payload)
    if notice is not None:
        text = f"{notice}\n{text}"
    return CommandResult(context=next_context, session=next_session, text=text, json_payload=payload)


def trace_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    run, next_session, notice = resolve_historical_run(
        tokens=tokens,
        session=session,
        context=context,
        command_name=tokens[0],
    )
    flow_run = require_flow_run(context, str(run.run_id))
    payload = trace_json(flow_run)
    text = render_trace(payload)
    if notice is not None:
        text = f"{notice}\n{text}"
    return CommandResult(context=context, session=next_session, text=text, json_payload=payload)


def lifecycle_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    run, next_session, notice = resolve_historical_run(
        tokens=tokens,
        session=session,
        context=context,
        command_name=tokens[0],
    )
    flow_run = require_flow_run(context, str(run.run_id))
    payload = lifecycle_json(flow_run)
    text = render_lifecycle(payload)
    if notice is not None:
        text = f"{notice}\n{text}"
    return CommandResult(context=context, session=next_session, text=text, json_payload=payload)


def _inspect_live_context_purpose(work_unit: WorkUnit) -> str:
    return f"operator explanation proposal support {work_unit.objective}"


def _build_inspect_live_context_package(
    *,
    context: InterfaceContext,
    project: Project,
    work_unit: WorkUnit,
    run: Run,
    assemble_live_context_package_fn: Callable[..., ContextPackage],
) -> ContextPackage:
    return assemble_live_context_package_fn(
        context=context,
        trigger_summary=work_unit.objective,
        purpose=_inspect_live_context_purpose(work_unit),
        scope=Scope(
            project_id=str(project.project_id),
            work_unit_id=str(work_unit.work_unit_id),
            run_id=str(run.run_id),
        ),
        knowledge_topic_query=work_unit.objective,
    )