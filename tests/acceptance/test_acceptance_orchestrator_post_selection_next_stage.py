from jeff.cognitive import (
    PlanArtifact,
    ProposalResult,
    ProposalResultOption,
    ResearchArtifact,
    ResearchFinding,
    SelectionResult,
    assemble_context_package,
)
from jeff.cognitive.post_selection import OperatorSelectionOverrideRequest, build_operator_selection_override
from jeff.cognitive.types import PlanStep, TriggerInput
from jeff.contracts import Action
from jeff.core.schemas import Scope
from jeff.core.state import bootstrap_global_state
from jeff.core.transition import TransitionRequest, apply_transition
from jeff.governance import CurrentTruthSnapshot, Policy, evaluate_action_entry
from jeff.infrastructure import (
    AdapterFactoryConfig,
    AdapterProviderKind,
    ModelAdapterRuntimeConfig,
    PurposeOverrides,
    build_infrastructure_services,
)
from jeff.orchestrator import run_flow


def test_acceptance_selected_planning_path_reaches_governance_when_plan_yields_one_bounded_action() -> None:
    scope = _scope()
    result = run_flow(
        flow_id="flow-planning-acceptance",
        flow_family="conditional_planning_insertion",
        scope=scope,
        stage_handlers=_conditional_stage_handlers(
            scope,
            proposal_type_one="planning_insertion",
            proposal_type_two=None,
            bridgeable_plan=True,
            planning_governance_truth_state_version=0,
            selection_result=SelectionResult(
                selection_id="selection-planning-1",
                considered_proposal_ids=("proposal-1",),
                selected_proposal_id="proposal-1",
                rationale="The bounded work should enter planning before any further downstream continuation.",
            ),
        ),
    )

    assert result.lifecycle.lifecycle_state == "waiting"
    assert result.lifecycle.current_stage == "governance"
    assert result.routing_decision is not None
    assert result.routing_decision.source_stage == "governance"
    assert "planning" in result.outputs
    assert isinstance(result.outputs["planning"], PlanArtifact)
    assert "action" in result.outputs
    assert result.outputs["action"].intent_summary == "Apply the bounded implementation"
    assert "governance" in result.outputs
    assert result.outputs["governance"].allowed_now is False
    assert str(result.outputs["action"].action_id) != "action-1"
    assert [event.stage for event in result.events if event.event_type == "stage_entered"][:5] == [
        "context",
        "proposal",
        "selection",
        "planning",
        "action",
    ]


def test_acceptance_planning_result_stays_explicitly_non_authorizing() -> None:
    scope = _scope()
    result = run_flow(
        flow_id="flow-planning-non-authorizing",
        flow_family="conditional_planning_insertion",
        scope=scope,
        stage_handlers=_conditional_stage_handlers(
            scope,
            proposal_type_one="planning_insertion",
            proposal_type_two=None,
            selection_result=SelectionResult(
                selection_id="selection-planning-2",
                considered_proposal_ids=("proposal-1",),
                selected_proposal_id="proposal-1",
                rationale="Planning is the truthful next support stage.",
            ),
        ),
    )

    assert result.routing_decision is not None
    assert "planning" in result.outputs
    assert "no Action could be formed from the current plan output because" in result.routing_decision.reason_summary
    assert "no governance evaluation occurred" in result.routing_decision.reason_summary
    assert "no action permission exists" in result.routing_decision.reason_summary
    assert "no execution occurred" in result.routing_decision.reason_summary
    assert "allowed_now" not in result.routing_decision.reason_summary
    assert "approval" not in result.routing_decision.reason_summary


