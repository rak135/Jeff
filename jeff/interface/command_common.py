"""Shared internal helpers for CLI command-family modules."""

from __future__ import annotations

import hashlib
import re

from jeff.action.execution import ExecutionResult
from jeff.cognitive import ContextPackage, SelectionResult, assemble_context_package
from jeff.cognitive.post_selection.action_formation import (
    ActionFormationRequest,
    form_action_from_materialized_proposal,
)
from jeff.cognitive.post_selection.action_resolution import (
    SelectionActionResolutionRequest,
    resolve_selection_action_basis,
)
from jeff.cognitive.post_selection.effective_proposal import (
    SelectionEffectiveProposalRequest,
    materialize_effective_proposal,
)
from jeff.cognitive.post_selection.governance_handoff import (
    ActionGovernanceHandoffRequest,
    handoff_action_to_governance,
)
from jeff.cognitive.post_selection.override import OperatorSelectionOverride
from jeff.cognitive.proposal import ProposalResult
from jeff.cognitive.research.archive import ResearchArchiveStore
from jeff.cognitive.types import TriggerInput
from jeff.core.containers.models import Project, Run, WorkUnit
from jeff.core.schemas import Scope
from jeff.core.state.models import GlobalState
from jeff.core.transition import TransitionRequest, apply_transition
from jeff.governance import Approval, CurrentTruthSnapshot, Policy
from jeff.infrastructure import InfrastructureServices
from jeff.knowledge import KnowledgeStore
from jeff.memory import InMemoryMemoryStore
from jeff.orchestrator import FlowRunResult

from .command_models import InterfaceContext, SelectionReviewRecord
from .session import CliSession


GENERAL_RESEARCH_PROJECT_ID = "general_research"


def assemble_live_context_package(
    *,
    context: InterfaceContext,
    trigger_summary: str,
    purpose: str,
    scope: Scope,
    support_inputs=(),
    knowledge_topic_query: str | None = None,
    governance_truth: CurrentTruthSnapshot | None = None,
    governance_policy: Policy | None = None,
    governance_approval: Approval | None = None,
) -> ContextPackage:
    selection_review = _selection_review_for_context(context=context, scope=scope)
    governance_readiness = None
    if (
        selection_review is not None
        and selection_review.governance_handoff_result is not None
        and selection_review.governance_handoff_result.governance_result is not None
    ):
        governance_readiness = selection_review.governance_handoff_result.governance_result.readiness

    effective_governance_truth = governance_truth
    effective_governance_policy = governance_policy
    effective_governance_approval = governance_approval
    if selection_review is not None:
        effective_governance_truth = selection_review.governance_truth
        effective_governance_policy = selection_review.governance_policy
        effective_governance_approval = selection_review.governance_approval

    return assemble_context_package(
        trigger=TriggerInput(trigger_summary=trigger_summary),
        purpose=purpose,
        scope=scope,
        state=context.state,
        support_inputs=tuple(support_inputs),
        memory_store=context.memory_store,
        knowledge_store=context.knowledge_store,
        archive_store=context.research_archive_store,
        knowledge_topic_query=knowledge_topic_query,
        governance_truth=effective_governance_truth,
        governance_policy=effective_governance_policy,
        governance_approval=effective_governance_approval,
        governance_readiness=governance_readiness,
    )


def build_run_governance_inputs(
    *,
    context: InterfaceContext,
    scope: Scope,
) -> tuple[Policy, Approval, CurrentTruthSnapshot]:
    return (
        Policy(),
        Approval.not_required(),
        CurrentTruthSnapshot(scope=scope, state_version=context.state.state_meta.state_version),
    )


def ensure_selection_review_for_run(
    *,
    context: InterfaceContext,
    run: Run,
    flow_run: FlowRunResult | None,
) -> tuple[InterfaceContext, SelectionReviewRecord | None]:
    run_id = str(run.run_id)
    existing_review = context.selection_reviews.get(run_id)
    selection_review = materialize_selection_review_from_available_data(
        existing_review=existing_review,
        flow_run=flow_run,
    )
    if selection_review is None:
        return context, None
    if existing_review == selection_review:
        return context, selection_review
    return replace_selection_review(context=context, run_id=run_id, selection_review=selection_review), selection_review


