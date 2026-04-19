"""Deterministic fail-closed bridge from sufficient research output into decision-support handoff."""

from __future__ import annotations

from dataclasses import dataclass

from jeff.cognitive import ResearchArtifact

from ..types import normalize_text_list, require_text
from .research_output_sufficiency_bridge import ResearchOutputSufficiencyResult

_CONTRADICTION_MARKERS = (
    "contradiction",
    "contradict",
    "conflict",
    "conflicting",
    "inconsistent",
    "disagree",
    "disagreement",
    "diverge",
)


@dataclass(frozen=True, slots=True)
class ResearchDecisionSupportIssue:
    code: str
    message: str
    field_name: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", require_text(self.code, field_name="code"))
        object.__setattr__(self, "message", require_text(self.message, field_name="message"))
        if self.field_name is not None:
            object.__setattr__(self, "field_name", require_text(self.field_name, field_name="field_name"))


class ResearchDecisionSupportError(ValueError):
    """Raised when a sufficient research output cannot be lawfully converted into decision support."""

    def __init__(self, issues: tuple[ResearchDecisionSupportIssue, ...]) -> None:
        if not issues:
            raise ValueError("research decision support errors must include at least one issue")
        self.issues = issues
        rendered = "; ".join(
            issue.message if issue.field_name is None else f"{issue.field_name}: {issue.message}"
            for issue in issues
        )
        super().__init__(f"research decision support bridge failed: {rendered}")


@dataclass(frozen=True, slots=True)
class ResearchDecisionSupportRequest:
    request_id: str
    research_artifact: ResearchArtifact
    research_sufficiency_result: ResearchOutputSufficiencyResult
    bounded_objective: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, str):
            raise TypeError("request_id must be a string")
        if not isinstance(self.research_artifact, ResearchArtifact):
            raise TypeError("research_artifact must be a ResearchArtifact")
        if not isinstance(self.research_sufficiency_result, ResearchOutputSufficiencyResult):
            raise TypeError("research_sufficiency_result must be a ResearchOutputSufficiencyResult")
        if self.bounded_objective is not None and not isinstance(self.bounded_objective, str):
            raise TypeError("bounded_objective must be a string when provided")


