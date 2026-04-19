"""Startup helpers for the persisted Jeff v1 runtime and bounded demo fixtures."""

from __future__ import annotations

from pathlib import Path

from jeff.action import GovernedExecutionRequest, normalize_outcome
from jeff.action.execution import ExecutionResult
from jeff.cognitive import ResearchArtifactStore, SelectionResult, evaluate_outcome
from jeff.cognitive.research.archive import ResearchArchiveStore
from jeff.cognitive.post_selection.action_formation import ActionFormationRequest, form_action_from_materialized_proposal
from jeff.cognitive.post_selection.action_resolution import SelectionActionResolutionRequest, resolve_selection_action_basis
from jeff.cognitive.post_selection.effective_proposal import SelectionEffectiveProposalRequest, materialize_effective_proposal
from jeff.cognitive.post_selection.governance_handoff import ActionGovernanceHandoffRequest, handoff_action_to_governance
from jeff.cognitive.proposal.contracts import ProposalResult, ProposalResultOption
from jeff.core.schemas import Scope
from jeff.core.state import GlobalState, bootstrap_global_state
from jeff.core.transition import TransitionRequest, apply_transition
from jeff.governance import Approval, CurrentTruthSnapshot, Policy
from jeff.infrastructure import (
    InfrastructureServices,
    JeffRuntimeConfig,
    ModelAdapterRuntimeConfig,
    build_model_adapter_runtime_config,
    build_infrastructure_services,
    load_runtime_config,
)
from jeff.interface.commands import InterfaceContext, SelectionReviewRecord
from jeff.knowledge import KnowledgeStore
from jeff.memory import InMemoryMemoryStore
from jeff.orchestrator.lifecycle import FlowLifecycle
from jeff.orchestrator.runner import FlowRunResult
from jeff.orchestrator.trace import OrchestrationEvent
from jeff.runtime_persistence import PersistedRuntimeStore

RUNTIME_CONFIG_FILENAME = "jeff.runtime.toml"


def build_infrastructure_runtime(
    config: ModelAdapterRuntimeConfig | JeffRuntimeConfig,
) -> InfrastructureServices:
    runtime_config = build_model_adapter_runtime_config(config) if isinstance(config, JeffRuntimeConfig) else config
    return build_infrastructure_services(runtime_config)


def build_demo_interface_context() -> InterfaceContext:
    state, scope = build_demo_state()
    selection_review = build_demo_selection_review(scope)
    flow_run = build_demo_flow_run(scope, selection_review=selection_review)
    return InterfaceContext(
        state=state,
        flow_runs={str(scope.run_id): flow_run},
        selection_reviews={str(scope.run_id): selection_review},
    )


def _initialize_persisted_runtime_state(runtime_store: PersistedRuntimeStore) -> tuple[GlobalState, Scope]:
    scope = Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1")
    state = bootstrap_global_state()
    for request in (
        TransitionRequest(
            transition_id="transition-project",
            transition_type="create_project",
            basis_state_version=0,
            scope=Scope(project_id=str(scope.project_id)),
            payload={"name": "Jeff Runtime Project"},
        ),
        TransitionRequest(
            transition_id="transition-work-unit",
            transition_type="create_work_unit",
            basis_state_version=1,
            scope=Scope(project_id=str(scope.project_id)),
            payload={
                "work_unit_id": str(scope.work_unit_id),
                "objective": "Inspect the current Jeff v1 backbone through the CLI.",
            },
        ),
        TransitionRequest(
            transition_id="transition-run",
            transition_type="create_run",
            basis_state_version=2,
            scope=Scope(project_id=str(scope.project_id), work_unit_id=str(scope.work_unit_id)),
            payload={"run_id": str(scope.run_id)},
        ),
    ):
        result = runtime_store.apply_transition(state, request)
        if result.transition_result != "committed":
            issue = result.validation_errors[0].message if result.validation_errors else "unknown transition failure"
            raise ValueError(f"persisted runtime initialization failed: {issue}")
        state = result.state
    return state, scope


