from jeff.action import GovernedExecutionRequest, normalize_outcome
from jeff.action.execution import ExecutionResult
from jeff.cognitive import ProposalOption, ProposalSet, SelectionResult, assemble_context_package, evaluate_outcome
from jeff.cognitive.types import TriggerInput
from jeff.contracts import Action
from jeff.core.schemas import Scope
from jeff.core.state import bootstrap_global_state
from jeff.core.transition import TransitionRequest, apply_transition
from jeff.governance import CurrentTruthSnapshot, Policy, evaluate_action_entry
from jeff.memory import InMemoryMemoryStore, MemorySupportRef, create_memory_candidate, write_memory_candidate
from jeff.orchestrator import run_flow


def _base_state() -> object:
    state = bootstrap_global_state()
    state = apply_transition(
        state,
        TransitionRequest(
            transition_id="transition-project",
            transition_type="create_project",
            basis_state_version=0,
            scope=Scope(project_id="project-1"),
            payload={"name": "Alpha"},
        ),
    ).state
    state = apply_transition(
        state,
        TransitionRequest(
            transition_id="transition-work-unit",
            transition_type="create_work_unit",
            basis_state_version=1,
            scope=Scope(project_id="project-1"),
            payload={"work_unit_id": "wu-1", "objective": "Backbone acceptance flow"},
        ),
    ).state
    return state


def test_bounded_backbone_flow_stays_lawful_end_to_end() -> None:
    state = _base_state()
    scope = Scope(project_id="project-1", work_unit_id="wu-1")
    store = InMemoryMemoryStore()
    action_cache: dict[str, Action] = {}

    def context_stage(_input):
        return assemble_context_package(
            trigger=TriggerInput(trigger_summary="Drive one lawful acceptance slice."),
            purpose="bounded decision support",
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
                    option_summary="Create the bounded acceptance run.",
                    scope=scope,
                ),
            ),
            scarcity_reason="Only one serious bounded option is available.",
        )

    def selection_stage(_proposal):
        return SelectionResult(
            selection_id="selection-1",
            considered_proposal_ids=("proposal-1",),
            selected_proposal_id="proposal-1",
            rationale="The bounded run-creation path fits the current objective.",
        )

    def action_stage(_selection):
        action = Action(
            action_id="action-1",
            scope=scope,
            intent_summary="Carry the lawful acceptance slice to completion.",
            basis_state_version=state.state_meta.state_version,
        )
        action_cache["action"] = action
        return action

    def governance_stage(action):
        return evaluate_action_entry(
            action=action,
            policy=Policy(),
            approval=None,
            truth=CurrentTruthSnapshot(scope=scope, state_version=state.state_meta.state_version),
        )

    def execution_stage(governance):
        return ExecutionResult(
            governed_request=GovernedExecutionRequest(
                action=action_cache["action"],
                governance_decision=governance,
            ),
            execution_status="completed",
            output_summary="Execution completed the bounded acceptance slice.",
        )

    def outcome_stage(execution):
        return normalize_outcome(
            execution_result=execution,
            outcome_state="complete",
            observed_completion_posture="execution completed",
            target_effect_posture="target reached",
            artifact_posture="artifact present",
            side_effect_posture="contained",
        )

    def evaluation_stage(outcome):
        return evaluate_outcome(
            objective_summary="Complete one lawful backbone slice",
            outcome=outcome,
            evidence_quality_posture="strong",
        )

    def memory_stage(evaluation):
        candidate = create_memory_candidate(
            candidate_id="candidate-1",
            memory_type="operational",
            scope=scope,
            summary="The bounded backbone slice completed lawfully.",
            remembered_points=("Governance, execution, outcome, and evaluation remained distinct.",),
            why_it_matters="This anchors bounded continuity without becoming current truth.",
            support_refs=(
                MemorySupportRef(
                    ref_kind="evaluation",
                    ref_id="evaluation-1",
                    summary="Evaluation verified the bounded slice.",
                ),
            ),
            support_quality="strong",
            stability="stable",
        )
        return write_memory_candidate(candidate=candidate, store=store)

    def transition_stage(_memory):
        return apply_transition(
            state,
            TransitionRequest(
                transition_id="transition-acceptance-run",
                transition_type="create_run",
                basis_state_version=state.state_meta.state_version,
                scope=scope,
                payload={"run_id": "run-acceptance-1"},
            ),
        )

    result = run_flow(
        flow_id="flow-acceptance",
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

    assert result.lifecycle.lifecycle_state == "completed"
    assert tuple(result.outputs.keys()) == (
        "context",
        "proposal",
        "selection",
        "action",
        "governance",
        "execution",
        "outcome",
        "evaluation",
        "memory",
        "transition",
    )
    assert result.outputs["governance"].allowed_now is True
    assert result.outputs["execution"].execution_status == "completed"
    assert result.outputs["outcome"].outcome_state == "complete"
    assert result.outputs["evaluation"].evaluation_verdict == "acceptable"
    assert result.outputs["memory"].write_outcome == "write"
    assert result.outputs["transition"].transition_result == "committed"
    assert "run-acceptance-1" in result.outputs["transition"].state.projects["project-1"].work_units["wu-1"].runs
    assert result.routing_decision is None
