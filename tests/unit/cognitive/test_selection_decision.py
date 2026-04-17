from __future__ import annotations

from jeff.cognitive import SelectionRequest
from jeff.cognitive.proposal import ProposalResult, ProposalResultOption
from jeff.cognitive.selection import run_selection
from jeff.core.schemas import Scope


def _request(*options: ProposalResultOption, scarcity_reason: str | None = None) -> SelectionRequest:
    if len(options) < 2 and scarcity_reason is None:
        scarcity_reason = "Only one serious option remains."
    proposal_result = ProposalResult(
        request_id="proposal-request-1",
        scope=Scope(project_id="project-1", work_unit_id="wu-1"),
        options=options,
        scarcity_reason=scarcity_reason,
    )
    return SelectionRequest(
        request_id="selection-request-1",
        proposal_result=proposal_result,
    )


def _option(
    *,
    option_index: int,
    proposal_id: str,
    proposal_type: str = "direct_action",
    support_refs: tuple[str, ...] = (),
    assumptions: tuple[str, ...] = (),
    main_risks: tuple[str, ...] = (),
    blockers: tuple[str, ...] = (),
    constraints: tuple[str, ...] = (),
    planning_needed: bool = False,
    reversibility: str | None = None,
    why_now: str = "Current truth keeps this option in play.",
    summary: str | None = None,
) -> ProposalResultOption:
    return ProposalResultOption(
        option_index=option_index,
        proposal_id=proposal_id,
        proposal_type=proposal_type,  # type: ignore[arg-type]
        title=f"Option {proposal_id}",
        why_now=why_now,
        summary=summary or f"Option {proposal_id}",
        support_refs=support_refs,
        assumptions=assumptions,
        main_risks=main_risks,
        blockers=blockers,
        constraints=constraints,
        planning_needed=planning_needed,
        reversibility=reversibility,
    )


def test_run_selection_selects_one_option_when_one_is_clearly_best() -> None:
    request = _request(
        _option(
            option_index=1,
            proposal_id="proposal-1",
            support_refs=("truth-1", "truth-2"),
            reversibility="Reversible with a clean rollback path.",
        ),
        _option(
            option_index=2,
            proposal_id="proposal-2",
            proposal_type="investigate",
            blockers=("Need more research before choosing the stronger path.",),
            summary="Investigate the missing edge case",
        ),
    )

    result = run_selection(request=request, selection_id="selection-1")

    assert result.selected_proposal_id == "proposal-1"
    assert result.non_selection_outcome is None
    assert result.disposition == "selected"
    assert "proposal-2" in result.rationale


def test_run_selection_returns_reject_all_when_no_option_is_honest_basis() -> None:
    request = _request(
        _option(
            option_index=1,
            proposal_id="proposal-1",
            blockers=("Out of scope for the current project boundary.",),
            main_risks=("Would conflict with current truth.",),
        ),
        _option(
            option_index=2,
            proposal_id="proposal-2",
            blockers=("Not possible under the current bounded constraints.",),
            assumptions=("Needs unsupported external behavior.",),
        ),
    )

    result = run_selection(request=request, selection_id="selection-2")

    assert result.selected_proposal_id is None
    assert result.non_selection_outcome == "reject_all"
    assert result.disposition == "reject_all"


def test_run_selection_returns_defer_when_more_bounded_clarification_is_needed() -> None:
    request = _request(
        _option(
            option_index=1,
            proposal_id="proposal-1",
            blockers=("Need missing dependency confirmation before proceeding.",),
            assumptions=("The dependency may still change.",),
        ),
        _option(
            option_index=2,
            proposal_id="proposal-2",
            proposal_type="clarify",
            summary="Clarify the missing dependency boundary",
        ),
    )

    result = run_selection(request=request, selection_id="selection-3")

    assert result.selected_proposal_id is None
    assert result.non_selection_outcome == "defer"
    assert result.disposition == "defer"


def test_run_selection_returns_escalate_when_operator_judgment_boundary_is_hit() -> None:
    request = _request(
        _option(
            option_index=1,
            proposal_id="proposal-1",
            proposal_type="escalate",
            summary="Escalate the strategic tradeoff to the operator",
            why_now="This is an operator judgment boundary under current risk posture.",
        ),
        _option(
            option_index=2,
            proposal_id="proposal-2",
            main_risks=("This still carries a strategic tradeoff with no stronger basis.",),
            assumptions=("The intent is acceptable without operator judgment.",),
        ),
    )

    result = run_selection(request=request, selection_id="selection-4")

    assert result.selected_proposal_id is None
    assert result.non_selection_outcome == "escalate"
    assert result.disposition == "escalate"


def test_run_selection_never_returns_more_than_one_outcome() -> None:
    request = _request(
        _option(
            option_index=1,
            proposal_id="proposal-1",
            support_refs=("truth-1",),
        ),
    )

    result = run_selection(request=request, selection_id="selection-5")

    assert (result.selected_proposal_id is None) != (result.non_selection_outcome is None)


def test_run_selection_rationale_avoids_permission_language() -> None:
    request = _request(
        _option(
            option_index=1,
            proposal_id="proposal-1",
            support_refs=("truth-1",),
        ),
        _option(
            option_index=2,
            proposal_id="proposal-2",
            proposal_type="investigate",
            summary="Investigate the remaining uncertainty",
        ),
    )

    result = run_selection(request=request, selection_id="selection-6")
    normalized = result.rationale.lower()

    assert "approval" not in normalized
    assert "readiness" not in normalized
    assert "permission" not in normalized
    assert "execution" not in normalized


def test_planning_needed_can_influence_choice_without_becoming_plan_authority() -> None:
    request = _request(
        _option(
            option_index=1,
            proposal_id="proposal-1",
            support_refs=("truth-1",),
            planning_needed=True,
            summary="Plan-heavy path",
        ),
        _option(
            option_index=2,
            proposal_id="proposal-2",
            support_refs=("truth-1",),
            planning_needed=False,
            summary="Tighter direct path",
        ),
    )

    result = run_selection(request=request, selection_id="selection-7")

    assert result.selected_proposal_id == "proposal-2"
    assert result.non_selection_outcome is None
    assert "plan authority" not in result.rationale.lower()