def test_acceptance_operator_override_can_switch_whether_planning_branch_reaches_governance() -> None:
    scope = _scope()
    selection_result = SelectionResult(
        selection_id="selection-override-1",
        considered_proposal_ids=("proposal-1", "proposal-2"),
        selected_proposal_id="proposal-1",
        rationale="The original Selection result points at the direct-action option.",
    )
    operator_override = build_operator_selection_override(
        OperatorSelectionOverrideRequest(
            request_id="override-request-1",
            selection_result=selection_result,
            chosen_proposal_id="proposal-2",
            operator_rationale="Use the already considered planning-oriented option instead.",
        )
    )

    without_override = run_flow(
        flow_id="flow-without-override",
        flow_family="conditional_planning_insertion",
        scope=scope,
        stage_handlers=_conditional_stage_handlers(
            scope,
            proposal_type_one="direct_action",
            proposal_type_two="planning_insertion",
            bridgeable_plan=True,
            selection_result=selection_result,
        ),
    )
    with_override = run_flow(
        flow_id="flow-with-override",
        flow_family="conditional_planning_insertion",
        scope=scope,
        stage_handlers=_conditional_stage_handlers(
            scope,
            proposal_type_one="direct_action",
            proposal_type_two="planning_insertion",
            bridgeable_plan=True,
            plan_selected_proposal_id="proposal-2",
            planning_governance_truth_state_version=0,
            selection_result=selection_result,
        ),
        operator_override=operator_override,
    )

    assert without_override.lifecycle.current_stage == "governance"
    assert without_override.routing_decision is not None
    assert without_override.routing_decision.routed_outcome == "approval_required"
    assert "planning" not in without_override.outputs
    assert "action" in without_override.outputs
    assert "governance" in without_override.outputs

    assert with_override.lifecycle.current_stage == "governance"
    assert with_override.routing_decision is not None
    assert with_override.routing_decision.source_stage == "governance"
    assert "planning" in with_override.outputs
    assert "action" in with_override.outputs
    assert with_override.outputs["action"].intent_summary == "Apply the bounded implementation"
    assert "governance" in with_override.outputs


def test_acceptance_direct_action_path_still_bypasses_planning() -> None:
    scope = _scope()
    result = run_flow(
        flow_id="flow-direct-action-bypass",
        flow_family="conditional_planning_insertion",
        scope=scope,
        stage_handlers=_conditional_stage_handlers(
            scope,
            proposal_type_one="direct_action",
            proposal_type_two=None,
            bridgeable_plan=True,
            selection_result=SelectionResult(
                selection_id="selection-direct-1",
                considered_proposal_ids=("proposal-1",),
                selected_proposal_id="proposal-1",
                rationale="The direct-action path stays the bounded next move here.",
            ),
        ),
    )

    assert result.lifecycle.lifecycle_state == "waiting"
    assert result.lifecycle.current_stage == "governance"
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "approval_required"
    assert "planning" not in result.outputs
    assert "action" in result.outputs
    assert str(result.outputs["action"].action_id) == "action-1"
    assert "governance" in result.outputs


def test_acceptance_selected_clarify_path_enters_real_research_continuation_and_reaches_next_lawful_boundary() -> None:
    scope = _scope()
    result = run_flow(
        flow_id="flow-clarify",
        flow_family="conditional_research_followup",
        scope=scope,
        stage_handlers=_research_followup_stage_handlers(
            scope,
            proposal_type_one="clarify",
            proposal_type_two=None,
            sufficient=True,
            selection_result=SelectionResult(
                selection_id="selection-clarify-1",
                considered_proposal_ids=("proposal-1",),
                selected_proposal_id="proposal-1",
                rationale="Clarification is the bounded next move.",
            ),
        ),
    )

    assert result.lifecycle.lifecycle_state == "waiting"
    assert result.lifecycle.current_stage == "research"
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "defer"
    assert result.routing_decision.source_stage == "research"
    assert "Research entered and produced a bounded research artifact" in result.routing_decision.reason_summary
    assert "Sufficiency evaluation: decision_support_ready." in result.routing_decision.reason_summary
    assert "Decision-support handoff ready:" in result.routing_decision.reason_summary
    assert "Proposal-support package ready:" in result.routing_decision.reason_summary
    assert "Proposal-input package ready:" in result.routing_decision.reason_summary
    assert "Proposal generation then ran via" in result.routing_decision.reason_summary
    assert "Proposal output ready:" in result.routing_decision.reason_summary
    assert "Selection then ran via" in result.routing_decision.reason_summary
    assert "reused the existing downstream post-selection chain" in result.routing_decision.reason_summary
    assert "research" in result.outputs
    assert isinstance(result.outputs["research"], ResearchArtifact)
    assert result.outputs["research_output_sufficiency"].downstream_target == "decision_support_ready"
    assert result.outputs["research_decision_support_handoff"].decision_support_ready is True
    assert result.outputs["research_proposal_support_package"].proposal_support_ready is True
    assert result.outputs["proposal_input_package"].proposal_input_ready is True
    assert result.outputs["proposal_generation_bridge_result"].proposal_generation_ran is True
    assert result.outputs["proposal_output"].proposal_count == 1
    assert result.outputs["selection_bridge_result"].selection_ran is True
    assert result.outputs["selection_output"].non_selection_outcome == "defer"
    assert "action" not in result.outputs
    assert "governance" not in result.outputs


