"""Validation helpers for the Phase 1 transition path."""

from __future__ import annotations

from typing import Mapping

from jeff.core.schemas.envelopes import ValidationIssue
from jeff.core.state.models import GlobalState

from .models import TransitionRequest


def validate_transition_request(
    state: GlobalState,
    request: TransitionRequest,
) -> tuple[ValidationIssue, ...]:
    validators = (
        _validate_basis,
        _validate_scope,
        _validate_payload_shape,
    )

    issues: list[ValidationIssue] = []
    for validator in validators:
        issues.extend(validator(state, request))

    return tuple(issues)


def validate_candidate_state(candidate: GlobalState) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []

    for project_id, project in candidate.projects.items():
        if project_id != project.project_id:
            issues.append(
                ValidationIssue(
                    code="invalid_project_registry_key",
                    message="project registry keys must match project.project_id",
                    field_path="projects",
                    related_id=str(project.project_id),
                ),
            )
        for work_unit_id, work_unit in project.work_units.items():
            if work_unit_id != work_unit.work_unit_id:
                issues.append(
                    ValidationIssue(
                        code="invalid_work_unit_registry_key",
                        message="work unit registry keys must match work_unit.work_unit_id",
                        field_path=f"projects.{project_id}.work_units",
                        related_id=str(work_unit.work_unit_id),
                    ),
                )
            if work_unit.project_id != project.project_id:
                issues.append(
                    ValidationIssue(
                        code="cross_project_work_unit",
                        message="work unit must remain inside its owning project",
                        field_path=f"projects.{project_id}.work_units.{work_unit_id}.project_id",
                        related_id=str(work_unit.work_unit_id),
                    ),
                )
            for run_id, run in work_unit.runs.items():
                if run_id != run.run_id:
                    issues.append(
                        ValidationIssue(
                            code="invalid_run_registry_key",
                            message="run registry keys must match run.run_id",
                            field_path=f"projects.{project_id}.work_units.{work_unit_id}.runs",
                            related_id=str(run.run_id),
                        ),
                    )
                if run.project_id != project.project_id:
                    issues.append(
                        ValidationIssue(
                            code="cross_project_run",
                            message="run must remain inside its owning project",
                            field_path=f"projects.{project_id}.work_units.{work_unit_id}.runs.{run_id}.project_id",
                            related_id=str(run.run_id),
                        ),
                    )
                if run.work_unit_id != work_unit.work_unit_id:
                    issues.append(
                        ValidationIssue(
                            code="wrong_work_unit_run_link",
                            message="run must remain inside its owning work unit",
                            field_path=f"projects.{project_id}.work_units.{work_unit_id}.runs.{run_id}.work_unit_id",
                            related_id=str(run.run_id),
                        ),
                    )

    return tuple(issues)


def _validate_basis(
    state: GlobalState,
    request: TransitionRequest,
) -> list[ValidationIssue]:
    if request.basis_state_version == state.state_meta.state_version:
        return []

    return [
        ValidationIssue(
            code="stale_basis_state_version",
            message="transition basis_state_version does not match the current canonical state",
            field_path="basis_state_version",
        ),
    ]


