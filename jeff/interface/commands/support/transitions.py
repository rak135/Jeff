"""Interface-side transition helper wiring."""

from __future__ import annotations

import re

from jeff.core.containers.models import Project, Run, WorkUnit
from jeff.core.schemas import Scope
from jeff.core.state.models import GlobalState
from jeff.core.transition import TransitionRequest, apply_transition

from ..models import InterfaceContext


def create_run_for_work_unit(
    *,
    context: InterfaceContext,
    project: Project,
    work_unit: WorkUnit,
) -> tuple[Run, InterfaceContext]:
    next_run_id = next_run_id_for_work_unit(work_unit)
    request = TransitionRequest(
        transition_id=f"transition-auto-create-run-{project.project_id}-{work_unit.work_unit_id}-{next_run_id}",
        transition_type="create_run",
        basis_state_version=context.state.state_meta.state_version,
        scope=Scope(project_id=str(project.project_id), work_unit_id=str(work_unit.work_unit_id)),
        payload={"run_id": next_run_id},
    )
    result = apply_context_transition(context=context, request=request)
    if result.transition_result != "committed":
        issue = result.validation_errors[0].message if result.validation_errors else "unknown transition failure"
        raise ValueError(f"automatic run creation failed: {issue}")
    next_context = replace_context_state(context, result.state)
    created_project = next_context.state.projects[str(project.project_id)]
    created_work_unit = created_project.work_units[str(work_unit.work_unit_id)]
    return created_work_unit.runs[next_run_id], next_context


def ensure_project_exists(
    *,
    context: InterfaceContext,
    project_id: str,
    name: str,
) -> tuple[Project, InterfaceContext, bool]:
    if project_id in context.state.projects:
        return context.state.projects[project_id], context, False

    result = apply_context_transition(
        context=context,
        request=TransitionRequest(
            transition_id=f"transition-auto-create-project-{project_id}",
            transition_type="create_project",
            basis_state_version=context.state.state_meta.state_version,
            scope=Scope(project_id=project_id),
            payload={"name": name},
        ),
    )
    if result.transition_result != "committed":
        issue = result.validation_errors[0].message if result.validation_errors else "unknown transition failure"
        raise ValueError(f"automatic project creation failed: {issue}")

    next_context = replace_context_state(context, result.state)
    return next_context.state.projects[project_id], next_context, True


def ensure_work_unit_exists(
    *,
    context: InterfaceContext,
    project: Project,
    work_unit_id: str,
    objective: str,
) -> tuple[WorkUnit, InterfaceContext, bool]:
    if work_unit_id in project.work_units:
        return project.work_units[work_unit_id], context, False

    result = apply_context_transition(
        context=context,
        request=TransitionRequest(
            transition_id=f"transition-auto-create-work-unit-{project.project_id}-{work_unit_id}",
            transition_type="create_work_unit",
            basis_state_version=context.state.state_meta.state_version,
            scope=Scope(project_id=str(project.project_id)),
            payload={"work_unit_id": work_unit_id, "objective": objective},
        ),
    )
    if result.transition_result != "committed":
        issue = result.validation_errors[0].message if result.validation_errors else "unknown transition failure"
        raise ValueError(f"automatic work unit creation failed: {issue}")

    next_context = replace_context_state(context, result.state)
    next_project = next_context.state.projects[str(project.project_id)]
    return next_project.work_units[work_unit_id], next_context, True


def replace_context_state(context: InterfaceContext, state: GlobalState) -> InterfaceContext:
    return InterfaceContext(
        state=state,
        flow_runs=context.flow_runs,
        selection_reviews=context.selection_reviews,
        infrastructure_services=context.infrastructure_services,
        research_artifact_store=context.research_artifact_store,
        research_archive_store=context.research_archive_store,
        knowledge_store=context.knowledge_store,
        memory_store=context.memory_store,
        research_memory_handoff_enabled=context.research_memory_handoff_enabled,
        runtime_store=context.runtime_store,
        startup_summary=context.startup_summary,
    )


def apply_context_transition(*, context: InterfaceContext, request: TransitionRequest):
    if context.runtime_store is not None:
        return context.runtime_store.apply_transition(context.state, request)
    return apply_transition(context.state, request)


def next_run_id_for_work_unit(work_unit: WorkUnit) -> str:
    numeric_suffixes = [
        int(match.group(1))
        for run in work_unit.runs.values()
        if (match := re.fullmatch(r"run-(\d+)", str(run.run_id))) is not None
    ]
    next_number = max(numeric_suffixes, default=0) + 1
    return f"run-{next_number}"