def test_acceptance_research_driven_selection_output_can_continue_into_governance() -> None:
    scope = _scope()
    result = run_flow(
        flow_id="flow-research-governance-acceptance",
        flow_family="conditional_research_followup",
        scope=scope,
        stage_handlers=_research_followup_stage_handlers(
            scope,
            proposal_type_one="clarify",
            proposal_type_two=None,
            sufficient=True,
            continued_proposal_type="direct_action",
            selection_result=SelectionResult(
                selection_id="selection-research-governance-1",
                considered_proposal_ids=("proposal-1",),
                selected_proposal_id="proposal-1",
                rationale="Clarification is the bounded next move into real research.",
            ),
        ),
    )

    assert result.lifecycle.lifecycle_state == "waiting"
    assert result.lifecycle.current_stage == "governance"
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "approval_required"
    assert "research" in result.outputs
    assert "proposal_output" in result.outputs
    assert "selection_output" in result.outputs
    assert "action" in result.outputs
    assert "governance" in result.outputs
    assert "reused the existing downstream post-selection chain" in result.routing_decision.reason_summary
    assert "Selection output remained non-authorizing until governance evaluated the formed action" in result.routing_decision.reason_summary


def test_acceptance_research_driven_selection_output_can_continue_into_planning_then_governance() -> None:
    scope = _scope()
    result = run_flow(
        flow_id="flow-research-planning-acceptance",
        flow_family="conditional_research_followup",
        scope=scope,
        stage_handlers=_research_followup_stage_handlers(
            scope,
            proposal_type_one="clarify",
            proposal_type_two=None,
            sufficient=True,
            continued_proposal_type="planning_insertion",
            include_planning=True,
            bridgeable_plan=True,
            governance_truth_state_version=0,
            selection_result=SelectionResult(
                selection_id="selection-research-planning-1",
                considered_proposal_ids=("proposal-1",),
                selected_proposal_id="proposal-1",
                rationale="Clarification is the bounded next move into real research.",
            ),
        ),
    )

    assert result.lifecycle.lifecycle_state == "waiting"
    assert result.lifecycle.current_stage == "governance"
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "approval_required"
    assert "research" in result.outputs
    assert "selection_output" in result.outputs
    assert "planning" in result.outputs
    assert "action" in result.outputs
    assert "governance" in result.outputs
    assert "Planning then continued through the existing plan-to-action bridge" in result.routing_decision.reason_summary


def test_acceptance_insufficient_research_preserves_explicit_new_gaps() -> None:
    scope = _scope()
    result = run_flow(
        flow_id="flow-research-insufficient",
        flow_family="conditional_research_followup",
        scope=scope,
        stage_handlers=_research_followup_stage_handlers(
            scope,
            proposal_type_one="investigate",
            proposal_type_two=None,
            sufficient=False,
            selection_result=SelectionResult(
                selection_id="selection-investigate-2",
                considered_proposal_ids=("proposal-1",),
                selected_proposal_id="proposal-1",
                rationale="Investigation is the truthful next support stage.",
            ),
        ),
    )

    assert result.lifecycle.lifecycle_state == "waiting"
    assert result.lifecycle.current_stage == "research"
    assert result.routing_decision is not None
    assert "Sufficiency evaluation: more_research_needed." in result.routing_decision.reason_summary
    assert (
        "Need a source-backed answer for whether the current export tier still allows the bounded batch path."
        in result.routing_decision.reason_summary
    )
    assert "Current research is not yet sufficient for bounded downstream use" in result.routing_decision.reason_summary
    assert result.outputs["research_output_sufficiency"].downstream_target == "more_research_needed"
    assert "research_decision_support_handoff" not in result.outputs
    assert "research_proposal_support_package" not in result.outputs
    assert "proposal_input_package" not in result.outputs
    assert "selection_output" not in result.outputs
    assert "research" in result.outputs
    assert "action" not in result.outputs
    assert "governance" not in result.outputs


def test_acceptance_research_result_stays_explicitly_non_authorizing() -> None:
    scope = _scope()
    result = run_flow(
        flow_id="flow-research-non-authorizing",
        flow_family="conditional_research_followup",
        scope=scope,
        stage_handlers=_research_followup_stage_handlers(
            scope,
            proposal_type_one="investigate",
            proposal_type_two=None,
            sufficient=True,
            selection_result=SelectionResult(
                selection_id="selection-investigate-1",
                considered_proposal_ids=("proposal-1",),
                selected_proposal_id="proposal-1",
                rationale="Investigation is the truthful next support stage.",
            ),
        ),
    )

    assert result.routing_decision is not None
    assert "decision_support_ready" in result.routing_decision.reason_summary
    assert "Decision-support handoff ready:" in result.routing_decision.reason_summary
    assert "Proposal-support package ready:" in result.routing_decision.reason_summary
    assert "Proposal-input package ready:" in result.routing_decision.reason_summary
    assert "Proposal output ready:" in result.routing_decision.reason_summary
    assert "Selection then ran via" in result.routing_decision.reason_summary
    assert "reused the existing downstream post-selection chain" in result.routing_decision.reason_summary
    assert "Selection output remains non-authorizing" in result.routing_decision.reason_summary
    assert "no execution occurred" in result.routing_decision.reason_summary
    assert "allowed_now" not in result.routing_decision.reason_summary
    assert "approval" not in result.routing_decision.reason_summary