@dataclass(frozen=True, slots=True)
class ResearchDecisionSupportHandoff:
    handoff_id: str
    research_artifact_ref: str
    decision_support_ready: bool
    supported_findings: tuple[str, ...]
    inference_points: tuple[str, ...]
    uncertainty_points: tuple[str, ...]
    contradiction_notes: tuple[str, ...]
    recommendation_candidates: tuple[str, ...]
    missing_information_markers: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    summary: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "handoff_id", require_text(self.handoff_id, field_name="handoff_id"))
        object.__setattr__(
            self,
            "research_artifact_ref",
            require_text(self.research_artifact_ref, field_name="research_artifact_ref"),
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

        if not self.decision_support_ready:
            raise ValueError("research decision support handoffs must remain decision_support_ready")
        if not self.supported_findings:
            raise ValueError("research decision support handoffs must preserve at least one supported finding")
        if not self.provenance_refs:
            raise ValueError("research decision support handoffs must preserve at least one provenance ref")


def build_research_decision_support_handoff(
    request: ResearchDecisionSupportRequest,
) -> ResearchDecisionSupportHandoff:
    issues = _collect_request_issues(request)
    if issues:
        raise ResearchDecisionSupportError(tuple(issues))

    request_id = require_text(request.request_id, field_name="request_id")
    artifact = request.research_artifact
    sufficiency_result = request.research_sufficiency_result

    supported_findings = tuple(require_text(finding.text, field_name="research_artifact.findings") for finding in artifact.findings)
    contradiction_notes = _contradiction_notes(artifact)

    if sufficiency_result.contradictions_present and not contradiction_notes:
        raise ResearchDecisionSupportError(
            (
                ResearchDecisionSupportIssue(
                    code="contradiction_notes_not_decomposable",
                    message="contradiction signals must remain visible in the decision-support handoff",
                    field_name="research_artifact",
                ),
            )
        )

    recommendation_candidates = (
        ()
        if artifact.recommendation is None
        else (require_text(artifact.recommendation, field_name="research_artifact.recommendation"),)
    )
    uncertainty_points = tuple(
        require_text(uncertainty, field_name="research_artifact.uncertainties")
        for uncertainty in artifact.uncertainties
    )
    missing_information_markers = _missing_information_markers(
        uncertainty_points=uncertainty_points,
        sufficiency_result=sufficiency_result,
    )

    return ResearchDecisionSupportHandoff(
        handoff_id=f"research-decision-support:{request_id}",
        research_artifact_ref=f"research-question:{require_text(artifact.question, field_name='research_artifact.question')}",
        decision_support_ready=True,
        supported_findings=supported_findings,
        inference_points=artifact.inferences,
        uncertainty_points=uncertainty_points,
        contradiction_notes=contradiction_notes,
        recommendation_candidates=recommendation_candidates,
        missing_information_markers=missing_information_markers,
        provenance_refs=artifact.source_ids,
        summary=(
            "Decision-support handoff built from sufficient research output for later downstream consumption only. "
            "It remains support-only and does not authorize proposal choice, selection, action, governance, or execution."
        ),
    )


def _collect_request_issues(
    request: ResearchDecisionSupportRequest,
) -> tuple[ResearchDecisionSupportIssue, ...]:
    issues: list[ResearchDecisionSupportIssue] = []

    try:
        require_text(request.request_id, field_name="request_id")
    except (TypeError, ValueError):
        issues.append(
            ResearchDecisionSupportIssue(
                code="invalid_request_id",
                message="request_id must be a non-empty string",
                field_name="request_id",
            )
        )

    artifact = request.research_artifact
    try:
        require_text(artifact.question, field_name="research_artifact.question")
    except (TypeError, ValueError):
        issues.append(
            ResearchDecisionSupportIssue(
                code="missing_question",
                message="research_artifact must preserve a non-empty question",
                field_name="research_artifact.question",
            )
        )

    if not artifact.findings:
        issues.append(
            ResearchDecisionSupportIssue(
                code="missing_findings",
                message="research_artifact must preserve at least one finding",
                field_name="research_artifact.findings",
            )
        )
    else:
        for index, finding in enumerate(artifact.findings):
            try:
                require_text(finding.text, field_name=f"research_artifact.findings[{index}].text")
            except (AttributeError, TypeError, ValueError):
                issues.append(
                    ResearchDecisionSupportIssue(
                        code="missing_finding_text",
                        message="research_artifact findings must preserve non-empty text",
                        field_name=f"research_artifact.findings[{index}].text",
                    )
                )

    if not artifact.source_ids:
        issues.append(
            ResearchDecisionSupportIssue(
                code="missing_source_ids",
                message="research_artifact must preserve at least one source_id",
                field_name="research_artifact.source_ids",
            )
        )
    else:
        for index, source_id in enumerate(artifact.source_ids):
            try:
                require_text(source_id, field_name=f"research_artifact.source_ids[{index}]")
            except (TypeError, ValueError):
                issues.append(
                    ResearchDecisionSupportIssue(
                        code="invalid_source_id",
                        message="research_artifact source_ids must be non-empty strings",
                        field_name=f"research_artifact.source_ids[{index}]",
                    )
                )

    for index, inference in enumerate(artifact.inferences):
        try:
            require_text(inference, field_name=f"research_artifact.inferences[{index}]")
        except (TypeError, ValueError):
            issues.append(
                ResearchDecisionSupportIssue(
                    code="invalid_inference_point",
                    message="research_artifact inferences must be non-empty strings",
                    field_name=f"research_artifact.inferences[{index}]",
                )
            )

    for index, uncertainty in enumerate(artifact.uncertainties):
        try:
            require_text(uncertainty, field_name=f"research_artifact.uncertainties[{index}]")
        except (TypeError, ValueError):
            issues.append(
                ResearchDecisionSupportIssue(
                    code="invalid_uncertainty_point",
                    message="research_artifact uncertainties must be non-empty strings",
                    field_name=f"research_artifact.uncertainties[{index}]",
                )
            )

    if artifact.recommendation is not None:
        try:
            require_text(artifact.recommendation, field_name="research_artifact.recommendation")
        except (TypeError, ValueError):
            issues.append(
                ResearchDecisionSupportIssue(
                    code="invalid_recommendation",
                    message="research_artifact recommendation must be a non-empty string when provided",
                    field_name="research_artifact.recommendation",
                )
            )

    sufficiency_result = request.research_sufficiency_result
    if not sufficiency_result.sufficient_for_downstream_use:
        issues.append(
            ResearchDecisionSupportIssue(
                code="research_not_sufficient",
                message="decision-support handoff may only be built from a sufficient research sufficiency result",
                field_name="research_sufficiency_result.sufficient_for_downstream_use",
            )
        )
    if sufficiency_result.downstream_target != "decision_support_ready":
        issues.append(
            ResearchDecisionSupportIssue(
                code="unsupported_downstream_target",
                message="decision-support handoff requires downstream_target decision_support_ready",
                field_name="research_sufficiency_result.downstream_target",
            )
        )
    if not sufficiency_result.key_supported_points:
        issues.append(
            ResearchDecisionSupportIssue(
                code="missing_supported_points",
                message="research_sufficiency_result must preserve key_supported_points",
                field_name="research_sufficiency_result.key_supported_points",
            )
        )
    elif artifact.findings:
        artifact_findings = {require_text(finding.text, field_name="research_artifact.findings") for finding in artifact.findings}
        for index, point in enumerate(sufficiency_result.key_supported_points):
            normalized_point = require_text(
                point,
                field_name=f"research_sufficiency_result.key_supported_points[{index}]",
            )
            if normalized_point not in artifact_findings:
                issues.append(
                    ResearchDecisionSupportIssue(
                        code="supported_point_not_in_artifact",
                        message="key_supported_points must remain grounded in the research artifact findings",
                        field_name=f"research_sufficiency_result.key_supported_points[{index}]",
                    )
                )

    if request.bounded_objective is not None:
        try:
            require_text(request.bounded_objective, field_name="bounded_objective")
        except (TypeError, ValueError):
            issues.append(
                ResearchDecisionSupportIssue(
                    code="invalid_bounded_objective",
                    message="bounded_objective must be a non-empty string when provided",
                    field_name="bounded_objective",
                )
            )

    return tuple(issues)


def _contradiction_notes(artifact: ResearchArtifact) -> tuple[str, ...]:
    notes: list[str] = []
    candidate_values = (
        artifact.summary,
        *(finding.text for finding in artifact.findings),
        *artifact.inferences,
        *artifact.uncertainties,
        *((artifact.recommendation,) if artifact.recommendation is not None else ()),
    )
    for value in candidate_values:
        normalized = require_text(value, field_name="research_artifact")
        lowered = normalized.lower()
        if any(marker in lowered for marker in _CONTRADICTION_MARKERS):
            notes.append(normalized)
    return tuple(dict.fromkeys(notes))


def _missing_information_markers(
    *,
    uncertainty_points: tuple[str, ...],
    sufficiency_result: ResearchOutputSufficiencyResult,
) -> tuple[str, ...]:
    markers = list(sufficiency_result.unresolved_items)
    for uncertainty in uncertainty_points:
        lowered = uncertainty.lower()
        if any(
            token in lowered
            for token in ("whether", "which", "what", "why", "how", "missing", "unknown", "confirm", "compare")
        ):
            markers.append(uncertainty)
    return tuple(dict.fromkeys(require_text(marker, field_name="missing_information_markers") for marker in markers))
