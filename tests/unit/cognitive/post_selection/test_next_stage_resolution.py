import pytest

from jeff.cognitive.post_selection.action_resolution import (
    SelectionActionResolutionRequest,
    resolve_selection_action_basis,
)
from jeff.cognitive.post_selection.effective_proposal import (
    MaterializedEffectiveProposal,
    SelectionEffectiveProposalRequest,
    materialize_effective_proposal,
)
from jeff.cognitive.post_selection.next_stage_resolution import (
    NextStageResolutionError,
    NextStageResolutionRequest,
    resolve_next_stage,
)
from jeff.cognitive.post_selection.override import (
    OperatorSelectionOverrideRequest,
    build_operator_selection_override,
)
from jeff.cognitive.proposal import ProposalResult, ProposalResultOption
from jeff.cognitive.selection import SelectionResult
from jeff.core.schemas import Scope


def test_none_source_reject_all_routes_to_terminal_non_selection() -> None:
    result = resolve_next_stage(
        NextStageResolutionRequest(
            request_id="next-stage-request-1",
            materialized_effective_proposal=_materialized_none_basis(non_selection_outcome="reject_all"),
        )
    )

    assert result.next_stage_target == "terminal_non_selection"
    assert result.terminal is True
    assert result.action_permitted_to_form is False


def test_none_source_defer_routes_to_terminal_non_selection() -> None:
    result = resolve_next_stage(
        NextStageResolutionRequest(
            request_id="next-stage-request-2",
            materialized_effective_proposal=_materialized_none_basis(non_selection_outcome="defer"),
        )
    )

    assert result.next_stage_target == "terminal_non_selection"
    assert result.non_selection_outcome == "defer"
    assert result.summary == "Next stage is terminal_non_selection because selection returned defer."


def test_none_source_escalate_routes_to_escalation_surface() -> None:
    result = resolve_next_stage(
        NextStageResolutionRequest(
            request_id="next-stage-request-3",
            materialized_effective_proposal=_materialized_none_basis(non_selection_outcome="escalate"),
        )
    )

    assert result.next_stage_target == "escalation_surface"
    assert result.terminal is True
    assert result.action_permitted_to_form is False


def test_direct_action_routes_to_governance() -> None:
    result = resolve_next_stage(
        NextStageResolutionRequest(
            request_id="next-stage-request-4",
            materialized_effective_proposal=_materialized_effective_proposal(proposal_type="direct_action"),
        )
    )

    assert result.next_stage_target == "governance"
    assert result.action_permitted_to_form is True
    assert result.terminal is False


def test_planning_insertion_routes_to_planning() -> None:
    result = resolve_next_stage(
        NextStageResolutionRequest(
            request_id="next-stage-request-5",
            materialized_effective_proposal=_materialized_effective_proposal(proposal_type="planning_insertion"),
        )
    )

    assert result.next_stage_target == "planning"
    assert result.action_permitted_to_form is False
    assert result.summary == "Next stage is planning because proposal proposal-1 requires planning insertion."


def test_investigate_routes_to_research_followup() -> None:
    result = resolve_next_stage(
        NextStageResolutionRequest(
            request_id="next-stage-request-6",
            materialized_effective_proposal=_materialized_effective_proposal(proposal_type="investigate"),
        )
    )

    assert result.next_stage_target == "research_followup"
    assert result.terminal is False


def test_clarify_routes_to_research_followup() -> None:
    result = resolve_next_stage(
        NextStageResolutionRequest(
            request_id="next-stage-request-7",
            materialized_effective_proposal=_materialized_effective_proposal(proposal_type="clarify"),
        )
    )

    assert result.next_stage_target == "research_followup"
    assert result.summary == "Next stage is research_followup because proposal proposal-1 is clarify."


def test_actionable_defer_routes_to_terminal_non_selection() -> None:
    result = resolve_next_stage(
        NextStageResolutionRequest(
            request_id="next-stage-request-8",
            materialized_effective_proposal=_materialized_effective_proposal(proposal_type="defer"),
        )
    )

    assert result.next_stage_target == "terminal_non_selection"
    assert result.terminal is True


def test_actionable_escalate_routes_to_escalation_surface() -> None:
    result = resolve_next_stage(
        NextStageResolutionRequest(
            request_id="next-stage-request-9",
            materialized_effective_proposal=_materialized_effective_proposal(proposal_type="escalate"),
        )
    )

    assert result.next_stage_target == "escalation_surface"
    assert result.terminal is True


