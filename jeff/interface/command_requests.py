"""Operator-triggered request command handlers."""

from __future__ import annotations

from pathlib import Path
import sys

from jeff.action import GovernedExecutionRequest, execute_governed_action, normalize_outcome
from jeff.action.execution import RepoLocalValidationPlan
from jeff.cognitive import evaluate_outcome
from jeff.cognitive.post_selection import ActionFormationRequest, form_action_from_materialized_proposal
from jeff.cognitive.post_selection import ActionGovernanceHandoffRequest, handoff_action_to_governance
from jeff.core.schemas import Scope
from jeff.governance import Approval, CurrentTruthSnapshot, Policy
from jeff.orchestrator.continuations import continue_approval_workflow
from jeff.orchestrator.routing import RoutingDecision, route_evaluation_followup, route_governance_outcome

from .command_common import (
    ensure_selection_review_for_run,
    replace_flow_run,
    replace_selection_review,
    require_flow_run,
    require_project_for_run,
    resolve_run_from_tokens,
    sync_run_truth_from_flow,
)
from .command_models import CommandResult, InterfaceContext
from .json_views import request_receipt_json
from .render import render_request_receipt
from .session import CliSession


_REQUEST_ENTRY_RULES = {
    "approve": {
        "required_outcomes": ("approval_required",),
        "availability_summary": "a run routed to approval_required",
        "receipt_only": False,
    },
    "reject": {
        "required_outcomes": ("approval_required", "revalidate"),
        "availability_summary": "a run routed to approval_required or revalidate",
        "receipt_only": False,
    },
    "retry": {
        "required_outcomes": ("retry",),
        "availability_summary": "a run routed to retry",
        "receipt_only": True,
    },
    "revalidate": {
        "required_outcomes": ("revalidate",),
        "availability_summary": "a run routed to revalidate with a bound granted approval",
        "receipt_only": False,
    },
    "recover": {
        "required_outcomes": ("recover",),
        "availability_summary": "a run routed to recover",
        "receipt_only": True,
    },
}


def request_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    request_type = tokens[0]
    target_run = resolve_run_from_tokens(tokens=tokens, session=session, context=context, command_name=tokens[0])
    run_id = str(target_run.run_id)
    flow_run = require_flow_run(context, run_id)
    routed_outcome = None if flow_run.routing_decision is None else flow_run.routing_decision.routed_outcome

    allowed_outcomes = set(_REQUEST_ENTRY_RULES[request_type]["required_outcomes"])
    if routed_outcome not in allowed_outcomes:
        raise ValueError(
            _request_unavailable_message(
                request_type=request_type,
                run_id=str(target_run.run_id),
                routed_outcome=routed_outcome,
            )
        )

    if request_type == "approve":
        return _approve_command(
            session=session,
            context=context,
            target_run=target_run,
            flow_run=flow_run,
        )
    if request_type == "reject":
        return _reject_command(
            session=session,
            context=context,
            target_run=target_run,
            flow_run=flow_run,
        )
    if request_type == "revalidate":
        return _revalidate_command(
            session=session,
            context=context,
            target_run=target_run,
            flow_run=flow_run,
        )

    note = (
        f"{request_type} request accepted for run {target_run.run_id}; "
        "this remains a bounded receipt-only command in v1."
    )
    payload = request_receipt_json(
        request_type=request_type,
        target=run_id,
        accepted=True,
        scope=_session_scope_payload(session),
        note=note,
    )
    return CommandResult(context=context, session=session, text=render_request_receipt(payload), json_payload=payload)


def _request_unavailable_message(*, request_type: str, run_id: str, routed_outcome: str | None) -> str:
    rule = _REQUEST_ENTRY_RULES[request_type]
    outcome_label = routed_outcome or "none"
    message = (
        f"{request_type} is not currently available for run {run_id}; "
        f"it requires {rule['availability_summary']}. "
        f"Current routed_outcome is {outcome_label}."
    )
    if rule["receipt_only"]:
        message += " In v1 this remains a bounded receipt-only command when it is available."
    return message


