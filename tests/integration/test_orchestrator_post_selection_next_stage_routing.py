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


def test_research_followup_branch_enters_research_and_holds_as_decision_support_ready(monkeypatch) -> None:
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
            "research": _research_stage(call_counts, sufficient=True),
            "action": _action_stage(scope, call_counts),
            "governance": _governance_stage(scope, call_counts),
        },
    )

    assert resolve_calls["count"] == 1
    assert result.lifecycle.lifecycle_state == "waiting"
    assert result.lifecycle.current_stage == "research"
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "research_followup"
    assert result.routing_decision.source_stage == "research"
    assert "Research entered and produced a bounded research artifact" in result.routing_decision.reason_summary
    assert "Sufficiency evaluation: decision_support_ready." in result.routing_decision.reason_summary
    assert "Current research is sufficient for bounded downstream decision support" in result.routing_decision.reason_summary
    assert "no governance evaluation occurred" in result.routing_decision.reason_summary
    assert "no action permission exists" in result.routing_decision.reason_summary
    assert call_counts == {"research": 1, "action": 0, "governance": 0}
    assert "research" in result.outputs
    assert isinstance(result.outputs["research"], ResearchArtifact)
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

    monkeypatch.setattr(runner_module, "evaluate_research_output_sufficiency", _fail_if_called)

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

    monkeypatch.setattr(runner_module, "evaluate_research_output_sufficiency", _fail_if_called)

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
