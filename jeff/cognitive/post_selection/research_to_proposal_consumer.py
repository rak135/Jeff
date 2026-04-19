"""Deterministic fail-closed consumer from research decision support into proposal support."""

from __future__ import annotations

from dataclasses import dataclass

from ..types import normalize_text_list, require_text
from .research_to_decision_support_bridge import ResearchDecisionSupportHandoff


@dataclass(frozen=True, slots=True)
class ResearchProposalConsumerIssue:
    code: str
    message: str
    field_name: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", require_text(self.code, field_name="code"))
        object.__setattr__(self, "message", require_text(self.message, field_name="message"))
        if self.field_name is not None:
            object.__setattr__(self, "field_name", require_text(self.field_name, field_name="field_name"))


class ResearchProposalConsumerError(ValueError):
    """Raised when a research decision-support handoff cannot be lawfully consumed for proposal support."""

    def __init__(self, issues: tuple[ResearchProposalConsumerIssue, ...]) -> None:
        if not issues:
            raise ValueError("research proposal consumer errors must include at least one issue")
        self.issues = issues
        rendered = "; ".join(
            issue.message if issue.field_name is None else f"{issue.field_name}: {issue.message}"
            for issue in issues
        )
        super().__init__(f"research proposal consumer failed: {rendered}")


@dataclass(frozen=True, slots=True)
class ResearchProposalConsumerRequest:
    request_id: str
    research_decision_support_handoff: ResearchDecisionSupportHandoff
    bounded_objective: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, str):
            raise TypeError("request_id must be a string")
        if not isinstance(self.research_decision_support_handoff, ResearchDecisionSupportHandoff):
            raise TypeError("research_decision_support_handoff must be a ResearchDecisionSupportHandoff")
        if self.bounded_objective is not None and not isinstance(self.bounded_objective, str):
            raise TypeError("bounded_objective must be a string when provided")


@dataclass(frozen=True, slots=True)
class ProposalSupportPackage:
    package_id: str
    source_handoff_id: str
    proposal_support_ready: bool
    supported_findings: tuple[str, ...]
    inference_points: tuple[str, ...]
    uncertainty_points: tuple[str, ...]
    contradiction_notes: tuple[str, ...]
    recommendation_candidates: tuple[str, ...]
    missing_information_markers: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    summary: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "package_id", require_text(self.package_id, field_name="package_id"))
        object.__setattr__(self, "source_handoff_id", require_text(self.source_handoff_id, field_name="source_handoff_id"))
        object.__setattr__(
            self,
            "supported_findings",
            normalize_text_list(self.supported_findings, field_name="supported_findings"),
        )
        object.__setattr__(
            self,
            "inference_points",
            normalize_text_list(self.inference_points, field_name="inference_points"),
        )
        object.__setattr__(
            self,
            "uncertainty_points",
            normalize_text_list(self.uncertainty_points, field_name="uncertainty_points"),
        )
        object.__setattr__(
            self,
            "contradiction_notes",
            normalize_text_list(self.contradiction_notes, field_name="contradiction_notes"),
        )
        object.__setattr__(
            self,
            "recommendation_candidates",
            normalize_text_list(self.recommendation_candidates, field_name="recommendation_candidates"),
        )
        object.__setattr__(
            self,
            "missing_information_markers",
            normalize_text_list(self.missing_information_markers, field_name="missing_information_markers"),
        )
        object.__setattr__(
            self,
            "provenance_refs",
            normalize_text_list(self.provenance_refs, field_name="provenance_refs"),
        )
        object.__setattr__(self, "summary", require_text(self.summary, field_name="summary"))

        if not self.proposal_support_ready:
            raise ValueError("proposal support packages must remain proposal_support_ready")
        if not self.supported_findings:
            raise ValueError("proposal support packages must preserve at least one supported finding")
        if not self.provenance_refs:
            raise ValueError("proposal support packages must preserve at least one provenance ref")


def consume_research_for_proposal_support(
    request: ResearchProposalConsumerRequest,
) -> ProposalSupportPackage:
    issues = _collect_request_issues(request)
    if issues:
        raise ResearchProposalConsumerError(tuple(issues))

    request_id = require_text(request.request_id, field_name="request_id")
    handoff = request.research_decision_support_handoff

    return ProposalSupportPackage(
        package_id=f"proposal-support:{request_id}",
        source_handoff_id=require_text(handoff.handoff_id, field_name="research_decision_support_handoff.handoff_id"),
        proposal_support_ready=True,
        supported_findings=handoff.supported_findings,
        inference_points=handoff.inference_points,
        uncertainty_points=handoff.uncertainty_points,
        contradiction_notes=handoff.contradiction_notes,
        recommendation_candidates=handoff.recommendation_candidates,
        missing_information_markers=handoff.missing_information_markers,
        provenance_refs=handoff.provenance_refs,
        summary=(
            "Proposal-support package built from a lawful research decision-support handoff for later proposal "
            "consumption only. It remains support-only and is not proposal output, not selection, not action, "
            "not permission, not governance, and not execution."
        ),
    )