def _approve_command(*, session: CliSession, context: InterfaceContext, target_run, flow_run) -> CommandResult:
    next_context, selection_review, policy, action, truth = _operator_governance_context(
        context=context,
        target_run=target_run,
        flow_run=flow_run,
        rebase_action=True,
    )
    approval = Approval.granted_for(
        action_id=str(action.action_id),
        action_binding_key=action.binding_key,
        basis_state_version=action.basis_state_version,
    )
    updated_review, decision = _refresh_selection_review_governance(
        selection_review=selection_review,
        policy=policy,
        approval=approval,
        truth=truth,
    )
    updated_flow_run = continue_approval_workflow(
        prior_flow_run=flow_run,
        governance_decision=decision,
        support_outputs={
            "governance_policy": policy,
            "governance_approval": approval,
            "governance_truth": truth,
        },
        routing_decision=RoutingDecision(
            route_kind="hold",
            routed_outcome="revalidate",
            scope=truth.scope,
            source_stage="governance",
            reason_summary="bounded approval recorded; explicit /revalidate is required before execution continues",
        ),
    )
    next_context = replace_selection_review(context=next_context, run_id=str(target_run.run_id), selection_review=updated_review)
    next_context = replace_flow_run(context=next_context, run_id=str(target_run.run_id), flow_run=updated_flow_run)

    payload = request_receipt_json(
        request_type="approve",
        target=str(target_run.run_id),
        accepted=True,
        effect_state="approval_recorded",
        scope=_session_scope_payload(session),
        note=(
            f"approval recorded for bounded action {action.action_id}; governance now shows the action as allowed, "
            "but execution still requires explicit /revalidate."
        ),
        detail={
            "action_id": str(action.action_id),
            "approval_verdict": decision.approval_verdict,
            "next_routed_outcome": "revalidate",
        },
    )
    return CommandResult(context=next_context, session=session, text=render_request_receipt(payload), json_payload=payload)


def _reject_command(*, session: CliSession, context: InterfaceContext, target_run, flow_run) -> CommandResult:
    next_context, selection_review, policy, action, truth = _operator_governance_context(
        context=context,
        target_run=target_run,
        flow_run=flow_run,
        rebase_action=True,
    )
    approval = Approval.denied_for(
        action_id=str(action.action_id),
        action_binding_key=action.binding_key,
        basis_state_version=action.basis_state_version,
    )
    updated_review, decision = _refresh_selection_review_governance(
        selection_review=selection_review,
        policy=policy,
        approval=approval,
        truth=truth,
    )
    routing_decision = route_governance_outcome(decision=decision, scope=truth.scope)
    updated_flow_run = continue_approval_workflow(
        prior_flow_run=flow_run,
        governance_decision=decision,
        support_outputs={
            "governance_policy": policy,
            "governance_approval": approval,
            "governance_truth": truth,
        },
        routing_decision=routing_decision,
    )
    next_context = replace_selection_review(context=next_context, run_id=str(target_run.run_id), selection_review=updated_review)
    next_context = replace_flow_run(context=next_context, run_id=str(target_run.run_id), flow_run=updated_flow_run)

    payload = request_receipt_json(
        request_type="reject",
        target=str(target_run.run_id),
        accepted=True,
        effect_state="continuation_rejected",
        scope=_session_scope_payload(session),
        note=(
            f"approval was denied for bounded action {action.action_id}; the continuation path is now terminally blocked "
            "until a new bounded run is formed."
        ),
        detail={
            "action_id": str(action.action_id),
            "approval_verdict": decision.approval_verdict,
            "governance_outcome": decision.governance_outcome,
        },
    )
    return CommandResult(context=next_context, session=session, text=render_request_receipt(payload), json_payload=payload)


