"""Normalized observed-result contract built from execution residue."""

from __future__ import annotations

from dataclasses import dataclass

from jeff.core.schemas import Scope

from .execution import ExecutionResult
from .types import OutcomeState, SupportRef, normalize_text_list, require_text


@dataclass(frozen=True, slots=True)
class Outcome:
    action_id: str
    scope: Scope
    outcome_state: OutcomeState
    observed_completion_posture: str
    target_effect_posture: str
    artifact_posture: str
    side_effect_posture: str
    uncertainty_markers: tuple[str, ...] = ()
    mismatch_markers: tuple[str, ...] = ()
    evidence_refs: tuple[SupportRef, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "action_id", require_text(self.action_id, field_name="action_id"))
        object.__setattr__(
            self,
            "observed_completion_posture",
            require_text(
                self.observed_completion_posture,
                field_name="observed_completion_posture",
            ),
        )
        object.__setattr__(
            self,
            "target_effect_posture",
            require_text(self.target_effect_posture, field_name="target_effect_posture"),
        )
        object.__setattr__(
            self,
            "artifact_posture",
            require_text(self.artifact_posture, field_name="artifact_posture"),
        )
        object.__setattr__(
            self,
            "side_effect_posture",
            require_text(self.side_effect_posture, field_name="side_effect_posture"),
        )
        object.__setattr__(
            self,
            "uncertainty_markers",
            normalize_text_list(self.uncertainty_markers, field_name="uncertainty_markers"),
        )
        object.__setattr__(
            self,
            "mismatch_markers",
            normalize_text_list(self.mismatch_markers, field_name="mismatch_markers"),
        )
        for ref in self.evidence_refs:
            if ref.ref_type not in {"artifact", "trace", "evidence"}:
                raise ValueError("outcome evidence_refs must stay within bounded support refs")
        if self.outcome_state == "mismatch_affected" and not self.mismatch_markers:
            raise ValueError("mismatch_affected outcomes require mismatch markers")


def normalize_outcome(
    *,
    execution_result: ExecutionResult,
    outcome_state: OutcomeState,
    observed_completion_posture: str,
    target_effect_posture: str,
    artifact_posture: str,
    side_effect_posture: str,
    uncertainty_markers: tuple[str, ...] = (),
    mismatch_markers: tuple[str, ...] = (),
    evidence_refs: tuple[SupportRef, ...] = (),
) -> Outcome:
    if not isinstance(execution_result, ExecutionResult):
        raise TypeError("outcome normalization requires an ExecutionResult")

    return Outcome(
        action_id=execution_result.action_id,
        scope=execution_result.scope,
        outcome_state=outcome_state,
        observed_completion_posture=observed_completion_posture,
        target_effect_posture=target_effect_posture,
        artifact_posture=artifact_posture,
        side_effect_posture=side_effect_posture,
        uncertainty_markers=uncertainty_markers,
        mismatch_markers=mismatch_markers,
        evidence_refs=evidence_refs,
    )