def materialize_selection_review_from_available_data(
    *,
    existing_review: SelectionReviewRecord | None,
    flow_run: FlowRunResult | None,
) -> SelectionReviewRecord | None:
    selection_result = None if existing_review is None else existing_review.selection_result
    if selection_result is None and flow_run is not None:
        candidate = flow_run.outputs.get("selection")
        if isinstance(candidate, SelectionResult):
            selection_result = candidate

    proposal_result = None if existing_review is None else existing_review.proposal_result
    if proposal_result is None and flow_run is not None:
        candidate = flow_run.outputs.get("proposal")
        if isinstance(candidate, ProposalResult):
            proposal_result = candidate

    if existing_review is None and selection_result is None and proposal_result is None:
        return None

    operator_override = None if existing_review is None else existing_review.operator_override
    resolved_basis = None if existing_review is None else existing_review.resolved_basis
    materialized_effective_proposal = None if existing_review is None else existing_review.materialized_effective_proposal
    formed_action_result = None if existing_review is None else existing_review.formed_action_result
    governance_handoff_result = None if existing_review is None else existing_review.governance_handoff_result

    governance_policy = None if existing_review is None else existing_review.governance_policy
    if governance_policy is None and flow_run is not None:
        candidate = flow_run.outputs.get("governance_policy")
        if isinstance(candidate, Policy):
            governance_policy = candidate

    governance_approval = None if existing_review is None else existing_review.governance_approval
    if governance_approval is None and flow_run is not None:
        candidate = flow_run.outputs.get("governance_approval")
        if isinstance(candidate, Approval):
            governance_approval = candidate

    governance_truth = None if existing_review is None else existing_review.governance_truth
    if governance_truth is None and flow_run is not None:
        candidate = flow_run.outputs.get("governance_truth")
        if isinstance(candidate, CurrentTruthSnapshot):
            governance_truth = candidate

    action_scope = None if existing_review is None else existing_review.action_scope
    if action_scope is None and proposal_result is not None:
        action_scope = proposal_result.scope
    basis_state_version = None if existing_review is None else existing_review.basis_state_version
    if governance_truth is not None and basis_state_version is None:
        basis_state_version = governance_truth.state_version

    execution_result = None
    if flow_run is not None:
        candidate = flow_run.outputs.get("execution")
        if isinstance(candidate, ExecutionResult):
            execution_result = candidate
    if execution_result is not None:
        if action_scope is None:
            action_scope = execution_result.governed_request.action.scope
        if basis_state_version is None:
            basis_state_version = execution_result.governed_request.action.basis_state_version

    if (
        selection_result is not None
        and resolved_basis is None
        and (flow_run is not None or proposal_result is not None or operator_override is not None)
    ):
        resolved_basis = resolve_selection_action_basis(
            SelectionActionResolutionRequest(
                request_id=f"selection-review-resolution:{selection_result.selection_id}",
                selection_result=selection_result,
                operator_override=operator_override,
            )
        )

    if proposal_result is not None and resolved_basis is not None and materialized_effective_proposal is None:
        materialized_effective_proposal = materialize_effective_proposal(
            SelectionEffectiveProposalRequest(
                request_id=f"selection-review-materialization:{selection_result.selection_id}",
                proposal_result=proposal_result,
                resolved_basis=resolved_basis,
            )
        )

    if (
        materialized_effective_proposal is not None
        and action_scope is not None
        and basis_state_version is not None
        and formed_action_result is None
    ):
        formed_action_result = form_action_from_materialized_proposal(
            ActionFormationRequest(
                request_id=f"selection-review-action-formation:{materialized_effective_proposal.selection_id}",
                materialized_effective_proposal=materialized_effective_proposal,
                scope=action_scope,
                basis_state_version=basis_state_version,
            )
        )

    if (
        formed_action_result is not None
        and governance_policy is not None
        and governance_truth is not None
        and governance_handoff_result is None
    ):
        governance_handoff_result = handoff_action_to_governance(
            ActionGovernanceHandoffRequest(
                request_id=f"selection-review-governance-handoff:{formed_action_result.selection_id}",
                formed_action_result=formed_action_result,
                policy=governance_policy,
                approval=governance_approval,
                truth=governance_truth,
            )
        )

    return SelectionReviewRecord(
        selection_result=selection_result,
        operator_override=operator_override,
        resolved_basis=resolved_basis,
        materialized_effective_proposal=materialized_effective_proposal,
        formed_action_result=formed_action_result,
        governance_handoff_result=governance_handoff_result,
        proposal_result=proposal_result,
        action_scope=action_scope,
        basis_state_version=basis_state_version,
        governance_policy=governance_policy,
        governance_approval=governance_approval,
        governance_truth=governance_truth,
    )


