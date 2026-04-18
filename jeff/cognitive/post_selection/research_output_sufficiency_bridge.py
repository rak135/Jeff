"""Deterministic fail-closed bridge from bounded research output into sufficiency evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from jeff.cognitive import ResearchArtifact
from jeff.cognitive.research.contracts import ResearchFinding

from ..types import normalize_text_list, require_text

ResearchOutputDownstreamTarget = Literal[
    "decision_support_ready",
    "more_research_needed",
    "defer",
    "escalate",
]

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
class ResearchOutputSufficiencyIssue:
    code: str
    message: str
    field_name: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", require_text(self.code, field_name="code"))
        object.__setattr__(self, "message", require_text(self.message, field_name="message"))
        if self.field_name is not None:
            object.__setattr__(self, "field_name", require_text(self.field_name, field_name="field_name"))


class ResearchOutputSufficiencyError(ValueError):
    """Raised when a research artifact cannot be lawfully evaluated for bounded downstream use."""

    def __init__(self, issues: tuple[ResearchOutputSufficiencyIssue, ...]) -> None:
        if not issues:
            raise ValueError("research output sufficiency errors must include at least one issue")
        self.issues = issues
        rendered = "; ".join(
            issue.message if issue.field_name is None else f"{issue.field_name}: {issue.message}"
            for issue in issues
        )
        super().__init__(f"research output sufficiency evaluation failed: {rendered}")


@dataclass(frozen=True, slots=True)
class ResearchOutputSufficiencyRequest:
    request_id: str
    research_artifact: ResearchArtifact
    bounded_objective: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, str):
            raise TypeError("request_id must be a string")
        if not isinstance(self.research_artifact, ResearchArtifact):
            raise TypeError("research_artifact must be a ResearchArtifact")
        if self.bounded_objective is not None and not isinstance(self.bounded_objective, str):
            raise TypeError("bounded_objective must be a string when provided")


@dataclass(frozen=True, slots=True)
class ResearchOutputSufficiencyResult:
    evaluation_id: str
    sufficient_for_downstream_use: bool
    downstream_target: ResearchOutputDownstreamTarget
    key_supported_points: tuple[str, ...]
    unresolved_items: tuple[str, ...]
    contradictions_present: bool
    insufficiency_reason: str | None
    summary: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "evaluation_id", require_text(self.evaluation_id, field_name="evaluation_id"))
        if self.downstream_target not in {
            "decision_support_ready",
            "more_research_needed",
            "defer",
            "escalate",
        }:
            raise ValueError("downstream_target must remain a lawful bounded research sufficiency target")
        object.__setattr__(
            self,
            "key_supported_points",
            normalize_text_list(self.key_supported_points, field_name="key_supported_points"),
        )
        object.__setattr__(
            self,
            "unresolved_items",
            normalize_text_list(self.unresolved_items, field_name="unresolved_items"),
        )
        if self.insufficiency_reason is not None:
            object.__setattr__(
                self,
                "insufficiency_reason",
                require_text(self.insufficiency_reason, field_name="insufficiency_reason"),
            )
        object.__setattr__(self, "summary", require_text(self.summary, field_name="summary"))

        if not self.key_supported_points:
            raise ValueError("research sufficiency results must preserve at least one key_supported_point")
        if self.sufficient_for_downstream_use:
            if self.downstream_target != "decision_support_ready":
                raise ValueError("sufficient research outputs must target decision_support_ready")
            if self.insufficiency_reason is not None:
                raise ValueError("sufficient research outputs must not carry insufficiency_reason")
        else:
            if self.downstream_target == "decision_support_ready":
                raise ValueError("insufficient research outputs must not target decision_support_ready")
            if not self.unresolved_items:
                raise ValueError("insufficient research outputs must preserve explicit unresolved_items")
            if self.insufficiency_reason is None:
                raise ValueError("insufficient research outputs must preserve insufficiency_reason")


def evaluate_research_output_sufficiency(
    request: ResearchOutputSufficiencyRequest,
) -> ResearchOutputSufficiencyResult:
    issues = _collect_request_issues(request)
    if issues:
        raise ResearchOutputSufficiencyError(tuple(issues))

    request_id = require_text(request.request_id, field_name="request_id")
    artifact = request.research_artifact
    key_supported_points = tuple(_validate_finding(finding, index=index) for index, finding in enumerate(artifact.findings))

    contradictions_present = _contradictions_present(artifact)
    unresolved_items = _build_unresolved_items(
        artifact=artifact,
        contradictions_present=contradictions_present,
        bounded_objective=request.bounded_objective,
    )

    if contradictions_present:
        insufficiency_reason = "Research preserves contradiction signals that remain unresolved."
    elif unresolved_items:
        insufficiency_reason = "Research preserves explicit uncertainty or missing information that remains unresolved."
    else:
        insufficiency_reason = None

    if insufficiency_reason is None:
        return ResearchOutputSufficiencyResult(
            evaluation_id=f"research-output-sufficiency:{request_id}",
            sufficient_for_downstream_use=True,
            downstream_target="decision_support_ready",
            key_supported_points=key_supported_points,
            unresolved_items=(),
            contradictions_present=False,
            insufficiency_reason=None,
            summary=(
                "Current research is sufficient for bounded downstream decision support, but it remains support-only "
                "and does not authorize action, governance, or execution."
            ),
        )

    if not unresolved_items:
        raise ResearchOutputSufficiencyError(
            (
                ResearchOutputSufficiencyIssue(
                    code="missing_unresolved_items",
                    message="insufficient research outputs must preserve explicit unresolved items",
                    field_name="research_artifact.uncertainties",
                ),
            )
        )

    return ResearchOutputSufficiencyResult(
        evaluation_id=f"research-output-sufficiency:{request_id}",
        sufficient_for_downstream_use=False,
        downstream_target="more_research_needed",
        key_supported_points=key_supported_points,
        unresolved_items=unresolved_items,
        contradictions_present=contradictions_present,
        insufficiency_reason=insufficiency_reason,
        summary=(
            "Current research is not yet sufficient for bounded downstream use because explicit unresolved items "
            "still remain."
        ),
    )


def _collect_request_issues(
    request: ResearchOutputSufficiencyRequest,
) -> tuple[ResearchOutputSufficiencyIssue, ...]:
    issues: list[ResearchOutputSufficiencyIssue] = []

    try:
        require_text(request.request_id, field_name="request_id")
    except (TypeError, ValueError):
        issues.append(
            ResearchOutputSufficiencyIssue(
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
            ResearchOutputSufficiencyIssue(
                code="missing_question",
                message="research_artifact must preserve the research question",
                field_name="research_artifact.question",
            )
        )

    try:
        require_text(artifact.summary, field_name="research_artifact.summary")
    except (TypeError, ValueError):
        issues.append(
            ResearchOutputSufficiencyIssue(
                code="missing_summary",
                message="research_artifact must preserve a non-empty summary",
                field_name="research_artifact.summary",
            )
        )

    if not artifact.findings:
        issues.append(
            ResearchOutputSufficiencyIssue(
                code="missing_findings",
                message="research_artifact must preserve at least one finding",
                field_name="research_artifact.findings",
            )
        )
    else:
        for index, finding in enumerate(artifact.findings):
            if not isinstance(finding, ResearchFinding):
                issues.append(
                    ResearchOutputSufficiencyIssue(
                        code="invalid_finding_type",
                        message="research_artifact.findings must contain ResearchFinding instances",
                        field_name=f"research_artifact.findings[{index}]",
                    )
                )
                continue
            try:
                require_text(finding.text, field_name=f"research_artifact.findings[{index}].text")
            except (TypeError, ValueError):
                issues.append(
                    ResearchOutputSufficiencyIssue(
                        code="missing_finding_text",
                        message="research findings must preserve non-empty text",
                        field_name=f"research_artifact.findings[{index}].text",
                    )
                )
            if not finding.source_refs:
                issues.append(
                    ResearchOutputSufficiencyIssue(
                        code="missing_finding_source_refs",
                        message="research findings must preserve at least one supporting source_ref",
                        field_name=f"research_artifact.findings[{index}].source_refs",
                    )
                )

    if not artifact.source_ids:
        issues.append(
            ResearchOutputSufficiencyIssue(
                code="missing_source_ids",
                message="research_artifact must preserve at least one source_id",
                field_name="research_artifact.source_ids",
            )
        )

    if request.bounded_objective is not None:
        try:
            require_text(request.bounded_objective, field_name="bounded_objective")
        except (TypeError, ValueError):
            issues.append(
                ResearchOutputSufficiencyIssue(
                    code="invalid_bounded_objective",
                    message="bounded_objective must be a non-empty string when provided",
                    field_name="bounded_objective",
                )
            )

    return tuple(issues)


def _validate_finding(finding: ResearchFinding, *, index: int) -> str:
    try:
        return require_text(finding.text, field_name=f"research_artifact.findings[{index}].text")
    except (TypeError, ValueError) as exc:
        raise ResearchOutputSufficiencyError(
            (
                ResearchOutputSufficiencyIssue(
                    code="missing_finding_text",
                    message="research findings must preserve non-empty text",
                    field_name=f"research_artifact.findings[{index}].text",
                ),
            )
        ) from exc


def _build_unresolved_items(
    *,
    artifact: ResearchArtifact,
    contradictions_present: bool,
    bounded_objective: str | None,
) -> tuple[str, ...]:
    unresolved_items: list[str] = [
        _to_unresolved_item(uncertainty, fallback_question=artifact.question)
        for uncertainty in artifact.uncertainties
    ]

    if contradictions_present:
        unresolved_items.append(
            "Need a source-backed resolution for contradictory research claims before downstream use."
        )

    normalized_objective = None
    if bounded_objective is not None:
        normalized_objective = require_text(bounded_objective, field_name="bounded_objective")

    if not unresolved_items and _signals_missing_information(artifact):
        target = normalized_objective or artifact.question
        unresolved_items.append(f"Need a source-backed answer for {target.rstrip('.')}.")

    deduped: list[str] = []
    seen: set[str] = set()
    for item in unresolved_items:
        normalized = require_text(item, field_name="unresolved_items")
        if normalized not in seen:
            seen.add(normalized)
            deduped.append(normalized)
    return tuple(deduped)


def _to_unresolved_item(text: str, *, fallback_question: str) -> str:
    normalized = require_text(text, field_name="research_artifact.uncertainties").rstrip(".")
    lowered = normalized.lower()
    if lowered.startswith("need "):
        return f"{normalized}."
    if lowered.startswith("confirm "):
        return f"Need a current-date confirmation for {normalized[8:].strip()}."
    if lowered.startswith("compare "):
        return f"Need a comparison between {normalized[8:].strip()}."
    if any(token in lowered for token in ("whether", "which", "what", "why", "how", "current-date", "current date")):
        return f"Need a source-backed answer for {normalized}."
    if lowered.startswith("missing "):
        return f"Need {normalized[8:].strip()}."
    if lowered.startswith("unresolved "):
        return f"Need a source-backed resolution for {normalized[11:].strip()}."
    return f"Need a source-backed answer for {normalized or fallback_question}."


def _contradictions_present(artifact: ResearchArtifact) -> bool:
    values = (
        artifact.summary,
        *(finding.text for finding in artifact.findings),
        *artifact.inferences,
        *artifact.uncertainties,
        *((artifact.recommendation,) if artifact.recommendation is not None else ()),
    )
    lowered_values = " ".join(value.lower() for value in values)
    return any(marker in lowered_values for marker in _CONTRADICTION_MARKERS)


def _signals_missing_information(artifact: ResearchArtifact) -> bool:
    values = (
        artifact.summary,
        *artifact.inferences,
        *((artifact.recommendation,) if artifact.recommendation is not None else ()),
    )
    lowered_values = " ".join(value.lower() for value in values)
    return any(
        marker in lowered_values
        for marker in (
            "need more research",
            "missing information",
            "missing source",
            "not enough information",
            "uncertain",
            "insufficient",
            "unknown",
        )
    )