def build_startup_interface_context(*, base_dir: str | Path | None = None) -> InterfaceContext:
    runtime_store = PersistedRuntimeStore.from_base_dir(base_dir=base_dir)
    if runtime_store.canonical_state_exists():
        state = runtime_store.load_canonical_state()
        flow_runs = runtime_store.load_flow_runs(state=state)
        selection_reviews = runtime_store.load_selection_reviews()
        startup_summary = f"Startup loaded persisted runtime state from {runtime_store.home.root_dir}."
    else:
        state, scope = _initialize_persisted_runtime_state(runtime_store)
        selection_review = build_demo_selection_review(scope)
        flow_run = build_demo_flow_run(scope, selection_review=selection_review)
        runtime_store.save_selection_review(str(scope.run_id), selection_review)
        runtime_store.save_flow_run(str(scope.run_id), flow_run)
        flow_runs = {str(scope.run_id): flow_run}
        selection_reviews = {str(scope.run_id): selection_review}
        startup_summary = f"Startup is initializing runtime state under {runtime_store.home.root_dir}."

    context = InterfaceContext(
        state=state,
        flow_runs=flow_runs,
        selection_reviews=selection_reviews,
        runtime_store=runtime_store,
        startup_summary=startup_summary,
    )
    runtime_config_entry = load_local_runtime_config(base_dir=base_dir)
    if runtime_config_entry is None:
        return context

    config_path, runtime_config = runtime_config_entry
    configured_root = _resolve_configured_research_artifact_store_root(config_path, runtime_config)
    return InterfaceContext(
        state=context.state,
        flow_runs=context.flow_runs,
        selection_reviews=context.selection_reviews,
        infrastructure_services=build_infrastructure_runtime(runtime_config),
        research_artifact_store=ResearchArtifactStore(
            runtime_store.home.research_artifacts_dir,
            legacy_root_dirs=runtime_store.research_artifact_legacy_dirs(configured_root),
        ),
        research_archive_store=ResearchArchiveStore(runtime_store.home.artifacts_dir),
        knowledge_store=KnowledgeStore(runtime_store.home.artifacts_dir),
        memory_store=InMemoryMemoryStore() if runtime_config.research.enable_memory_handoff else None,
        research_memory_handoff_enabled=runtime_config.research.enable_memory_handoff,
        runtime_store=runtime_store,
        startup_summary=startup_summary,
    )


def build_demo_state() -> tuple[GlobalState, Scope]:
    scope = Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1")
    state = bootstrap_global_state()
    state = apply_transition(
        state,
        TransitionRequest(
            transition_id="transition-project",
            transition_type="create_project",
            basis_state_version=0,
            scope=Scope(project_id=str(scope.project_id)),
            payload={"name": "Jeff Demo Project"},
        ),
    ).state
    state = apply_transition(
        state,
        TransitionRequest(
            transition_id="transition-work-unit",
            transition_type="create_work_unit",
            basis_state_version=1,
            scope=Scope(project_id=str(scope.project_id)),
            payload={
                "work_unit_id": str(scope.work_unit_id),
                "objective": "Inspect the current Jeff v1 backbone through the CLI.",
            },
        ),
    ).state
    state = apply_transition(
        state,
        TransitionRequest(
            transition_id="transition-run",
            transition_type="create_run",
            basis_state_version=2,
            scope=Scope(project_id=str(scope.project_id), work_unit_id=str(scope.work_unit_id)),
            payload={"run_id": str(scope.run_id)},
        ),
    ).state
    return state, scope


def build_demo_flow_run(scope: Scope, *, selection_review: SelectionReviewRecord | None = None) -> FlowRunResult:
    review = selection_review or build_demo_selection_review(scope)
    if review.formed_action_result is None or review.formed_action_result.action is None:
        raise ValueError("demo flow run requires a formed Action in the demo selection review chain")
    if review.governance_handoff_result is None or review.governance_handoff_result.governance_result is None:
        raise ValueError("demo flow run requires a governance handoff result in the demo selection review chain")

    governance = review.governance_handoff_result.governance_result
    execution = ExecutionResult(
        governed_request=GovernedExecutionRequest(action=review.formed_action_result.action, governance_decision=governance),
        execution_status="completed",
        output_summary="Demo execution reached its bounded operational endpoint.",
    )
    outcome = normalize_outcome(
        execution_result=execution,
        outcome_state="complete",
        observed_completion_posture="execution completed",
        target_effect_posture="target reached",
        artifact_posture="artifact present",
        side_effect_posture="contained",
    )
    evaluation = evaluate_outcome(
        objective_summary="Expose one bounded demo flow for operator inspection",
        outcome=outcome,
        evidence_quality_posture="strong",
    )
    lifecycle = FlowLifecycle(
        flow_id="flow-demo-1",
        flow_family="bounded_proposal_selection_action",
        scope=scope,
        lifecycle_state="completed",
        current_stage="evaluation",
        reason_summary="demo bootstrap flow completed",
    )
    events = (
        OrchestrationEvent(
            ordinal=1,
            flow_family="bounded_proposal_selection_action",
            scope=scope,
            stage=None,
            event_type="flow_started",
            summary="demo flow started",
            emitted_at="2026-04-11T09:00:00+00:00",
        ),
        OrchestrationEvent(
            ordinal=2,
            flow_family="bounded_proposal_selection_action",
            scope=scope,
            stage="context",
            event_type="stage_entered",
            summary="entered context",
            emitted_at="2026-04-11T09:00:01+00:00",
        ),
        OrchestrationEvent(
            ordinal=3,
            flow_family="bounded_proposal_selection_action",
            scope=scope,
            stage="proposal",
            event_type="stage_entered",
            summary="entered proposal",
            emitted_at="2026-04-11T09:00:02+00:00",
        ),
        OrchestrationEvent(
            ordinal=4,
            flow_family="bounded_proposal_selection_action",
            scope=scope,
            stage="selection",
            event_type="stage_exited",
            summary="exited selection",
            emitted_at="2026-04-11T09:00:03+00:00",
        ),
        OrchestrationEvent(
            ordinal=5,
            flow_family="bounded_proposal_selection_action",
            scope=scope,
            stage="evaluation",
            event_type="flow_completed",
            summary="demo flow completed",
            emitted_at="2026-04-11T09:00:04+00:00",
        ),
    )
    return FlowRunResult(
        lifecycle=lifecycle,
        outputs={
            "proposal": review.proposal_result,
            "selection": review.selection_result,
            "governance": governance,
            "execution": execution,
            "outcome": outcome,
            "evaluation": evaluation,
        },
        events=events,
    )