def _validate_scope(
    state: GlobalState,
    request: TransitionRequest,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    project = state.projects.get(request.scope.project_id)

    if request.transition_type == "create_project":
        if request.scope.work_unit_id is not None or request.scope.run_id is not None:
            issues.append(
                ValidationIssue(
                    code="illegal_project_create_scope",
                    message="create_project scope cannot include work_unit_id or run_id",
                    field_path="scope",
                ),
            )
        return issues

    if project is None:
        issues.append(
            ValidationIssue(
                code="unknown_project",
                message="project_id must resolve inside canonical state",
                field_path="scope.project_id",
                related_id=str(request.scope.project_id),
            ),
        )
        return issues

    if request.transition_type == "create_work_unit":
        if request.scope.work_unit_id is not None or request.scope.run_id is not None:
            issues.append(
                ValidationIssue(
                    code="illegal_work_unit_create_scope",
                    message="create_work_unit scope cannot include work_unit_id or run_id",
                    field_path="scope",
                    related_id=str(request.scope.project_id),
                ),
            )
        return issues

    if request.transition_type == "update_run":
        if request.scope.work_unit_id is None:
            issues.append(
                ValidationIssue(
                    code="missing_work_unit_scope",
                    message="update_run requires work_unit_id in scope",
                    field_path="scope.work_unit_id",
                    related_id=str(request.scope.project_id),
                ),
            )
            return issues

        work_unit = project.work_units.get(request.scope.work_unit_id)
        if work_unit is None:
            issues.append(
                ValidationIssue(
                    code="unknown_work_unit",
                    message="work_unit_id must resolve inside the scoped project",
                    field_path="scope.work_unit_id",
                    related_id=str(request.scope.work_unit_id),
                ),
            )
            return issues

        if request.scope.run_id is None:
            issues.append(
                ValidationIssue(
                    code="missing_run_scope",
                    message="update_run requires run_id in scope",
                    field_path="scope.run_id",
                    related_id=str(request.scope.work_unit_id),
                ),
            )
            return issues

        if request.scope.run_id not in work_unit.runs:
            issues.append(
                ValidationIssue(
                    code="unknown_run",
                    message="run_id must resolve inside the scoped work unit",
                    field_path="scope.run_id",
                    related_id=str(request.scope.run_id),
                ),
            )
        return issues

    if request.scope.work_unit_id is None:
        issues.append(
            ValidationIssue(
                code="missing_work_unit_scope",
                message="create_run requires work_unit_id in scope",
                field_path="scope.work_unit_id",
                related_id=str(request.scope.project_id),
            ),
        )
        return issues

    work_unit = project.work_units.get(request.scope.work_unit_id)
    if work_unit is None:
        issues.append(
            ValidationIssue(
                code="unknown_work_unit",
                message="work_unit_id must resolve inside the scoped project",
                field_path="scope.work_unit_id",
                related_id=str(request.scope.work_unit_id),
            ),
        )

    if request.scope.run_id is not None:
        issues.append(
            ValidationIssue(
                code="illegal_run_create_scope",
                message="create_run scope cannot include run_id",
                field_path="scope.run_id",
                related_id=str(request.scope.run_id),
            ),
        )

    return issues


def _validate_payload_shape(
    state: GlobalState,
    request: TransitionRequest,
) -> list[ValidationIssue]:
    del state

    required_fields: Mapping[str, tuple[str, ...]] = {
        "create_project": ("name",),
        "create_work_unit": ("work_unit_id", "objective"),
        "create_run": ("run_id",),
        "update_run": ("run_lifecycle_state",),
    }
    allowed_fields: Mapping[str, tuple[str, ...]] = {
        "create_project": ("name", "project_lifecycle_state"),
        "create_work_unit": (
            "work_unit_id",
            "objective",
            "work_unit_lifecycle_state",
        ),
        "create_run": ("run_id", "run_lifecycle_state"),
        "update_run": (
            "run_lifecycle_state",
            "last_execution_status",
            "last_outcome_state",
            "last_evaluation_verdict",
        ),
    }

    issues: list[ValidationIssue] = []
    present_fields = set(request.payload)

    for field_name in required_fields[request.transition_type]:
        if field_name not in request.payload:
            issues.append(
                ValidationIssue(
                    code="missing_payload_field",
                    message=f"{field_name} is required for {request.transition_type}",
                    field_path=f"payload.{field_name}",
                ),
            )

    unexpected = present_fields - set(allowed_fields[request.transition_type])
    for field_name in sorted(unexpected):
        issues.append(
            ValidationIssue(
                code="unexpected_payload_field",
                message=f"{field_name} is not supported for {request.transition_type}",
                field_path=f"payload.{field_name}",
            ),
        )

    return issues
