import jeff.orchestrator.runner as runner_module
from jeff.cognitive import (
    PlanArtifact,
    ProposalResult,
    ProposalResultOption,
    ResearchArtifact,
    ResearchFinding,
    SelectionResult,
    assemble_context_package,
)
from jeff.cognitive.types import PlanStep
from jeff.cognitive.types import TriggerInput
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


def test_direct_action_branch_continues_into_action_and_governance() -> None:
    scope = _scope()
    call_counts = {"action": 0, "governance": 0}

    result = run_flow(
        flow_id="flow-direct-action",
        flow_family="blocked_or_escalation",
        scope=scope,
        stage_handlers={
            "context": _context_stage(scope),
            "proposal": lambda _context: _proposal_result(scope=scope, proposal_type="direct_action"),
            "selection": lambda _proposal: _selected_selection_result(),
            "action": _action_stage(scope, call_counts),
            "governance": _governance_stage(scope, call_counts),
        },
    )

    assert result.lifecycle.lifecycle_state == "completed"
    assert result.routing_decision is None
    assert call_counts == {"action": 1, "governance": 1}
    assert "action" in result.outputs
    assert "governance" in result.outputs


def test_planning_branch_enters_planning_and_holds_at_planning_boundary(monkeypatch) -> None:
    scope = _scope()
    call_counts = {"planning": 0, "action": 0, "governance": 0}
    resolve_calls = {"count": 0}
    original = runner_module.resolve_next_stage

    def _counting_resolve_next_stage(request):
        resolve_calls["count"] += 1
        return original(request)

    monkeypatch.setattr(runner_module, "resolve_next_stage", _counting_resolve_next_stage)

    result = run_flow(
        flow_id="flow-planning",
        flow_family="conditional_planning_insertion",
        scope=scope,
        stage_handlers={
            "context": _context_stage(scope),
            "proposal": lambda _context: _proposal_result(scope=scope, proposal_type="planning_insertion"),
            "selection": lambda _proposal: _selected_selection_result(),
            "planning": _planning_stage(call_counts),
            "action": _action_stage(scope, call_counts),
            "governance": _governance_stage(scope, call_counts),
            "execution": _unexpected_stage("execution"),
            "outcome": _unexpected_stage("outcome"),
            "evaluation": _unexpected_stage("evaluation"),
            "memory": _unexpected_stage("memory"),
            "transition": _unexpected_stage("transition"),
        },
    )

    assert resolve_calls["count"] == 1
    assert result.lifecycle.lifecycle_state == "waiting"
    assert result.lifecycle.current_stage == "planning"
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "planning"
    assert result.routing_decision.source_stage == "planning"
    assert "Planning entered and produced a bounded plan artifact" in result.routing_decision.reason_summary
    assert "no Action could be formed from the current plan output because" in result.routing_decision.reason_summary
    assert "no governance evaluation occurred" in result.routing_decision.reason_summary
    assert "no action permission exists" in result.routing_decision.reason_summary
    assert call_counts == {"planning": 1, "action": 0, "governance": 0}
    assert "planning" in result.outputs
    assert isinstance(result.outputs["planning"], PlanArtifact)
    assert "research" not in result.outputs
    assert "action" not in result.outputs
    assert "governance" not in result.outputs


def test_planning_branch_can_bridge_single_bounded_step_into_action_and_continue_to_governance() -> None:
    scope = _scope()
    call_counts = {"planning": 0, "action": 0, "governance": 0}

    def governance_stage(action):
        call_counts["governance"] += 1
        return evaluate_action_entry(
            action=action,
            policy=Policy(approval_required=True),
            approval=None,
            truth=CurrentTruthSnapshot(scope=scope, state_version=0),
        )

    result = run_flow(
        flow_id="flow-planning-bridge",
        flow_family="conditional_planning_insertion",
        scope=scope,
        stage_handlers={
            "context": _context_stage(scope),
            "proposal": lambda _context: _proposal_result(scope=scope, proposal_type="planning_insertion"),
            "selection": lambda _proposal: _selected_selection_result(),
            "planning": _bridgeable_planning_stage(call_counts),
            "action": _action_stage(scope, call_counts),
            "governance": governance_stage,
            "execution": _unexpected_stage("execution"),
            "outcome": _unexpected_stage("outcome"),
            "evaluation": _unexpected_stage("evaluation"),
            "memory": _unexpected_stage("memory"),
            "transition": _unexpected_stage("transition"),
        },
    )

    assert result.lifecycle.lifecycle_state == "waiting"
    assert result.lifecycle.current_stage == "governance"
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "approval_required"
    assert call_counts == {"planning": 1, "action": 0, "governance": 1}
    assert "planning" in result.outputs
    assert "action" in result.outputs
    assert result.outputs["action"].intent_summary == "Apply the bounded implementation"
    assert result.outputs["action"].target_summary == "Plan the bounded option"
    assert "governance" in result.outputs


