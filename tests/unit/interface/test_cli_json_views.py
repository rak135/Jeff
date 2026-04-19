import json

from jeff.interface import JeffCLI

from tests.fixtures.cli import build_interface_context_with_flow


def test_show_json_view_preserves_truth_support_and_derived_distinctions() -> None:
    context, _ = build_interface_context_with_flow(current_stage="execution", lifecycle_state="active")
    cli = JeffCLI(context=context)
    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    cli.run_one_shot("/run use run-1")

    payload = json.loads(cli.run_one_shot("/show", json_output=True))

    assert payload["view"] == "run_show"
    assert "truth" in payload
    assert "derived" in payload
    assert "support" in payload
    assert "telemetry" in payload
    assert "run_lifecycle_state" in payload["truth"]
    assert payload["truth"]["last_execution_status"] == "completed"
    assert payload["truth"]["last_outcome_state"] == "complete"
    assert payload["truth"]["last_evaluation_verdict"] == "acceptable"
    assert "selected_proposal_id" in payload["derived"]
    assert "governance_outcome" in payload["derived"]
    assert "recent_events" in payload["support"]
    assert payload["support"]["proposal_summary"]["available"] is True
    assert payload["support"]["proposal_summary"]["serious_option_count"] == 2
    assert payload["support"]["evaluation_summary"]["available"] is True
    assert payload["support"]["live_context"] is None
    assert "health_posture" in payload["telemetry"]
    assert "status" not in payload["derived"]


def test_inspect_json_view_keeps_live_context_in_support_not_truth() -> None:
    context, _ = build_interface_context_with_flow(current_stage="execution", lifecycle_state="active")
    cli = JeffCLI(context=context)
    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")

    payload = json.loads(cli.run_one_shot("/inspect", json_output=True))

    assert payload["view"] == "run_show"
    assert "live_context" not in payload["truth"]
    assert payload["truth"]["run_lifecycle_state"] == "active"
    assert payload["support"]["live_context"]["purpose"] == "operator explanation proposal support CLI coverage"
    assert payload["support"]["live_context"]["truth_families"] == ["project", "work_unit", "run"]
    assert payload["support"]["live_context"]["ordered_support_source_families"] == []


def test_trace_json_view_is_machine_readable_and_ordered() -> None:
    context, _ = build_interface_context_with_flow(lifecycle_state="active", current_stage="execution")
    cli = JeffCLI(context=context)
    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    cli.run_one_shot("/run use run-1")
    cli.run_one_shot("/json on")

    payload = json.loads(cli.run_one_shot("/trace"))

    assert payload["view"] == "trace"
    assert [event["ordinal"] for event in payload["support"]["events"]] == [1, 2, 3, 4, 5]
    assert payload["derived"]["run_id"] == "run-1"


def test_lifecycle_json_view_keeps_stage_and_health_separate() -> None:
    context, _ = build_interface_context_with_flow(lifecycle_state="waiting", current_stage="governance")
    cli = JeffCLI(context=context)
    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    cli.run_one_shot("/run use run-1")

    payload = json.loads(cli.run_one_shot("/lifecycle", json_output=True))

    assert payload["derived"]["lifecycle_state"] == "waiting"
    assert payload["derived"]["current_stage"] == "governance"
    assert payload["derived"]["active_module"] == "governance"
    assert payload["telemetry"]["health_posture"] == "blocked"


def test_show_json_view_surfaces_only_lawful_request_entry_hints() -> None:
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

    payload = json.loads(cli.run_one_shot("/show", json_output=True))

    assert payload["support"]["request_entry_hint"]["current_routed_outcome"] == "revalidate"
    assert payload["support"]["request_entry_hint"]["conditional_commands"] == [
        "/reject run-1",
        "/revalidate run-1",
    ]
    assert payload["support"]["request_entry_hint"]["receipt_only_commands"] == []


def test_show_json_view_omits_request_entry_hint_for_ordinary_runs() -> None:
    context, _ = build_interface_context_with_flow(lifecycle_state="completed", current_stage="evaluation")
    cli = JeffCLI(context=context)
    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    cli.run_one_shot("/run use run-1")

    payload = json.loads(cli.run_one_shot("/show", json_output=True))

    assert payload["support"]["request_entry_hint"] is None
