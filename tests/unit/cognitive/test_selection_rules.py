import pytest

from jeff.cognitive import SelectionDisposition, SelectionRequest, SelectionResult
from jeff.cognitive.proposal import ProposalResult, ProposalResultOption
from jeff.core.schemas import Scope
from jeff.governance import may_start_now


def _proposal_result() -> ProposalResult:
    scope = Scope(project_id="project-1", work_unit_id="wu-1")
    return ProposalResult(
        request_id="proposal-request-1",
        scope=scope,
        options=(
            ProposalResultOption(
                option_index=1,
                proposal_id="proposal-1",
                proposal_type="direct_action",
                title="Implement the bounded change",
                why_now="The bounded path is ready.",
                summary="Implement the bounded change",
            ),
            ProposalResultOption(
                option_index=2,
                proposal_id="proposal-2",
                proposal_type="investigate",
                title="Investigate the missing edge case first",
                why_now="Remaining uncertainty matters.",
                summary="Investigate the missing edge case first",
            ),
        ),
    )


def test_selection_can_choose_one_proposal() -> None:
    request = SelectionRequest(
        request_id="selection-request-1",
        proposal_result=_proposal_result(),
    )
    result = SelectionResult(
        selection_id="selection-1",
        considered_proposal_ids=request.considered_proposal_ids,
        selected_proposal_id=request.considered_proposal_ids[0],
        rationale="This path fits the current scope with the lowest assumption burden",
    )

    assert result.selected_proposal_id == "proposal-1"
    assert result.non_selection_outcome is None
    assert result.disposition == "selected"


def test_selection_non_selection_outcomes_remain_explicit() -> None:
    request = SelectionRequest(
        request_id="selection-request-2",
        proposal_result=_proposal_result(),
    )
    result = SelectionResult(
        selection_id="selection-2",
        considered_proposal_ids=request.considered_proposal_ids,
        non_selection_outcome="defer",
        rationale="Current uncertainty is too high for an honest choice",
    )

    assert result.selected_proposal_id is None
    assert result.non_selection_outcome == "defer"
    assert result.disposition == "defer"


def test_selection_disposition_values_stay_bounded() -> None:
    dispositions: tuple[SelectionDisposition, ...] = ("selected", "reject_all", "defer", "escalate")

    assert dispositions == ("selected", "reject_all", "defer", "escalate")


def test_selection_cannot_choose_more_than_one_path_or_become_permission() -> None:
    with pytest.raises(ValueError, match="exactly one proposal or one explicit non-selection"):
        SelectionResult(
            selection_id="selection-3",
            considered_proposal_ids=("proposal-1", "proposal-2"),
            selected_proposal_id="proposal-1",
            non_selection_outcome="reject_all",
            rationale="Invalid mixed outcome",
        )

    with pytest.raises(TypeError, match="ActionEntryDecision"):
        request = SelectionRequest(
            request_id="selection-request-4",
            proposal_result=_proposal_result(),
        )
        may_start_now(
            SelectionResult(
                selection_id="selection-4",
                considered_proposal_ids=request.considered_proposal_ids,
                selected_proposal_id="proposal-1",
                rationale="Choice is not permission",
            ),
        )  # type: ignore[arg-type]
