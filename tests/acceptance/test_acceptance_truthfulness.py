import json

from jeff.cognitive import ProposalResult, ProposalResultOption, SelectionResult, assemble_context_package
from jeff.cognitive.types import TriggerInput
from jeff.contracts import Action
from jeff.governance import CurrentTruthSnapshot, Policy, evaluate_action_entry
from jeff.interface import JeffCLI
from jeff.orchestrator import run_flow

from tests.fixtures.cli import build_interface_context_with_flow, build_state_with_run


def _proposal_result(*, scope):
    return ProposalResult(
        request_id="proposal-request-1",
        scope=scope,
        options=(
            ProposalResultOption(
                option_index=1,
                proposal_id="proposal-1",
                proposal_type="direct_action",
                title="Attempt the governed action.",
                why_now="This is the only bounded path under current truth.",
                summary="Attempt the governed action.",
                constraints=("Stay inside current scope",),
            ),
        ),
        scarcity_reason="Only one serious bounded option is available.",
    )


def test_approval_gated_flow_stops_honestly_before_execution() -> None:
    state, scope = build_state_with_run()

    result = run_flow(
        flow_id="flow-approval-gated",
        flow_family="blocked_or_escalation",
        scope=scope,
        stage_handlers={
            "context": lambda _input: assemble_context_package(
                trigger=TriggerInput(trigger_summary="Attempt an approval-gated action."),
                purpose="bounded decision support",
                scope=scope,
                state=state,
            ),
            "proposal": lambda _context: _proposal_result(scope=scope),
            "selection": lambda _proposal: SelectionResult(
                selection_id="selection-1",
                considered_proposal_ids=("proposal-1",),
                selected_proposal_id="proposal-1",
                rationale="The governed action is the current best option.",
            ),
            "action": lambda _selection: Action(
                action_id="action-1",
                scope=scope,
                intent_summary="Attempt the approval-gated action.",
                basis_state_version=state.state_meta.state_version,
            ),
            "governance": lambda action: evaluate_action_entry(
                action=action,
                policy=Policy(approval_required=True),
                approval=None,
                truth=CurrentTruthSnapshot(scope=scope, state_version=state.state_meta.state_version),
            ),
        },
    )

    assert result.lifecycle.lifecycle_state == "waiting"
    assert tuple(result.outputs.keys()) == ("context", "proposal", "selection", "action", "governance")
    assert result.outputs["governance"].allowed_now is False
    assert result.outputs["governance"].approval_verdict == "absent"
    assert result.outputs["governance"].readiness.readiness_state == "pending_approval"
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "approval_required"


def test_cli_approval_receipt_stays_request_only() -> None:
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

    show_payload = json.loads(cli.run_one_shot("/show", json_output=True))
    receipt_payload = json.loads(cli.run_one_shot("/approve", json_output=True))

    assert show_payload["derived"]["selected_proposal_id"] == "proposal-1"
    assert show_payload["derived"]["allowed_now"] is False
    assert show_payload["derived"]["approval_verdict"] == "absent"
    assert receipt_payload["derived"]["accepted"] is True
    assert receipt_payload["derived"]["effect_state"] == "request_accepted"
    assert "does not imply apply, completion, or truth mutation" in receipt_payload["support"]["note"]