def test_direct_action_branch_in_conditional_flow_bypasses_planning_and_reaches_action_and_governance() -> None:
    scope = _scope()
    call_counts = {"planning": 0, "action": 0, "governance": 0}

    def governance_stage(action):
        call_counts["governance"] += 1
        return evaluate_action_entry(
            action=action,
            policy=Policy(approval_required=True),
            approval=None,
            truth=CurrentTruthSnapshot(scope=scope, state_version=3),
        )

    result = run_flow(
        flow_id="flow-conditional-direct-action",
        flow_family="conditional_planning_insertion",
        scope=scope,
        stage_handlers={
            "context": _context_stage(scope),
            "proposal": lambda _context: _proposal_result(scope=scope, proposal_type="direct_action"),
            "selection": lambda _proposal: _selected_selection_result(),
            "planning": _planning_stage(call_counts),
            "action": _action_stage(scope, call_counts),
            "governance": governance_stage,
            "execution": _unexpected_stage("execution"),
            "outcome": _unexpected_stage("outcome"),
            "evaluation": _unexpected_stage("evaluation"),
            "memory": _unexpected_stage("memory"),
            "transition": _unexpected_stage("transition"),
        },
    )

    assert result.lifecycle.lifecycle_state == "waiting"
    assert result.lifecycle.current_stage == "governance"
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "approval_required"
    assert call_counts == {"planning": 0, "action": 1, "governance": 1}
    assert "planning" not in result.outputs
    assert "action" in result.outputs
    assert "governance" in result.outputs


def test_research_followup_branch_continues_selection_output_into_terminal_non_selection_boundary(monkeypatch) -> None:
    scope = _scope()
    call_counts = {"research": 0, "action": 0, "governance": 0}
    resolve_calls = {"count": 0}
    original = runner_module.resolve_next_stage

    def _counting_resolve_next_stage(request):
        resolve_calls["count"] += 1
        return original(request)

    monkeypatch.setattr(runner_module, "resolve_next_stage", _counting_resolve_next_stage)

    result = run_flow(
        flow_id="flow-research-followup",
        flow_family="conditional_research_followup",
        scope=scope,
        stage_handlers={
            "context": _context_stage(scope),
            "proposal": lambda _context: _proposal_result(scope=scope, proposal_type="clarify"),
            "selection": lambda _proposal: _selected_selection_result(),
            "research": _research_stage(call_counts, sufficient=True, bridgeable_proposal_generation=True),
            "action": _action_stage(scope, call_counts),
            "governance": _governance_stage(scope, call_counts),
        },
    )

    assert resolve_calls["count"] == 2
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
    assert "terminal non-execution boundary" in result.routing_decision.reason_summary
    assert "Selection output remains non-authorizing" in result.routing_decision.reason_summary
    assert call_counts == {"research": 1, "action": 0, "governance": 0}
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


def test_research_followup_branch_continues_beyond_selection_output_into_governance_path() -> None:
    scope = _scope()
    call_counts = {"research": 0, "action": 0, "governance": 0}

    def governance_stage(action):
        call_counts["governance"] += 1
        return evaluate_action_entry(
            action=action,
            policy=Policy(approval_required=True),
            approval=None,
            truth=CurrentTruthSnapshot(scope=scope, state_version=3),
        )

    result = run_flow(
        flow_id="flow-research-followup-governance",
        flow_family="conditional_research_followup",
        scope=scope,
        stage_handlers={
            "context": _context_stage(scope),
            "proposal": lambda _context: _proposal_result(scope=scope, proposal_type="clarify"),
            "selection": lambda _proposal: _selected_selection_result(),
            "research": _research_stage(
                call_counts,
                sufficient=True,
                bridgeable_proposal_generation=True,
                proposal_generation_output_text=_one_option_output_text(proposal_type="direct_action"),
            ),
            "action": _action_stage(scope, call_counts),
            "governance": governance_stage,
        },
    )

    assert result.lifecycle.lifecycle_state == "waiting"
    assert result.lifecycle.current_stage == "governance"
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "approval_required"
    assert "reused the existing downstream post-selection chain" in result.routing_decision.reason_summary
    assert "Selection output remained non-authorizing until governance evaluated the formed action" in result.routing_decision.reason_summary
    assert call_counts == {"research": 1, "action": 1, "governance": 1}
    assert result.outputs["proposal_output"].options[0].proposal_type == "direct_action"
    assert result.outputs["selection_output"].selected_proposal_id == "proposal-1"
    assert "planning" not in result.outputs
    assert "action" in result.outputs
    assert "governance" in result.outputs


def test_research_followup_branch_continues_beyond_selection_output_into_planning_path() -> None:
    scope = _scope()
    call_counts = {"research": 0, "planning": 0, "action": 0, "governance": 0}

    def governance_stage(action):
        call_counts["governance"] += 1
        return evaluate_action_entry(
            action=action,
            policy=Policy(approval_required=True),
            approval=None,
            truth=CurrentTruthSnapshot(scope=scope, state_version=0),
        )

    result = run_flow(
        flow_id="flow-research-followup-planning",
        flow_family="conditional_research_followup",
        scope=scope,
        stage_handlers={
            "context": _context_stage(scope),
            "proposal": lambda _context: _proposal_result(scope=scope, proposal_type="clarify"),
            "selection": lambda _proposal: _selected_selection_result(),
            "research": _research_stage(
                call_counts,
                sufficient=True,
                bridgeable_proposal_generation=True,
                proposal_generation_output_text=_one_option_output_text(proposal_type="planning_insertion"),
            ),
            "planning": _bridgeable_planning_stage(call_counts),
            "action": _action_stage(scope, call_counts),
            "governance": governance_stage,
        },
    )

    assert result.lifecycle.lifecycle_state == "waiting"
    assert result.lifecycle.current_stage == "governance"
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "approval_required"
    assert "reused the existing downstream post-selection chain" in result.routing_decision.reason_summary
    assert "Planning then continued through the existing plan-to-action bridge" in result.routing_decision.reason_summary
    assert call_counts == {"research": 1, "planning": 1, "action": 0, "governance": 1}
    assert result.outputs["proposal_output"].options[0].proposal_type == "planning_insertion"
    assert result.outputs["selection_output"].selected_proposal_id == "proposal-1"
    assert "planning" in result.outputs
    assert "action" in result.outputs
    assert "governance" in result.outputs