def test_acceptance_operator_override_can_switch_from_governance_path_to_real_research_entry() -> None:
    scope = _scope()
    selection_result = SelectionResult(
        selection_id="selection-override-research-1",
        considered_proposal_ids=("proposal-1", "proposal-2"),
        selected_proposal_id="proposal-1",
        rationale="The original Selection result points at the direct-action option.",
    )
    operator_override = build_operator_selection_override(
        OperatorSelectionOverrideRequest(
            request_id="override-request-research-1",
            selection_result=selection_result,
            chosen_proposal_id="proposal-2",
            operator_rationale="Use the already considered clarify option instead.",
        )
    )

    without_override = run_flow(
        flow_id="flow-without-override-research",
        flow_family="conditional_research_followup",
        scope=scope,
        stage_handlers=_research_followup_stage_handlers(
            scope,
            proposal_type_one="direct_action",
            proposal_type_two="clarify",
            sufficient=True,
            selection_result=selection_result,
        ),
    )
    with_override = run_flow(
        flow_id="flow-with-override-research",
        flow_family="conditional_research_followup",
        scope=scope,
        stage_handlers=_research_followup_stage_handlers(
            scope,
            proposal_type_one="direct_action",
            proposal_type_two="clarify",
            sufficient=True,
            selection_result=selection_result,
        ),
        operator_override=operator_override,
    )

    assert without_override.lifecycle.current_stage == "governance"
    assert without_override.routing_decision is not None
    assert without_override.routing_decision.routed_outcome == "approval_required"
    assert "research" not in without_override.outputs
    assert "action" in without_override.outputs
    assert "governance" in without_override.outputs

    assert with_override.lifecycle.current_stage == "research"
    assert with_override.routing_decision is not None
    assert with_override.routing_decision.routed_outcome == "defer"
    assert with_override.routing_decision.source_stage == "research"
    assert "Sufficiency evaluation: decision_support_ready." in with_override.routing_decision.reason_summary
    assert "Decision-support handoff ready:" in with_override.routing_decision.reason_summary
    assert "Proposal-support package ready:" in with_override.routing_decision.reason_summary
    assert "Proposal-input package ready:" in with_override.routing_decision.reason_summary
    assert "Proposal output ready:" in with_override.routing_decision.reason_summary
    assert "Selection then ran via" in with_override.routing_decision.reason_summary
    assert "reused the existing downstream post-selection chain" in with_override.routing_decision.reason_summary
    assert "research" in with_override.outputs
    assert with_override.outputs["research_decision_support_handoff"].decision_support_ready is True
    assert with_override.outputs["research_proposal_support_package"].proposal_support_ready is True
    assert with_override.outputs["proposal_input_package"].proposal_input_ready is True
    assert with_override.outputs["proposal_output"].proposal_count == 1
    assert with_override.outputs["selection_output"].non_selection_outcome == "defer"
    assert "action" not in with_override.outputs
    assert "governance" not in with_override.outputs


def test_acceptance_continued_selection_output_remains_explicitly_non_authorizing() -> None:
    scope = _scope()
    result = run_flow(
        flow_id="flow-selection-output-non-authorizing",
        flow_family="conditional_research_followup",
        scope=scope,
        stage_handlers=_research_followup_stage_handlers(
            scope,
            proposal_type_one="clarify",
            proposal_type_two=None,
            sufficient=True,
            selection_result=SelectionResult(
                selection_id="selection-output-boundary-1",
                considered_proposal_ids=("proposal-1",),
                selected_proposal_id="proposal-1",
                rationale="Clarification is the bounded next move.",
            ),
        ),
    )

    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "defer"
    assert "reused the existing downstream post-selection chain" in result.routing_decision.reason_summary
    assert "Selection output remains non-authorizing" in result.routing_decision.reason_summary
    assert "no action formed" in result.routing_decision.reason_summary
    assert "no governance evaluation occurred" in result.routing_decision.reason_summary
    assert "no execution occurred" in result.routing_decision.reason_summary


