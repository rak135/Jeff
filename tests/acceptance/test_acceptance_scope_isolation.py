import pytest

from jeff.cognitive import ProposalResult, ProposalResultOption, SelectionResult, assemble_context_package
from jeff.cognitive.types import TriggerInput
from jeff.contracts import Action
from jeff.core.schemas import Scope
from jeff.core.state import bootstrap_global_state
from jeff.core.transition import TransitionRequest, apply_transition
from jeff.interface import InterfaceContext, JeffCLI
from jeff.orchestrator import run_flow


def _proposal_result(*, scope):
    return ProposalResult(
        request_id="proposal-request-1",
        scope=scope,
        options=(
            ProposalResultOption(
                option_index=1,
                proposal_id="proposal-1",
                proposal_type="direct_action",
                title="Attempt the action.",
                why_now="This is the only bounded path under current scope.",
                summary="Attempt the action.",
                constraints=("Stay inside current project scope",),
            ),
        ),
        scarcity_reason="Only one serious bounded option is available.",
    )


def _state_with_projects_and_runs(*, duplicate_run_ids: bool) -> object:
    state = bootstrap_global_state()
    project_specs = (
        ("project-1", "Alpha", "wu-1", "run-1"),
        ("project-2", "Beta", "wu-2", "run-1" if duplicate_run_ids else "run-2"),
    )
    for project_id, name, work_unit_id, run_id in project_specs:
        state = apply_transition(
            state,
            TransitionRequest(
                transition_id=f"transition-{project_id}",
                transition_type="create_project",
                basis_state_version=state.state_meta.state_version,
                scope=Scope(project_id=project_id),
                payload={"name": name},
            ),
        ).state
        state = apply_transition(
            state,
            TransitionRequest(
                transition_id=f"transition-{work_unit_id}",
                transition_type="create_work_unit",
                basis_state_version=state.state_meta.state_version,
                scope=Scope(project_id=project_id),
                payload={"work_unit_id": work_unit_id, "objective": f"Work in {name}"},
            ),
        ).state
        state = apply_transition(
            state,
            TransitionRequest(
                transition_id=f"transition-{project_id}-{run_id}",
                transition_type="create_run",
                basis_state_version=state.state_meta.state_version,
                scope=Scope(project_id=project_id, work_unit_id=work_unit_id),
                payload={"run_id": run_id},
            ),
        ).state
    return state


def test_wrong_scope_flow_is_invalidated_cleanly() -> None:
    state = _state_with_projects_and_runs(duplicate_run_ids=False)
    flow_scope = Scope(project_id="project-1", work_unit_id="wu-1")
    wrong_scope = Scope(project_id="project-2", work_unit_id="wu-2")

    result = run_flow(
        flow_id="flow-wrong-scope",
        flow_family="blocked_or_escalation",
        scope=flow_scope,
        stage_handlers={
            "context": lambda _input: assemble_context_package(
                trigger=TriggerInput(trigger_summary="Attempt a wrong-project action."),
                purpose="bounded decision support",
                scope=flow_scope,
                state=state,
            ),
            "proposal": lambda _context: _proposal_result(scope=flow_scope),
            "selection": lambda _proposal: SelectionResult(
                selection_id="selection-1",
                considered_proposal_ids=("proposal-1",),
                selected_proposal_id="proposal-1",
                rationale="Use the selected option.",
            ),
            "action": lambda _selection: Action(
                action_id="action-1",
                scope=wrong_scope,
                intent_summary="This action points at the wrong project.",
                basis_state_version=state.state_meta.state_version,
            ),
            "governance": lambda _action: pytest.fail("governance should not run"),
        },
    )

    assert result.lifecycle.lifecycle_state == "invalidated"
    assert tuple(result.outputs.keys()) == ("context", "proposal", "selection")
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "invalidated"


def test_cli_rejects_wrong_project_run_lookup_under_current_scope() -> None:
    state = _state_with_projects_and_runs(duplicate_run_ids=False)
    cli = JeffCLI(context=InterfaceContext(state=state))
    cli.run_one_shot("/project use project-2")

    with pytest.raises(ValueError, match="current project scope"):
        cli.run_one_shot("/show run-1")


def test_cli_rejects_ambiguous_global_run_lookup_without_scope() -> None:
    state = _state_with_projects_and_runs(duplicate_run_ids=True)
    cli = JeffCLI(context=InterfaceContext(state=state))

    with pytest.raises(ValueError, match="ambiguous run_id"):
        cli.run_one_shot("/show run-1")
