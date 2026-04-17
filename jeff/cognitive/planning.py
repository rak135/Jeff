"""Conditional planning support artifacts."""

from __future__ import annotations

from dataclasses import dataclass

from jeff.core.schemas import ProposalId, coerce_proposal_id

from .proposal import ProposalResultOption
from .types import PlanStep, normalize_text_list, require_text


@dataclass(frozen=True, slots=True)
class PlanArtifact:
    bounded_objective: str
    intended_steps: tuple[PlanStep, ...]
    assumptions: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    checkpoints: tuple[str, ...] = ()
    stop_conditions: tuple[str, ...] = ()
    invalidation_conditions: tuple[str, ...] = ()
    selected_proposal_id: ProposalId | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "bounded_objective",
            require_text(self.bounded_objective, field_name="bounded_objective"),
        )
        if not self.intended_steps:
            raise ValueError("plan artifacts require at least one intended step")
        object.__setattr__(
            self,
            "assumptions",
            normalize_text_list(self.assumptions, field_name="assumptions"),
        )
        object.__setattr__(
            self,
            "dependencies",
            normalize_text_list(self.dependencies, field_name="dependencies"),
        )
        object.__setattr__(self, "risks", normalize_text_list(self.risks, field_name="risks"))
        object.__setattr__(
            self,
            "checkpoints",
            normalize_text_list(self.checkpoints, field_name="checkpoints"),
        )
        object.__setattr__(
            self,
            "stop_conditions",
            normalize_text_list(self.stop_conditions, field_name="stop_conditions"),
        )
        object.__setattr__(
            self,
            "invalidation_conditions",
            normalize_text_list(
                self.invalidation_conditions,
                field_name="invalidation_conditions",
            ),
        )
        if self.selected_proposal_id is not None:
            object.__setattr__(
                self,
                "selected_proposal_id",
                coerce_proposal_id(str(self.selected_proposal_id)),
            )


def should_plan(
    *,
    selected_option: ProposalResultOption | None,
    operator_requested: bool = False,
    multi_step: bool = False,
    review_heavy: bool = False,
    high_risk: bool = False,
    time_spanning: bool = False,
) -> bool:
    if operator_requested:
        return True
    if selected_option is None:
        return False
    return any(
        [
            selected_option.planning_needed,
            multi_step,
            review_heavy,
            high_risk,
            time_spanning,
        ],
    )


def create_plan(
    *,
    selected_option: ProposalResultOption,
    intended_steps: tuple[PlanStep, ...],
    operator_requested: bool = False,
    multi_step: bool = False,
    review_heavy: bool = False,
    high_risk: bool = False,
    time_spanning: bool = False,
    assumptions: tuple[str, ...] = (),
    dependencies: tuple[str, ...] = (),
    risks: tuple[str, ...] = (),
    checkpoints: tuple[str, ...] = (),
    stop_conditions: tuple[str, ...] = (),
    invalidation_conditions: tuple[str, ...] = (),
) -> PlanArtifact:
    if not should_plan(
        selected_option=selected_option,
        operator_requested=operator_requested,
        multi_step=multi_step,
        review_heavy=review_heavy,
        high_risk=high_risk,
        time_spanning=time_spanning,
    ):
        raise ValueError("planning is conditional and must not run for simple unjustified work")

    return PlanArtifact(
        bounded_objective=selected_option.summary,
        intended_steps=intended_steps,
        assumptions=assumptions,
        dependencies=dependencies,
        risks=risks,
        checkpoints=checkpoints,
        stop_conditions=stop_conditions,
        invalidation_conditions=invalidation_conditions,
        selected_proposal_id=selected_option.proposal_id,
    )
