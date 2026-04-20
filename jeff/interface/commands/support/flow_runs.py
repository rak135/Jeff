"""Flow-run persistence and run-truth synchronization helpers."""

from __future__ import annotations

from jeff.action.execution import ExecutionResult
from jeff.cognitive.run_memory_handoff import build_run_memory_handoff_input, summarize_memory_write_decision
from jeff.core.containers.models import Run
from jeff.core.schemas import Scope
from jeff.core.transition import TransitionRequest
from jeff.memory import handoff_run_summary_to_memory
from jeff.orchestrator import FlowRunResult

from ..models import InterfaceContext
from .scope_resolution import get_project, get_run, get_work_unit
from .transitions import apply_context_transition, replace_context_state


def replace_flow_run(
    *,
    context: InterfaceContext,
    run_id: str,
    flow_run: FlowRunResult,
    objective_summary: str | None = None,
) -> InterfaceContext:
    prepared_flow_run = _prepare_flow_run_for_storage(
        context=context,
        run_id=run_id,
        flow_run=flow_run,
        objective_summary=objective_summary,
    )
    if context.runtime_store is not None:
        context.runtime_store.save_flow_run(run_id, prepared_flow_run)
    next_flow_runs = dict(context.flow_runs)
    next_flow_runs[run_id] = prepared_flow_run
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


def _prepare_flow_run_for_storage(
    *,
    context: InterfaceContext,
    run_id: str,
    flow_run: FlowRunResult,
    objective_summary: str | None,
) -> FlowRunResult:
    prior_flow_run = context.flow_runs.get(run_id)
    resolved_objective = _resolve_flow_objective_summary(
        flow_run=flow_run,
        prior_flow_run=prior_flow_run,
        objective_summary=objective_summary,
    )
    handoff_attempted = False
    handoff_result = flow_run.memory_handoff_result
    handoff_note = flow_run.memory_handoff_note

    if context.memory_store is None:
        handoff_note = "automatic run memory handoff unavailable: no configured memory store"
    elif resolved_objective is None:
        handoff_note = "automatic run memory handoff unavailable: no lawful bounded objective summary"
    else:
        handoff_attempted = True
        handoff_input = build_run_memory_handoff_input(
            scope=flow_run.lifecycle.scope,
            flow_run=flow_run,
            objective=resolved_objective,
        )
        handoff_decision = handoff_run_summary_to_memory(handoff_input, store=context.memory_store)
        handoff_result = summarize_memory_write_decision(handoff_decision)
        handoff_note = f"automatic run memory handoff completed with outcome {handoff_result.write_outcome}"

    return FlowRunResult(
        lifecycle=flow_run.lifecycle,
        outputs=flow_run.outputs,
        events=flow_run.events,
        routing_decision=flow_run.routing_decision,
        selection_failure=flow_run.selection_failure,
        objective_summary=resolved_objective,
        memory_handoff_attempted=handoff_attempted,
        memory_handoff_result=handoff_result,
        memory_handoff_note=handoff_note,
    )


def _resolve_flow_objective_summary(
    *,
    flow_run: FlowRunResult,
    prior_flow_run: FlowRunResult | None,
    objective_summary: str | None,
) -> str | None:
    if objective_summary is not None and objective_summary.strip():
        return objective_summary.strip()
    if flow_run.objective_summary is not None and flow_run.objective_summary.strip():
        return flow_run.objective_summary.strip()
    if prior_flow_run is not None and prior_flow_run.objective_summary is not None and prior_flow_run.objective_summary.strip():
        return prior_flow_run.objective_summary.strip()
    evaluation = flow_run.outputs.get("evaluation")
    if evaluation is not None and getattr(evaluation, "objective_summary", None):
        return evaluation.objective_summary
    return None


def sync_run_truth_from_flow(
    *,
    context: InterfaceContext,
    run: Run,
    flow_run: FlowRunResult,
) -> tuple[InterfaceContext, Run]:
    requested_lifecycle_state = _canonical_run_lifecycle_state(flow_run)
    requested_execution_status = _execution_status_from_flow(flow_run)
    requested_outcome_state = _outcome_state_from_flow(flow_run)
    requested_evaluation_verdict = _evaluation_verdict_from_flow(flow_run)

    if (
        run.run_lifecycle_state == requested_lifecycle_state
        and run.last_execution_status == requested_execution_status
        and run.last_outcome_state == requested_outcome_state
        and run.last_evaluation_verdict == requested_evaluation_verdict
    ):
        return context, run

    result = apply_context_transition(
        context=context,
        request=TransitionRequest(
            transition_id=(
                f"transition-sync-run-{run.project_id}-{run.work_unit_id}-{run.run_id}-"
                f"{context.state.state_meta.state_version + 1}"
            ),
            transition_type="update_run",
            basis_state_version=context.state.state_meta.state_version,
            scope=Scope(
                project_id=str(run.project_id),
                work_unit_id=str(run.work_unit_id),
                run_id=str(run.run_id),
            ),
            payload={
                "run_lifecycle_state": requested_lifecycle_state,
                "last_execution_status": requested_execution_status,
                "last_outcome_state": requested_outcome_state,
                "last_evaluation_verdict": requested_evaluation_verdict,
            },
        ),
    )
    if result.transition_result != "committed":
        issue = result.validation_errors[0].message if result.validation_errors else "unknown transition failure"
        raise ValueError(f"run truth synchronization failed: {issue}")

    next_context = replace_context_state(context, result.state)
    synced_project = get_project(next_context, str(run.project_id))
    synced_work_unit = get_work_unit(synced_project, str(run.work_unit_id))
    return next_context, get_run(synced_work_unit, str(run.run_id))


def _canonical_run_lifecycle_state(flow_run: FlowRunResult) -> str:
    routing = flow_run.routing_decision
    execution_status = _execution_status_from_flow(flow_run)
    if routing is not None and routing.routed_outcome == "approval_required":
        return "approval_required"
    if execution_status is None and routing is not None:
        if routing.routed_outcome in {"defer", "reject_all", "revalidate"}:
            return "deferred"
        if routing.routed_outcome == "blocked":
            return "blocked"
    if execution_status is None and flow_run.lifecycle.lifecycle_state in {"failed", "invalidated"}:
        return "failed_before_execution"
    mapping = {
        "started": "active",
        "active": "active",
        "waiting": "blocked",
        "blocked": "blocked",
        "escalated": "escalated",
        "completed": "completed",
        "failed": "failed",
        "invalidated": "failed",
    }
    return mapping.get(flow_run.lifecycle.lifecycle_state, flow_run.lifecycle.lifecycle_state)


def _execution_status_from_flow(flow_run: FlowRunResult) -> str | None:
    execution = flow_run.outputs.get("execution")
    if isinstance(execution, ExecutionResult):
        return execution.execution_status
    return None


def _outcome_state_from_flow(flow_run: FlowRunResult) -> str | None:
    outcome = flow_run.outputs.get("outcome")
    return None if outcome is None else outcome.outcome_state


def _evaluation_verdict_from_flow(flow_run: FlowRunResult) -> str | None:
    evaluation = flow_run.outputs.get("evaluation")
    return None if evaluation is None else evaluation.evaluation_verdict


def require_flow_run(context: InterfaceContext, run_id: str) -> FlowRunResult:
    try:
        return context.flow_runs[run_id]
    except KeyError as exc:
        raise ValueError(f"no orchestrator flow result is available for run {run_id}") from exc