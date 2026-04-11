"""Fail-closed governance evaluation for bounded action entry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from jeff.contracts import Action
from jeff.core.schemas import Scope
from jeff.governance.approval import Approval, ApprovalVerdict
from jeff.governance.policy import Policy
from jeff.governance.readiness import Readiness

PolicyVerdict = Literal["allowed", "approval_required", "forbidden"]
GovernanceOutcome = Literal[
    "allowed_now",
    "blocked",
    "approval_required",
    "deferred_pending_revalidation",
    "invalidated",
    "escalated",
]


@dataclass(frozen=True, slots=True)
class CurrentTruthSnapshot:
    scope: Scope
    state_version: int
    blocked_reasons: tuple[str, ...] = ()
    degraded_truth: bool = False
    truth_mismatch: bool = False
    direction_ok: bool = True
    target_available: bool = True
    requires_revalidation: bool = False

    def __post_init__(self) -> None:
        if self.state_version < 0:
            raise ValueError("state_version must be zero or greater")


@dataclass(frozen=True, slots=True)
class ActionEntryDecision:
    action_id: str
    action_binding_key: str
    policy_verdict: PolicyVerdict
    approval_verdict: ApprovalVerdict
    readiness: Readiness
    governance_outcome: GovernanceOutcome
    allowed_now: bool


def evaluate_action_entry(
    *,
    action: Action,
    policy: Policy,
    approval: Approval | None,
    truth: CurrentTruthSnapshot,
) -> ActionEntryDecision:
    if not isinstance(action, Action):
        raise TypeError("governance requires a bounded Action input")
    if not isinstance(policy, Policy):
        raise TypeError("governance requires a Policy input")
    if approval is not None and not isinstance(approval, Approval):
        raise TypeError("approval must be an Approval object or None")
    if not isinstance(truth, CurrentTruthSnapshot):
        raise TypeError("truth must be a CurrentTruthSnapshot")

    policy_verdict = _evaluate_policy(policy)
    approval_verdict = _evaluate_approval(action=action, policy=policy, approval=approval, truth=truth)
    readiness = _evaluate_readiness(
        action=action,
        policy=policy,
        policy_verdict=policy_verdict,
        approval_verdict=approval_verdict,
        truth=truth,
    )
    governance_outcome = _map_outcome(policy_verdict=policy_verdict, readiness=readiness)

    return ActionEntryDecision(
        action_id=str(action.action_id),
        action_binding_key=action.binding_key,
        policy_verdict=policy_verdict,
        approval_verdict=approval_verdict,
        readiness=readiness,
        governance_outcome=governance_outcome,
        allowed_now=governance_outcome == "allowed_now",
    )


def may_start_now(decision: ActionEntryDecision) -> bool:
    if not isinstance(decision, ActionEntryDecision):
        raise TypeError("action start requires an ActionEntryDecision")
    return decision.allowed_now


def _evaluate_policy(policy: Policy) -> PolicyVerdict:
    if policy.action_forbidden:
        return "forbidden"
    if policy.approval_required:
        return "approval_required"
    return "allowed"


def _evaluate_approval(
    *,
    action: Action,
    policy: Policy,
    approval: Approval | None,
    truth: CurrentTruthSnapshot,
) -> ApprovalVerdict:
    if not policy.approval_required:
        return "not_required"
    if approval is None:
        return "absent"
    if approval.approval_verdict in {"absent", "not_required", "stale", "mismatched"}:
        return approval.approval_verdict
    if approval.action_id != action.action_id or approval.action_binding_key != action.binding_key:
        return "mismatched"
    if policy.freshness_sensitive and approval.basis_state_version != truth.state_version:
        return "stale"
    return approval.approval_verdict


def _evaluate_readiness(
    *,
    action: Action,
    policy: Policy,
    policy_verdict: PolicyVerdict,
    approval_verdict: ApprovalVerdict,
    truth: CurrentTruthSnapshot,
) -> Readiness:
    reasons: list[str] = []
    cautions: list[str] = []

    if not _scope_matches(action.scope, truth.scope):
        return Readiness(
            action_id=action.action_id,
            readiness_state="invalidated",
            checked_at_state_version=truth.state_version,
            reasons=("action scope no longer matches current truth scope",),
        )

    if action.basis_state_version != truth.state_version:
        return Readiness(
            action_id=action.action_id,
            readiness_state="pending_revalidation",
            checked_at_state_version=truth.state_version,
            reasons=("action basis_state_version is stale against current truth",),
        )

    if policy.revalidation_required or truth.requires_revalidation:
        return Readiness(
            action_id=action.action_id,
            readiness_state="pending_revalidation",
            checked_at_state_version=truth.state_version,
            reasons=("current truth requires revalidation before lawful start",),
        )

    if policy_verdict == "forbidden":
        return Readiness(
            action_id=action.action_id,
            readiness_state="blocked",
            checked_at_state_version=truth.state_version,
            reasons=("effective policy forbids this action",),
        )

    if approval_verdict == "denied":
        return Readiness(
            action_id=action.action_id,
            readiness_state="blocked",
            checked_at_state_version=truth.state_version,
            reasons=("required approval was denied",),
        )

    if approval_verdict == "mismatched":
        return Readiness(
            action_id=action.action_id,
            readiness_state="invalidated",
            checked_at_state_version=truth.state_version,
            reasons=("approval does not bind to this bounded action",),
        )

    if approval_verdict == "stale":
        return Readiness(
            action_id=action.action_id,
            readiness_state="pending_revalidation",
            checked_at_state_version=truth.state_version,
            reasons=("approval basis is stale and must be revalidated",),
        )

    if policy.approval_required and approval_verdict == "absent":
        return Readiness(
            action_id=action.action_id,
            readiness_state="pending_approval",
            checked_at_state_version=truth.state_version,
            reasons=("required approval is absent",),
        )

    if truth.blocked_reasons:
        return Readiness(
            action_id=action.action_id,
            readiness_state="blocked",
            checked_at_state_version=truth.state_version,
            reasons=truth.blocked_reasons,
        )

    if not truth.direction_ok and policy.direction_sensitive:
        return Readiness(
            action_id=action.action_id,
            readiness_state="invalidated",
            checked_at_state_version=truth.state_version,
            reasons=("current direction no longer supports this action",),
        )

    if truth.truth_mismatch:
        return Readiness(
            action_id=action.action_id,
            readiness_state="escalated",
            checked_at_state_version=truth.state_version,
            reasons=("truth mismatch requires operator judgment before start",),
        )

    if truth.degraded_truth and (policy.destructive or policy.protected_surface or policy.direction_sensitive):
        return Readiness(
            action_id=action.action_id,
            readiness_state="escalated",
            checked_at_state_version=truth.state_version,
            reasons=("degraded truth requires escalation for this protected action",),
        )

    if not truth.target_available:
        return Readiness(
            action_id=action.action_id,
            readiness_state="blocked",
            checked_at_state_version=truth.state_version,
            reasons=("target is not currently available",),
        )

    if policy.protected_surface:
        cautions.append("action touches a protected surface")
    if policy.destructive:
        cautions.append("action is destructive or hard to reverse")
    if policy.direction_sensitive:
        cautions.append("action remains direction-sensitive")

    return Readiness(
        action_id=action.action_id,
        readiness_state="ready_with_cautions" if cautions else "ready",
        checked_at_state_version=truth.state_version,
        cautions=tuple(cautions),
    )


def _map_outcome(
    *,
    policy_verdict: PolicyVerdict,
    readiness: Readiness,
) -> GovernanceOutcome:
    if readiness.readiness_state in {"ready", "ready_with_cautions"} and policy_verdict in {
        "allowed",
        "approval_required",
    }:
        return "allowed_now"
    if readiness.readiness_state == "pending_approval":
        return "approval_required"
    if readiness.readiness_state == "pending_revalidation":
        return "deferred_pending_revalidation"
    if readiness.readiness_state == "invalidated":
        return "invalidated"
    if readiness.readiness_state == "escalated":
        return "escalated"
    return "blocked"


def _scope_matches(action_scope: Scope, truth_scope: Scope) -> bool:
    if action_scope.project_id != truth_scope.project_id:
        return False
    if action_scope.work_unit_id != truth_scope.work_unit_id:
        return False
    if action_scope.run_id != truth_scope.run_id:
        return False
    return True
