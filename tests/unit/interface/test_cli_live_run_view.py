from jeff.interface import JeffCLI

from tests.fixtures.cli import build_interface_context_with_flow


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


def test_show_emits_request_entry_hint_only_for_approval_required_runs() -> None:
    context, _ = build_interface_context_with_flow(
        flow_family="blocked_or_escalation",
        lifecycle_state="waiting",
        current_stage="governance",
        approval_required=True,
        approval_granted=False,
        routed_outcome="approval_required",
        route_reason="required approval is absent",
    )
    cli = JeffCLI(context=context)
    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    cli.run_one_shot("/run use run-1")

    text = cli.run_one_shot("/show")

    assert "[next] request_entry=/approve run-1 | /reject run-1" in text


def test_show_emits_revalidate_hint_only_when_revalidation_is_lawful() -> None:
    context, _ = build_interface_context_with_flow(
        flow_family="blocked_or_escalation",
        lifecycle_state="waiting",
        current_stage="governance",
        approval_required=True,
        approval_granted=True,
        routed_outcome="revalidate",
        route_reason="bounded approval recorded; explicit /revalidate is required before execution continues",
    )
    cli = JeffCLI(context=context)
    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    cli.run_one_shot("/run use run-1")

    text = cli.run_one_shot("/show")

    assert "[next] request_entry=/reject run-1 | /revalidate run-1" in text


def test_show_omits_request_entry_hint_for_ordinary_runs() -> None:
    context, _ = build_interface_context_with_flow(lifecycle_state="completed", current_stage="evaluation")
    cli = JeffCLI(context=context)
    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    cli.run_one_shot("/run use run-1")

    text = cli.run_one_shot("/show")

    assert "[next] request_entry=" not in text
    assert "[next] receipt_only_request_entry=" not in text