def test_acceptance_recursive_research_followup_is_blocked_truthfully() -> None:
    import jeff.orchestrator.runner as runner_module

    scope = _scope()

    def _selected_clarify(request):
        selection_request = runner_module.SelectionRequest(
            request_id=request.request_id,
            proposal_result=request.proposal_result,
        )
        selection_result = SelectionResult(
            selection_id=request.selection_id,
            considered_proposal_ids=("proposal-1",),
            selected_proposal_id="proposal-1",
            rationale="A lawful preserved selection result may still point at the clarify proposal.",
        )
        return runner_module.SelectionBridgeResult(
            bridge_id=f"proposal-output-to-selection:{request.request_id}",
            proposal_result_id=request.proposal_result.request_id,
            selection_request_built=True,
            selection_ran=True,
            selection_request=selection_request,
            selection_result=selection_result,
            selected_proposal_id="proposal-1",
            selection_disposition="selected",
            no_selection_reason=None,
            summary="Forced lawful clarify selection for anti-loop acceptance coverage.",
        )

    original = runner_module.build_and_run_selection
    runner_module.build_and_run_selection = _selected_clarify
    try:
        result = run_flow(
            flow_id="flow-research-anti-loop-acceptance",
            flow_family="conditional_research_followup",
            scope=scope,
            stage_handlers=_research_followup_stage_handlers(
                scope,
                proposal_type_one="clarify",
                proposal_type_two=None,
                sufficient=True,
                selection_result=SelectionResult(
                    selection_id="selection-research-anti-loop-1",
                    considered_proposal_ids=("proposal-1",),
                    selected_proposal_id="proposal-1",
                    rationale="Clarification is the bounded next move into real research.",
                ),
            ),
        )
    finally:
        runner_module.build_and_run_selection = original

    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "research_followup"
    assert "reused the existing downstream post-selection chain" in result.routing_decision.reason_summary
    assert "does not auto-enter recursive research" in result.routing_decision.reason_summary
    assert "hidden loop" in result.routing_decision.reason_summary
    assert "selection_output" in result.outputs


def test_acceptance_direct_action_path_still_bypasses_research() -> None:
    scope = _scope()
    result = run_flow(
        flow_id="flow-direct-action-research-bypass",
        flow_family="conditional_research_followup",
        scope=scope,
        stage_handlers=_research_followup_stage_handlers(
            scope,
            proposal_type_one="direct_action",
            proposal_type_two=None,
            selection_result=SelectionResult(
                selection_id="selection-direct-research-1",
                considered_proposal_ids=("proposal-1",),
                selected_proposal_id="proposal-1",
                rationale="The direct-action path stays the bounded next move here.",
            ),
        ),
    )

    assert result.lifecycle.lifecycle_state == "waiting"
    assert result.lifecycle.current_stage == "governance"
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "approval_required"
    assert "research" not in result.outputs
    assert "action" in result.outputs
    assert "governance" in result.outputs


def test_acceptance_defer_and_reject_all_stay_truthful_non_execution_paths() -> None:
    scope = _scope()
    reject_all_result = run_flow(
        flow_id="flow-reject-all",
        flow_family="blocked_or_escalation",
        scope=scope,
        stage_handlers=_blocked_stage_handlers(
            scope,
            proposal_type_one="direct_action",
            proposal_type_two=None,
            selection_result=SelectionResult(
                selection_id="selection-reject-all-1",
                considered_proposal_ids=("proposal-1",),
                non_selection_outcome="reject_all",
                rationale="No considered option is lawful enough to continue.",
            ),
        ),
    )
    defer_result = run_flow(
        flow_id="flow-defer",
        flow_family="blocked_or_escalation",
        scope=scope,
        stage_handlers=_blocked_stage_handlers(
            scope,
            proposal_type_one="direct_action",
            proposal_type_two=None,
            selection_result=SelectionResult(
                selection_id="selection-defer-1",
                considered_proposal_ids=("proposal-1",),
                non_selection_outcome="defer",
                rationale="The truthful next step is to defer without execution.",
            ),
        ),
    )

    assert reject_all_result.lifecycle.lifecycle_state == "completed"
    assert reject_all_result.routing_decision is not None
    assert reject_all_result.routing_decision.routed_outcome == "reject_all"
    assert reject_all_result.routing_decision.source_stage == "selection"
    assert "governance" not in reject_all_result.outputs
    assert reject_all_result.lifecycle.lifecycle_state not in {"blocked", "failed"}

    assert defer_result.lifecycle.lifecycle_state == "completed"
    assert defer_result.routing_decision is not None
    assert defer_result.routing_decision.routed_outcome == "defer"
    assert defer_result.routing_decision.source_stage == "selection"
    assert "governance" not in defer_result.outputs
    assert defer_result.lifecycle.lifecycle_state not in {"blocked", "failed"}