def test_research_followup_branch_continues_selection_output_into_escalation_surface() -> None:
    scope = _scope()
    call_counts = {"research": 0, "action": 0, "governance": 0}

    result = run_flow(
        flow_id="flow-research-followup-escalation",
        flow_family="conditional_research_followup",
        scope=scope,
        stage_handlers={
            "context": _context_stage(scope),
            "proposal": lambda _context: _proposal_result(scope=scope, proposal_type="clarify"),
            "selection": lambda _proposal: _selected_selection_result(),
            "research": _research_stage(
                call_counts,
                sufficient=True,
                bridgeable_proposal_generation=True,
                proposal_generation_output_text=_one_option_output_text(proposal_type="escalate"),
            ),
            "action": _action_stage(scope, call_counts),
            "governance": _governance_stage(scope, call_counts),
        },
    )

    assert result.lifecycle.lifecycle_state == "escalated"
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "escalated"
    assert "reused the existing downstream post-selection chain" in result.routing_decision.reason_summary
    assert "explicit escalation surface" in result.routing_decision.reason_summary
    assert call_counts == {"research": 1, "action": 0, "governance": 0}
    assert result.outputs["selection_output"].non_selection_outcome == "escalate"
    assert "action" not in result.outputs
    assert "governance" not in result.outputs


def test_research_followup_branch_blocks_recursive_reentry_without_hidden_loop(monkeypatch) -> None:
    scope = _scope()
    call_counts = {"research": 0, "action": 0, "governance": 0}

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
            summary="Forced lawful clarify selection for anti-loop coverage.",
        )

    monkeypatch.setattr(runner_module, "build_and_run_selection", _selected_clarify)

    result = run_flow(
        flow_id="flow-research-followup-anti-loop",
        flow_family="conditional_research_followup",
        scope=scope,
        stage_handlers={
            "context": _context_stage(scope),
            "proposal": lambda _context: _proposal_result(scope=scope, proposal_type="clarify"),
            "selection": lambda _proposal: _selected_selection_result(),
            "research": _research_stage(call_counts, sufficient=True, bridgeable_proposal_generation=True),
            "action": _action_stage(scope, call_counts),
            "governance": _governance_stage(scope, call_counts),
        },
    )

    assert result.lifecycle.lifecycle_state == "waiting"
    assert result.lifecycle.current_stage == "research"
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "research_followup"
    assert "reused the existing downstream post-selection chain" in result.routing_decision.reason_summary
    assert "does not auto-enter recursive research" in result.routing_decision.reason_summary
    assert "hidden loop" in result.routing_decision.reason_summary
    assert call_counts == {"research": 1, "action": 0, "governance": 0}
    assert result.outputs["selection_output"].selected_proposal_id == "proposal-1"
    assert "action" not in result.outputs
    assert "governance" not in result.outputs


def test_research_followup_branch_preserves_explicit_unresolved_items_when_insufficient() -> None:
    scope = _scope()
    call_counts = {"research": 0, "action": 0, "governance": 0}

    result = run_flow(
        flow_id="flow-research-followup-insufficient",
        flow_family="conditional_research_followup",
        scope=scope,
        stage_handlers={
            "context": _context_stage(scope),
            "proposal": lambda _context: _proposal_result(scope=scope, proposal_type="investigate"),
            "selection": lambda _proposal: _selected_selection_result(),
            "research": _research_stage(call_counts, sufficient=False),
            "action": _action_stage(scope, call_counts),
            "governance": _governance_stage(scope, call_counts),
        },
    )

    assert result.lifecycle.lifecycle_state == "waiting"
    assert result.lifecycle.current_stage == "research"
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "research_followup"
    assert "Sufficiency evaluation: more_research_needed." in result.routing_decision.reason_summary
    assert (
        "Need a source-backed answer for whether the current export tier still allows the bounded batch path."
        in result.routing_decision.reason_summary
    )
    assert "Jeff does not auto-loop into more research or any downstream action" in result.routing_decision.reason_summary
    assert call_counts == {"research": 1, "action": 0, "governance": 0}
    assert "research" in result.outputs
    assert result.outputs["research_output_sufficiency"].downstream_target == "more_research_needed"
    assert "research_decision_support_handoff" not in result.outputs
    assert "research_proposal_support_package" not in result.outputs
    assert "proposal_input_package" not in result.outputs
    assert "selection_bridge_result" not in result.outputs
    assert "selection_output" not in result.outputs
    assert "action" not in result.outputs
    assert "governance" not in result.outputs


