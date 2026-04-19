import json

from jeff.interface import JeffCLI

from tests.fixtures.cli import build_interface_context_with_flow


def test_cli_inspect_trace_and_lifecycle_stay_aligned_with_orchestrator_truth() -> None:
    context, _ = build_interface_context_with_flow(
        flow_family="evaluation_driven_followup",
        lifecycle_state="completed",
        current_stage="evaluation",
        outcome_state="partial",
        target_effect_posture="target moved partially",
        routed_outcome="retry",
        route_kind="follow_up",
        route_reason="evaluation recommended a bounded retry",
    )
    cli = JeffCLI(context=context)
    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    cli.run_one_shot("/run use run-1")

    show_payload = json.loads(cli.run_one_shot("/inspect", json_output=True))
    trace_payload = json.loads(cli.run_one_shot("/trace", json_output=True))
    lifecycle_payload = json.loads(cli.run_one_shot("/lifecycle", json_output=True))

    assert show_payload["truth"]["run_id"] == "run-1"
    assert show_payload["derived"]["flow_id"] == lifecycle_payload["derived"]["flow_id"]
    assert trace_payload["derived"]["flow_id"] == lifecycle_payload["derived"]["flow_id"]
    assert show_payload["derived"]["active_stage"] == "evaluation"
    assert show_payload["derived"]["active_module"] == "cognitive"
    assert lifecycle_payload["derived"]["current_stage"] == "evaluation"
    assert lifecycle_payload["derived"]["active_module"] == "cognitive"
    assert trace_payload["derived"]["run_id"] == "run-1"
    assert trace_payload["support"]["events"][-1]["stage"] == "evaluation"
    assert "recent_events" not in show_payload["truth"]
    assert "routing_decision" in show_payload["support"]


def test_show_view_keeps_support_artifacts_out_of_canonical_truth() -> None:
    context, _ = build_interface_context_with_flow(
        flow_family="evaluation_driven_followup",
        lifecycle_state="completed",
        current_stage="evaluation",
        routed_outcome="retry",
        route_kind="follow_up",
        route_reason="evaluation recommended a bounded retry",
    )
    cli = JeffCLI(context=context)
    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    cli.run_one_shot("/run use run-1")

    payload = json.loads(cli.run_one_shot("/show", json_output=True))

    assert "routing_decision" not in payload["truth"]
    assert "recent_events" not in payload["truth"]
    assert payload["support"]["routing_decision"]["source_stage"] == "evaluation"
    assert payload["support"]["recent_events"][-1]["stage"] == "evaluation"


def test_cli_help_describes_bounded_runtime_contract_truthfully() -> None:
    context, _ = build_interface_context_with_flow()
    cli = JeffCLI(context=context)

    text = cli.run_one_shot("/help")

    assert "A local jeff.runtime.toml enables /run <repo-local-validation-objective> and /research ..." in text
    assert "/run runs one bounded repo-local pytest validation plan under the current model configuration." in text
    assert "Conditionally available request-entry:" in text
    assert "Bounded receipt-only request-entry:" in text
    assert "approve/revalidate/reject only apply when the current run routed to the required request-entry state." in text
