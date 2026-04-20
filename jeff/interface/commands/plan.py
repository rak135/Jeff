"""Planning inspect, checkpoint, and one-step execution command handlers."""

from __future__ import annotations

from pathlib import Path
import sys

from jeff.action import GovernedExecutionRequest, execute_governed_action, normalize_outcome
from jeff.action.execution import RepoLocalValidationPlan
from jeff.cognitive import PlanArtifact, evaluate_outcome
from jeff.cognitive.planning import (
    PlanStepRuntimeRecord,
    apply_checkpoint_decision,
    checkpoint_from_evaluation,
    materialize_active_step_action,
    with_step_runtime_record,
)
from jeff.core.schemas import Scope
from jeff.governance import evaluate_action_entry
from jeff.orchestrator import FlowRunResult
from jeff.orchestrator.lifecycle import update_lifecycle
from jeff.orchestrator.routing import RoutingDecision, route_governance_outcome
from jeff.orchestrator.trace import build_event

from ..json_views import plan_checkpoint_json, plan_execute_json, plan_show_json, plan_steps_json
from ..render import render_plan_checkpoint, render_plan_execute, render_plan_show, render_plan_steps
from ..session import CliSession
from .models import CommandResult, InterfaceContext
from .support.context import build_run_governance_inputs
from .support.flow_runs import replace_flow_run, require_flow_run, sync_run_truth_from_flow
from .support.scope_resolution import require_project_for_run, resolve_historical_run

_CHECKPOINT_DECISIONS = {
    "continue_next_step",
    "revalidate_plan",
    "replan_from_here",
    "escalate",
    "stop_complete",
    "stop_failed",
}


def plan_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    if len(tokens) < 2:
        raise ValueError(
            "plan command must be 'plan show [run_id]', 'plan steps [run_id]', 'plan execute [run_id]', or 'plan checkpoint [decision] [run_id]'"
        )
    if tokens[1] == "show":
        return plan_show_command(tokens=tokens, session=session, context=context)
    if tokens[1] == "steps":
        return plan_steps_command(tokens=tokens, session=session, context=context)
    if tokens[1] == "execute":
        return plan_execute_command(tokens=tokens, session=session, context=context)
    if tokens[1] == "checkpoint":
        return plan_checkpoint_command(tokens=tokens, session=session, context=context)
    raise ValueError(
        "plan command must be 'plan show [run_id]', 'plan steps [run_id]', 'plan execute [run_id]', or 'plan checkpoint [decision] [run_id]'"
    )


def plan_show_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    if len(tokens) > 3:
        raise ValueError("plan show must be 'plan show [run_id]'")
    run, next_session, notice = resolve_historical_run(
        tokens=["plan show", *tokens[2:]],
        session=session,
        context=context,
        command_name="plan show",
    )
    project = require_project_for_run(context, run.project_id)
    work_unit = project.work_units[run.work_unit_id]
    flow_run = require_flow_run(context, str(run.run_id))
    plan = _require_plan(flow_run, str(run.run_id))
    payload = plan_show_json(project=project, work_unit=work_unit, run=run, flow_run=flow_run, plan=plan)
    text = render_plan_show(payload)
    if notice is not None:
        text = f"{notice}\n{text}"
    return CommandResult(context=context, session=next_session, text=text, json_payload=payload)


def plan_steps_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    if len(tokens) > 3:
        raise ValueError("plan steps must be 'plan steps [run_id]'")
    run, next_session, notice = resolve_historical_run(
        tokens=["plan steps", *tokens[2:]],
        session=session,
        context=context,
        command_name="plan steps",
    )
    project = require_project_for_run(context, run.project_id)
    work_unit = project.work_units[run.work_unit_id]
    plan = _require_plan(require_flow_run(context, str(run.run_id)), str(run.run_id))
    payload = plan_steps_json(project=project, work_unit=work_unit, run=run, plan=plan)
    text = render_plan_steps(payload)
    if notice is not None:
        text = f"{notice}\n{text}"
    return CommandResult(context=context, session=next_session, text=text, json_payload=payload)


