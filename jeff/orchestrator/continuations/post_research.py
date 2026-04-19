"""Orchestration-local continuation helpers after Research output exists."""

from __future__ import annotations

from typing import TYPE_CHECKING, Mapping

from jeff.cognitive import ContextPackage, ResearchArtifact, SelectionBridgeError
from jeff.cognitive.post_selection import (
    ProposalSupportPackage,
    ResearchDecisionSupportHandoff,
    ResearchDecisionSupportRequest,
    ResearchOutputSufficiencyRequest,
    ResearchOutputSufficiencyResult,
    build_research_decision_support_handoff,
    consume_research_for_proposal_support,
    evaluate_research_output_sufficiency,
)
from jeff.cognitive.proposal import (
    ProposalGenerationBridgeRequest,
    ProposalGenerationBridgeResult,
    ProposalInputPackage,
    ProposalSupportConsumerRequest,
    build_and_run_proposal_generation,
    consume_proposal_support_package,
)
from jeff.cognitive.post_selection import ResearchProposalConsumerRequest
from jeff.core.schemas import Scope

from ..flows import FlowFamily, StageName
from ..validation import ValidationResult
from . import (
    PROPOSAL_GENERATION_BRIDGE_OUTPUT_KEY,
    PROPOSAL_INPUT_OUTPUT_KEY,
    PROPOSAL_OUTPUT_OUTPUT_KEY,
    RESEARCH_DECISION_SUPPORT_OUTPUT_KEY,
    RESEARCH_PROPOSAL_SUPPORT_OUTPUT_KEY,
    RESEARCH_SUFFICIENCY_OUTPUT_KEY,
    SELECTION_BRIDGE_OUTPUT_KEY,
    SELECTION_OUTPUT_OUTPUT_KEY,
)
from .boundary_routes import route_research_boundary

if TYPE_CHECKING:
    from ..runner import FlowRunResult, HybridSelectionStageConfig, StageHandler


def evaluate_research_output(
    *,
    flow_id: str,
    research_output: object,
    evaluate_research_output_sufficiency_fn=evaluate_research_output_sufficiency,
) -> ResearchOutputSufficiencyResult:
    if not isinstance(research_output, ResearchArtifact):
        raise TypeError("research output sufficiency bridge requires ResearchArtifact output from the research stage")

    return evaluate_research_output_sufficiency_fn(
        ResearchOutputSufficiencyRequest(
            request_id=f"{flow_id}:research-output-sufficiency",
            research_artifact=research_output,
        )
    )


def build_research_decision_support(
    *,
    flow_id: str,
    research_output: object,
    sufficiency_result: ResearchOutputSufficiencyResult,
    build_research_decision_support_handoff_fn=build_research_decision_support_handoff,
) -> ResearchDecisionSupportHandoff:
    if not isinstance(research_output, ResearchArtifact):
        raise TypeError("research decision support bridge requires ResearchArtifact output from the research stage")

    return build_research_decision_support_handoff_fn(
        ResearchDecisionSupportRequest(
            request_id=f"{flow_id}:research-decision-support",
            research_artifact=research_output,
            research_sufficiency_result=sufficiency_result,
        )
    )


def consume_research_proposal_support(
    *,
    flow_id: str,
    decision_support_handoff: ResearchDecisionSupportHandoff,
    consume_research_for_proposal_support_fn=consume_research_for_proposal_support,
) -> ProposalSupportPackage:
    return consume_research_for_proposal_support_fn(
        ResearchProposalConsumerRequest(
            request_id=f"{flow_id}:research-proposal-support",
            research_decision_support_handoff=decision_support_handoff,
        )
    )


def build_proposal_input_package(
    *,
    flow_id: str,
    proposal_support_package: ProposalSupportPackage,
    consume_proposal_support_package_fn=consume_proposal_support_package,
) -> ProposalInputPackage:
    return consume_proposal_support_package_fn(
        ProposalSupportConsumerRequest(
            request_id=f"{flow_id}:proposal-input",
            proposal_support_package=proposal_support_package,
        )
    )


