import pytest

from jeff.cognitive.proposal.contracts import ProposalResult, ProposalResultOption
from jeff.core.schemas import Scope


def test_proposal_result_enforces_honest_cardinality_and_scarcity() -> None:
    scope = Scope(project_id="project-1", work_unit_id="wu-1")
    one_option = ProposalResult(
        request_id="proposal-request-1",
        scope=scope,
        options=(
            ProposalResultOption(
                option_index=1,
                proposal_id="proposal-1",
                proposal_type="direct_action",
                title="Implement the bounded core change",
                why_now="This is the only path.",
                summary="Implement the bounded core change",
            ),
        ),
        scarcity_reason="Only one serious path survives current constraints",
    )

    assert len(one_option.options) == 1
    assert one_option.scarcity_reason is not None

    with pytest.raises(ValueError, match="at most 3 serious options"):
        ProposalResult(
            request_id="proposal-request-2",
            scope=scope,
            options=tuple(
                ProposalResultOption(
                    option_index=index,
                    proposal_id=f"proposal-{index}",
                    proposal_type="investigate",
                    title=f"Option {index}",
                    why_now="Test option",
                    summary=f"Option {index}",
                )
                for index in range(1, 5)
            ),
            scarcity_reason=None,
        )


def test_proposal_result_rejects_padded_near_duplicates() -> None:
    scope = Scope(project_id="project-1", work_unit_id="wu-1")

    with pytest.raises(ValueError, match="near-duplicate"):
        ProposalResult(
            request_id="proposal-request-3",
            scope=scope,
            options=(
                ProposalResultOption(
                    option_index=1,
                    proposal_id="proposal-1",
                    proposal_type="direct_action",
                    title="Apply the safe patch now",
                    why_now="Test",
                    summary="Apply the safe patch now",
                ),
                ProposalResultOption(
                    option_index=2,
                    proposal_id="proposal-2",
                    proposal_type="direct_action",
                    title="Apply   the safe patch now.",
                    why_now="Test",
                    summary="Apply   the safe patch now.",
                ),
            ),
        )