def plan_execute_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    if len(tokens) > 3:
        raise ValueError("plan execute must be 'plan execute [run_id]'")
    run, next_session, notice = resolve_historical_run(
        tokens=["plan execute", *tokens[2:]],
        session=session,
        context=context,
        command_name="plan execute",
    )
    project = require_project_for_run(context, run.project_id)
    work_unit = project.work_units[run.work_unit_id]
    run_id = str(run.run_id)
    flow_run = require_flow_run(context, run_id)
    plan = _require_plan(flow_run, run_id)
    run_scope = Scope(project_id=str(run.project_id), work_unit_id=str(run.work_unit_id), run_id=run_id)

    governance_policy, governance_approval, governance_truth = build_run_governance_inputs(
        context=context,
        scope=run_scope,
    )
    candidate = materialize_active_step_action(
        plan=plan,
        scope=run_scope,
        basis_state_version=governance_truth.state_version,
        require_single_open_step=False,
    )

    governance_result = None
    execution_result = None
    outcome_result = None
    evaluation_result = None
    execution_reason = candidate.summary
    executable = candidate.action_formed and candidate.action is not None
    executed = False
    updated_plan = plan
    routing = None

    if not executable:
        runtime_record = PlanStepRuntimeRecord(
            step_id=candidate.step_id or plan.active_step_id or _require_active_step_id(plan),
            runtime_state="not_executable",
            executability_posture=candidate.no_action_reason or candidate.summary,
            latest_checkpoint_decision=None,
            latest_checkpoint_summary=None,
        )
        updated_plan = with_step_runtime_record(plan=plan, runtime_record=runtime_record)
        routing = RoutingDecision(
            route_kind="hold",
            routed_outcome="planning",
            scope=run_scope,
            source_stage="planning",
            reason_summary=candidate.no_action_reason or candidate.summary,
        )
    else:
        governance_result = evaluate_action_entry(
            action=candidate.action,
            policy=governance_policy,
            approval=governance_approval,
            truth=governance_truth,
        )
        governance_reason = _governance_reason_summary(governance_result)
        execution_reason = governance_reason or candidate.summary
        if not governance_result.allowed_now:
            runtime_record = PlanStepRuntimeRecord(
                step_id=_require_active_step_id(plan),
                runtime_state="governance_blocked",
                executability_posture="fresh governance re-entry blocked the current active step",
                action_id=str(candidate.action.action_id),
                action_intent_summary=candidate.action.intent_summary,
                last_governance_outcome=governance_result.governance_outcome,
                last_governance_allowed_now=governance_result.allowed_now,
                last_governance_reason_summary=governance_reason,
            )
            updated_plan = with_step_runtime_record(plan=plan, runtime_record=runtime_record)
            routing = route_governance_outcome(decision=governance_result, scope=run_scope)
        else:
            execution_result = execute_governed_action(
                GovernedExecutionRequest(action=candidate.action, governance_decision=governance_result),
                execution_plan=_build_planned_step_execution_plan(context),
            )
            outcome_result = _planned_step_outcome(execution_result)
            evaluation_result = evaluate_outcome(
                objective_summary=(plan.active_step.step_objective if plan.active_step is not None else plan.bounded_objective),
                outcome=outcome_result,
                evidence_quality_posture=("moderate" if outcome_result.outcome_state == "inconclusive" else "strong"),
            )
            checkpoint_outcome = checkpoint_from_evaluation(plan=plan, evaluation=evaluation_result)
            updated_plan = apply_checkpoint_decision(
                plan=plan,
                decision=checkpoint_outcome.decision,
                summary=checkpoint_outcome.summary,
            )
            executed = True
            execution_reason = checkpoint_outcome.summary
            runtime_record = PlanStepRuntimeRecord(
                step_id=_require_active_step_id(plan),
                runtime_state="checkpointed",
                executability_posture="the current active step executed through governance, outcome, and evaluation",
                action_id=str(candidate.action.action_id),
                action_intent_summary=candidate.action.intent_summary,
                last_governance_outcome=governance_result.governance_outcome,
                last_governance_allowed_now=governance_result.allowed_now,
                last_governance_reason_summary=governance_reason,
                last_execution_status=execution_result.execution_status,
                last_execution_command_id=execution_result.execution_command_id,
                last_execution_summary=execution_result.output_summary,
                last_outcome_state=outcome_result.outcome_state,
                last_outcome_summary=outcome_result.observed_completion_posture,
                last_evaluation_verdict=evaluation_result.evaluation_verdict,
                last_evaluation_next_step=evaluation_result.recommended_next_step,
                last_evaluation_reason_summary=evaluation_result.rationale,
                latest_checkpoint_decision=checkpoint_outcome.decision,
                latest_checkpoint_summary=checkpoint_outcome.summary,
            )
            updated_plan = with_step_runtime_record(plan=updated_plan, runtime_record=runtime_record)
            routing = _routing_for_plan_status(plan=updated_plan, scope=run_scope, reason_summary=checkpoint_outcome.summary)

    next_flow_run = _updated_flow_run(
        flow_run=flow_run,
        plan=updated_plan,
        routing=routing,
        governance_result=governance_result,
        execution_result=execution_result,
        outcome_result=outcome_result,
        evaluation_result=evaluation_result,
        attempt_summary=execution_reason,
    )
    next_context = replace_flow_run(context=context, run_id=run_id, flow_run=next_flow_run)
    flow_run = next_context.flow_runs[run_id]
    next_context, run = sync_run_truth_from_flow(context=next_context, run=run, flow_run=flow_run)
    project = require_project_for_run(next_context, run.project_id)
    work_unit = project.work_units[run.work_unit_id]
    updated_plan = _require_plan(flow_run, run_id)

    payload = plan_execute_json(
        project=project,
        work_unit=work_unit,
        run=run,
        plan=updated_plan,
        executable=executable,
        executed=executed,
        action_id=None if candidate.action is None else str(candidate.action.action_id),
        execution_reason=execution_reason,
        governance=governance_result,
        execution=execution_result,
        outcome=outcome_result,
        evaluation=evaluation_result,
    )
    text = render_plan_execute(payload)
    if notice is not None:
        text = f"{notice}\n{text}"
    return CommandResult(context=next_context, session=next_session, text=text, json_payload=payload)