def _revalidate_command(*, session: CliSession, context: InterfaceContext, target_run, flow_run) -> CommandResult:
    next_context, selection_review, policy, action, truth = _operator_governance_context(
        context=context,
        target_run=target_run,
        flow_run=flow_run,
        rebase_action=False,
    )
    approval = selection_review.governance_approval
    if approval is None or approval.approval_verdict != "granted":
        raise ValueError(f"revalidate requires a bound granted approval for run {target_run.run_id}")

    updated_review, decision = _refresh_selection_review_governance(
        selection_review=selection_review,
        policy=policy,
        approval=approval,
        truth=truth,
    )
    support_outputs = {
        "governance_policy": policy,
        "governance_approval": approval,
        "governance_truth": truth,
    }
    execution_result = None
    outcome = None
    evaluation = None
    routing_decision = None
    effect_state = "continuation_blocked"
    note = "governance did not allow the continuation to proceed after revalidation."
    detail = {
        "action_id": str(action.action_id),
        "approval_verdict": decision.approval_verdict,
        "governance_outcome": decision.governance_outcome,
    }

    if decision.allowed_now:
        execution_result = execute_governed_action(
            GovernedExecutionRequest(action=action, governance_decision=decision),
            execution_plan=_build_repo_local_validation_plan(context),
        )
        outcome = _normalize_execution_outcome(execution_result)
        evaluation = evaluate_outcome(
            objective_summary=action.intent_summary,
            outcome=outcome,
            evidence_quality_posture="moderate" if outcome.outcome_state == "inconclusive" else "strong",
        )
        routing_decision = route_evaluation_followup(evaluation=evaluation, scope=truth.scope)
        effect_state = "continued_to_execution"
        note = f"revalidation continued the bounded flow through execution with status {execution_result.execution_status}."
        detail = {
            "action_id": str(action.action_id),
            "approval_verdict": decision.approval_verdict,
            "execution_status": execution_result.execution_status,
            "evaluation_verdict": evaluation.evaluation_verdict,
        }
    else:
        routing_decision = route_governance_outcome(decision=decision, scope=truth.scope)
        note = (
            f"revalidation failed closed for bounded action {action.action_id}; "
            f"governance outcome is {decision.governance_outcome}."
        )

    updated_flow_run = continue_approval_workflow(
        prior_flow_run=flow_run,
        governance_decision=decision,
        support_outputs=support_outputs,
        routing_decision=routing_decision,
        execution_result=execution_result,
        outcome=outcome,
        evaluation=evaluation,
    )
    next_context = replace_selection_review(context=next_context, run_id=str(target_run.run_id), selection_review=updated_review)
    next_context = replace_flow_run(context=next_context, run_id=str(target_run.run_id), flow_run=updated_flow_run)
    if execution_result is not None:
        next_context, target_run = sync_run_truth_from_flow(context=next_context, run=target_run, flow_run=updated_flow_run)

    payload = request_receipt_json(
        request_type="revalidate",
        target=str(target_run.run_id),
        accepted=True,
        effect_state=effect_state,
        scope=_session_scope_payload(session),
        note=note,
        detail=detail,
    )
    return CommandResult(context=next_context, session=session, text=render_request_receipt(payload), json_payload=payload)


def _operator_governance_context(*, context: InterfaceContext, target_run, flow_run, rebase_action: bool):
    next_context, selection_review = ensure_selection_review_for_run(context=context, run=target_run, flow_run=flow_run)
    if selection_review is None:
        raise ValueError(f"no selection review data is available for run {target_run.run_id}")
    if (
        selection_review.formed_action_result is None
        or not selection_review.formed_action_result.action_formed
        or selection_review.formed_action_result.action is None
    ):
        raise ValueError(f"run {target_run.run_id} has no persisted bounded action to govern")

    policy = selection_review.governance_policy or Policy(approval_required=True)
    truth = CurrentTruthSnapshot(
        scope=Scope(
            project_id=str(target_run.project_id),
            work_unit_id=str(target_run.work_unit_id),
            run_id=str(target_run.run_id),
        ),
        state_version=context.state.state_meta.state_version,
    )
    if not rebase_action:
        return next_context, selection_review, policy, selection_review.formed_action_result.action, truth
    rebased_review, rebased_action = _rebase_selection_review_action(selection_review=selection_review, truth=truth)
    return next_context, rebased_review, policy, rebased_action, truth


