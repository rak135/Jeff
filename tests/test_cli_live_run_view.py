from jeff.interface import JeffCLI

from tests.cli_test_helpers import build_interface_context_with_flow


def test_live_run_view_shows_flow_family_stage_module_and_health() -> None:
    context, _ = build_interface_context_with_flow(lifecycle_state="active", current_stage="execution")
    cli = JeffCLI(context=context)
    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    cli.run_one_shot("/run use run-1")

    text = cli.run_one_shot("/show")

    assert "flow_family=bounded_proposal_selection_action" in text
    assert "active_stage=execution active_module=action" in text
    assert "health_posture=ok" in text
    assert "[support] recent_events" in text


def test_trace_view_reflects_orchestrator_stage_order_honestly() -> None:
    context, _ = build_interface_context_with_flow(lifecycle_state="active", current_stage="execution")
    cli = JeffCLI(context=context)
    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    cli.run_one_shot("/run use run-1")

    text = cli.run_one_shot("/trace")

    lines = text.splitlines()
    assert lines[0] == "TRACE flow_id=flow-1 run_id=run-1"
    assert "1. stage=- type=flow_started summary=flow started" in lines[1]
    assert "2. stage=context type=stage_entered summary=entered context" in lines[2]
    assert "3. stage=proposal type=stage_entered summary=entered proposal" in lines[3]


def test_lifecycle_view_preserves_escalated_posture() -> None:
    context, _ = build_interface_context_with_flow(
        lifecycle_state="escalated",
        current_stage="governance",
        reason_summary="truth mismatch requires operator judgment",
    )
    cli = JeffCLI(context=context)
    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    cli.run_one_shot("/run use run-1")

    text = cli.run_one_shot("/lifecycle")

    assert "lifecycle_state=escalated" in text
    assert "reason_summary=truth mismatch requires operator judgment" in text
    assert "health_posture=escalated" in text