def plan_checkpoint_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    if len(tokens) > 4:
        raise ValueError("plan checkpoint must be 'plan checkpoint [decision] [run_id]'")
    decision = None
    run_token_index = 2
    if len(tokens) >= 3 and tokens[2] in _CHECKPOINT_DECISIONS:
        decision = tokens[2]
        run_token_index = 3
    run_tokens = ["plan checkpoint", *tokens[run_token_index:]]
    run, next_session, notice = resolve_historical_run(
        tokens=run_tokens,
        session=session,
        context=context,
        command_name="plan checkpoint",
    )
    project = require_project_for_run(context, run.project_id)
    work_unit = project.work_units[run.work_unit_id]
    run_id = str(run.run_id)
    flow_run = require_flow_run(context, run_id)
    plan = _require_plan(flow_run, run_id)

    next_context = context
    if decision is not None:
        updated_plan = apply_checkpoint_decision(
            plan=plan,
            decision=decision,
            summary=f"operator recorded checkpoint decision {decision}",
        )
        next_flow_run = FlowRunResult(
            lifecycle=_lifecycle_for_plan_update(
                flow_run=flow_run,
                plan=updated_plan,
                reason_summary=f"operator recorded checkpoint decision {decision}",
            ),
            outputs={**flow_run.outputs, "planning": updated_plan},
            events=flow_run.events
            + (
                build_event(
                    ordinal=len(flow_run.events) + 1,
                    flow_family=flow_run.lifecycle.flow_family,
                    scope=flow_run.lifecycle.scope,
                    stage="planning",
                    event_type="routing_decision",
                    summary=f"planning checkpoint recorded: {decision}",
                ),
            ),
            routing_decision=_routing_for_plan_status(
                plan=updated_plan,
                scope=flow_run.lifecycle.scope,
                reason_summary=f"operator recorded checkpoint decision {decision}",
            ),
            selection_failure=flow_run.selection_failure,
            objective_summary=flow_run.objective_summary,
            memory_handoff_attempted=flow_run.memory_handoff_attempted,
            memory_handoff_result=flow_run.memory_handoff_result,
            memory_handoff_note=flow_run.memory_handoff_note,
        )
        next_context = replace_flow_run(context=context, run_id=run_id, flow_run=next_flow_run)
        flow_run = next_context.flow_runs[run_id]
        next_context, run = sync_run_truth_from_flow(context=next_context, run=run, flow_run=flow_run)
        project = require_project_for_run(next_context, run.project_id)
        work_unit = project.work_units[run.work_unit_id]
        plan = _require_plan(flow_run, run_id)

    payload = plan_checkpoint_json(project=project, work_unit=work_unit, run=run, plan=plan)
    text = render_plan_checkpoint(payload)
    if notice is not None:
        text = f"{notice}\n{text}"
    return CommandResult(context=next_context, session=next_session, text=text, json_payload=payload)


