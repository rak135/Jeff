from jeff.interface import JeffCLI

from tests.fixtures.cli import build_interface_context, build_interface_context_with_flow


def test_session_scope_changes_do_not_mutate_canonical_state() -> None:
    context, _ = build_interface_context_with_flow()
    state_before = context.state

    cli = JeffCLI(context=context)
    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    cli.run_one_shot("/run use run-1")

    assert cli.session.scope.project_id == "project-1"
    assert cli.session.scope.work_unit_id == "wu-1"
    assert cli.session.scope.run_id == "run-1"
    assert context.state is state_before
    assert tuple(context.state.projects.keys()) == ("project-1",)


def test_interactive_and_one_shot_modes_share_command_semantics() -> None:
    context, _ = build_interface_context()

    one_shot_cli = JeffCLI(context=context)
    one_shot_cli.run_one_shot("/project use project-1")
    one_shot_cli.run_one_shot("/work use wu-1")
    one_shot_cli.run_one_shot("/run use run-1")
    one_shot_scope = one_shot_cli.run_one_shot("/scope show")

    interactive_cli = JeffCLI(context=context)
    outputs = interactive_cli.run_interactive(
        [
            "/project use project-1",
            "/work use wu-1",
            "/run use run-1",
            "/scope show",
        ]
    )

    assert outputs[-1] == one_shot_scope
    assert interactive_cli.prompt == "jeff:/project-1/wu-1>"


def test_scope_clear_resets_local_session_scope_only() -> None:
    context, _ = build_interface_context()
    cli = JeffCLI(context=context)

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    cli.run_one_shot("/run use run-1")
    cli.run_one_shot("/scope clear")

    assert cli.session.scope.project_id is None
    assert cli.session.scope.work_unit_id is None
    assert cli.session.scope.run_id is None
    assert "project-1" in context.state.projects


def test_scope_show_guides_operator_toward_next_valid_scope_step() -> None:
    context, _ = build_interface_context()
    cli = JeffCLI(context=context)

    text = cli.run_one_shot("/scope show")
    assert "[hint] next=/project list then /project use <project_id>" in text

    cli.run_one_shot("/project use project-1")
    text = cli.run_one_shot("/scope show")
    assert "[hint] next=/work list then /work use <work_unit_id>" in text

    cli.run_one_shot("/work use wu-1")
    text = cli.run_one_shot("/scope show")
    assert "[hint] next=/inspect (auto-selects or creates a run) or /run list for manual history/debug" in text