def build_and_run_proposal_generation_from_research_followup(
    *,
    flow_id: str,
    proposal_input_package: ProposalInputPackage,
    context_output: object | None,
    research_output: object,
    research_handler: StageHandler | HybridSelectionStageConfig,
    build_and_run_proposal_generation_fn=build_and_run_proposal_generation,
) -> ProposalGenerationBridgeResult:
    if context_output is not None and not isinstance(context_output, ContextPackage):
        raise TypeError("proposal generation bridge requires ContextPackage output from the context stage")
    if not isinstance(research_output, ResearchArtifact):
        raise TypeError("proposal generation bridge requires ResearchArtifact output from the research stage")

    infrastructure_services = getattr(
        research_handler,
        "proposal_generation_infrastructure_services",
        getattr(research_handler, "infrastructure_services", None),
    )
    bounded_objective = getattr(
        research_handler,
        "proposal_generation_objective",
        getattr(research_handler, "bounded_objective", None),
    )
    visible_constraints = getattr(research_handler, "proposal_generation_visible_constraints", ())
    adapter_id = getattr(research_handler, "proposal_generation_adapter_id", None)

    return build_and_run_proposal_generation_fn(
        ProposalGenerationBridgeRequest(
            request_id=f"{flow_id}:proposal-generation-bridge",
            proposal_input_package=proposal_input_package,
            context_package=context_output,
            research_artifact=research_output,
            infrastructure_services=infrastructure_services,
            bounded_objective=bounded_objective,
            visible_constraints=visible_constraints,
            adapter_id=adapter_id,
        )
    )