def _require_plan(flow_run: FlowRunResult, run_id: str) -> PlanArtifact:
    plan = flow_run.outputs.get("planning")
    if not isinstance(plan, PlanArtifact):
        raise ValueError(f"no planning artifact is available for run {run_id}")
    return plan


def _require_active_step_id(plan: PlanArtifact) -> str:
    if plan.active_step_id is None:
        raise ValueError("the persisted plan has no active step")
    return plan.active_step_id


def _build_planned_step_execution_plan(context: InterfaceContext) -> RepoLocalValidationPlan:
    repo_root = Path.cwd()
    if context.runtime_store is not None:
        repo_root = context.runtime_store.home.root_dir.parent
    return RepoLocalValidationPlan(
        command_id="smoke_quickstart_validation",
        argv=(
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/smoke/test_bootstrap_smoke.py",
            "tests/smoke/test_cli_entry_smoke.py",
            "tests/smoke/test_quickstart_paths.py",
        ),
        working_directory=str(repo_root),
        description="Run the bounded repo-local CLI/bootstrap smoke validation suite.",
        timeout_seconds=180,
    )


def _planned_step_outcome(execution_output):
    if execution_output.execution_status == "completed":
        return normalize_outcome(
            execution_result=execution_output,
            outcome_state="complete",
            observed_completion_posture=f"execution {execution_output.execution_status}",
            target_effect_posture="bounded repo-local validation passed",
            artifact_posture="report not persisted",
            side_effect_posture="contained",
        )
    if execution_output.execution_status == "interrupted":
        return normalize_outcome(
            execution_result=execution_output,
            outcome_state="inconclusive",
            observed_completion_posture=f"execution {execution_output.execution_status}",
            target_effect_posture="bounded repo-local validation did not finish cleanly",
            artifact_posture="report unavailable",
            side_effect_posture="contained",
            uncertainty_markers=("validation execution did not finish cleanly",),
        )
    return normalize_outcome(
        execution_result=execution_output,
        outcome_state="failed",
        observed_completion_posture=f"execution {execution_output.execution_status}",
        target_effect_posture="bounded repo-local validation reported failures",
        artifact_posture="report unavailable",
        side_effect_posture="contained",
    )


def _governance_reason_summary(governance_result) -> str | None:
    reasons = governance_result.readiness.reasons or governance_result.readiness.cautions
    if not reasons:
        return None
    return "; ".join(reasons)


