"""Deterministic fail-closed consumer from proposal support into proposal input."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..types import normalize_text_list, require_text

if TYPE_CHECKING:
    from jeff.cognitive.post_selection.research_to_proposal_consumer import ProposalSupportPackage


@dataclass(frozen=True, slots=True)
class ProposalSupportConsumerIssue:
    code: str
    message: str
    field_name: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", require_text(self.code, field_name="code"))
        object.__setattr__(self, "message", require_text(self.message, field_name="message"))
        if self.field_name is not None:
            object.__setattr__(self, "field_name", require_text(self.field_name, field_name="field_name"))


class ProposalSupportConsumerError(ValueError):
    """Raised when a proposal-support package cannot be lawfully consumed into proposal input."""

    def __init__(self, issues: tuple[ProposalSupportConsumerIssue, ...]) -> None:
        if not issues:
            raise ValueError("proposal support consumer errors must include at least one issue")
        self.issues = issues
        rendered = "; ".join(
            issue.message if issue.field_name is None else f"{issue.field_name}: {issue.message}"
            for issue in issues
        )
        super().__init__(f"proposal support consumer failed: {rendered}")


@dataclass(frozen=True, slots=True)
class ProposalSupportConsumerRequest:
    request_id: str
    proposal_support_package: ProposalSupportPackage
    bounded_objective: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, str):
            raise TypeError("request_id must be a string")
        if not isinstance(self.proposal_support_package, _proposal_support_package_type()):
            raise TypeError("proposal_support_package must be a ProposalSupportPackage")
        if self.bounded_objective is not None and not isinstance(self.bounded_objective, str):
            raise TypeError("bounded_objective must be a string when provided")


@dataclass(frozen=True, slots=True)
class ProposalInputPackage:
    package_id: str
    source_proposal_support_package_id: str
    proposal_input_ready: bool
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
        object.__setattr__(
            self,
            "source_proposal_support_package_id",
            require_text(self.source_proposal_support_package_id, field_name="source_proposal_support_package_id"),
        )
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

        if not self.proposal_input_ready:
            raise ValueError("proposal input packages must remain proposal_input_ready")
        if not self.supported_findings:
            raise ValueError("proposal input packages must preserve at least one supported finding")
        if not self.provenance_refs:
            raise ValueError("proposal input packages must preserve at least one provenance ref")


def consume_proposal_support_package(
    request: ProposalSupportConsumerRequest,
) -> ProposalInputPackage:
    issues = _collect_request_issues(request)
    if issues:
        raise ProposalSupportConsumerError(tuple(issues))

    request_id = require_text(request.request_id, field_name="request_id")
    package = request.proposal_support_package

    return ProposalInputPackage(
        package_id=f"proposal-input:{request_id}",
        source_proposal_support_package_id=require_text(
            package.package_id,
            field_name="proposal_support_package.package_id",
        ),
        proposal_input_ready=True,
        supported_findings=package.supported_findings,
        inference_points=package.inference_points,
        uncertainty_points=package.uncertainty_points,
        contradiction_notes=package.contradiction_notes,
        recommendation_candidates=package.recommendation_candidates,
        missing_information_markers=package.missing_information_markers,
        provenance_refs=package.provenance_refs,
        summary=(
            "Proposal-input package built from a lawful proposal-support package for later proposal generation only. "
            "It remains support-only and is not proposal output, not selection, not action, not permission, not "
            "governance, and not execution."
        ),
    )


def _collect_request_issues(
    request: ProposalSupportConsumerRequest,
) -> tuple[ProposalSupportConsumerIssue, ...]:
    issues: list[ProposalSupportConsumerIssue] = []

    try:
        require_text(request.request_id, field_name="request_id")
    except (TypeError, ValueError):
        issues.append(
            ProposalSupportConsumerIssue(
                code="invalid_request_id",
                message="request_id must be a non-empty string",
                field_name="request_id",
            )
        )

    package = request.proposal_support_package
    try:
        require_text(package.package_id, field_name="proposal_support_package.package_id")
    except (TypeError, ValueError):
        issues.append(
            ProposalSupportConsumerIssue(
                code="missing_package_id",
                message="proposal-support package must preserve a non-empty package_id",
                field_name="proposal_support_package.package_id",
            )
        )

    if not package.proposal_support_ready:
        issues.append(
            ProposalSupportConsumerIssue(
                code="proposal_support_not_ready",
                message="proposal input may only be built from a proposal-support-ready package",
                field_name="proposal_support_package.proposal_support_ready",
            )
        )

    issues.extend(
        _validate_text_items(
            package.supported_findings,
            field_name="proposal_support_package.supported_findings",
            missing_code="missing_supported_findings",
            missing_message="proposal-support package must preserve at least one supported finding",
            invalid_code="invalid_supported_finding",
            invalid_message="supported findings must be non-empty strings",
        )
    )
    issues.extend(
        _validate_text_items(
            package.inference_points,
            field_name="proposal_support_package.inference_points",
            missing_code=None,
            missing_message=None,
            invalid_code="invalid_inference_point",
            invalid_message="inference points must be non-empty strings",
        )
    )
    issues.extend(
        _validate_text_items(
            package.uncertainty_points,
            field_name="proposal_support_package.uncertainty_points",
            missing_code=None,
            missing_message=None,
            invalid_code="invalid_uncertainty_point",
            invalid_message="uncertainty points must be non-empty strings",
        )
    )
    issues.extend(
        _validate_text_items(
            package.contradiction_notes,
            field_name="proposal_support_package.contradiction_notes",
            missing_code=None,
            missing_message=None,
            invalid_code="invalid_contradiction_note",
            invalid_message="contradiction notes must be non-empty strings",
        )
    )
    issues.extend(
        _validate_text_items(
            package.recommendation_candidates,
            field_name="proposal_support_package.recommendation_candidates",
            missing_code=None,
            missing_message=None,
            invalid_code="invalid_recommendation_candidate",
            invalid_message="recommendation candidates must be non-empty strings",
        )
    )
    issues.extend(
        _validate_text_items(
            package.missing_information_markers,
            field_name="proposal_support_package.missing_information_markers",
            missing_code=None,
            missing_message=None,
            invalid_code="invalid_missing_information_marker",
            invalid_message="missing-information markers must be non-empty strings",
        )
    )
    issues.extend(
        _validate_text_items(
            package.provenance_refs,
            field_name="proposal_support_package.provenance_refs",
            missing_code="missing_provenance_refs",
            missing_message="proposal-support package must preserve at least one provenance ref",
            invalid_code="invalid_provenance_ref",
            invalid_message="provenance refs must be non-empty strings",
        )
    )

    if request.bounded_objective is not None:
        try:
            require_text(request.bounded_objective, field_name="bounded_objective")
        except (TypeError, ValueError):
            issues.append(
                ProposalSupportConsumerIssue(
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
) -> tuple[ProposalSupportConsumerIssue, ...]:
    issues: list[ProposalSupportConsumerIssue] = []
    if not values:
        if missing_code is not None and missing_message is not None:
            issues.append(
                ProposalSupportConsumerIssue(
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
                ProposalSupportConsumerIssue(
                    code=invalid_code,
                    message=invalid_message,
                    field_name=f"{field_name}[{index}]",
                )
            )
    return tuple(issues)


def _proposal_support_package_type():
    from jeff.cognitive.post_selection.research_to_proposal_consumer import ProposalSupportPackage

    return ProposalSupportPackage