def handle_post_research_continuation(
    *,
    flow_id: str,
    lifecycle,
    outputs: dict[StageName, object],
    events,
    flow_family: FlowFamily,
    scope: Scope,
    stage_handlers: Mapping[StageName, StageHandler | HybridSelectionStageConfig],
    research_output: object,
    finish_with_validation_failure,
    finish_with_routing,
    evaluate_research_output_sufficiency_fn,
    build_research_decision_support_handoff_fn,
    consume_research_for_proposal_support_fn,
    consume_proposal_support_package_fn,
    build_and_run_proposal_generation_from_research_followup_fn,
    build_and_run_selection_from_proposal_output_fn,
    continue_from_research_selection_output_fn,
) -> FlowRunResult:
    try:
        research_sufficiency = evaluate_research_output_sufficiency_fn(
            flow_id=flow_id,
            research_output=research_output,
        )
    except Exception as exc:
        return finish_with_validation_failure(
            lifecycle=lifecycle,
            outputs=outputs,
            events=events,
            flow_family=flow_family,
            scope=scope,
            stage="action",
            validation=ValidationResult(
                valid=False,
                code="research_output_sufficiency_bridge_failed",
                reason=str(exc),
            ),
        )

    outputs[RESEARCH_SUFFICIENCY_OUTPUT_KEY] = research_sufficiency
    decision_support_handoff = None
    proposal_support_package = None
    proposal_input_package = None
    proposal_generation_bridge_result = None
    proposal_output = None
    selection_bridge_result = None
    selection_output = None
    selection_bridge_reason = None
    if research_sufficiency.sufficient_for_downstream_use:
        try:
            decision_support_handoff = build_research_decision_support_handoff_fn(
                flow_id=flow_id,
                research_output=research_output,
                sufficiency_result=research_sufficiency,
            )
        except Exception as exc:
            return finish_with_validation_failure(
                lifecycle=lifecycle,
                outputs=outputs,
                events=events,
                flow_family=flow_family,
                scope=scope,
                stage="action",
                validation=ValidationResult(
                    valid=False,
                    code="research_to_decision_support_bridge_failed",
                    reason=str(exc),
                ),
            )
        outputs[RESEARCH_DECISION_SUPPORT_OUTPUT_KEY] = decision_support_handoff
        try:
            proposal_support_package = consume_research_for_proposal_support_fn(
                flow_id=flow_id,
                decision_support_handoff=decision_support_handoff,
            )
        except Exception as exc:
            return finish_with_validation_failure(
                lifecycle=lifecycle,
                outputs=outputs,
                events=events,
                flow_family=flow_family,
                scope=scope,
                stage="action",
                validation=ValidationResult(
                    valid=False,
                    code="research_to_proposal_consumer_failed",
                    reason=str(exc),
                ),
            )
        outputs[RESEARCH_PROPOSAL_SUPPORT_OUTPUT_KEY] = proposal_support_package
        try:
            proposal_input_package = consume_proposal_support_package_fn(
                flow_id=flow_id,
                proposal_support_package=proposal_support_package,
            )
        except Exception as exc:
            return finish_with_validation_failure(
                lifecycle=lifecycle,
                outputs=outputs,
                events=events,
                flow_family=flow_family,
                scope=scope,
                stage="action",
                validation=ValidationResult(
                    valid=False,
                    code="proposal_support_package_consumer_failed",
                    reason=str(exc),
                ),
            )
        outputs[PROPOSAL_INPUT_OUTPUT_KEY] = proposal_input_package
        try:
            proposal_generation_bridge_result = build_and_run_proposal_generation_from_research_followup_fn(
                flow_id=flow_id,
                proposal_input_package=proposal_input_package,
                context_output=outputs.get("context"),
                research_output=research_output,
                research_handler=stage_handlers["research"],
            )
        except Exception as exc:
            return finish_with_validation_failure(
                lifecycle=lifecycle,
                outputs=outputs,
                events=events,
                flow_family=flow_family,
                scope=scope,
                stage="action",
                validation=ValidationResult(
                    valid=False,
                    code="proposal_generation_bridge_failed",
                    reason=str(exc),
                ),
            )
        outputs[PROPOSAL_GENERATION_BRIDGE_OUTPUT_KEY] = proposal_generation_bridge_result
        if proposal_generation_bridge_result.proposal_result is not None:
            proposal_output = proposal_generation_bridge_result.proposal_result
            outputs[PROPOSAL_OUTPUT_OUTPUT_KEY] = proposal_output
            try:
                selection_bridge_result = build_and_run_selection_from_proposal_output_fn(
                    flow_id=flow_id,
                    proposal_output=proposal_output,
                    research_handler=stage_handlers["research"],
                )
            except SelectionBridgeError as exc:
                selection_bridge_reason = str(exc)
            else:
                outputs[SELECTION_BRIDGE_OUTPUT_KEY] = selection_bridge_result
                selection_output = selection_bridge_result.selection_result
                outputs[SELECTION_OUTPUT_OUTPUT_KEY] = selection_output

    if selection_output is not None:
        return continue_from_research_selection_output_fn(
            flow_id=flow_id,
            lifecycle=lifecycle,
            outputs=outputs,
            events=events,
            flow_family=flow_family,
            scope=scope,
            stage_handlers=stage_handlers,
            research=research_output,
            decision_support_handoff=decision_support_handoff,
            proposal_support_package=proposal_support_package,
            proposal_input_package=proposal_input_package,
            proposal_generation_bridge_result=proposal_generation_bridge_result,
            proposal_output=proposal_output,
            selection_bridge_result=selection_bridge_result,
            selection_output=selection_output,
        )

    return finish_with_routing(
        lifecycle=lifecycle,
        outputs=outputs,
        events=events,
        routing=route_research_boundary(
            research=research_output,
            sufficiency_result=research_sufficiency,
            decision_support_handoff=decision_support_handoff,
            proposal_support_package=proposal_support_package,
            proposal_input_package=proposal_input_package,
            proposal_generation_bridge_result=proposal_generation_bridge_result,
            proposal_output=proposal_output,
            selection_bridge_result=selection_bridge_result,
            selection_output=selection_output,
            selection_bridge_reason=selection_bridge_reason,
            scope=scope,
        ),
        flow_family=flow_family,
    )