def test_acceptance_escalation_path_remains_explicit() -> None:
    scope = _scope()
    result = run_flow(
        flow_id="flow-escalation",
        flow_family="blocked_or_escalation",
        scope=scope,
        stage_handlers=_blocked_stage_handlers(
            scope,
            proposal_type_one="direct_action",
            proposal_type_two=None,
            selection_result=SelectionResult(
                selection_id="selection-escalation-1",
                considered_proposal_ids=("proposal-1",),
                non_selection_outcome="escalate",
                rationale="Operator judgment is still required before any continuation.",
            ),
        ),
    )

    assert result.lifecycle.lifecycle_state == "escalated"
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "escalated"
    assert result.routing_decision.source_stage == "selection"
    assert "explicit escalation surface" in result.routing_decision.reason_summary
    assert "action" not in result.outputs
    assert "governance" not in result.outputs


def _blocked_stage_handlers(
    scope: Scope,
    *,
    proposal_type_one: str,
    proposal_type_two: str | None,
    selection_result: SelectionResult,
) -> dict[str, object]:
    state = _state(scope)

    def context_stage(_):
        return assemble_context_package(
            trigger=TriggerInput(trigger_summary="Exercise acceptance-visible post-selection routing."),
            purpose="proposal support",
            scope=scope,
            state=state,
        )

    def proposal_stage(_context):
        options = [
            ProposalResultOption(
                option_index=1,
                proposal_id="proposal-1",
                proposal_type=proposal_type_one,  # type: ignore[arg-type]
                title="Proposal one",
                why_now="This proposal defines the primary routed branch.",
                summary="Proposal one",
            )
        ]
        if proposal_type_two is not None:
            options.append(
                ProposalResultOption(
                    option_index=2,
                    proposal_id="proposal-2",
                    proposal_type=proposal_type_two,  # type: ignore[arg-type]
                    title="Proposal two",
                    why_now="This proposal exists for override-driven rerouting.",
                    summary="Proposal two",
                )
            )
        return ProposalResult(
            request_id="proposal-request-1",
            scope=scope,
            options=tuple(options),
            scarcity_reason=None if len(options) > 1 else "Only one serious bounded option exists here.",
        )

    def selection_stage(_proposal):
        return selection_result

    def action_stage(_selection):
        return Action(
            action_id="action-1",
            scope=scope,
            intent_summary="Carry the override-resolved direct action path.",
            basis_state_version=3,
        )

    def governance_stage(action):
        return evaluate_action_entry(
            action=action,
            policy=Policy(),
            approval=None,
            truth=CurrentTruthSnapshot(scope=scope, state_version=3),
        )

    return {
        "context": context_stage,
        "proposal": proposal_stage,
        "selection": selection_stage,
        "action": action_stage,
        "governance": governance_stage,
    }


def _conditional_stage_handlers(
    scope: Scope,
    *,
    proposal_type_one: str,
    proposal_type_two: str | None,
    bridgeable_plan: bool = False,
    plan_selected_proposal_id: str | None = None,
    planning_governance_truth_state_version: int = 3,
    selection_result: SelectionResult,
) -> dict[str, object]:
    blocked_handlers = _blocked_stage_handlers(
        scope,
        proposal_type_one=proposal_type_one,
        proposal_type_two=proposal_type_two,
        selection_result=selection_result,
    )

    def planning_stage(_selection):
        selected_proposal_id = (
            selection_result.selected_proposal_id
            if plan_selected_proposal_id is None
            else plan_selected_proposal_id
        )
        if bridgeable_plan:
            return PlanArtifact(
                bounded_objective="Produce the bounded support plan",
                intended_steps=(PlanStep(summary="Apply the bounded implementation"),),
                selected_proposal_id=selected_proposal_id,
            )
        return PlanArtifact(
            bounded_objective="Produce the bounded support plan",
            intended_steps=(
                PlanStep(summary="Review the bounded scope and checkpoints", review_required=True),
                PlanStep(summary="Pause at the planning boundary for a later lawful downstream slice"),
            ),
            selected_proposal_id=selected_proposal_id,
        )

    def unexpected_stage(stage_name: str):
        def _stage(_input):
            raise AssertionError(f"{stage_name} stage should not run in this acceptance routing test")

        return _stage

    return {
        "context": blocked_handlers["context"],
        "proposal": blocked_handlers["proposal"],
        "selection": blocked_handlers["selection"],
        "planning": planning_stage,
        "action": blocked_handlers["action"],
        "governance": lambda action: evaluate_action_entry(
            action=action,
            policy=Policy(approval_required=True),
            approval=None,
            truth=CurrentTruthSnapshot(scope=scope, state_version=planning_governance_truth_state_version),
        ),
        "execution": unexpected_stage("execution"),
        "outcome": unexpected_stage("outcome"),
        "evaluation": unexpected_stage("evaluation"),
        "memory": unexpected_stage("memory"),
        "transition": unexpected_stage("transition"),
    }


