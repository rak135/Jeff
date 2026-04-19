"""Orchestration-local routing summaries for continuation boundaries."""

from __future__ import annotations

from jeff.cognitive import PlanArtifact, ProposalResult, ResearchArtifact, SelectionBridgeResult, SelectionResult
from jeff.cognitive.post_selection import (
    PlannedActionBridgeResult,
    ProposalSupportPackage,
    ResearchDecisionSupportHandoff,
    ResearchOutputSufficiencyResult,
)
from jeff.cognitive.proposal import ProposalGenerationBridgeResult, ProposalInputPackage
from jeff.core.schemas import Scope

from ..routing import RoutingDecision


def build_research_post_selection_prefix(
    *,
    research: ResearchArtifact,
    decision_support_handoff: ResearchDecisionSupportHandoff,
    proposal_support_package: ProposalSupportPackage,
    proposal_input_package: ProposalInputPackage,
    proposal_generation_bridge_result: ProposalGenerationBridgeResult,
    proposal_output: ProposalResult,
    selection_bridge_result: SelectionBridgeResult,
    selection_output: SelectionResult,
) -> str:
    disposition_summary = (
        f"selected proposal {selection_output.selected_proposal_id}"
        if selection_output.selected_proposal_id is not None
        else f"returned explicit non-selection outcome {selection_output.disposition}"
    )
    return (
        f"Research entered and produced a bounded research artifact for question '{research.question}' "
        f"with {len(research.findings)} finding(s) across {len(research.source_ids)} source(s). "
        "Sufficiency evaluation: decision_support_ready. "
        f"Decision-support handoff ready: {decision_support_handoff.handoff_id} with "
        f"{len(decision_support_handoff.supported_findings)} supported finding(s), "
        f"{len(decision_support_handoff.inference_points)} inference point(s), "
        f"{len(decision_support_handoff.uncertainty_points)} uncertainty point(s), and "
        f"{len(decision_support_handoff.provenance_refs)} provenance ref(s). "
        f"Proposal-support package ready: {proposal_support_package.package_id} with "
        f"{len(proposal_support_package.supported_findings)} supported finding(s), "
        f"{len(proposal_support_package.inference_points)} inference point(s), "
        f"{len(proposal_support_package.uncertainty_points)} uncertainty point(s), and "
        f"{len(proposal_support_package.provenance_refs)} provenance ref(s). "
        f"Proposal-input package ready: {proposal_input_package.package_id} with "
        f"{len(proposal_input_package.supported_findings)} supported finding(s), "
        f"{len(proposal_input_package.inference_points)} inference point(s), "
        f"{len(proposal_input_package.uncertainty_points)} uncertainty point(s), and "
        f"{len(proposal_input_package.provenance_refs)} provenance ref(s). "
        f"Proposal generation then ran via {proposal_generation_bridge_result.bridge_id}. "
        f"Proposal output ready: {proposal_output.request_id} with {proposal_output.proposal_count} serious "
        f"option(s). Selection then ran via {selection_bridge_result.bridge_id} and preserved selection output "
        f"that {disposition_summary}. Orchestrator then reused the existing downstream post-selection chain "
        "from that preserved SelectionResult. "
    )


def route_planning_boundary(
    *,
    plan: PlanArtifact,
    scope: Scope,
    bridge_result: PlannedActionBridgeResult | None = None,
) -> RoutingDecision:
    proposal_summary = (
        "the selected proposal"
        if plan.selected_proposal_id is None
        else f"proposal {plan.selected_proposal_id}"
    )
    bridge_reason = (
        "no repo-local plan-to-action bridge is implemented in the current slice."
        if bridge_result is None
        else f"no Action could be formed from the current plan output because {bridge_result.no_action_reason}"
    )
    return RoutingDecision(
        route_kind="hold",
        routed_outcome="planning",
        scope=scope,
        source_stage="planning",
        reason_summary=(
            f"Planning entered and produced a bounded plan artifact for {proposal_summary} "
            f"with {len(plan.intended_steps)} intended step(s). Planning remains support-only; "
            "no governance evaluation occurred, no action permission exists, no execution occurred, "
            f"and {bridge_reason}"
        ),
    )


