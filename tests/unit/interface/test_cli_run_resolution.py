import pytest

import jeff.interface.commands as commands_module
from jeff.interface.commands.support.flow_runs import _canonical_run_lifecycle_state

from jeff.interface import InterfaceContext, JeffCLI

from tests.fixtures.cli import build_flow_run, build_state_with_runs


def test_inspect_auto_binds_existing_run_in_selected_work_unit() -> None:
    state, scope = build_state_with_runs()
    flow_run = build_flow_run(scope)
    cli = JeffCLI(context=InterfaceContext(state=state, flow_runs={str(scope.run_id): flow_run}))

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")

    text = cli.run_one_shot("/inspect")

    assert "auto-selected current run: run-1" in text
    assert "RUN run-1" in text
    assert "[support][live_context] purpose=operator explanation proposal support CLI coverage" in text
    assert "[support][live_context] truth_families=project,work_unit,run" in text
    assert "[support][proposal] serious_option_count=2" in text
    assert cli.session.scope.run_id == "run-1"
    assert "run-1" in cli.execute("/inspect").context.selection_reviews


def test_inspect_creates_new_run_through_transition_path_when_none_exist() -> None:
    state, _ = build_state_with_runs(run_specs=())
    cli = JeffCLI(context=InterfaceContext(state=state))

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    text = cli.run_one_shot("/inspect")

    assert "created and selected new run: run-1" in text
    assert "RUN run-1" in text
    assert "[support][live_context] purpose=operator explanation proposal support CLI coverage" in text
    assert "[support][live_context] truth_families=project,work_unit,run" in text
    assert "[derived] no orchestrator flow is attached to this run" in text
    assert cli.session.scope.run_id == "run-1"
    assert '"run_id": "run-1"' in cli.run_one_shot("/show", json_output=True)
    assert "- run-1 lifecycle=created" in cli.run_one_shot("/run list")


def test_inspect_calls_live_context_assembly_once_for_the_selected_run(monkeypatch) -> None:
    state, scope = build_state_with_runs()
    flow_run = build_flow_run(scope)
    cli = JeffCLI(context=InterfaceContext(state=state, flow_runs={str(scope.run_id): flow_run}))
    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")

    call_count = {"value": 0}
    original = commands_module.assemble_live_context_package

    def _counting_live_context(**kwargs):
        call_count["value"] += 1
        return original(**kwargs)

    monkeypatch.setattr(commands_module, "assemble_live_context_package", _counting_live_context)

    result = cli.execute("/inspect")

    assert call_count["value"] == 1
    assert result.json_payload is not None
    assert result.json_payload["view"] == "run_show"


def test_historical_show_requires_explicit_run_when_multiple_runs_exist() -> None:
    state, scope = build_state_with_runs(run_specs=(("run-1", "created"), ("run-2", "created")))
    flow_run = build_flow_run(scope)
    cli = JeffCLI(context=InterfaceContext(state=state, flow_runs={str(scope.run_id): flow_run}))

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")

    with pytest.raises(ValueError, match="found multiple runs in work_unit wu-1"):
        cli.run_one_shot("/show")

    assert cli.session.scope.run_id is None


def test_historical_commands_do_not_create_new_run_when_no_run_exists() -> None:
    state, _ = build_state_with_runs(run_specs=())
    cli = JeffCLI(context=InterfaceContext(state=state))

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")

    with pytest.raises(ValueError, match="Use /inspect to create and select a new run"):
        cli.run_one_shot("/show")

    assert cli.session.scope.run_id is None
    assert "- none" in cli.run_one_shot("/run list")


def test_inspect_requires_explicit_run_when_multiple_runs_exist() -> None:
    state, scope = build_state_with_runs(run_specs=(("run-1", "created"), ("run-2", "created")))
    flow_run = build_flow_run(scope)
    cli = JeffCLI(context=InterfaceContext(state=state, flow_runs={str(scope.run_id): flow_run}))

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")

    with pytest.raises(ValueError, match="inspect found multiple runs in work_unit wu-1"):
        cli.run_one_shot("/inspect")

    assert cli.session.scope.run_id is None


def test_selecting_different_work_unit_clears_incompatible_current_run() -> None:
    state, _ = build_state_with_runs(run_specs=())
    state = _add_work_unit(state, work_unit_id="wu-2", objective="Second bounded effort")
    cli = JeffCLI(context=InterfaceContext(state=state))

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    cli.run_one_shot("/inspect")

    assert cli.session.scope.run_id == "run-1"

    cli.run_one_shot("/work use wu-2")

    assert cli.session.scope.work_unit_id == "wu-2"
    assert cli.session.scope.run_id is None


def test_help_text_marks_run_commands_as_manual_history_debug_path() -> None:
    state, _ = build_state_with_runs()
    cli = JeffCLI(context=InterfaceContext(state=state))

    text = cli.run_one_shot("/help")

    assert "Primary flow:" in text
    assert "- /run <repo-local-validation-objective>" in text
    assert "/run runs one bounded repo-local pytest validation plan under the current model configuration." in text
    assert "History/debug:" in text
    assert "- /run list" in text
    assert "- /run use <run_id>" in text


def test_canonical_run_lifecycle_state_marks_non_execution_defer_as_deferred() -> None:
    _, scope = build_state_with_runs()
    flow_run = build_flow_run(
        scope,
        lifecycle_state="waiting",
        current_stage="selection",
        approval_required=True,
        approval_granted=False,
        routed_outcome="defer",
        route_kind="hold",
        route_reason="Selection deferred bounded execution for operator follow-up.",
    )

    assert _canonical_run_lifecycle_state(flow_run) == "deferred"


def test_canonical_run_lifecycle_state_marks_failed_pre_execution_truthfully() -> None:
    _, scope = build_state_with_runs()
    flow_run = build_flow_run(
        scope,
        lifecycle_state="failed",
        current_stage="proposal",
        approval_required=True,
        approval_granted=False,
        reason_summary="proposal validation rejected live provider output (forbidden authority language). /run cannot proceed; try /research docs for inspection instead.",
    )

    assert _canonical_run_lifecycle_state(flow_run) == "failed_before_execution"


def test_run_command_requires_runtime_configuration_for_objective_launch() -> None:
    state, _ = build_state_with_runs()
    cli = JeffCLI(context=InterfaceContext(state=state))

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")

    with pytest.raises(ValueError, match="run objective launch requires configured InfrastructureServices"):
        cli.run_one_shot("/run compare heat pump options")


def _add_work_unit(state: object, *, work_unit_id: str, objective: str) -> object:
    from jeff.core.schemas import Scope
    from jeff.core.transition import TransitionRequest, apply_transition

    return apply_transition(
        state,
        TransitionRequest(
            transition_id=f"transition-add-{work_unit_id}",
            transition_type="create_work_unit",
            basis_state_version=state.state_meta.state_version,
            scope=Scope(project_id="project-1"),
            payload={"work_unit_id": work_unit_id, "objective": objective},
        ),
    ).state