def build_demo_selection_review(scope: Scope) -> SelectionReviewRecord:
    proposal_result = ProposalResult(
        request_id="proposal-demo-1",
        scope=scope,
        options=(
            ProposalResultOption(
                option_index=1,
                proposal_id="proposal-1",
                proposal_type="direct_action",
                title="Inspect the bounded Jeff demo flow",
                why_now="Testing the current v1 backbone end-to-end.",
                summary="Inspect the bounded Jeff demo flow.",
                assumptions=("The current demo workspace remains stable.",),
                main_risks=("The demo path may hide real-world operator friction.",),
            ),
            ProposalResultOption(
                option_index=2,
                proposal_id="proposal-2",
                proposal_type="direct_action",
                title="Inspect the alternate bounded demo path",
                why_now="Keeps a lawful alternate option visible for review and override.",
                summary="Inspect the alternate bounded demo path.",
                assumptions=("The alternate demo path still fits the current scope.",),
                main_risks=("The alternate path may surface less representative follow-up detail.",),
            ),
        ),
    )
    selection_result = SelectionResult(
        selection_id="selection-1",
        considered_proposal_ids=tuple(option.proposal_id for option in proposal_result.options),
        selected_proposal_id="proposal-1",
        rationale="The bounded operator-inspection path is the active demo selection under current scope.",
    )
    policy = Policy()
    approval = Approval.not_required()
    truth = CurrentTruthSnapshot(scope=scope, state_version=3)
    resolved_basis = resolve_selection_action_basis(
        SelectionActionResolutionRequest(
            request_id="demo-selection-resolution",
            selection_result=selection_result,
        )
    )
    materialized = materialize_effective_proposal(
        SelectionEffectiveProposalRequest(
            request_id="demo-selection-materialization",
            proposal_result=proposal_result,
            resolved_basis=resolved_basis,
        )
    )
    formed_action = form_action_from_materialized_proposal(
        ActionFormationRequest(
            request_id="demo-selection-action-formation",
            materialized_effective_proposal=materialized,
            scope=scope,
            basis_state_version=3,
        )
    )
    governance_handoff = handoff_action_to_governance(
        ActionGovernanceHandoffRequest(
            request_id="demo-selection-governance-handoff",
            formed_action_result=formed_action,
            policy=policy,
            approval=approval,
            truth=truth,
        )
    )
    return SelectionReviewRecord(
        selection_result=selection_result,
        operator_override=None,
        resolved_basis=resolved_basis,
        materialized_effective_proposal=materialized,
        formed_action_result=formed_action,
        governance_handoff_result=governance_handoff,
        proposal_result=proposal_result,
        action_scope=scope,
        basis_state_version=truth.state_version,
        governance_policy=policy,
        governance_approval=approval,
        governance_truth=truth,
    )


def load_local_runtime_config(*, base_dir: str | Path | None = None) -> tuple[Path, JeffRuntimeConfig] | None:
    config_path = runtime_config_path(base_dir=base_dir)
    if not config_path.exists():
        return None
    return config_path, load_runtime_config(config_path)


def runtime_config_path(*, base_dir: str | Path | None = None) -> Path:
    root = Path.cwd() if base_dir is None else Path(base_dir)
    return root / RUNTIME_CONFIG_FILENAME


def run_startup_preflight(*, base_dir: str | Path | None = None) -> tuple[str, ...]:
    context = build_startup_interface_context(base_dir=base_dir)
    config_path = runtime_config_path(base_dir=base_dir)
    checks = [
        "package imports resolved",
        "persisted runtime interface context bootstrapped",
        context.startup_summary or "persisted runtime startup summary unavailable",
        f"runtime project scope ready: {next(iter(context.state.projects.keys()))}",
        "CLI entry surface is available through jeff.interface.JeffCLI",
    ]
    if context.runtime_store is not None:
        checks.append(f"runtime home ready: {context.runtime_store.home.root_dir}")
    if context.infrastructure_services is None:
        checks.append(f"no local runtime config found at {config_path}; research CLI remains unavailable")
    else:
        checks.append(f"local runtime config loaded: {config_path}")
        checks.append(
            f"research runtime configured with default adapter {context.infrastructure_services.default_model_adapter_id}"
        )
        if context.research_artifact_store is not None:
            checks.append(f"research artifact store root ready: {context.research_artifact_store.root_dir}")
    return tuple(checks)


def _resolve_configured_research_artifact_store_root(config_path: Path, runtime_config: JeffRuntimeConfig) -> Path:
    configured_root = Path(runtime_config.research.artifact_store_root)
    if configured_root.is_absolute():
        return configured_root
    return config_path.parent / configured_root