def recompute_selection_review_record(
    *,
    existing_review: SelectionReviewRecord,
    selection_result: SelectionResult,
    operator_override: OperatorSelectionOverride,
) -> SelectionReviewRecord:
    resolved_basis = resolve_selection_action_basis(
        SelectionActionResolutionRequest(
            request_id=f"selection-review-resolution:{selection_result.selection_id}",
            selection_result=selection_result,
            operator_override=operator_override,
        )
    )

    proposal_result = existing_review.proposal_result
    action_scope = existing_review.action_scope
    materialized_effective_proposal = None
    formed_action_result = None
    governance_handoff_result = None

    if proposal_result is not None:
        materialized_effective_proposal = materialize_effective_proposal(
            SelectionEffectiveProposalRequest(
                request_id=f"selection-review-materialization:{selection_result.selection_id}",
                proposal_result=proposal_result,
                resolved_basis=resolved_basis,
            )
        )

        action_scope = action_scope or proposal_result.scope
        formed_action_result = form_action_from_materialized_proposal(
            ActionFormationRequest(
                request_id=f"selection-review-action-formation:{selection_result.selection_id}",
                materialized_effective_proposal=materialized_effective_proposal,
                scope=action_scope,
                basis_state_version=selection_review_basis_state_version(existing_review),
            )
        )

        if existing_review.governance_policy is not None and existing_review.governance_truth is not None:
            governance_handoff_result = handoff_action_to_governance(
                ActionGovernanceHandoffRequest(
                    request_id=f"selection-review-governance-handoff:{selection_result.selection_id}",
                    formed_action_result=formed_action_result,
                    policy=existing_review.governance_policy,
                    approval=existing_review.governance_approval,
                    truth=existing_review.governance_truth,
                )
            )

    return SelectionReviewRecord(
        selection_result=selection_result,
        operator_override=operator_override,
        resolved_basis=resolved_basis,
        materialized_effective_proposal=materialized_effective_proposal,
        formed_action_result=formed_action_result,
        governance_handoff_result=governance_handoff_result,
        proposal_result=proposal_result,
        action_scope=action_scope,
        basis_state_version=selection_review_basis_state_version(existing_review),
        governance_policy=existing_review.governance_policy,
        governance_approval=existing_review.governance_approval,
        governance_truth=existing_review.governance_truth,
    )


def selection_review_basis_state_version(selection_review: SelectionReviewRecord) -> int:
    if selection_review.basis_state_version is not None:
        return selection_review.basis_state_version
    if (
        selection_review.formed_action_result is not None
        and selection_review.formed_action_result.action is not None
    ):
        return selection_review.formed_action_result.action.basis_state_version
    if (
        selection_review.governance_handoff_result is not None
        and selection_review.governance_handoff_result.action is not None
    ):
        return selection_review.governance_handoff_result.action.basis_state_version
    return 0


def replace_selection_review(
    *,
    context: InterfaceContext,
    run_id: str,
    selection_review: SelectionReviewRecord,
) -> InterfaceContext:
    if context.runtime_store is not None:
        context.runtime_store.save_selection_review(run_id, selection_review)
    next_reviews = dict(context.selection_reviews)
    next_reviews[run_id] = selection_review
    return InterfaceContext(
        state=context.state,
        flow_runs=context.flow_runs,
        selection_reviews=next_reviews,
        infrastructure_services=context.infrastructure_services,
        research_artifact_store=context.research_artifact_store,
        research_archive_store=context.research_archive_store,
        knowledge_store=context.knowledge_store,
        memory_store=context.memory_store,
        research_memory_handoff_enabled=context.research_memory_handoff_enabled,
        runtime_store=context.runtime_store,
        startup_summary=context.startup_summary,
    )