def _research_followup_stage_handlers(
    scope: Scope,
    *,
    proposal_type_one: str,
    proposal_type_two: str | None,
    sufficient: bool = True,
    bridgeable_proposal_generation: bool = True,
    continued_proposal_type: str = "clarify",
    include_planning: bool = False,
    bridgeable_plan: bool = False,
    governance_truth_state_version: int = 3,
    selection_result: SelectionResult,
) -> dict[str, object]:
    blocked_handlers = _blocked_stage_handlers(
        scope,
        proposal_type_one=proposal_type_one,
        proposal_type_two=proposal_type_two,
        selection_result=selection_result,
    )

    def research_stage(_selection):
        return ResearchArtifact(
            question="What bounded follow-up research is still needed before any downstream step?",
            summary=(
                "The bounded evidence clarifies the current comparison without granting authority."
                if sufficient
                else "The bounded evidence still leaves one decisive gap unresolved."
            ),
            findings=(
                ResearchFinding(
                    text="A narrow follow-up check can reduce the current uncertainty.",
                    source_refs=("source-1",),
                ),
            ),
            inferences=("Research remains support-only in this flow.",),
            uncertainties=()
            if sufficient
            else ("whether the current export tier still allows the bounded batch path",),
            recommendation="Pause after research until a later lawful downstream slice exists.",
            source_ids=("source-1",),
        )

    def planning_stage(_selection):
        if bridgeable_plan:
            return PlanArtifact(
                bounded_objective="Produce the bounded support plan",
                intended_steps=(PlanStep(summary="Apply the bounded implementation"),),
                selected_proposal_id="proposal-1",
            )
        return PlanArtifact(
            bounded_objective="Produce the bounded support plan",
            intended_steps=(
                PlanStep(summary="Review the bounded scope and checkpoints", review_required=True),
                PlanStep(summary="Pause at the planning boundary for a later lawful downstream slice"),
            ),
            selected_proposal_id="proposal-1",
        )

    if sufficient and bridgeable_proposal_generation:
        research_stage.proposal_generation_infrastructure_services = _proposal_generation_services(
            _one_option_output_text(proposal_type=continued_proposal_type)
        )
        research_stage.proposal_generation_objective = "Frame bounded follow-up options from the preserved research"
        research_stage.proposal_generation_visible_constraints = ("Stay inside the current project scope.",)

    handlers: dict[str, object] = {
        "context": blocked_handlers["context"],
        "proposal": blocked_handlers["proposal"],
        "selection": blocked_handlers["selection"],
        "research": research_stage,
        "action": blocked_handlers["action"],
        "governance": lambda action: evaluate_action_entry(
            action=action,
            policy=Policy(approval_required=True),
            approval=None,
            truth=CurrentTruthSnapshot(scope=scope, state_version=governance_truth_state_version),
        ),
    }
    if include_planning:
        handlers = {
            "context": handlers["context"],
            "proposal": handlers["proposal"],
            "selection": handlers["selection"],
            "research": handlers["research"],
            "planning": planning_stage,
            "action": handlers["action"],
            "governance": handlers["governance"],
        }
    return handlers


def _scope() -> Scope:
    return Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1")


def _proposal_generation_services(output_text: str):
    return build_infrastructure_services(
        ModelAdapterRuntimeConfig(
            default_adapter_id="fake-default",
            adapters=(
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id="fake-default",
                    model_name="default-model",
                    fake_text_response="wrong adapter",
                ),
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id="fake-proposal",
                    model_name="proposal-model",
                    fake_text_response=output_text,
                ),
            ),
            purpose_overrides=PurposeOverrides(proposal="fake-proposal"),
        )
    )