def test_unknown_proposal_type_fails_closed() -> None:
    materialized = _materialized_effective_proposal(proposal_type="direct_action")
    object.__setattr__(materialized.effective_proposal_option, "proposal_type", "unknown_type")

    with pytest.raises(NextStageResolutionError) as exc_info:
        resolve_next_stage(
            NextStageResolutionRequest(
                request_id="next-stage-request-10",
                materialized_effective_proposal=materialized,
            )
        )

    assert tuple(issue.code for issue in exc_info.value.issues) == ("unknown_proposal_type",)


def test_missing_effective_proposal_option_fails_closed() -> None:
    materialized = _materialized_effective_proposal(proposal_type="direct_action")
    object.__setattr__(materialized, "effective_proposal_option", None)

    with pytest.raises(NextStageResolutionError) as exc_info:
        resolve_next_stage(
            NextStageResolutionRequest(
                request_id="next-stage-request-11",
                materialized_effective_proposal=materialized,
            )
        )

    assert tuple(issue.code for issue in exc_info.value.issues) == ("missing_effective_proposal_option",)


def test_blank_request_id_fails_closed() -> None:
    with pytest.raises(NextStageResolutionError) as exc_info:
        resolve_next_stage(
            NextStageResolutionRequest(
                request_id="   ",
                materialized_effective_proposal=_materialized_effective_proposal(proposal_type="direct_action"),
            )
        )

    assert tuple(issue.code for issue in exc_info.value.issues) == ("invalid_request_id",)


def _materialized_effective_proposal(
    *,
    proposal_type: str = "direct_action",
    effective_source: str = "selection",
) -> MaterializedEffectiveProposal:
    selection_result = _selected_selection_result()
    proposal_result = _proposal_result(first_proposal_type=proposal_type)

    if effective_source == "operator_override":
        operator_override = build_operator_selection_override(
            OperatorSelectionOverrideRequest(
                request_id="override-request-1",
                selection_result=selection_result,
                chosen_proposal_id="proposal-2",
                operator_rationale="Carry a separate downstream operator choice.",
            )
        )
    else:
        operator_override = None

    resolved = resolve_selection_action_basis(
        SelectionActionResolutionRequest(
            request_id="resolution-request-1",
            selection_result=selection_result,
            operator_override=operator_override,
        )
    )
    return materialize_effective_proposal(
        SelectionEffectiveProposalRequest(
            request_id="materialization-request-1",
            proposal_result=proposal_result,
            resolved_basis=resolved,
        )
    )


def _materialized_none_basis(*, non_selection_outcome: str) -> MaterializedEffectiveProposal:
    selection_result = SelectionResult(
        selection_id="selection-none",
        considered_proposal_ids=("proposal-1", "proposal-2"),
        non_selection_outcome=non_selection_outcome,  # type: ignore[arg-type]
        rationale="Selection did not materialize an effective proposal.",
    )
    resolved = resolve_selection_action_basis(
        SelectionActionResolutionRequest(
            request_id="resolution-request-none",
            selection_result=selection_result,
        )
    )
    return materialize_effective_proposal(
        SelectionEffectiveProposalRequest(
            request_id="materialization-request-none",
            proposal_result=_proposal_result(),
            resolved_basis=resolved,
        )
    )


def _proposal_result(*, first_proposal_type: str = "direct_action") -> ProposalResult:
    return ProposalResult(
        request_id="proposal-request-1",
        scope=_scope(),
        options=(
            ProposalResultOption(
                option_index=1,
                proposal_id="proposal-1",
                proposal_type=first_proposal_type,  # type: ignore[arg-type]
                title="Implement the bounded change",
                why_now="The bounded path is ready.",
                summary="Implement the bounded change",
            ),
            ProposalResultOption(
                option_index=2,
                proposal_id="proposal-2",
                proposal_type="clarify",
                title="Clarify the missing edge case first",
                why_now="Remaining uncertainty matters.",
                summary="Clarify the missing edge case first",
            ),
        ),
    )


def _selected_selection_result() -> SelectionResult:
    return SelectionResult(
        selection_id="selection-1",
        considered_proposal_ids=("proposal-1", "proposal-2"),
        selected_proposal_id="proposal-1",
        rationale="The original Selection result chose the first bounded option.",
    )


def _scope() -> Scope:
    return Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1")
