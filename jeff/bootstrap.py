"""Explicit bootstrap helpers for the current operator-ready demo context."""

from __future__ import annotations

from pathlib import Path

from jeff.action import GovernedExecutionRequest, normalize_outcome
from jeff.action.execution import ExecutionResult
from jeff.cognitive import ResearchArtifactStore, SelectionResult, evaluate_outcome
from jeff.cognitive.proposal.contracts import ProposalResult, ProposalResultOption
from jeff.contracts import Action
from jeff.core.schemas import Scope
from jeff.core.state import GlobalState, bootstrap_global_state
from jeff.core.transition import TransitionRequest, apply_transition
from jeff.governance import Approval, CurrentTruthSnapshot, Policy, evaluate_action_entry
from jeff.infrastructure import (
    InfrastructureServices,
    JeffRuntimeConfig,
    ModelAdapterRuntimeConfig,
    build_model_adapter_runtime_config,
    build_infrastructure_services,
    load_runtime_config,
)
from jeff.interface.commands import InterfaceContext
from jeff.memory import InMemoryMemoryStore
from jeff.orchestrator.lifecycle import FlowLifecycle
from jeff.orchestrator.runner import FlowRunResult
from jeff.orchestrator.trace import OrchestrationEvent

RUNTIME_CONFIG_FILENAME = "jeff.runtime.toml"


def build_infrastructure_runtime(
    config: ModelAdapterRuntimeConfig | JeffRuntimeConfig,
) -> InfrastructureServices:
    runtime_config = build_model_adapter_runtime_config(config) if isinstance(config, JeffRuntimeConfig) else config
    return build_infrastructure_services(runtime_config)


def build_demo_interface_context() -> InterfaceContext:
    state, scope = build_demo_state()
    flow_run = build_demo_flow_run(scope)
    return InterfaceContext(
        state=state,
        flow_runs={str(scope.run_id): flow_run},
    )


def build_startup_interface_context(*, base_dir: str | Path | None = None) -> InterfaceContext:
    context = build_demo_interface_context()
    runtime_config_entry = load_local_runtime_config(base_dir=base_dir)
    if runtime_config_entry is None:
        return context

    config_path, runtime_config = runtime_config_entry
    return InterfaceContext(
        state=context.state,
        flow_runs=context.flow_runs,
        infrastructure_services=build_infrastructure_runtime(runtime_config),
        research_artifact_store=ResearchArtifactStore(_resolve_research_artifact_store_root(config_path, runtime_config)),
        memory_store=InMemoryMemoryStore() if runtime_config.research.enable_memory_handoff else None,
        research_memory_handoff_enabled=runtime_config.research.enable_memory_handoff,
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


def build_demo_flow_run(scope: Scope) -> FlowRunResult:
    result_option = ProposalResultOption(
        option_index=1,
        proposal_id="proposal-1",
        proposal_type="direct_action",
        title="Inspect the bounded Jeff demo flow",
        why_now="Testing the current v1 backbone end-to-end.",
        summary="Inspect the bounded Jeff demo flow.",
    )
    selection = SelectionResult(
        selection_id="selection-1",
        considered_proposal_ids=(result_option.proposal_id,),
        selected_proposal_id="proposal-1",
        rationale="The bounded operator-inspection path is the active demo selection.",
    )
    action = Action(
        action_id="action-1",
        scope=scope,
        intent_summary="Render one truthful demo flow for operator inspection.",
        basis_state_version=3,
    )
    governance = evaluate_action_entry(
        action=action,
        policy=Policy(),
        approval=Approval.not_required(),
        truth=CurrentTruthSnapshot(scope=scope, state_version=3),
    )
    execution = ExecutionResult(
        governed_request=GovernedExecutionRequest(action=action, governance_decision=governance),
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
            "selection": selection,
            "governance": governance,
            "execution": execution,
            "outcome": outcome,
            "evaluation": evaluation,
        },
        events=events,
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
        "demo interface context bootstrapped",
        f"demo project scope ready: {next(iter(context.state.projects.keys()))}",
        "CLI entry surface is available through jeff.interface.JeffCLI",
    ]
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


def _resolve_research_artifact_store_root(config_path: Path, runtime_config: JeffRuntimeConfig) -> Path:
    configured_root = Path(runtime_config.research.artifact_store_root)
    if configured_root.is_absolute():
        return configured_root
    return config_path.parent / configured_root