def _one_option_output_text(*, proposal_type: str = "clarify") -> str:
    blockers = _proposal_blockers(proposal_type)
    blockers_line = "" if blockers == "" else f"OPTION_1_BLOCKERS: {blockers}\n"
    return (
        "PROPOSAL_COUNT: 1\n"
        "SCARCITY_REASON: Only one serious bounded option is currently grounded.\n"
        f"OPTION_1_TYPE: {proposal_type}\n"
        f"OPTION_1_TITLE: {_proposal_title(proposal_type)}\n"
        f"OPTION_1_SUMMARY: {_proposal_summary(proposal_type)}\n"
        f"OPTION_1_WHY_NOW: {_proposal_why_now(proposal_type)}\n"
        f"OPTION_1_ASSUMPTIONS: {_proposal_assumptions(proposal_type)}\n"
        f"OPTION_1_RISKS: {_proposal_risks(proposal_type)}\n"
        "OPTION_1_CONSTRAINTS: Stay inside the current project scope\n"
        f"{blockers_line}"
        f"OPTION_1_PLANNING_NEEDED: {'yes' if proposal_type == 'planning_insertion' else 'no'}\n"
        "OPTION_1_FEASIBILITY: Feasible with one bounded follow-up check\n"
        "OPTION_1_REVERSIBILITY: Fully reversible\n"
        "OPTION_1_SUPPORT_REFS: source-1\n"
    )


def _proposal_title(proposal_type: str) -> str:
    mapping = {
        "direct_action": "Carry the bounded direct action",
        "planning_insertion": "Enter bounded planning before any action",
        "escalate": "Escalate the bounded decision surface",
        "clarify": "Clarify the current export constraint",
        "investigate": "Investigate the current export constraint",
    }
    return mapping.get(proposal_type, "Carry the bounded follow-up option")


def _proposal_summary(proposal_type: str) -> str:
    mapping = {
        "direct_action": "Carry one bounded direct action to the next lawful review boundary.",
        "planning_insertion": "Enter one bounded planning step before any later downstream review.",
        "escalate": "Escalate to an explicit operator judgment surface.",
        "clarify": "Ask one bounded clarifying question before any later downstream review step.",
        "investigate": "Run one bounded investigation before any later downstream review step.",
    }
    return mapping.get(proposal_type, "Carry one bounded follow-up option.")


def _proposal_why_now(proposal_type: str) -> str:
    mapping = {
        "direct_action": "Current research now grounds one bounded direct move.",
        "planning_insertion": "Current research grounds one bounded plan-first move.",
        "escalate": "Current research exposes a remaining judgment boundary.",
        "clarify": "Current research narrows the path but still preserves one decisive uncertainty.",
        "investigate": "Current research still points to one bounded investigation path.",
    }
    return mapping.get(proposal_type, "Current research grounds one bounded follow-up move.")


def _proposal_assumptions(proposal_type: str) -> str:
    mapping = {
        "direct_action": "The bounded direct action still fits the current scope",
        "planning_insertion": "The bounded plan can stay inside the current scope",
        "escalate": "Operator review can resolve the remaining judgment boundary quickly",
        "clarify": "The current export constraint can be clarified quickly",
        "investigate": "The remaining gap can be narrowed with one bounded investigation",
    }
    return mapping.get(proposal_type, "The bounded follow-up remains inside the current scope")


def _proposal_risks(proposal_type: str) -> str:
    mapping = {
        "direct_action": "A later downstream review may still stop further continuation",
        "planning_insertion": "Planning may still stop before any later continuation",
        "escalate": "Escalation may still delay any further downstream continuation",
        "clarify": "Clarification may confirm there is still no stronger path",
        "investigate": "Investigation may confirm more support work is still needed",
    }
    return mapping.get(proposal_type, "The bounded follow-up may still stop at a later lawful boundary")


def _proposal_blockers(proposal_type: str) -> str:
    if proposal_type in {"direct_action", "planning_insertion"}:
        return "No explicit blockers identified from the provided support."
    return "Further downstream review remains outside this proposal slice"


def _state(scope: Scope):
    state = bootstrap_global_state()
    state = apply_transition(
        state,
        TransitionRequest(
            transition_id="transition-project",
            transition_type="create_project",
            basis_state_version=0,
            scope=Scope(project_id=str(scope.project_id)),
            payload={"name": "Alpha"},
        ),
    ).state
    state = apply_transition(
        state,
        TransitionRequest(
            transition_id="transition-work-unit",
            transition_type="create_work_unit",
            basis_state_version=1,
            scope=Scope(project_id=str(scope.project_id)),
            payload={"work_unit_id": str(scope.work_unit_id), "objective": "Acceptance next-stage routing"},
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
    return state