def route_research_boundary(
    *,
    research: ResearchArtifact,
    sufficiency_result: ResearchOutputSufficiencyResult,
    decision_support_handoff: ResearchDecisionSupportHandoff | None,
    proposal_support_package: ProposalSupportPackage | None,
    proposal_input_package: ProposalInputPackage | None,
    proposal_generation_bridge_result: ProposalGenerationBridgeResult | None,
    proposal_output: ProposalResult | None,
    selection_bridge_result: SelectionBridgeResult | None,
    selection_output: SelectionResult | None,
    selection_bridge_reason: str | None,
    scope: Scope,
) -> RoutingDecision:
    if sufficiency_result.sufficient_for_downstream_use:
        if decision_support_handoff is None:
            raise ValueError("decision-support-ready research routing requires ResearchDecisionSupportHandoff")
        if proposal_support_package is None:
            raise ValueError("decision-support-ready research routing requires ProposalSupportPackage")
        if proposal_input_package is None:
            raise ValueError("decision-support-ready research routing requires ProposalInputPackage")
        if proposal_generation_bridge_result is None:
            raise ValueError("decision-support-ready research routing requires ProposalGenerationBridgeResult")
        if proposal_output is not None:
            if selection_output is not None:
                if selection_bridge_result is None:
                    raise ValueError("selection-output-ready research routing requires SelectionBridgeResult")
                disposition_summary = (
                    f"selected proposal {selection_output.selected_proposal_id}"
                    if selection_output.selected_proposal_id is not None
                    else f"returned explicit non-selection outcome {selection_output.disposition}"
                )
                return RoutingDecision(
                    route_kind="hold",
                    routed_outcome="selection_output_ready",
                    scope=scope,
                    source_stage="research",
                    reason_summary=(
                        f"Research entered and produced a bounded research artifact for question '{research.question}' "
                        f"with {len(research.findings)} finding(s) across {len(research.source_ids)} source(s). "
                        "Sufficiency evaluation: decision_support_ready. "
                        f"Decision-support handoff ready: {decision_support_handoff.handoff_id} with "
                        f"{len(decision_support_handoff.supported_findings)} supported finding(s), "
                        f"{len(decision_support_handoff.inference_points)} inference point(s), "
                        f"{len(decision_support_handoff.uncertainty_points)} uncertainty point(s), and "
                        f"{len(decision_support_handoff.provenance_refs)} provenance ref(s). "
                        f"Proposal-support package ready: {proposal_support_package.package_id} with "
                        f"{len(proposal_support_package.supported_findings)} supported finding(s), "
                        f"{len(proposal_support_package.inference_points)} inference point(s), "
                        f"{len(proposal_support_package.uncertainty_points)} uncertainty point(s), and "
                        f"{len(proposal_support_package.provenance_refs)} provenance ref(s). "
                        f"Proposal-input package ready: {proposal_input_package.package_id} with "
                        f"{len(proposal_input_package.supported_findings)} supported finding(s), "
                        f"{len(proposal_input_package.inference_points)} inference point(s), "
                        f"{len(proposal_input_package.uncertainty_points)} uncertainty point(s), and "
                        f"{len(proposal_input_package.provenance_refs)} provenance ref(s). "
                        f"Proposal generation then ran via {proposal_generation_bridge_result.bridge_id}. "
                        f"Proposal output ready: {proposal_output.request_id} with {proposal_output.proposal_count} "
                        f"serious option(s). Selection then ran via {selection_bridge_result.bridge_id} and "
                        f"preserved selection output that {disposition_summary}. Selection output remains "
                        "selection-only; it is not action, not permission, not governance, and not execution. "
                        "no governance evaluation occurred, no action permission exists, no execution occurred, "
                        "and no automatic continuation into action, governance, or execution is implemented in the "
                        "current slice."
                    ),
                )
            if selection_bridge_reason is not None:
                return RoutingDecision(
                    route_kind="hold",
                    routed_outcome="proposal_output_ready",
                    scope=scope,
                    source_stage="research",
                    reason_summary=(
                        f"Research entered and produced a bounded research artifact for question '{research.question}' "
                        f"with {len(research.findings)} finding(s) across {len(research.source_ids)} source(s). "
                        "Sufficiency evaluation: decision_support_ready. "
                        f"Decision-support handoff ready: {decision_support_handoff.handoff_id} with "
                        f"{len(decision_support_handoff.supported_findings)} supported finding(s), "
                        f"{len(decision_support_handoff.inference_points)} inference point(s), "
                        f"{len(decision_support_handoff.uncertainty_points)} uncertainty point(s), and "
                        f"{len(decision_support_handoff.provenance_refs)} provenance ref(s). "
                        f"Proposal-support package ready: {proposal_support_package.package_id} with "
                        f"{len(proposal_support_package.supported_findings)} supported finding(s), "
                        f"{len(proposal_support_package.inference_points)} inference point(s), "
                        f"{len(proposal_support_package.uncertainty_points)} uncertainty point(s), and "
                        f"{len(proposal_support_package.provenance_refs)} provenance ref(s). "
                        f"Proposal-input package ready: {proposal_input_package.package_id} with "
                        f"{len(proposal_input_package.supported_findings)} supported finding(s), "
                        f"{len(proposal_input_package.inference_points)} inference point(s), "
                        f"{len(proposal_input_package.uncertainty_points)} uncertainty point(s), and "
                        f"{len(proposal_input_package.provenance_refs)} provenance ref(s). "
                        f"Proposal generation then ran via {proposal_generation_bridge_result.bridge_id}. "
                        f"Proposal output ready: {proposal_output.request_id} with {proposal_output.proposal_count} "
                        f"serious option(s). No lawful selection output exists because {selection_bridge_reason}. "
                        "Proposal output remains proposal-only at the current truthful boundary; it is not selection, "
                        "not action, not permission, not governance, and not execution. No governance evaluation "
                        "occurred, no action permission exists, no execution occurred, and no automatic continuation "
                        "into action, governance, or execution is implemented in the current slice."
                    ),
                )
            return RoutingDecision(
                route_kind="hold",
                routed_outcome="proposal_output_ready",
                scope=scope,
                source_stage="research",
                reason_summary=(
                    f"Research entered and produced a bounded research artifact for question '{research.question}' "
                    f"with {len(research.findings)} finding(s) across {len(research.source_ids)} source(s). "
                    "Sufficiency evaluation: decision_support_ready. "
                    f"Decision-support handoff ready: {decision_support_handoff.handoff_id} with "
                    f"{len(decision_support_handoff.supported_findings)} supported finding(s), "
                    f"{len(decision_support_handoff.inference_points)} inference point(s), "
                    f"{len(decision_support_handoff.uncertainty_points)} uncertainty point(s), and "
                    f"{len(decision_support_handoff.provenance_refs)} provenance ref(s). "
                    f"Proposal-support package ready: {proposal_support_package.package_id} with "
                    f"{len(proposal_support_package.supported_findings)} supported finding(s), "
                    f"{len(proposal_support_package.inference_points)} inference point(s), "
                    f"{len(proposal_support_package.uncertainty_points)} uncertainty point(s), and "
                    f"{len(proposal_support_package.provenance_refs)} provenance ref(s). "
                    f"Proposal-input package ready: {proposal_input_package.package_id} with "
                    f"{len(proposal_input_package.supported_findings)} supported finding(s), "
                    f"{len(proposal_input_package.inference_points)} inference point(s), "
                    f"{len(proposal_input_package.uncertainty_points)} uncertainty point(s), and "
                    f"{len(proposal_input_package.provenance_refs)} provenance ref(s). "
                    f"Proposal generation then ran via {proposal_generation_bridge_result.bridge_id}. "
                    f"Proposal output ready: {proposal_output.request_id} with {proposal_output.proposal_count} "
                    "serious option(s). Proposal output remains proposal-only; it is not selection, not action, "
                    "not permission, not governance, and not execution. "
                    "No selection occurred after research, no governance evaluation occurred, no action permission "
                    "exists, no execution occurred, and no automatic continuation into selection, action, "
                    "governance, or execution is implemented in the current slice."
                ),
            )
        return RoutingDecision(
            route_kind="hold",
            routed_outcome="proposal_input_boundary",
            scope=scope,
            source_stage="research",
            reason_summary=(
                f"Research entered and produced a bounded research artifact for question '{research.question}' "
                f"with {len(research.findings)} finding(s) across {len(research.source_ids)} source(s). "
                "Sufficiency evaluation: decision_support_ready. "
                f"Decision-support handoff ready: {decision_support_handoff.handoff_id} with "
                f"{len(decision_support_handoff.supported_findings)} supported finding(s), "
                f"{len(decision_support_handoff.inference_points)} inference point(s), "
                f"{len(decision_support_handoff.uncertainty_points)} uncertainty point(s), and "
                f"{len(decision_support_handoff.provenance_refs)} provenance ref(s). "
                f"Proposal-support package ready: {proposal_support_package.package_id} with "
                f"{len(proposal_support_package.supported_findings)} supported finding(s), "
                f"{len(proposal_support_package.inference_points)} inference point(s), "
                f"{len(proposal_support_package.uncertainty_points)} uncertainty point(s), and "
                f"{len(proposal_support_package.provenance_refs)} provenance ref(s). "
                f"Proposal-input package ready: {proposal_input_package.package_id} with "
                f"{len(proposal_input_package.supported_findings)} supported finding(s), "
                f"{len(proposal_input_package.inference_points)} inference point(s), "
                f"{len(proposal_input_package.uncertainty_points)} uncertainty point(s), and "
                f"{len(proposal_input_package.provenance_refs)} provenance ref(s). "
                f"Proposal generation did not produce lawful proposal output because "
                f"{proposal_generation_bridge_result.no_generation_reason}. "
                "The preserved proposal-input package remains support-only at the proposal-input boundary; it is "
                "not proposal output, not selection, not action, not permission, not governance, and not "
                "execution. No selection occurred after research, no governance evaluation occurred, no action "
                "permission exists, no execution occurred, and no automatic continuation into selection, action, "
                "governance, or execution is implemented in the current slice."
            ),
        )

    unresolved_items = "; ".join(sufficiency_result.unresolved_items)
    contradiction_note = (
        " Contradictions remain visible and unresolved."
        if sufficiency_result.contradictions_present
        else ""
    )
    return RoutingDecision(
        route_kind="hold",
        routed_outcome="research_followup",
        scope=scope,
        source_stage="research",
        reason_summary=(
            f"Research entered and produced a bounded research artifact for question '{research.question}' "
            f"with {len(research.findings)} finding(s) across {len(research.source_ids)} source(s). "
            "Sufficiency evaluation: more_research_needed. Current research is not yet sufficient for bounded "
            f"downstream use because these unresolved items remain: {unresolved_items}.{contradiction_note} "
            "Research remains support-only; no governance evaluation occurred, no action permission exists, "
            "no execution occurred, and Jeff does not auto-loop into more research or any downstream action in "
            "the current slice."
        ),
    )
