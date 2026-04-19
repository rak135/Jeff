"""Candidate construction and commit/reject path for Phase 1 transitions."""

from __future__ import annotations

from dataclasses import replace

from jeff.core.containers.models import Project, Run, WorkUnit
from jeff.core.schemas.envelopes import ValidationIssue
from jeff.core.schemas.ids import coerce_run_id, coerce_work_unit_id
from jeff.core.state.models import GlobalState

from .models import CandidateState, TransitionRequest, TransitionResult
from .validator import validate_candidate_state, validate_transition_request


def apply_transition(
    state: GlobalState,
    request: TransitionRequest,
) -> TransitionResult:
    request_issues = validate_transition_request(state, request)
    if request_issues:
        return _reject(state, request, request_issues)

    try:
        candidate = _build_candidate_state(state, request)
    except (TypeError, ValueError) as exc:
        return _reject(
            state,
            request,
            (
                ValidationIssue(
                    code="candidate_construction_failed",
                    message=str(exc),
                ),
            ),
        )

    candidate_issues = validate_candidate_state(candidate.state)
    if candidate_issues:
        return _reject(state, request, candidate_issues)

    committed_state = _commit_candidate(candidate.state, request)
    return TransitionResult(
        transition_id=request.transition_id,
        transition_result="committed",
        state_before_version=state.state_meta.state_version,
        state_after_version=committed_state.state_meta.state_version,
        state=committed_state,
        changed_paths=candidate.changed_paths,
        validation_errors=(),
    )


def _build_candidate_state(
    state: GlobalState,
    request: TransitionRequest,
) -> CandidateState:
    if request.transition_type == "create_project":
        return _build_project_candidate(state, request)
    if request.transition_type == "create_work_unit":
        return _build_work_unit_candidate(state, request)
    if request.transition_type == "create_run":
        return _build_run_candidate(state, request)
    if request.transition_type == "update_run":
        return _build_run_update_candidate(state, request)

    raise ValueError(f"unsupported transition_type: {request.transition_type}")


def _build_project_candidate(
    state: GlobalState,
    request: TransitionRequest,
) -> CandidateState:
    project_id = request.scope.project_id
    if project_id in state.projects:
        raise ValueError("project_id already exists")

    project = Project(
        project_id=project_id,
        name=str(request.payload["name"]),
        project_lifecycle_state=str(
            request.payload.get("project_lifecycle_state", "active"),
        ),
    )
    projects = dict(state.projects)
    projects[project.project_id] = project

    return CandidateState(
        state=replace(state, projects=projects),
        changed_paths=(f"projects.{project.project_id}",),
    )


def _build_work_unit_candidate(
    state: GlobalState,
    request: TransitionRequest,
) -> CandidateState:
    project = state.projects[request.scope.project_id]
    work_unit_id = coerce_work_unit_id(str(request.payload["work_unit_id"]))
    if work_unit_id in project.work_units:
        raise ValueError("work_unit_id already exists in the scoped project")

    work_unit = WorkUnit(
        work_unit_id=work_unit_id,
        project_id=project.project_id,
        objective=str(request.payload["objective"]),
        work_unit_lifecycle_state=str(
            request.payload.get("work_unit_lifecycle_state", "open"),
        ),
    )

    work_units = dict(project.work_units)
    work_units[work_unit.work_unit_id] = work_unit
    project_candidate = replace(project, work_units=work_units)

    projects = dict(state.projects)
    projects[project.project_id] = project_candidate

    return CandidateState(
        state=replace(state, projects=projects),
        changed_paths=(
            f"projects.{project.project_id}.work_units.{work_unit.work_unit_id}",
        ),
    )


def _build_run_candidate(
    state: GlobalState,
    request: TransitionRequest,
) -> CandidateState:
    project = state.projects[request.scope.project_id]
    work_unit = project.work_units[request.scope.work_unit_id]
    run_id = coerce_run_id(str(request.payload["run_id"]))
    if run_id in work_unit.runs:
        raise ValueError("run_id already exists in the scoped work unit")

    run = Run(
        run_id=run_id,
        project_id=project.project_id,
        work_unit_id=work_unit.work_unit_id,
        run_lifecycle_state=str(request.payload.get("run_lifecycle_state", "created")),
    )

    runs = dict(work_unit.runs)
    runs[run.run_id] = run
    work_unit_candidate = replace(work_unit, runs=runs)

    work_units = dict(project.work_units)
    work_units[work_unit.work_unit_id] = work_unit_candidate
    project_candidate = replace(project, work_units=work_units)

    projects = dict(state.projects)
    projects[project.project_id] = project_candidate

    return CandidateState(
        state=replace(state, projects=projects),
        changed_paths=(
            "projects."
            f"{project.project_id}.work_units.{work_unit.work_unit_id}.runs.{run.run_id}",
        ),
    )


def _build_run_update_candidate(
    state: GlobalState,
    request: TransitionRequest,
) -> CandidateState:
    project = state.projects[request.scope.project_id]
    work_unit = project.work_units[request.scope.work_unit_id]
    run = work_unit.runs[request.scope.run_id]

    updated_run = replace(
        run,
        run_lifecycle_state=str(request.payload["run_lifecycle_state"]),
        last_execution_status=(
            None
            if request.payload.get("last_execution_status") is None
            else str(request.payload["last_execution_status"])
        ),
        last_outcome_state=(
            None
            if request.payload.get("last_outcome_state") is None
            else str(request.payload["last_outcome_state"])
        ),
        last_evaluation_verdict=(
            None
            if request.payload.get("last_evaluation_verdict") is None
            else str(request.payload["last_evaluation_verdict"])
        ),
    )

    runs = dict(work_unit.runs)
    runs[updated_run.run_id] = updated_run
    work_unit_candidate = replace(work_unit, runs=runs)

    work_units = dict(project.work_units)
    work_units[work_unit_candidate.work_unit_id] = work_unit_candidate
    project_candidate = replace(project, work_units=work_units)

    projects = dict(state.projects)
    projects[project_candidate.project_id] = project_candidate

    base = f"projects.{project.project_id}.work_units.{work_unit.work_unit_id}.runs.{run.run_id}"
    return CandidateState(
        state=replace(state, projects=projects),
        changed_paths=(
            f"{base}.run_lifecycle_state",
            f"{base}.last_execution_status",
            f"{base}.last_outcome_state",
            f"{base}.last_evaluation_verdict",
        ),
    )


def _commit_candidate(
    candidate_state: GlobalState,
    request: TransitionRequest,
) -> GlobalState:
    new_meta = replace(
        candidate_state.state_meta,
        state_version=candidate_state.state_meta.state_version + 1,
        last_transition_id=request.transition_id,
    )
    return replace(candidate_state, state_meta=new_meta)


def _reject(
    state: GlobalState,
    request: TransitionRequest,
    issues: tuple[ValidationIssue, ...],
) -> TransitionResult:
    return TransitionResult(
        transition_id=request.transition_id,
        transition_result="rejected",
        state_before_version=state.state_meta.state_version,
        state_after_version=state.state_meta.state_version,
        state=state,
        changed_paths=(),
        validation_errors=issues,
    )