def _collect_request_issues(
    request: ResearchProposalConsumerRequest,
) -> tuple[ResearchProposalConsumerIssue, ...]:
    issues: list[ResearchProposalConsumerIssue] = []

    try:
        require_text(request.request_id, field_name="request_id")
    except (TypeError, ValueError):
        issues.append(
            ResearchProposalConsumerIssue(
                code="invalid_request_id",
                message="request_id must be a non-empty string",
                field_name="request_id",
            )
        )

    handoff = request.research_decision_support_handoff
    try:
        require_text(handoff.handoff_id, field_name="research_decision_support_handoff.handoff_id")
    except (TypeError, ValueError):
        issues.append(
            ResearchProposalConsumerIssue(
                code="missing_handoff_id",
                message="research decision-support handoff must preserve a non-empty handoff_id",
                field_name="research_decision_support_handoff.handoff_id",
            )
        )

    if not handoff.decision_support_ready:
        issues.append(
            ResearchProposalConsumerIssue(
                code="decision_support_not_ready",
                message="proposal support may only be built from a decision-support-ready handoff",
                field_name="research_decision_support_handoff.decision_support_ready",
            )
        )

    issues.extend(
        _validate_text_items(
            handoff.supported_findings,
            field_name="research_decision_support_handoff.supported_findings",
            missing_code="missing_supported_findings",
            missing_message="research decision-support handoff must preserve at least one supported finding",
            invalid_code="invalid_supported_finding",
            invalid_message="supported findings must be non-empty strings",
        )
    )
    issues.extend(
        _validate_text_items(
            handoff.inference_points,
            field_name="research_decision_support_handoff.inference_points",
            missing_code=None,
            missing_message=None,
            invalid_code="invalid_inference_point",
            invalid_message="inference points must be non-empty strings",
        )
    )
    issues.extend(
        _validate_text_items(
            handoff.uncertainty_points,
            field_name="research_decision_support_handoff.uncertainty_points",
            missing_code=None,
            missing_message=None,
            invalid_code="invalid_uncertainty_point",
            invalid_message="uncertainty points must be non-empty strings",
        )
    )
    issues.extend(
        _validate_text_items(
            handoff.contradiction_notes,
            field_name="research_decision_support_handoff.contradiction_notes",
            missing_code=None,
            missing_message=None,
            invalid_code="invalid_contradiction_note",
            invalid_message="contradiction notes must be non-empty strings",
        )
    )
    issues.extend(
        _validate_text_items(
            handoff.recommendation_candidates,
            field_name="research_decision_support_handoff.recommendation_candidates",
            missing_code=None,
            missing_message=None,
            invalid_code="invalid_recommendation_candidate",
            invalid_message="recommendation candidates must be non-empty strings",
        )
    )
    issues.extend(
        _validate_text_items(
            handoff.missing_information_markers,
            field_name="research_decision_support_handoff.missing_information_markers",
            missing_code=None,
            missing_message=None,
            invalid_code="invalid_missing_information_marker",
            invalid_message="missing-information markers must be non-empty strings",
        )
    )
    issues.extend(
        _validate_text_items(
            handoff.provenance_refs,
            field_name="research_decision_support_handoff.provenance_refs",
            missing_code="missing_provenance_refs",
            missing_message="research decision-support handoff must preserve at least one provenance ref",
            invalid_code="invalid_provenance_ref",
            invalid_message="provenance refs must be non-empty strings",
        )
    )

    if request.bounded_objective is not None:
        try:
            require_text(request.bounded_objective, field_name="bounded_objective")
        except (TypeError, ValueError):
            issues.append(
                ResearchProposalConsumerIssue(
                    code="invalid_bounded_objective",
                    message="bounded_objective must be a non-empty string when provided",
                    field_name="bounded_objective",
                )
            )

    return tuple(issues)


def _validate_text_items(
    values: tuple[str, ...],
    *,
    field_name: str,
    missing_code: str | None,
    missing_message: str | None,
    invalid_code: str,
    invalid_message: str,
) -> tuple[ResearchProposalConsumerIssue, ...]:
    issues: list[ResearchProposalConsumerIssue] = []
    if not values:
        if missing_code is not None and missing_message is not None:
            issues.append(
                ResearchProposalConsumerIssue(
                    code=missing_code,
                    message=missing_message,
                    field_name=field_name,
                )
            )
        return tuple(issues)

    for index, value in enumerate(values):
        try:
            require_text(value, field_name=f"{field_name}[{index}]")
        except (TypeError, ValueError):
            issues.append(
                ResearchProposalConsumerIssue(
                    code=invalid_code,
                    message=invalid_message,
                    field_name=f"{field_name}[{index}]",
                )
            )
    return tuple(issues)
