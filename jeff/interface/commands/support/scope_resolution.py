"""CLI/session scope and run-resolution helpers."""

from __future__ import annotations

import re

from jeff.core.containers.models import Project, Run, WorkUnit

from ...session import CliSession
from ..models import InterfaceContext
from .transitions import create_run_for_work_unit


def get_project(context: InterfaceContext, project_id: str) -> Project:
    try:
        return context.state.projects[project_id]
    except KeyError as exc:
        raise ValueError(
            f"unknown project_id: {project_id}. Use /project list to discover valid project_id values."
        ) from exc


def require_scoped_project(session: CliSession, context: InterfaceContext) -> Project:
    if session.scope.project_id is None:
        raise ValueError(
            "current session scope has no project_id. "
            "Use /project list, then /project use <project_id>."
        )
    return get_project(context, session.scope.project_id)


def get_work_unit(project: Project, work_unit_id: str) -> WorkUnit:
    try:
        return project.work_units[work_unit_id]
    except KeyError as exc:
        raise ValueError(
            f"unknown work_unit_id: {work_unit_id}. Use /work list to discover valid work_unit_id values."
        ) from exc


def require_scoped_work_unit(session: CliSession, project: Project) -> WorkUnit:
    if session.scope.work_unit_id is None:
        raise ValueError(
            "current session scope has no work_unit_id. "
            "Use /work list, then /work use <work_unit_id>."
        )
    return get_work_unit(project, session.scope.work_unit_id)


def get_run(work_unit: WorkUnit, run_id: str) -> Run:
    try:
        return work_unit.runs[run_id]
    except KeyError as exc:
        raise ValueError(
            f"unknown run_id: {run_id}. Use /run list to discover valid run_id values."
        ) from exc


def resolve_run_from_tokens(
    *,
    tokens: list[str],
    session: CliSession,
    context: InterfaceContext,
    command_name: str,
) -> Run:
    run_id = tokens[1] if len(tokens) > 1 else session.scope.run_id
    if run_id is None:
        raise ValueError(missing_run_message(command_name))
    if session.scope.project_id is not None:
        project = get_project(context, session.scope.project_id)
        if session.scope.work_unit_id is not None:
            work_unit = get_work_unit(project, session.scope.work_unit_id)
            return get_run(work_unit, run_id)

        matches = [
            work_unit.runs[run_id]
            for work_unit in project.work_units.values()
            if run_id in work_unit.runs
        ]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ValueError(
                f"ambiguous run_id: {run_id} requires work_unit scope inside current project scope {project.project_id}. "
                "Use /work list, then /work use <work_unit_id>."
            )
        raise ValueError(
            f"unknown run_id: {run_id} in current project scope {project.project_id}. "
            "Use /work list or /run list to discover valid IDs."
        )

    matches = [
        work_unit.runs[run_id]
        for project in context.state.projects.values()
        for work_unit in project.work_units.values()
        if run_id in work_unit.runs
    ]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(
            f"ambiguous run_id: {run_id} requires project or work_unit scope. "
            "Use /project list, /project use <project_id>, and /work list to narrow scope."
        )
    raise ValueError(f"unknown run_id: {run_id}. Use /project list, /work list, or /run list to discover valid IDs.")


def resolve_historical_run(
    *,
    tokens: list[str],
    session: CliSession,
    context: InterfaceContext,
    command_name: str,
) -> tuple[Run, CliSession, str | None]:
    if len(tokens) > 1:
        run = resolve_run_from_tokens(tokens=tokens, session=session, context=context, command_name=command_name)
        return run, session, None
    if session.scope.run_id is not None:
        run = resolve_run_from_tokens(tokens=tokens, session=session, context=context, command_name=command_name)
        return run, session, None
    if session.scope.project_id is None or session.scope.work_unit_id is None:
        raise ValueError(
            f"{command_name} requires a current run, an explicit <run_id>, or selected work_unit scope. "
            "Use /project list, /project use <project_id>, /work list, and /work use <work_unit_id>."
        )
    project = get_project(context, session.scope.project_id)
    work_unit = get_work_unit(project, session.scope.work_unit_id)
    runs = existing_runs_in_work_unit(work_unit)
    if not runs:
        raise ValueError(
            f"{command_name} found no existing run in work_unit {work_unit.work_unit_id}. "
            "Use /inspect to create and select a new run, or /run list to confirm history."
        )
    if len(runs) > 1:
        raise ValueError(
            f"{command_name} found multiple runs in work_unit {work_unit.work_unit_id}. "
            "Use /run list, then /run use <run_id> or pass an explicit <run_id>."
        )
    run = runs[0]
    next_session = session.with_scope(
        project_id=str(project.project_id),
        work_unit_id=str(work_unit.work_unit_id),
        run_id=str(run.run_id),
    )
    return run, next_session, f"auto-selected current run: {run.run_id}"


def resolve_or_create_active_run(
    *,
    session: CliSession,
    context: InterfaceContext,
    project: Project,
    work_unit: WorkUnit,
) -> tuple[Run, CliSession, InterfaceContext, str | None]:
    if session.scope.run_id is not None and session.scope.work_unit_id == str(work_unit.work_unit_id):
        run = get_run(work_unit, session.scope.run_id)
        return run, session, context, None

    runs = existing_runs_in_work_unit(work_unit)
    if len(runs) == 1:
        existing_run = runs[0]
        next_session = session.with_scope(
            project_id=str(project.project_id),
            work_unit_id=str(work_unit.work_unit_id),
            run_id=str(existing_run.run_id),
        )
        return existing_run, next_session, context, f"auto-selected current run: {existing_run.run_id}"
    if len(runs) > 1:
        raise ValueError(
            f"inspect found multiple runs in work_unit {work_unit.work_unit_id}. "
            "Use /run list, then /run use <run_id> to choose the current run."
        )

    created_run, next_context = create_run_for_work_unit(context=context, project=project, work_unit=work_unit)
    next_session = session.with_scope(
        project_id=str(project.project_id),
        work_unit_id=str(work_unit.work_unit_id),
        run_id=str(created_run.run_id),
    )
    return created_run, next_session, next_context, f"created and selected new run: {created_run.run_id}"


def select_existing_run(work_unit: WorkUnit) -> Run | None:
    runs = existing_runs_in_work_unit(work_unit)
    if not runs:
        return None
    return max(runs, key=run_sort_key)


def existing_runs_in_work_unit(work_unit: WorkUnit) -> tuple[Run, ...]:
    return tuple(sorted(work_unit.runs.values(), key=run_sort_key))


def run_sort_key(run: Run) -> tuple[int, str]:
    run_id = str(run.run_id)
    match = re.fullmatch(r"run-(\d+)", run_id)
    if match is not None:
        return (int(match.group(1)), run_id)
    return (-1, run_id)


def missing_run_message(command_name: str) -> str:
    return (
        f"{command_name} requires a current run or an explicit <run_id>. "
        "Use /run list, /run use <run_id>, or /scope show."
    )


def require_project_for_run(context: InterfaceContext, project_id: str) -> Project:
    return get_project(context, str(project_id))