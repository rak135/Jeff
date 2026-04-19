import json
import pytest

from jeff.interface import JeffCLI

from tests.fixtures.cli import build_interface_context_with_flow


def test_selected_is_not_rendered_as_permitted() -> None:
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

    payload = json.loads(cli.run_one_shot("/show", json_output=True))

    assert payload["derived"]["selected_proposal_id"] == "proposal-1"
    assert payload["derived"]["allowed_now"] is False
    assert payload["derived"]["governance_outcome"] == "approval_required"


def test_execution_completion_is_not_rendered_as_objective_completion() -> None:
    context, _ = build_interface_context_with_flow(
        lifecycle_state="completed",
        current_stage="evaluation",
        execution_status="completed",
        outcome_state="partial",
        target_effect_posture="partial target effect",
    )
    cli = JeffCLI(context=context)
    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    cli.run_one_shot("/run use run-1")

    payload = json.loads(cli.run_one_shot("/show", json_output=True))

    assert payload["derived"]["execution_status"] == "completed"
    assert payload["derived"]["outcome_state"] == "partial"
    assert payload["derived"]["evaluation_verdict"] == "partial"


def test_request_command_output_distinguishes_acceptance_from_effect() -> None:
    context, _ = build_interface_context_with_flow(
        flow_family="evaluation_driven_followup",
        lifecycle_state="completed",
        current_stage="evaluation",
        routed_outcome="retry",
        route_kind="follow_up",
        route_reason="evaluation recommended bounded retry",
    )
    cli = JeffCLI(context=context)
    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    cli.run_one_shot("/run use run-1")

    text = cli.run_one_shot("/retry")

    assert "accepted=True" in text
    assert "effect_state=request_accepted" in text
    assert "remains a bounded receipt-only command in v1" in text


def test_approve_command_records_bounded_approval_without_claiming_execution() -> None:
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

    text = cli.run_one_shot("/approve")
    show_text = cli.run_one_shot("/show")

    assert "effect_state=approval_recorded" in text
    assert "next_routed_outcome=revalidate" in text
    assert "explicit /revalidate" in text
    assert "approval_verdict=granted" in show_text
    assert "routed_outcome=revalidate" in show_text
    assert "execution_status=-" in show_text


def test_blocked_and_inconclusive_states_remain_visible() -> None:
    context, _ = build_interface_context_with_flow(
        lifecycle_state="completed",
        current_stage="evaluation",
        execution_status="completed_with_degradation",
        outcome_state="inconclusive",
        target_effect_posture="target could not be confirmed",
        evidence_quality_posture="limited",
    )
    cli = JeffCLI(context=context)
    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    cli.run_one_shot("/run use run-1")

    text = cli.run_one_shot("/show")

    assert "execution_status=completed_with_degradation" in text
    assert "outcome_state=inconclusive" in text
    assert "evaluation_verdict=inconclusive" in text
    assert "[support][evaluation] verdict=inconclusive recommended_next_step=request_clarification" in text


def test_request_unavailable_message_names_required_routed_outcome() -> None:
    context, _ = build_interface_context_with_flow(
        flow_family="evaluation_driven_followup",
        lifecycle_state="completed",
        current_stage="evaluation",
        routed_outcome="retry",
        route_kind="follow_up",
        route_reason="evaluation recommended bounded retry",
    )
    cli = JeffCLI(context=context)
    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    cli.run_one_shot("/run use run-1")

    with pytest.raises(ValueError, match="it requires a run routed to approval_required"):
        cli.run_one_shot("/approve")
