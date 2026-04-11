from jeff.action import GovernedExecutionRequest, normalize_outcome
from jeff.action.execution import ExecutionResult
from jeff.cognitive import ProposalOption, ProposalSet, SelectionResult, assemble_context_package, evaluate_outcome
from jeff.cognitive.types import TriggerInput
from jeff.contracts import Action
from jeff.core.schemas import Scope
from jeff.core.state import bootstrap_global_state
from jeff.core.transition import TransitionRequest, TransitionResult, apply_transition
from jeff.governance import CurrentTruthSnapshot, Policy, evaluate_action_entry
from jeff.memory import InMemoryMemoryStore, MemorySupportRef, create_memory_candidate, write_memory_candidate
from jeff.orchestrator import run_flow, stage_order_for_flow


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
            payload={"work_unit_id": str(scope.work_unit_id), "objective": "Trace orchestration"},
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


def test_trace_events_are_emitted_in_stable_stage_order() -> None:
    scope = _scope()
    state = _state()
    store = InMemoryMemoryStore()

    def context_stage(_):
        return assemble_context_package(
            trigger=TriggerInput(trigger_summary="Trace the standard flow"),
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
                    option_summary="Trace the standard flow",
                    scope=scope,
                ),
            ),
            scarcity_reason="Only one bounded tracing option exists.",
        )

    def selection_stage(proposal_set):
        return SelectionResult(
            selection_id="selection-1",
            considered_proposal_ids=tuple(option.proposal_id for option in proposal_set.options),
            selected_proposal_id="proposal-1",
            rationale="The trace flow has one bounded option.",
        )

    def action_stage(_selection):
        return Action(
            action_id="action-1",
            scope=scope,
            intent_summary="Trace the standard flow",
            basis_state_version=3,
        )

    def governance_stage(action):
        return evaluate_action_entry(
            action=action,
            policy=Policy(),
            approval=None,
            truth=CurrentTruthSnapshot(scope=scope, state_version=3),
        )

    def execution_stage(governance):
        action = Action(
            action_id="action-1",
            scope=scope,
            intent_summary="Trace the standard flow",
            basis_state_version=3,
        )
        return ExecutionResult(
            governed_request=GovernedExecutionRequest(action=action, governance_decision=governance),
            execution_status="completed",
            output_summary="Execution completed",
        )

    def outcome_stage(execution):
        return normalize_outcome(
            execution_result=execution,
            outcome_state="complete",
            observed_completion_posture="completed",
            target_effect_posture="target reached",
            artifact_posture="artifact not required",
            side_effect_posture="contained",
        )

    def evaluation_stage(outcome):
        return evaluate_outcome(
            objective_summary="Trace the standard flow",
            outcome=outcome,
            evidence_quality_posture="strong",
        )

    def memory_stage(_evaluation):
        candidate = create_memory_candidate(
            candidate_id="candidate-1",
            memory_type="operational",
            scope=scope,
            summary="Trace events should preserve stable stage order",
            remembered_points=("The orchestrator emits ordered stage_entered and stage_exited events.",),
            why_it_matters="Stable trace order is needed for later truthful CLI surfaces.",
            support_refs=(
                MemorySupportRef(
                    ref_kind="evaluation",
                    ref_id="evaluation-1",
                    summary="Evaluation confirmed the flow completed",
                ),
            ),
            support_quality="strong",
            stability="stable",
        )
        return write_memory_candidate(candidate=candidate, store=store)

    def transition_stage(_memory_write):
        return TransitionResult(
            transition_id="transition-final",
            transition_result="committed",
            state_before_version=3,
            state_after_version=4,
            state=state,
            changed_paths=("projects.project-1.work_units.wu-1.runs.run-1",),
        )

    result = run_flow(
        flow_id="flow-trace",
        flow_family="bounded_proposal_selection_action",
        scope=scope,
        stage_handlers={
            "context": context_stage,
            "proposal": proposal_stage,
            "selection": selection_stage,
            "action": action_stage,
            "governance": governance_stage,
            "execution": execution_stage,
            "outcome": outcome_stage,
            "evaluation": evaluation_stage,
            "memory": memory_stage,
            "transition": transition_stage,
        },
    )

    entered_stages = [event.stage for event in result.events if event.event_type == "stage_entered"]
    exited_stages = [event.stage for event in result.events if event.event_type == "stage_exited"]

    assert result.lifecycle.lifecycle_state == "completed"
    assert entered_stages == list(stage_order_for_flow("bounded_proposal_selection_action"))
    assert exited_stages == list(stage_order_for_flow("bounded_proposal_selection_action"))
    assert [event.ordinal for event in result.events] == list(range(1, len(result.events) + 1))
    assert result.events[0].event_type == "flow_started"
    assert result.events[-1].event_type == "flow_completed"


def test_lifecycle_state_changes_stay_orchestration_local() -> None:
    scope = _scope()
    state = _state()

    def context_stage(_):
        return assemble_context_package(
            trigger=TriggerInput(trigger_summary="Hold at governance"),
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
                    option_summary="Hold at governance",
                    scope=scope,
                ),
            ),
            scarcity_reason="Only one bounded option exists here.",
        )

    def selection_stage(proposal_set):
        return SelectionResult(
            selection_id="selection-1",
            considered_proposal_ids=tuple(option.proposal_id for option in proposal_set.options),
            selected_proposal_id="proposal-1",
            rationale="The hold path still selects one bounded option.",
        )

    def action_stage(_selection):
        return Action(
            action_id="action-1",
            scope=scope,
            intent_summary="Hold at governance",
            basis_state_version=3,
        )

    def governance_stage(action):
        return evaluate_action_entry(
            action=action,
            policy=Policy(approval_required=True),
            approval=None,
            truth=CurrentTruthSnapshot(scope=scope, state_version=3),
        )

    result = run_flow(
        flow_id="flow-lifecycle",
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

    assert result.lifecycle.lifecycle_state == "waiting"
    assert result.lifecycle.current_stage == "governance"
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "approval_required"
    assert "transition" not in result.outputs
