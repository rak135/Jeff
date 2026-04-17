"""Deterministic Selection-local choice behavior."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..proposal import ProposalResultOption
from ..types import normalized_identity
from .contracts import SelectionRequest, SelectionResult

_AssessmentKind = Literal["selectable", "defer", "escalate", "reject"]

_SELECTABLE_TYPES = {"direct_action", "planning_insertion"}
_DEFER_TYPES = {"investigate", "clarify", "defer"}
_ESCALATE_TYPES = {"escalate"}
_HARD_REJECT_PHRASES = (
    "out of scope",
    "scope violation",
    "cross project",
    "contradiction",
    "conflict",
    "dishonest",
    "not possible",
    "impossible",
    "invalid basis",
)
_PRECONDITION_PHRASES = (
    "need ",
    "needs ",
    "missing ",
    "await ",
    "awaiting ",
    "before proceeding",
    "before choosing",
    "prerequisite",
    "clarify",
    "clarification",
    "research",
    "investigate",
    "unknown",
    "unclear",
    "dependency",
)
_JUDGMENT_BOUNDARY_PHRASES = (
    "operator",
    "user decision",
    "stakeholder",
    "judgment boundary",
    "judgment call",
    "strategic tradeoff",
    "policy tradeoff",
    "legal",
    "compliance",
    "sensitive",
)
_REVERSIBLE_POSITIVE_PHRASES = (
    "reversible",
    "rollback",
    "recoverable",
    "undo",
    "contained",
)
_REVERSIBLE_NEGATIVE_PHRASES = (
    "irreversible",
    "one way",
    "hard to reverse",
    "destructive",
)


@dataclass(frozen=True, slots=True)
class _OptionAssessment:
    option: ProposalResultOption
    kind: _AssessmentKind
    support_count: int
    concern_count: int
    reversibility_score: int

    @property
    def selection_rank(self) -> tuple[int, int, int, int, int, int]:
        return (
            self.support_count,
            self.reversibility_score,
            -len(self.option.main_risks),
            -len(self.option.assumptions),
            -(1 if self.option.planning_needed else 0),
            -self.option.option_index,
        )


def run_selection(*, request: SelectionRequest, selection_id: str) -> SelectionResult:
    """Choose one bounded proposal option or return an explicit non-selection outcome."""

    assessments = tuple(_assess_option(option) for option in request.proposal_result.options)
    considered_ids = request.considered_proposal_ids

    if not assessments:
        scarcity_reason = request.proposal_result.scarcity_reason or "proposal returned no serious options"
        return SelectionResult(
            selection_id=selection_id,
            considered_proposal_ids=considered_ids,
            non_selection_outcome="reject_all",
            rationale=f"reject_all because no proposal option is available to judge under current scope; {scarcity_reason}.",
        )

    selectable = sorted(
        (assessment for assessment in assessments if assessment.kind == "selectable"),
        key=lambda assessment: assessment.selection_rank,
        reverse=True,
    )
    best_selectable = selectable[0] if selectable else None

    if best_selectable is not None and _should_select(best_selectable, assessments):
        strongest_alternative = _strongest_alternative(assessments, excluded=best_selectable.option.proposal_id)
        return SelectionResult(
            selection_id=selection_id,
            considered_proposal_ids=considered_ids,
            selected_proposal_id=best_selectable.option.proposal_id,
            rationale=_build_selected_rationale(best_selectable, strongest_alternative),
        )

    escalate_candidate = _best_of_kind(assessments, "escalate")
    if escalate_candidate is not None:
        strongest_alternative = _strongest_alternative(assessments, excluded=escalate_candidate.option.proposal_id)
        return SelectionResult(
            selection_id=selection_id,
            considered_proposal_ids=considered_ids,
            non_selection_outcome="escalate",
            rationale=_build_escalate_rationale(escalate_candidate, strongest_alternative),
        )

    defer_candidate = _best_of_kind(assessments, "defer")
    if defer_candidate is not None:
        strongest_alternative = _strongest_alternative(assessments, excluded=defer_candidate.option.proposal_id)
        return SelectionResult(
            selection_id=selection_id,
            considered_proposal_ids=considered_ids,
            non_selection_outcome="defer",
            rationale=_build_defer_rationale(defer_candidate, strongest_alternative),
        )

    strongest_option = _strongest_alternative(assessments, excluded=None)
    scarcity_reason = request.proposal_result.scarcity_reason
    rationale = "reject_all because none of the proposed options is an honest basis for bounded choice now"
    if strongest_option is not None:
        rationale = f"{rationale}; {strongest_option.option.proposal_id} stays blocked, out of scope, or too weakly supported"
    if scarcity_reason:
        rationale = f"{rationale}; {scarcity_reason}"

    return SelectionResult(
        selection_id=selection_id,
        considered_proposal_ids=considered_ids,
        non_selection_outcome="reject_all",
        rationale=f"{rationale}.",
    )


def _assess_option(option: ProposalResultOption) -> _OptionAssessment:
    text_blob = _option_text(option)
    hard_reject = _contains_any(text_blob, _HARD_REJECT_PHRASES)
    precondition_gap = _contains_any(text_blob, _PRECONDITION_PHRASES)
    judgment_boundary = _contains_any(text_blob, _JUDGMENT_BOUNDARY_PHRASES)

    support_count = len(option.support_refs)
    concern_count = len(option.blockers) + len(option.main_risks) + len(option.assumptions)
    reversibility_score = _reversibility_score(option)

    kind: _AssessmentKind
    if hard_reject:
        kind = "reject"
    elif option.proposal_type in _ESCALATE_TYPES or judgment_boundary:
        kind = "escalate"
    elif option.proposal_type in _DEFER_TYPES:
        kind = "defer"
    elif option.proposal_type in _SELECTABLE_TYPES:
        if option.blockers:
            kind = "defer" if precondition_gap else "reject"
        elif support_count == 0 and concern_count >= 3:
            kind = "reject"
        elif support_count == 0 and len(option.main_risks) >= 2:
            kind = "reject"
        else:
            kind = "selectable"
    else:
        kind = "reject"

    return _OptionAssessment(
        option=option,
        kind=kind,
        support_count=support_count,
        concern_count=concern_count,
        reversibility_score=reversibility_score,
    )


def _should_select(best: _OptionAssessment, assessments: tuple[_OptionAssessment, ...]) -> bool:
    if best.support_count == 0 and best.concern_count >= 2:
        return False

    if best.support_count == 0 and any(assessment.kind in {"defer", "escalate"} for assessment in assessments):
        return False

    return True


def _best_of_kind(
    assessments: tuple[_OptionAssessment, ...],
    kind: _AssessmentKind,
) -> _OptionAssessment | None:
    candidates = [assessment for assessment in assessments if assessment.kind == kind]
    if not candidates:
        return None
    return max(candidates, key=lambda assessment: assessment.selection_rank)


def _strongest_alternative(
    assessments: tuple[_OptionAssessment, ...],
    *,
    excluded,
) -> _OptionAssessment | None:
    candidates = [
        assessment
        for assessment in assessments
        if excluded is None or assessment.option.proposal_id != excluded
    ]
    if not candidates:
        return None

    priority = {"selectable": 3, "escalate": 2, "defer": 1, "reject": 0}
    return max(candidates, key=lambda assessment: (priority[assessment.kind], assessment.selection_rank))


def _build_selected_rationale(
    winner: _OptionAssessment,
    alternative: _OptionAssessment | None,
) -> str:
    rationale = (
        f"selected {winner.option.proposal_id} because it stays within bounded choice with "
        f"{_support_phrase(winner)} and {_burden_phrase(winner)}"
    )
    if winner.option.planning_needed:
        rationale = f"{rationale}; planning may still be needed later, but that does not decide the choice"
    if alternative is not None:
        rationale = (
            f"{rationale}; {alternative.option.proposal_id} did not win because "
            f"{_comparison_loss_phrase(alternative, winner)}"
        )
    return f"{rationale}."


def _build_defer_rationale(
    candidate: _OptionAssessment,
    alternative: _OptionAssessment | None,
) -> str:
    rationale = (
        f"defer because {candidate.option.proposal_id} shows that bounded clarification, investigation, "
        f"or another precondition is still needed before honest choice"
    )
    if alternative is not None:
        rationale = (
            f"{rationale}; {alternative.option.proposal_id} does not overcome the same uncertainty with a stronger basis"
        )
    return f"{rationale}."


def _build_escalate_rationale(
    candidate: _OptionAssessment,
    alternative: _OptionAssessment | None,
) -> str:
    rationale = (
        f"escalate because {candidate.option.proposal_id} frames an operator judgment boundary more honestly "
        f"than forcing a bounded autonomous choice"
    )
    if alternative is not None:
        rationale = (
            f"{rationale}; {alternative.option.proposal_id} does not resolve that boundary with a clearly stronger basis"
        )
    return f"{rationale}."


def _support_phrase(assessment: _OptionAssessment) -> str:
    if assessment.support_count > 1:
        return "stronger visible support"
    if assessment.support_count == 1:
        return "some visible support"
    return "low assumption burden"


def _burden_phrase(assessment: _OptionAssessment) -> str:
    if assessment.concern_count == 0:
        return "no unresolved blockers or material burden"
    if assessment.concern_count == 1:
        return "the lightest visible decision burden"
    return "less visible burden than the alternatives"


def _comparison_loss_phrase(loser: _OptionAssessment, winner: _OptionAssessment) -> str:
    if loser.kind == "escalate":
        return "it crosses an operator judgment boundary that the winner avoids"
    if loser.kind == "defer":
        return "it still depends on clarification or investigation before choice"
    if loser.support_count < winner.support_count:
        return "it has weaker visible support"
    if loser.concern_count > winner.concern_count:
        return "it carries more visible burden"
    if loser.option.planning_needed and not winner.option.planning_needed:
        return "it needs more downstream structure without a stronger basis"
    return "it is not the strongest bounded path under the current visible factors"


def _option_text(option: ProposalResultOption) -> str:
    parts = [
        option.title,
        option.why_now,
        option.summary,
        *option.constraints,
        *option.blockers,
        *option.main_risks,
        *option.assumptions,
    ]
    if option.feasibility is not None:
        parts.append(option.feasibility)
    if option.reversibility is not None:
        parts.append(option.reversibility)
    return " ".join(normalized_identity(part) for part in parts)


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def _reversibility_score(option: ProposalResultOption) -> int:
    if option.reversibility is None:
        return 0

    normalized = normalized_identity(option.reversibility)
    if _contains_any(normalized, _REVERSIBLE_NEGATIVE_PHRASES):
        return -1
    if _contains_any(normalized, _REVERSIBLE_POSITIVE_PHRASES):
        return 1
    return 0