def _updated_flow_run(
    *,
    flow_run: FlowRunResult,
    plan: PlanArtifact,
    routing: RoutingDecision | None,
    governance_result,
    execution_result,
    outcome_result,
    evaluation_result,
    attempt_summary: str,
) -> FlowRunResult:
    outputs = {**flow_run.outputs, "planning": plan}
    if governance_result is not None:
        outputs["governance"] = governance_result
    if execution_result is not None:
        outputs["execution"] = execution_result
    if outcome_result is not None:
        outputs["outcome"] = outcome_result
    if evaluation_result is not None:
        outputs["evaluation"] = evaluation_result

    events = list(flow_run.events)
    ordinal = len(events)

    def add(stage, event_type, summary):
        nonlocal ordinal
        ordinal += 1
        events.append(
            build_event(
                ordinal=ordinal,
                flow_family=flow_run.lifecycle.flow_family,
                scope=flow_run.lifecycle.scope,
                stage=stage,
                event_type=event_type,
                summary=summary,
            )
        )

    add("planning", "stage_entered", f"entered planned-step execution for {plan.active_step_id or '-'}")
    if governance_result is not None:
        add("governance", "stage_entered", "entered governance re-entry for planned step")
        add(
            "governance",
            "stage_exited",
            f"exited governance with outcome {governance_result.governance_outcome}",
        )
    if execution_result is not None:
        add("execution", "stage_entered", "entered execution for planned step")
        add("execution", "stage_exited", f"exited execution with status {execution_result.execution_status}")
    if outcome_result is not None:
        add("outcome", "stage_entered", "entered outcome normalization for planned step")
        add("outcome", "stage_exited", f"exited outcome with state {outcome_result.outcome_state}")
    if evaluation_result is not None:
        add("evaluation", "stage_entered", "entered evaluation for planned step")
        add(
            "evaluation",
            "stage_exited",
            f"exited evaluation with verdict {evaluation_result.evaluation_verdict}",
        )
    add("planning", "routing_decision", attempt_summary)

    return FlowRunResult(
        lifecycle=_lifecycle_for_plan_update(flow_run=flow_run, plan=plan, reason_summary=attempt_summary),
        outputs=outputs,
        events=tuple(events),
        routing_decision=routing,
        selection_failure=flow_run.selection_failure,
        objective_summary=flow_run.objective_summary,
        memory_handoff_attempted=flow_run.memory_handoff_attempted,
        memory_handoff_result=flow_run.memory_handoff_result,
        memory_handoff_note=flow_run.memory_handoff_note,
    )


def _lifecycle_for_plan_update(*, flow_run: FlowRunResult, plan: PlanArtifact, reason_summary: str):
    if plan.plan_status in {"active", "needs_revalidation", "needs_replan"}:
        return update_lifecycle(
            flow_run.lifecycle,
            lifecycle_state="waiting",
            current_stage="planning",
            reason_summary=reason_summary,
        )
    if plan.plan_status == "escalated":
        return update_lifecycle(
            flow_run.lifecycle,
            lifecycle_state="escalated",
            current_stage="planning",
            reason_summary=reason_summary,
        )
    if plan.plan_status == "failed":
        return update_lifecycle(
            flow_run.lifecycle,
            lifecycle_state="failed",
            current_stage="evaluation",
            reason_summary=reason_summary,
        )
    return update_lifecycle(
        flow_run.lifecycle,
        lifecycle_state="completed",
        current_stage="evaluation",
        reason_summary=reason_summary,
    )


def _routing_for_plan_status(*, plan: PlanArtifact, scope: Scope, reason_summary: str) -> RoutingDecision | None:
    if plan.plan_status == "active":
        return RoutingDecision(
            route_kind="hold",
            routed_outcome="planning",
            scope=scope,
            source_stage="planning",
            reason_summary=reason_summary,
        )
    if plan.plan_status == "needs_revalidation":
        return RoutingDecision(
            route_kind="hold",
            routed_outcome="revalidate",
            scope=scope,
            source_stage="planning",
            reason_summary=reason_summary,
        )
    if plan.plan_status == "needs_replan":
        return RoutingDecision(
            route_kind="follow_up",
            routed_outcome="terminate_and_replan",
            scope=scope,
            source_stage="planning",
            reason_summary=reason_summary,
        )
    if plan.plan_status == "escalated":
        return RoutingDecision(
            route_kind="hold",
            routed_outcome="escalated",
            scope=scope,
            source_stage="planning",
            reason_summary=reason_summary,
        )
    return None