def _refresh_selection_review_governance(*, selection_review, policy: Policy, approval: Approval, truth: CurrentTruthSnapshot):
    governance_handoff_result = handoff_action_to_governance(
        ActionGovernanceHandoffRequest(
            request_id=f"selection-review-governance-handoff:{selection_review.formed_action_result.selection_id}",
            formed_action_result=selection_review.formed_action_result,
            policy=policy,
            approval=approval,
            truth=truth,
        )
    )
    return (
        selection_review.__class__(
            selection_result=selection_review.selection_result,
            operator_override=selection_review.operator_override,
            resolved_basis=selection_review.resolved_basis,
            materialized_effective_proposal=selection_review.materialized_effective_proposal,
            formed_action_result=selection_review.formed_action_result,
            governance_handoff_result=governance_handoff_result,
            proposal_result=selection_review.proposal_result,
            action_scope=selection_review.action_scope,
            basis_state_version=truth.state_version,
            governance_policy=policy,
            governance_approval=approval,
            governance_truth=truth,
        ),
        governance_handoff_result.governance_result,
    )


def _rebase_selection_review_action(*, selection_review, truth: CurrentTruthSnapshot):
    formed_action_result = selection_review.formed_action_result
    if formed_action_result is None or formed_action_result.action is None:
        raise ValueError("selection review has no formed bounded action to rebase")
    if formed_action_result.action.basis_state_version == truth.state_version:
        return selection_review, formed_action_result.action
    if selection_review.materialized_effective_proposal is None or selection_review.action_scope is None:
        return selection_review, formed_action_result.action

    rebased_action_result = form_action_from_materialized_proposal(
        ActionFormationRequest(
            request_id=f"selection-review-action-formation:{formed_action_result.selection_id}:rebase:{truth.state_version}",
            materialized_effective_proposal=selection_review.materialized_effective_proposal,
            scope=selection_review.action_scope,
            basis_state_version=truth.state_version,
        )
    )
    updated_review = selection_review.__class__(
        selection_result=selection_review.selection_result,
        operator_override=selection_review.operator_override,
        resolved_basis=selection_review.resolved_basis,
        materialized_effective_proposal=selection_review.materialized_effective_proposal,
        formed_action_result=rebased_action_result,
        governance_handoff_result=selection_review.governance_handoff_result,
        proposal_result=selection_review.proposal_result,
        action_scope=selection_review.action_scope,
        basis_state_version=truth.state_version,
        governance_policy=selection_review.governance_policy,
        governance_approval=selection_review.governance_approval,
        governance_truth=selection_review.governance_truth,
    )
    return updated_review, rebased_action_result.action


def _normalize_execution_outcome(execution_result):
    if execution_result.execution_status == "completed":
        return normalize_outcome(
            execution_result=execution_result,
            outcome_state="complete",
            observed_completion_posture=f"execution {execution_result.execution_status}",
            target_effect_posture="bounded repo-local validation passed",
            artifact_posture="report not persisted",
            side_effect_posture="contained",
        )
    if execution_result.execution_status == "interrupted":
        return normalize_outcome(
            execution_result=execution_result,
            outcome_state="inconclusive",
            observed_completion_posture=f"execution {execution_result.execution_status}",
            target_effect_posture="bounded repo-local validation did not finish cleanly",
            artifact_posture="report unavailable",
            side_effect_posture="contained",
            uncertainty_markers=("validation execution did not finish cleanly",),
        )
    return normalize_outcome(
        execution_result=execution_result,
        outcome_state="failed",
        observed_completion_posture=f"execution {execution_result.execution_status}",
        target_effect_posture="bounded repo-local validation reported failures",
        artifact_posture="report unavailable",
        side_effect_posture="contained",
    )


def _build_repo_local_validation_plan(context: InterfaceContext) -> RepoLocalValidationPlan:
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


def _session_scope_payload(session: CliSession) -> dict[str, str | None]:
    return {
        "project_id": session.scope.project_id,
        "work_unit_id": session.scope.work_unit_id,
        "run_id": session.scope.run_id,
    }