def test_direct_action_branch_in_conditional_research_flow_bypasses_research_and_reaches_action_and_governance() -> None:
    scope = _scope()
    call_counts = {"research": 0, "action": 0, "governance": 0}

    def governance_stage(action):
        call_counts["governance"] += 1
        return evaluate_action_entry(
            action=action,
            policy=Policy(approval_required=True),
            approval=None,
            truth=CurrentTruthSnapshot(scope=scope, state_version=3),
        )

    result = run_flow(
        flow_id="flow-conditional-research-direct-action",
        flow_family="conditional_research_followup",
        scope=scope,
        stage_handlers={
            "context": _context_stage(scope),
            "proposal": lambda _context: _proposal_result(scope=scope, proposal_type="direct_action"),
            "selection": lambda _proposal: _selected_selection_result(),
            "research": _research_stage(call_counts),
            "action": _action_stage(scope, call_counts),
            "governance": governance_stage,
        },
    )

    assert result.lifecycle.lifecycle_state == "waiting"
    assert result.lifecycle.current_stage == "governance"
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "approval_required"
    assert call_counts == {"research": 0, "action": 1, "governance": 1}
    assert "research" not in result.outputs
    assert "action" in result.outputs
    assert "governance" in result.outputs


def test_direct_action_branch_still_bypasses_research_sufficiency_logic(monkeypatch) -> None:
    scope = _scope()
    call_counts = {"research": 0, "action": 0, "governance": 0}

    def _fail_if_called(request):
        raise AssertionError("research sufficiency bridge should not run on the direct-action branch")

    def _fail_if_handoff_called(request):
        raise AssertionError("research decision support bridge should not run on the direct-action branch")

    def _fail_if_proposal_support_called(request):
        raise AssertionError("research proposal consumer should not run on the direct-action branch")

    def _fail_if_proposal_input_called(request):
        raise AssertionError("proposal support package consumer should not run on the direct-action branch")

    def _fail_if_proposal_generation_bridge_called(request):
        raise AssertionError("proposal generation bridge should not run on the direct-action branch")

    monkeypatch.setattr(runner_module, "evaluate_research_output_sufficiency", _fail_if_called)
    monkeypatch.setattr(runner_module, "build_research_decision_support_handoff", _fail_if_handoff_called)
    monkeypatch.setattr(runner_module, "consume_research_for_proposal_support", _fail_if_proposal_support_called)
    monkeypatch.setattr(runner_module, "consume_proposal_support_package", _fail_if_proposal_input_called)
    monkeypatch.setattr(runner_module, "build_and_run_proposal_generation", _fail_if_proposal_generation_bridge_called)

    result = run_flow(
        flow_id="flow-conditional-research-direct-action-bypass-bridge",
        flow_family="conditional_research_followup",
        scope=scope,
        stage_handlers={
            "context": _context_stage(scope),
            "proposal": lambda _context: _proposal_result(scope=scope, proposal_type="direct_action"),
            "selection": lambda _proposal: _selected_selection_result(),
            "research": _research_stage(call_counts, sufficient=True),
            "action": _action_stage(scope, call_counts),
            "governance": _governance_stage(scope, call_counts),
        },
    )

    assert result.lifecycle.current_stage == "governance"
    assert result.lifecycle.lifecycle_state == "completed"
    assert result.routing_decision is None
    assert call_counts == {"research": 0, "action": 1, "governance": 1}


def test_planning_branch_remains_unchanged_and_does_not_use_research_sufficiency_logic(monkeypatch) -> None:
    scope = _scope()
    call_counts = {"planning": 0, "action": 0, "governance": 0}

    def _fail_if_called(request):
        raise AssertionError("research sufficiency bridge should not run on the planning branch")

    def _fail_if_handoff_called(request):
        raise AssertionError("research decision support bridge should not run on the planning branch")

    def _fail_if_proposal_support_called(request):
        raise AssertionError("research proposal consumer should not run on the planning branch")

    def _fail_if_proposal_input_called(request):
        raise AssertionError("proposal support package consumer should not run on the planning branch")

    def _fail_if_proposal_generation_bridge_called(request):
        raise AssertionError("proposal generation bridge should not run on the planning branch")

    monkeypatch.setattr(runner_module, "evaluate_research_output_sufficiency", _fail_if_called)
    monkeypatch.setattr(runner_module, "build_research_decision_support_handoff", _fail_if_handoff_called)
    monkeypatch.setattr(runner_module, "consume_research_for_proposal_support", _fail_if_proposal_support_called)
    monkeypatch.setattr(runner_module, "consume_proposal_support_package", _fail_if_proposal_input_called)
    monkeypatch.setattr(runner_module, "build_and_run_proposal_generation", _fail_if_proposal_generation_bridge_called)

    result = run_flow(
        flow_id="flow-planning-no-research-sufficiency",
        flow_family="conditional_planning_insertion",
        scope=scope,
        stage_handlers={
            "context": _context_stage(scope),
            "proposal": lambda _context: _proposal_result(scope=scope, proposal_type="planning_insertion"),
            "selection": lambda _proposal: _selected_selection_result(),
            "planning": _planning_stage(call_counts),
            "action": _action_stage(scope, call_counts),
            "governance": _governance_stage(scope, call_counts),
            "execution": _unexpected_stage("execution"),
            "outcome": _unexpected_stage("outcome"),
            "evaluation": _unexpected_stage("evaluation"),
            "memory": _unexpected_stage("memory"),
            "transition": _unexpected_stage("transition"),
        },
    )

    assert result.lifecycle.current_stage == "planning"
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "planning"
    assert call_counts == {"planning": 1, "action": 0, "governance": 0}