def replace_flow_run(
    *,
    context: InterfaceContext,
    run_id: str,
    flow_run: FlowRunResult,
) -> InterfaceContext:
    if context.runtime_store is not None:
        context.runtime_store.save_flow_run(run_id, flow_run)
    next_flow_runs = dict(context.flow_runs)
    next_flow_runs[run_id] = flow_run
    return InterfaceContext(
        state=context.state,
        flow_runs=next_flow_runs,
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
    run = select_existing_run(work_unit)
    if run is None:
        raise ValueError(
            f"{command_name} found no existing run in work_unit {work_unit.work_unit_id}. "
            "Use /inspect to create and select a new run, or /run list to confirm history."
        )
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

    existing_run = select_existing_run(work_unit)
    if existing_run is not None:
        next_session = session.with_scope(
            project_id=str(project.project_id),
            work_unit_id=str(work_unit.work_unit_id),
            run_id=str(existing_run.run_id),
        )
        return existing_run, next_session, context, f"auto-selected current run: {existing_run.run_id}"

    created_run, next_context = create_run_for_work_unit(context=context, project=project, work_unit=work_unit)
    next_session = session.with_scope(
        project_id=str(project.project_id),
        work_unit_id=str(work_unit.work_unit_id),
        run_id=str(created_run.run_id),
    )
    return created_run, next_session, next_context, f"created and selected new run: {created_run.run_id}"


def select_existing_run(work_unit: WorkUnit) -> Run | None:
    runs = tuple(work_unit.runs.values())
    if not runs:
        return None
    return max(runs, key=run_sort_key)


def run_sort_key(run: Run) -> tuple[int, str]:
    run_id = str(run.run_id)
    match = re.fullmatch(r"run-(\d+)", run_id)
    if match is not None:
        return (int(match.group(1)), run_id)
    return (-1, run_id)


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
    created_project = get_project(next_context, str(project.project_id))
    created_work_unit = get_work_unit(created_project, str(work_unit.work_unit_id))
    return get_run(created_work_unit, next_run_id), next_context


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
    return get_project(next_context, project_id), next_context, True


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
    next_project = get_project(next_context, str(project.project_id))
    return get_work_unit(next_project, work_unit_id), next_context, True


def require_research_infrastructure(context: InterfaceContext) -> InfrastructureServices:
    if context.infrastructure_services is None:
        raise ValueError(
            "research runtime is not configured for this CLI context. "
            "Add jeff.runtime.toml in the startup directory to enable research CLI."
        )
    return context.infrastructure_services


def require_research_store(context: InterfaceContext):
    if context.research_artifact_store is None:
        raise ValueError("research artifact persistence store is not configured for this CLI context")
    return context.research_artifact_store


def require_memory_store(context: InterfaceContext) -> InMemoryMemoryStore:
    if not context.research_memory_handoff_enabled:
        raise ValueError("research memory handoff is disabled by the current runtime config")
    if context.memory_store is None:
        raise ValueError("memory store is not configured for research handoff in this CLI context")
    return context.memory_store


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


def general_research_work_unit_id(*, mode: str, question: str) -> str:
    slug_parts = re.findall(r"[a-z0-9]+", question.lower())
    slug = "-".join(slug_parts[:8]) or "question"
    slug = slug[:48].strip("-")
    digest = hashlib.sha1(f"{mode}|{question}".encode("utf-8")).hexdigest()[:8]
    return f"research-{mode}-{slug}-{digest}"


def next_run_id_for_work_unit(work_unit: WorkUnit) -> str:
    numeric_suffixes = [
        int(match.group(1))
        for run in work_unit.runs.values()
        if (match := re.fullmatch(r"run-(\d+)", str(run.run_id))) is not None
    ]
    next_number = max(numeric_suffixes, default=0) + 1
    return f"run-{next_number}"


def missing_run_message(command_name: str) -> str:
    return (
        f"{command_name} requires a current run or an explicit <run_id>. "
        "Use /run list, /run use <run_id>, or /scope show."
    )


def require_project_for_run(context: InterfaceContext, project_id: str) -> Project:
    return get_project(context, str(project_id))


def require_flow_run(context: InterfaceContext, run_id: str) -> FlowRunResult:
    try:
        return context.flow_runs[run_id]
    except KeyError as exc:
        raise ValueError(f"no orchestrator flow result is available for run {run_id}") from exc


def _selection_review_for_context(*, context: InterfaceContext, scope: Scope) -> SelectionReviewRecord | None:
    if scope.run_id is None:
        return None

    run_id = str(scope.run_id)
    return materialize_selection_review_from_available_data(
        existing_review=context.selection_reviews.get(run_id),
        flow_run=context.flow_runs.get(run_id),
    )