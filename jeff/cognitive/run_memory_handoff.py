"""Bounded per-run memory handoff input assembly from real flow results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from jeff.action.execution import ExecutionResult
from jeff.cognitive.evaluation import EvaluationResult
from jeff.core.schemas import Scope
from jeff.memory.models import MemoryWriteDecision

if TYPE_CHECKING:
    from jeff.orchestrator.runner import FlowRunResult


@dataclass(frozen=True, slots=True)
class RunMemoryHandoffInput:
    project_id: str
    work_unit_id: str | None
    run_id: str
    flow_id: str
    flow_family: str
    objective: str
    terminal_posture: str
    summary: str
    remembered_points: tuple[str, ...]
    why_it_matters: str
    support_summary: str
    support_quality: str
    stability: str


@dataclass(frozen=True, slots=True)
class RunMemoryHandoffResultSummary:
    write_outcome: str
    candidate_id: str
    memory_id: str | None
    reasons: tuple[str, ...]


def summarize_memory_write_decision(decision: MemoryWriteDecision) -> RunMemoryHandoffResultSummary:
    return RunMemoryHandoffResultSummary(
        write_outcome=decision.write_outcome,
        candidate_id=str(decision.candidate_id),
        memory_id=None if decision.memory_id is None else str(decision.memory_id),
        reasons=tuple(decision.reasons),
    )


def build_run_memory_handoff_input(
    *,
    scope: Scope,
    flow_run: FlowRunResult,
    objective: str,
) -> RunMemoryHandoffInput:
    objective_text = objective.strip()
    if not objective_text:
        raise ValueError("run memory handoff requires a bounded objective")

    terminal_posture = _terminal_posture(flow_run)
    remembered_points = _remembered_points(flow_run=flow_run, terminal_posture=terminal_posture)
    if not remembered_points:
        raise ValueError("run memory handoff requires at least one bounded remembered point")

    return RunMemoryHandoffInput(
        project_id=str(scope.project_id),
        work_unit_id=None if scope.work_unit_id is None else str(scope.work_unit_id),
        run_id=str(scope.run_id),
        flow_id=flow_run.lifecycle.flow_id,
        flow_family=flow_run.lifecycle.flow_family,
        objective=objective_text,
        terminal_posture=terminal_posture,
        summary=_summary(objective_text, terminal_posture),
        remembered_points=remembered_points,
        why_it_matters=_why_it_matters(terminal_posture),
        support_summary=_support_summary(flow_run=flow_run, terminal_posture=terminal_posture),
        support_quality=_support_quality(flow_run),
        stability=_stability(flow_run),
    )


def _terminal_posture(flow_run: FlowRunResult) -> str:
    routing = flow_run.routing_decision
    execution = flow_run.outputs.get("execution")
    outcome = flow_run.outputs.get("outcome")
    evaluation = flow_run.outputs.get("evaluation")

    if routing is not None and routing.routed_outcome == "approval_required":
        return "approval_required_before_execution"
    if routing is not None and routing.routed_outcome == "defer":
        return "deferred_before_execution"
    if routing is not None and routing.routed_outcome == "reject_all":
        return "rejected_before_execution"
    if routing is not None and routing.routed_outcome == "blocked" and execution is None:
        return "blocked_before_execution"
    if execution is None and flow_run.lifecycle.lifecycle_state in {"failed", "invalidated"}:
        return "failed_before_execution"
    if isinstance(execution, ExecutionResult):
        if execution.execution_status == "completed":
            if outcome is not None and getattr(outcome, "outcome_state", None) == "failed":
                return "execution_completed_with_failed_outcome"
            if isinstance(evaluation, EvaluationResult) and evaluation.evaluation_verdict == "unacceptable":
                return "execution_completed_with_unacceptable_evaluation"
            return "execution_completed"
        if execution.execution_status == "failed":
            return "execution_failed"
        if execution.execution_status == "interrupted":
            return "execution_interrupted"
        return f"execution_{execution.execution_status}"
    return flow_run.lifecycle.lifecycle_state


def _summary(objective: str, terminal_posture: str) -> str:
    return f"Run for '{_truncate(objective, 72)}' ended as {terminal_posture.replace('_', ' ')}."


def _remembered_points(*, flow_run: FlowRunResult, terminal_posture: str) -> tuple[str, ...]:
    points: list[str] = [f"Terminal posture: {terminal_posture.replace('_', ' ')}"]

    routing = flow_run.routing_decision
    if routing is not None:
        points.append(f"Routing outcome: {routing.routed_outcome} ({_truncate(routing.reason_summary, 120)})")

    execution = flow_run.outputs.get("execution")
    if isinstance(execution, ExecutionResult):
        execution_point = f"Execution status: {execution.execution_status}"
        if execution.exit_code is not None:
            execution_point += f" exit_code={execution.exit_code}"
        points.append(execution_point)
        if execution.output_summary:
            points.append(f"Execution summary: {_truncate(execution.output_summary, 120)}")

    outcome = flow_run.outputs.get("outcome")
    if outcome is not None:
        points.append(f"Outcome state: {outcome.outcome_state}")

    evaluation = flow_run.outputs.get("evaluation")
    if isinstance(evaluation, EvaluationResult):
        points.append(f"Evaluation verdict: {evaluation.evaluation_verdict}")

    selection = flow_run.outputs.get("selection")
    if selection is not None and getattr(selection, "selected_proposal_id", None) is not None:
        points.append(f"Selected proposal: {selection.selected_proposal_id}")
    elif selection is not None and getattr(selection, "non_selection_outcome", None) is not None:
        points.append(f"Selection outcome: {selection.non_selection_outcome}")

    reason_summary = flow_run.lifecycle.reason_summary
    if reason_summary:
        points.append(f"Flow reason: {_truncate(reason_summary, 120)}")

    bounded: list[str] = []
    for point in points:
        text = point.strip()
        if text and text not in bounded:
            bounded.append(_truncate(text, 160))
    return tuple(bounded[:5])


def _support_summary(*, flow_run: FlowRunResult, terminal_posture: str) -> str:
    return _truncate(
        f"Flow {flow_run.lifecycle.flow_id} from {flow_run.lifecycle.flow_family} ended as {terminal_posture.replace('_', ' ')}",
        160,
    )


def _support_quality(flow_run: FlowRunResult) -> str:
    execution = flow_run.outputs.get("execution")
    evaluation = flow_run.outputs.get("evaluation")
    routing = flow_run.routing_decision

    if isinstance(execution, ExecutionResult) and execution.execution_status == "completed":
        if isinstance(evaluation, EvaluationResult) and evaluation.evaluation_verdict == "acceptable":
            return "strong"
        return "moderate"
    if routing is not None and routing.routed_outcome in {"approval_required", "defer", "revalidate", "recover", "retry"}:
        return "weak"
    return "weak"


def _stability(flow_run: FlowRunResult) -> str:
    execution = flow_run.outputs.get("execution")
    routing = flow_run.routing_decision

    if isinstance(execution, ExecutionResult) and execution.execution_status == "completed":
        return "stable"
    if routing is not None and routing.routed_outcome in {"approval_required", "defer", "revalidate", "recover", "retry"}:
        return "volatile"
    return "tentative"


def _why_it_matters(terminal_posture: str) -> str:
    if terminal_posture == "execution_completed":
        return "This bounded run completed and may serve as a reusable precedent later."
    if "before_execution" in terminal_posture:
        return "This bounded run stopped before execution and may prevent repeated dead-end attempts later."
    return "This bounded run produced outcome evidence that may matter for later project work."


def _truncate(value: str, limit: int) -> str:
    text = value.strip()
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3].rstrip()}..."