def test_research_followup_branch_holds_at_proposal_output_boundary_when_selection_inputs_are_missing() -> None:
    scope = _scope()
    call_counts = {"research": 0, "action": 0, "governance": 0}

    research_stage = _research_stage(call_counts, sufficient=True, bridgeable_proposal_generation=True)
    research_stage.selection_bridge_selection_id = " "

    result = run_flow(
        flow_id="flow-research-followup-missing-selection-id",
        flow_family="conditional_research_followup",
        scope=scope,
        stage_handlers={
            "context": _context_stage(scope),
            "proposal": lambda _context: _proposal_result(scope=scope, proposal_type="clarify"),
            "selection": lambda _proposal: _selected_selection_result(),
            "research": research_stage,
            "action": _action_stage(scope, call_counts),
            "governance": _governance_stage(scope, call_counts),
        },
    )

    assert result.lifecycle.lifecycle_state == "waiting"
    assert result.lifecycle.current_stage == "research"
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "proposal_output_ready"
    assert "Proposal output ready:" in result.routing_decision.reason_summary
    assert "No lawful selection output exists because selection bridge failed" in result.routing_decision.reason_summary
    assert "selection_id" in result.routing_decision.reason_summary
    assert result.outputs["proposal_output"].proposal_count == 1
    assert "selection_bridge_result" not in result.outputs
    assert "selection_output" not in result.outputs


def test_planning_stage_wrong_output_type_fails_closed_without_guessing_downstream_semantics() -> None:
    scope = _scope()
    call_counts = {"action": 0, "governance": 0}

    result = run_flow(
        flow_id="flow-planning-invalid-output",
        flow_family="conditional_planning_insertion",
        scope=scope,
        stage_handlers={
            "context": _context_stage(scope),
            "proposal": lambda _context: _proposal_result(scope=scope, proposal_type="planning_insertion"),
            "selection": lambda _proposal: _selected_selection_result(),
            "planning": lambda _selection: _selected_selection_result(),
            "action": _action_stage(scope, call_counts),
            "governance": _governance_stage(scope, call_counts),
            "execution": _unexpected_stage("execution"),
            "outcome": _unexpected_stage("outcome"),
            "evaluation": _unexpected_stage("evaluation"),
            "memory": _unexpected_stage("memory"),
            "transition": _unexpected_stage("transition"),
        },
    )

    assert result.lifecycle.lifecycle_state == "invalidated"
    assert result.lifecycle.current_stage == "planning"
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "invalidated"
    assert result.routing_decision.source_stage == "planning"
    assert result.routing_decision.reason_summary == "planning must emit PlanArtifact"
    assert call_counts == {"action": 0, "governance": 0}
    assert "planning" not in result.outputs
    assert "action" not in result.outputs
    assert "governance" not in result.outputs


def test_research_stage_wrong_output_type_fails_closed_without_guessing_downstream_semantics() -> None:
    scope = _scope()
    call_counts = {"action": 0, "governance": 0}

    result = run_flow(
        flow_id="flow-research-invalid-output",
        flow_family="conditional_research_followup",
        scope=scope,
        stage_handlers={
            "context": _context_stage(scope),
            "proposal": lambda _context: _proposal_result(scope=scope, proposal_type="clarify"),
            "selection": lambda _proposal: _selected_selection_result(),
            "research": lambda _selection: _selected_selection_result(),
            "action": _action_stage(scope, call_counts),
            "governance": _governance_stage(scope, call_counts),
        },
    )

    assert result.lifecycle.lifecycle_state == "invalidated"
    assert result.lifecycle.current_stage == "research"
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "invalidated"
    assert result.routing_decision.source_stage == "research"
    assert result.routing_decision.reason_summary == "research must emit ResearchArtifact"
    assert call_counts == {"action": 0, "governance": 0}
    assert "research" not in result.outputs
    assert "action" not in result.outputs
    assert "governance" not in result.outputs


def test_research_sufficiency_bridge_fails_closed_on_malformed_research_output() -> None:
    scope = _scope()
    call_counts = {"research": 0, "action": 0, "governance": 0}

    result = run_flow(
        flow_id="flow-research-sufficiency-invalid-output",
        flow_family="conditional_research_followup",
        scope=scope,
        stage_handlers={
            "context": _context_stage(scope),
            "proposal": lambda _context: _proposal_result(scope=scope, proposal_type="clarify"),
            "selection": lambda _proposal: _selected_selection_result(),
            "research": _research_stage(call_counts, malformed=True),
            "action": _action_stage(scope, call_counts),
            "governance": _governance_stage(scope, call_counts),
        },
    )

    assert result.lifecycle.lifecycle_state == "invalidated"
    assert result.lifecycle.current_stage == "action"
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "invalidated"
    assert "research output sufficiency evaluation failed" in result.routing_decision.reason_summary
    assert "research_artifact.findings" in result.routing_decision.reason_summary
    assert call_counts == {"research": 1, "action": 0, "governance": 0}
    assert "research" in result.outputs
    assert "action" not in result.outputs
    assert "governance" not in result.outputs


