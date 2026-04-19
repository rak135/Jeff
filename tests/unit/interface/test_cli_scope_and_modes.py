from jeff.interface import CliSession, JeffCLI, SessionScope
import json

from tests.fixtures.cli import build_interface_context, build_interface_context_with_flow


def test_session_scope_changes_do_not_mutate_canonical_state() -> None:
    context, _ = build_interface_context_with_flow()
    state_before = context.state

    cli = JeffCLI(context=context)
    project_text = cli.run_one_shot("/project use project-1")
    work_text = cli.run_one_shot("/work use wu-1")
    run_text = cli.run_one_shot("/run use run-1")

    assert cli.session.scope.project_id == "project-1"
    assert cli.session.scope.work_unit_id == "wu-1"
    assert cli.session.scope.run_id == "run-1"
    assert "process-local only" in project_text
    assert "process-local only" in work_text
    assert "process-local only" in run_text
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
    text = cli.run_one_shot("/scope clear")

    assert cli.session.scope.project_id is None
    assert cli.session.scope.work_unit_id is None
    assert cli.session.scope.run_id is None
    assert text == "session scope cleared (process-local only)"
    assert "project-1" in context.state.projects


def test_scope_show_guides_operator_toward_next_valid_scope_step() -> None:
    context, _ = build_interface_context()
    cli = JeffCLI(context=context)

    text = cli.run_one_shot("/scope show")
    assert "scope_model=session-local/process-local only" in text
    assert "outer flags: --project <project_id> --work <work_unit_id> --run <run_id>" in text
    assert "[hint] next=/project list then /project use <project_id>" in text

    cli.run_one_shot("/project use project-1")
    text = cli.run_one_shot("/scope show")
    assert "[hint] next=/work list then /work use <work_unit_id>" in text

    cli.run_one_shot("/work use wu-1")
    text = cli.run_one_shot("/scope show")
    assert "[hint] next=/inspect (creates a run when none exists) or /run list then /run use <run_id>" in text


def test_scope_show_json_surfaces_process_local_scope_model_and_outer_flags() -> None:
    context, _ = build_interface_context()
    cli = JeffCLI(context=context)

    payload = json.loads(cli.run_one_shot("/scope show", json_output=True))

    assert payload["view"] == "scope"
    assert payload["support"]["scope_model"] == "session-local/process-local only"
    assert payload["support"]["one_shot_scope_flags"] == ["--project", "--work", "--run"]


def test_seeded_session_scope_is_local_only_and_does_not_mutate_canonical_state() -> None:
    context, _ = build_interface_context_with_flow()
    state_before = context.state
    cli = JeffCLI(
        context=context,
        session=CliSession(scope=SessionScope(project_id="project-1", work_unit_id="wu-1", run_id="run-1")),
    )

    text = cli.run_one_shot("/show")

    assert "RUN run-1" in text
    assert cli.session.scope.run_id == "run-1"
    assert context.state is state_before


def test_help_text_explains_session_local_scope_and_json_scope() -> None:
    context, _ = build_interface_context()
    cli = JeffCLI(context=context)

    text = cli.run_one_shot("/help")

    assert "Session scope is session-local/process-local only." in text
    assert "One-shot --json applies to one-shot output only." in text
