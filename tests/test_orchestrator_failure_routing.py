import pytest

from jeff.action import Outcome
from jeff.cognitive import EvaluationResult, ProposalOption, ProposalSet, SelectionResult, assemble_context_package
from jeff.cognitive.types import TriggerInput
from jeff.contracts import Action
from jeff.core.schemas import Scope
from jeff.core.state import bootstrap_global_state
from jeff.core.transition import TransitionRequest, apply_transition
from jeff.governance import CurrentTruthSnapshot, Policy, evaluate_action_entry
from jeff.orchestrator import run_flow
from jeff.orchestrator.routing import route_evaluation_followup


def _scope() -> Scope:
    return Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1")


def _state():
    scope = _scope()
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
            payload={"work_unit_id": str(scope.work_unit_id), "objective": "Route failures lawfully"},
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


def _blocked_flow_handlers():
    scope = _scope()
    state = _state()

    def context_stage(_):
        return assemble_context_package(
            trigger=TriggerInput(trigger_summary="Drive the blocked path"),
            purpose="proposal support",
            scope=scope,
            state=state,
        )

    def proposal_stage(_context):
        return ProposalSet(
            scope=scope,
            options=(
                ProposalOption(
                    proposal_id="proposal-1",
                    proposal_type="direct_action",
                    option_summary="Attempt the blocked action",
                    scope=scope,
                ),
            ),
            scarcity_reason="Only one blocked bounded option exists.",
        )

    def selection_stage(proposal_set):
        return SelectionResult(
            selection_id="selection-1",
            considered_proposal_ids=tuple(option.proposal_id for option in proposal_set.options),
            selected_proposal_id="proposal-1",
            rationale="The blocked option is still the only bounded path.",
        )

    def action_stage(_selection):
        return Action(
            action_id="action-1",
            scope=scope,
            intent_summary="Attempt the blocked action",
            basis_state_version=3,
        )

    def governance_stage(action):
        return evaluate_action_entry(
            action=action,
            policy=Policy(),
            approval=None,
            truth=CurrentTruthSnapshot(
                scope=scope,
                state_version=3,
                blocked_reasons=("target is currently blocked by integrity checks",),
            ),
        )

    return {
        "context": context_stage,
        "proposal": proposal_stage,
        "selection": selection_stage,
        "action": action_stage,
        "governance": governance_stage,
    }


def test_blocked_governance_routes_with_reason_and_scope() -> None:
    result = run_flow(
        flow_id="flow-blocked",
        flow_family="blocked_or_escalation",
        scope=_scope(),
        stage_handlers=_blocked_flow_handlers(),
    )

    assert result.lifecycle.lifecycle_state == "blocked"
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "blocked"
    assert result.routing_decision.source_stage == "governance"
    assert result.routing_decision.scope == _scope()
    assert "integrity checks" in result.routing_decision.reason_summary
    assert "execution" not in result.outputs


def test_escalated_governance_routes_with_reason_and_scope() -> None:
    scope = _scope()
    state = _state()

    def context_stage(_):
        return assemble_context_package(
            trigger=TriggerInput(trigger_summary="Drive the escalated path"),
            purpose="proposal support",
            scope=scope,
            state=state,
        )

    def proposal_stage(_context):
        return ProposalSet(
            scope=scope,
            options=(
                ProposalOption(
                    proposal_id="proposal-1",
                    proposal_type="direct_action",
                    option_summary="Attempt the escalated action",
                    scope=scope,
                ),
            ),
            scarcity_reason="Only one escalated bounded option exists.",
        )

    def selection_stage(proposal_set):
        return SelectionResult(
            selection_id="selection-1",
            considered_proposal_ids=tuple(option.proposal_id for option in proposal_set.options),
            selected_proposal_id="proposal-1",
            rationale="The escalated option is still the only bounded path.",
        )

    def action_stage(_selection):
        return Action(
            action_id="action-1",
            scope=scope,
            intent_summary="Attempt the escalated action",
            basis_state_version=3,
        )

    def governance_stage(action):
        return evaluate_action_entry(
            action=action,
            policy=Policy(),
            approval=None,
            truth=CurrentTruthSnapshot(scope=scope, state_version=3, truth_mismatch=True),
        )

    result = run_flow(
        flow_id="flow-escalated",
        flow_family="blocked_or_escalation",
        scope=scope,
        stage_handlers={
            "context": context_stage,
            "proposal": proposal_stage,
            "selection": selection_stage,
            "action": action_stage,
            "governance": governance_stage,
        },
    )

    assert result.lifecycle.lifecycle_state == "escalated"
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "escalated"
    assert result.routing_decision.source_stage == "governance"
    assert result.routing_decision.scope == scope
    assert any(event.event_type == "flow_escalated" for event in result.events)


@pytest.mark.parametrize(
    ("recommended_next_step", "expected_route_kind", "expected_outcome", "expected_lifecycle"),
    [
        ("retry", "follow_up", "retry", "completed"),
        ("revalidate", "follow_up", "revalidate", "completed"),
        ("recover", "follow_up", "recover", "completed"),
        ("terminate_and_replan", "follow_up", "terminate_and_replan", "completed"),
        ("request_clarification", "hold", "request_clarification", "waiting"),
        ("escalate", "hold", "escalated", "escalated"),
    ],
)
def test_evaluation_followup_routing_remains_non_authorizing(
    recommended_next_step: str,
    expected_route_kind: str,
    expected_outcome: str,
    expected_lifecycle: str,
) -> None:
    evaluation = EvaluationResult(
        objective_summary="Judge the bounded result",
        outcome=Outcome(
            action_id="action-1",
            scope=_scope(),
            outcome_state="inconclusive",
            observed_completion_posture="insufficient evidence",
            target_effect_posture="unknown",
            artifact_posture="uncertain",
            side_effect_posture="contained",
            uncertainty_markers=("evidence gap",),
        ),
        evaluation_verdict="inconclusive",
        rationale="The next lawful move is a routed follow-up, not automatic execution.",
        recommended_next_step=recommended_next_step,  # type: ignore[arg-type]
    )

    direct_route = route_evaluation_followup(evaluation=evaluation, scope=_scope())
    result = run_flow(
        flow_id=f"flow-followup-{recommended_next_step}",
        flow_family="evaluation_driven_followup",
        scope=_scope(),
        stage_handlers={"evaluation": lambda _input: evaluation},
    )

    assert direct_route is not None
    assert direct_route.auto_execute is False
    assert direct_route.route_kind == expected_route_kind
    assert direct_route.routed_outcome == expected_outcome
    assert result.routing_decision is not None
    assert result.routing_decision.auto_execute is False
    assert result.lifecycle.lifecycle_state == expected_lifecycle