def test_research_decision_support_bridge_fails_closed_on_malformed_sufficient_result(monkeypatch) -> None:
    scope = _scope()
    call_counts = {"research": 0, "action": 0, "governance": 0}

    def _malformed_sufficient_result(request):
        return runner_module.ResearchOutputSufficiencyResult(
            evaluation_id="research-sufficiency-bad",
            sufficient_for_downstream_use=True,
            downstream_target="decision_support_ready",
            key_supported_points=("This supported point is not preserved in the artifact.",),
            unresolved_items=(),
            contradictions_present=False,
            insufficiency_reason=None,
            summary="Research is decision-support-ready.",
        )

    monkeypatch.setattr(runner_module, "evaluate_research_output_sufficiency", _malformed_sufficient_result)

    result = run_flow(
        flow_id="flow-research-decision-support-invalid-output",
        flow_family="conditional_research_followup",
        scope=scope,
        stage_handlers={
            "context": _context_stage(scope),
            "proposal": lambda _context: _proposal_result(scope=scope, proposal_type="clarify"),
            "selection": lambda _proposal: _selected_selection_result(),
            "research": _research_stage(call_counts, sufficient=True),
            "action": _action_stage(scope, call_counts),
            "governance": _governance_stage(scope, call_counts),
        },
    )

    assert result.lifecycle.lifecycle_state == "invalidated"
    assert result.lifecycle.current_stage == "action"
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "invalidated"
    assert "research decision support bridge failed" in result.routing_decision.reason_summary
    assert "key_supported_points" in result.routing_decision.reason_summary
    assert call_counts == {"research": 1, "action": 0, "governance": 0}
    assert "research" in result.outputs
    assert result.outputs["research_output_sufficiency"].downstream_target == "decision_support_ready"
    assert "research_decision_support_handoff" not in result.outputs


def test_research_proposal_support_consumer_fails_closed_on_malformed_sufficient_handoff(monkeypatch) -> None:
    scope = _scope()
    call_counts = {"research": 0, "action": 0, "governance": 0}
    original = runner_module.build_research_decision_support_handoff

    def _malformed_handoff(request):
        handoff = original(request)
        object.__setattr__(handoff, "supported_findings", ())
        return handoff

    monkeypatch.setattr(runner_module, "build_research_decision_support_handoff", _malformed_handoff)

    result = run_flow(
        flow_id="flow-research-proposal-support-invalid-output",
        flow_family="conditional_research_followup",
        scope=scope,
        stage_handlers={
            "context": _context_stage(scope),
            "proposal": lambda _context: _proposal_result(scope=scope, proposal_type="clarify"),
            "selection": lambda _proposal: _selected_selection_result(),
            "research": _research_stage(call_counts, sufficient=True),
            "action": _action_stage(scope, call_counts),
            "governance": _governance_stage(scope, call_counts),
        },
    )

    assert result.lifecycle.lifecycle_state == "invalidated"
    assert result.lifecycle.current_stage == "action"
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "invalidated"
    assert "research proposal consumer failed" in result.routing_decision.reason_summary
    assert "supported_findings" in result.routing_decision.reason_summary
    assert call_counts == {"research": 1, "action": 0, "governance": 0}
    assert "research" in result.outputs
    assert result.outputs["research_output_sufficiency"].downstream_target == "decision_support_ready"
    assert result.outputs["research_decision_support_handoff"].decision_support_ready is True
    assert "research_proposal_support_package" not in result.outputs
    assert "proposal_input_package" not in result.outputs


def test_proposal_support_package_consumer_fails_closed_on_malformed_support_package(monkeypatch) -> None:
    scope = _scope()
    call_counts = {"research": 0, "action": 0, "governance": 0}
    original = runner_module.consume_research_for_proposal_support

    def _malformed_proposal_support(request):
        proposal_support_package = original(request)
        object.__setattr__(proposal_support_package, "supported_findings", ())
        return proposal_support_package

    monkeypatch.setattr(runner_module, "consume_research_for_proposal_support", _malformed_proposal_support)

    result = run_flow(
        flow_id="flow-proposal-input-invalid-output",
        flow_family="conditional_research_followup",
        scope=scope,
        stage_handlers={
            "context": _context_stage(scope),
            "proposal": lambda _context: _proposal_result(scope=scope, proposal_type="clarify"),
            "selection": lambda _proposal: _selected_selection_result(),
            "research": _research_stage(call_counts, sufficient=True),
            "action": _action_stage(scope, call_counts),
            "governance": _governance_stage(scope, call_counts),
        },
    )

    assert result.lifecycle.lifecycle_state == "invalidated"
    assert result.lifecycle.current_stage == "action"
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "invalidated"
    assert "proposal support consumer failed" in result.routing_decision.reason_summary
    assert "supported_findings" in result.routing_decision.reason_summary
    assert call_counts == {"research": 1, "action": 0, "governance": 0}
    assert "research" in result.outputs
    assert result.outputs["research_output_sufficiency"].downstream_target == "decision_support_ready"
    assert result.outputs["research_decision_support_handoff"].decision_support_ready is True
    assert result.outputs["research_proposal_support_package"].proposal_support_ready is True
    assert "proposal_input_package" not in result.outputs


def test_proposal_generation_bridge_holds_at_proposal_input_boundary_when_runtime_inputs_are_missing() -> None:
    scope = _scope()
    call_counts = {"research": 0, "action": 0, "governance": 0}

    result = run_flow(
        flow_id="flow-proposal-generation-missing-runtime-inputs",
        flow_family="conditional_research_followup",
        scope=scope,
        stage_handlers={
            "context": _context_stage(scope),
            "proposal": lambda _context: _proposal_result(scope=scope, proposal_type="clarify"),
            "selection": lambda _proposal: _selected_selection_result(),
            "research": _research_stage(call_counts, sufficient=True, bridgeable_proposal_generation=False),
            "action": _action_stage(scope, call_counts),
            "governance": _governance_stage(scope, call_counts),
        },
    )

    assert result.lifecycle.lifecycle_state == "waiting"
    assert result.lifecycle.current_stage == "research"
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "proposal_input_boundary"
    assert "Proposal generation did not produce lawful proposal output because" in result.routing_decision.reason_summary
    assert "InfrastructureServices" in result.routing_decision.reason_summary
    assert call_counts == {"research": 1, "action": 0, "governance": 0}
    assert result.outputs["proposal_input_package"].proposal_input_ready is True
    assert result.outputs["proposal_generation_bridge_result"].proposal_generation_ran is False
    assert "proposal_output" not in result.outputs
    assert "action" not in result.outputs
    assert "governance" not in result.outputs


