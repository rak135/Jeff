"""Interface-owned live context and governance-default helpers."""

from __future__ import annotations

from jeff.cognitive import ContextPackage, assemble_context_package
from jeff.core.schemas import Scope
from jeff.governance import Approval, CurrentTruthSnapshot, Policy

from ..models import InterfaceContext
from .selection_review_runtime import _selection_review_for_context


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


from jeff.cognitive.types import TriggerInput