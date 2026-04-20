"""Deterministic bounded planning gate."""

from __future__ import annotations

from dataclasses import dataclass

from ..proposal import ProposalResultOption


@dataclass(frozen=True, slots=True)
class PlanningGateDecision:
    should_plan: bool
    reasons: tuple[str, ...]


def evaluate_planning_gate(
    *,
    selected_option: ProposalResultOption | None,
    operator_requested: bool = False,
    multi_step: bool = False,
    review_heavy: bool = False,
    high_risk: bool = False,
    time_spanning: bool = False,
    dependency_heavy: bool = False,
    checkpoint_heavy: bool = False,
) -> PlanningGateDecision:
    reasons: list[str] = []
    if operator_requested:
        reasons.append("operator_requested")
    if selected_option is not None:
        if selected_option.planning_needed:
            reasons.append("selected_option_planning_needed")
        if selected_option.proposal_type == "planning_insertion":
            reasons.append("selected_option_is_planning_insertion")
        if len(selected_option.blockers) > 0:
            reasons.append("selected_option_has_blockers")
    if multi_step:
        reasons.append("multi_step")
    if review_heavy:
        reasons.append("review_heavy")
    if high_risk:
        reasons.append("high_risk")
    if time_spanning:
        reasons.append("time_spanning")
    if dependency_heavy:
        reasons.append("dependency_heavy")
    if checkpoint_heavy:
        reasons.append("checkpoint_heavy")
    if selected_option is None and not operator_requested:
        return PlanningGateDecision(should_plan=False, reasons=())
    return PlanningGateDecision(should_plan=bool(reasons), reasons=tuple(reasons))


def should_plan(
    *,
    selected_option: ProposalResultOption | None,
    operator_requested: bool = False,
    multi_step: bool = False,
    review_heavy: bool = False,
    high_risk: bool = False,
    time_spanning: bool = False,
    dependency_heavy: bool = False,
    checkpoint_heavy: bool = False,
) -> bool:
    return evaluate_planning_gate(
        selected_option=selected_option,
        operator_requested=operator_requested,
        multi_step=multi_step,
        review_heavy=review_heavy,
        high_risk=high_risk,
        time_spanning=time_spanning,
        dependency_heavy=dependency_heavy,
        checkpoint_heavy=checkpoint_heavy,
    ).should_plan