def test_proposal_generation_bridge_fails_closed_on_malformed_proposal_input_package(monkeypatch) -> None:
    scope = _scope()
    call_counts = {"research": 0, "action": 0, "governance": 0}
    original = runner_module.consume_proposal_support_package

    def _malformed_proposal_input(request):
        proposal_input_package = original(request)
        object.__setattr__(proposal_input_package, "supported_findings", ())
        return proposal_input_package

    monkeypatch.setattr(runner_module, "consume_proposal_support_package", _malformed_proposal_input)

    result = run_flow(
        flow_id="flow-proposal-generation-invalid-input-package",
        flow_family="conditional_research_followup",
        scope=scope,
        stage_handlers={
            "context": _context_stage(scope),
            "proposal": lambda _context: _proposal_result(scope=scope, proposal_type="clarify"),
            "selection": lambda _proposal: _selected_selection_result(),
            "research": _research_stage(call_counts, sufficient=True, bridgeable_proposal_generation=True),
            "action": _action_stage(scope, call_counts),
            "governance": _governance_stage(scope, call_counts),
        },
    )

    assert result.lifecycle.lifecycle_state == "invalidated"
    assert result.lifecycle.current_stage == "action"
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "invalidated"
    assert "proposal generation bridge failed" in result.routing_decision.reason_summary
    assert "supported_findings" in result.routing_decision.reason_summary
    assert call_counts == {"research": 1, "action": 0, "governance": 0}
    assert "proposal_generation_bridge_result" not in result.outputs
    assert "proposal_output" not in result.outputs


def test_terminal_non_selection_branch_stops_without_action_or_governance() -> None:
    scope = _scope()
    call_counts = {"action": 0, "governance": 0}

    result = run_flow(
        flow_id="flow-terminal-non-selection",
        flow_family="blocked_or_escalation",
        scope=scope,
        stage_handlers={
            "context": _context_stage(scope),
            "proposal": lambda _context: _proposal_result(scope=scope, proposal_type="direct_action"),
            "selection": lambda _proposal: SelectionResult(
                selection_id="selection-2",
                considered_proposal_ids=("proposal-1",),
                non_selection_outcome="reject_all",
                rationale="No currently considered proposal is lawful enough to continue.",
            ),
            "action": _action_stage(scope, call_counts),
            "governance": _governance_stage(scope, call_counts),
        },
    )

    assert result.lifecycle.lifecycle_state == "completed"
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "reject_all"
    assert "terminal non-execution path" in result.routing_decision.reason_summary
    assert call_counts == {"action": 0, "governance": 0}
    assert "action" not in result.outputs
    assert "governance" not in result.outputs


def test_terminal_non_selection_branch_in_conditional_research_flow_does_not_enter_research() -> None:
    scope = _scope()
    call_counts = {"research": 0, "action": 0, "governance": 0}

    result = run_flow(
        flow_id="flow-terminal-non-selection-research-family",
        flow_family="conditional_research_followup",
        scope=scope,
        stage_handlers={
            "context": _context_stage(scope),
            "proposal": lambda _context: _proposal_result(scope=scope, proposal_type="clarify"),
            "selection": lambda _proposal: SelectionResult(
                selection_id="selection-2b",
                considered_proposal_ids=("proposal-1",),
                non_selection_outcome="reject_all",
                rationale="No currently considered proposal is lawful enough to continue.",
            ),
            "research": _research_stage(call_counts),
            "action": _action_stage(scope, call_counts),
            "governance": _governance_stage(scope, call_counts),
        },
    )

    assert result.lifecycle.lifecycle_state == "completed"
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "reject_all"
    assert call_counts == {"research": 0, "action": 0, "governance": 0}
    assert "research" not in result.outputs
    assert "action" not in result.outputs
    assert "governance" not in result.outputs


def test_escalation_branch_routes_to_explicit_escalation_surface_without_action_or_governance() -> None:
    scope = _scope()
    call_counts = {"action": 0, "governance": 0}

    result = run_flow(
        flow_id="flow-escalation-surface",
        flow_family="blocked_or_escalation",
        scope=scope,
        stage_handlers={
            "context": _context_stage(scope),
            "proposal": lambda _context: _proposal_result(scope=scope, proposal_type="direct_action"),
            "selection": lambda _proposal: SelectionResult(
                selection_id="selection-3",
                considered_proposal_ids=("proposal-1",),
                non_selection_outcome="escalate",
                rationale="Operator judgment is required before any downstream continuation.",
            ),
            "action": _action_stage(scope, call_counts),
            "governance": _governance_stage(scope, call_counts),
        },
    )

    assert result.lifecycle.lifecycle_state == "escalated"
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "escalated"
    assert "explicit escalation surface" in result.routing_decision.reason_summary
    assert call_counts == {"action": 0, "governance": 0}
    assert "action" not in result.outputs
    assert "governance" not in result.outputs


