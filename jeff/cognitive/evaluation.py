"""Bounded evaluation results with deterministic override checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from jeff.action.outcome import Outcome

from .types import normalize_text_list, require_text

EvaluationVerdict = Literal[
    "acceptable",
    "acceptable_with_cautions",
    "partial",
    "degraded",
    "blocked",
    "inconclusive",
    "unacceptable",
    "mismatch_affected",
]

RecommendedNextStep = Literal[
    "accept_as_complete",
    "continue",
    "retry",
    "revalidate",
    "recover",
    "escalate",
    "terminate_and_replan",
    "request_clarification",
]


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    objective_summary: str
    outcome: Outcome
    evaluation_verdict: EvaluationVerdict
    rationale: str
    recommended_next_step: RecommendedNextStep
    deterministic_override_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "objective_summary",
            require_text(self.objective_summary, field_name="objective_summary"),
        )
        if not isinstance(self.outcome, Outcome):
            raise TypeError("evaluation requires a normalized Outcome")
        object.__setattr__(self, "rationale", require_text(self.rationale, field_name="rationale"))
        object.__setattr__(
            self,
            "deterministic_override_reasons",
            normalize_text_list(
                self.deterministic_override_reasons,
                field_name="deterministic_override_reasons",
            ),
        )


def evaluate_outcome(
    *,
    objective_summary: str,
    outcome: Outcome,
    evidence_quality_posture: str,
    direction_fit: bool | None = None,
    blocker_fit: bool | None = None,
    required_artifacts_present: bool = True,
    required_verification_present: bool = True,
    constraint_violations: tuple[str, ...] = (),
    mandatory_target_reached: bool = True,
    critical_mismatch_unresolved: bool = False,
    sufficient_evidence_for_claim: bool = True,
) -> EvaluationResult:
    if not isinstance(outcome, Outcome):
        raise TypeError("evaluation requires a normalized Outcome")

    objective_summary = require_text(objective_summary, field_name="objective_summary")
    evidence_quality_posture = require_text(
        evidence_quality_posture,
        field_name="evidence_quality_posture",
    )
    constraint_violations = normalize_text_list(
        constraint_violations,
        field_name="constraint_violations",
    )

    verdict, recommended_next_step = _base_disposition_from_outcome(outcome)
    override_reasons = deterministic_override_reasons(
        outcome=outcome,
        required_artifacts_present=required_artifacts_present,
        required_verification_present=required_verification_present,
        constraint_violations=constraint_violations,
        mandatory_target_reached=mandatory_target_reached,
        critical_mismatch_unresolved=critical_mismatch_unresolved,
        sufficient_evidence_for_claim=sufficient_evidence_for_claim,
    )

    if override_reasons:
        verdict, recommended_next_step = _apply_overrides(
            base_verdict=verdict,
            override_reasons=override_reasons,
        )

    if direction_fit is False and verdict in {"acceptable", "acceptable_with_cautions"}:
        verdict = "unacceptable"
        recommended_next_step = "terminate_and_replan"
        override_reasons = override_reasons + ("result does not fit current direction",)

    if blocker_fit is False and verdict in {"acceptable", "acceptable_with_cautions"}:
        verdict = "blocked"
        recommended_next_step = "revalidate"
        override_reasons = override_reasons + ("known blocker fit remains unresolved",)

    if not override_reasons and evidence_quality_posture != "strong" and verdict == "acceptable":
        verdict = "acceptable_with_cautions"
        recommended_next_step = "continue"

    rationale = _build_rationale(
        objective_summary=objective_summary,
        outcome=outcome,
        evidence_quality_posture=evidence_quality_posture,
        override_reasons=override_reasons,
    )
    return EvaluationResult(
        objective_summary=objective_summary,
        outcome=outcome,
        evaluation_verdict=verdict,
        rationale=rationale,
        recommended_next_step=recommended_next_step,
        deterministic_override_reasons=override_reasons,
    )


def deterministic_override_reasons(
    *,
    outcome: Outcome,
    required_artifacts_present: bool,
    required_verification_present: bool,
    constraint_violations: tuple[str, ...],
    mandatory_target_reached: bool,
    critical_mismatch_unresolved: bool,
    sufficient_evidence_for_claim: bool,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if not required_artifacts_present:
        reasons.append("required artifact missing")
    if not required_verification_present:
        reasons.append("required verification missing")
    reasons.extend(constraint_violations)
    if not mandatory_target_reached:
        reasons.append("mandatory target not reached")
    if critical_mismatch_unresolved or outcome.outcome_state == "mismatch_affected":
        reasons.append("unresolved critical mismatch remains")
    if not sufficient_evidence_for_claim:
        reasons.append("insufficient evidence for the claimed result")
    return tuple(reasons)


def _base_disposition_from_outcome(
    outcome: Outcome,
) -> tuple[EvaluationVerdict, RecommendedNextStep]:
    mapping: dict[str, tuple[EvaluationVerdict, RecommendedNextStep]] = {
        "complete": ("acceptable", "accept_as_complete"),
        "partial": ("partial", "continue"),
        "degraded": ("degraded", "recover"),
        "blocked": ("blocked", "revalidate"),
        "failed": ("unacceptable", "retry"),
        "inconclusive": ("inconclusive", "request_clarification"),
        "mismatch_affected": ("mismatch_affected", "escalate"),
    }
    return mapping[outcome.outcome_state]


def _apply_overrides(
    *,
    base_verdict: EvaluationVerdict,
    override_reasons: tuple[str, ...],
) -> tuple[EvaluationVerdict, RecommendedNextStep]:
    if any("constraint" in reason for reason in override_reasons):
        return "unacceptable", "recover"
    if any("critical mismatch" in reason for reason in override_reasons):
        return "mismatch_affected", "escalate"
    if any("mandatory target not reached" in reason for reason in override_reasons):
        return "partial", "terminate_and_replan"
    if any("verification" in reason or "insufficient evidence" in reason for reason in override_reasons):
        return "inconclusive", "revalidate"
    if any("artifact missing" in reason for reason in override_reasons):
        return "blocked", "revalidate"
    if base_verdict == "acceptable":
        return "acceptable_with_cautions", "continue"
    return base_verdict, "continue"


def _build_rationale(
    *,
    objective_summary: str,
    outcome: Outcome,
    evidence_quality_posture: str,
    override_reasons: tuple[str, ...],
) -> str:
    if override_reasons:
        joined = "; ".join(override_reasons)
        return (
            f"Evaluation for '{objective_summary}' is capped by deterministic checks: {joined}. "
            f"Outcome state was {outcome.outcome_state} with evidence quality {evidence_quality_posture}."
        )
    return (
        f"Evaluation for '{objective_summary}' follows normalized outcome {outcome.outcome_state} "
        f"with evidence quality {evidence_quality_posture}."
    )