def test_escalation_branch_in_conditional_research_flow_does_not_enter_research() -> None:
    scope = _scope()
    call_counts = {"research": 0, "action": 0, "governance": 0}

    result = run_flow(
        flow_id="flow-escalation-research-family",
        flow_family="conditional_research_followup",
        scope=scope,
        stage_handlers={
            "context": _context_stage(scope),
            "proposal": lambda _context: _proposal_result(scope=scope, proposal_type="clarify"),
            "selection": lambda _proposal: SelectionResult(
                selection_id="selection-3b",
                considered_proposal_ids=("proposal-1",),
                non_selection_outcome="escalate",
                rationale="Operator judgment is required before any downstream continuation.",
            ),
            "research": _research_stage(call_counts),
            "action": _action_stage(scope, call_counts),
            "governance": _governance_stage(scope, call_counts),
        },
    )

    assert result.lifecycle.lifecycle_state == "escalated"
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "escalated"
    assert call_counts == {"research": 0, "action": 0, "governance": 0}
    assert "research" not in result.outputs
    assert "action" not in result.outputs
    assert "governance" not in result.outputs


def _context_stage(scope: Scope):
    state = _state(scope)

    def _stage(_):
        return assemble_context_package(
            trigger=TriggerInput(trigger_summary="Drive the post-selection next-stage routing slice."),
            purpose="proposal support",
            scope=scope,
            state=state,
        )

    return _stage


def _proposal_result(*, scope: Scope, proposal_type: str) -> ProposalResult:
    return ProposalResult(
        request_id="proposal-request-1",
        scope=scope,
        options=(
            ProposalResultOption(
                option_index=1,
                proposal_id="proposal-1",
                proposal_type=proposal_type,  # type: ignore[arg-type]
                title="Carry the bounded option",
                why_now="This is the explicit option used by the routing test.",
                summary="Carry the bounded option",
            ),
        ),
        scarcity_reason="Only one serious bounded option exists for this orchestration test.",
    )


def _selected_selection_result() -> SelectionResult:
    return SelectionResult(
        selection_id="selection-1",
        considered_proposal_ids=("proposal-1",),
        selected_proposal_id="proposal-1",
        rationale="The single bounded option is selected for downstream routing.",
    )


def _action_stage(scope: Scope, call_counts: dict[str, int]):
    def _stage(_selection):
        call_counts["action"] += 1
        return Action(
            action_id="action-1",
            scope=scope,
            intent_summary="Apply the bounded routed action",
            basis_state_version=3,
        )

    return _stage


def _planning_stage(call_counts: dict[str, int]):
    def _stage(_selection):
        call_counts["planning"] += 1
        return PlanArtifact(
            bounded_objective="Plan the bounded option",
            intended_steps=(
                PlanStep(summary="Review scope and checkpoints", review_required=True),
                PlanStep(summary="Pause at the planning boundary for a later lawful downstream slice"),
            ),
            selected_proposal_id="proposal-1",
        )

    return _stage


def _bridgeable_planning_stage(call_counts: dict[str, int]):
    def _stage(_selection):
        call_counts["planning"] += 1
        return PlanArtifact(
            bounded_objective="Plan the bounded option",
            intended_steps=(PlanStep(summary="Apply the bounded implementation"),),
            selected_proposal_id="proposal-1",
        )

    return _stage


def _research_stage(
    call_counts: dict[str, int],
    *,
    sufficient: bool = True,
    malformed: bool = False,
    bridgeable_proposal_generation: bool = False,
    proposal_generation_output_text: str | None = None,
):
    def _stage(_selection):
        call_counts["research"] += 1
        artifact = ResearchArtifact(
            question="Clarify the bounded uncertainty before any further downstream step.",
            summary=(
                "The bounded evidence clarifies the current comparison without granting authority."
                if sufficient
                else "The bounded evidence is still incomplete for the current comparison."
            ),
            findings=(
                ResearchFinding(
                    text="The next ambiguity can be reduced with one bounded follow-up check.",
                    source_refs=("source-1",),
                ),
            ),
            inferences=("The clarify path remains support-only.",),
            uncertainties=()
            if sufficient
            else ("whether the current export tier still allows the bounded batch path",),
            recommendation="Pause after research until a later lawful downstream slice exists.",
            source_ids=("source-1",),
        )
        if malformed:
            object.__setattr__(artifact, "findings", ())
        return artifact

    if bridgeable_proposal_generation:
        _stage.proposal_generation_infrastructure_services = _proposal_generation_services(
            _one_option_output_text() if proposal_generation_output_text is None else proposal_generation_output_text
        )
        _stage.proposal_generation_objective = "Frame bounded follow-up options from the preserved research"
        _stage.proposal_generation_visible_constraints = ("Stay inside the current project scope.",)

    return _stage


def _governance_stage(scope: Scope, call_counts: dict[str, int]):
    def _stage(action):
        call_counts["governance"] += 1
        return evaluate_action_entry(
            action=action,
            policy=Policy(),
            approval=None,
            truth=CurrentTruthSnapshot(scope=scope, state_version=3),
        )

    return _stage


def _unexpected_stage(stage_name: str):
    def _stage(_input):
        raise AssertionError(f"{stage_name} stage should not run in this routing test")

    return _stage


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
        return "NONE"
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
            payload={"work_unit_id": str(scope.work_unit_id), "objective": "Exercise orchestrator next-stage routing"},
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
