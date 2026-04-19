"""Research-owned archive models for durable research artifacts and history."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from jeff.cognitive.types import normalize_text_list, require_text
from jeff.core.schemas import coerce_project_id, coerce_run_id, coerce_work_unit_id
from jeff.memory.types import utc_now

from .ids import ArchiveArtifactId, coerce_archive_artifact_id

ARTIFACT_FAMILIES = {
    "research_brief",
    "research_comparison",
    "evidence_bundle",
    "source_set",
    "brief_history_record",
    "event_history_record",
}
HISTORY_FAMILIES = {"brief_history_record", "event_history_record"}
STALENESS_SENSITIVITIES = {"low", "medium", "high"}
FRESHNESS_POSTURES = {"current", "dated", "historical", "stale"}
SCHEMA_VERSION = "1.0"


@dataclass(frozen=True, slots=True)
class ArchiveEvidenceItem:
    evidence_id: str
    claim: str
    evidence_text: str
    source_refs: tuple[str, ...]
    extraction_quality: str | None = None
    caution: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_id", require_text(self.evidence_id, field_name="evidence_id"))
        object.__setattr__(self, "claim", require_text(self.claim, field_name="claim"))
        object.__setattr__(self, "evidence_text", require_text(self.evidence_text, field_name="evidence_text"))
        object.__setattr__(self, "source_refs", normalize_text_list(self.source_refs, field_name="source_refs"))
        if not self.source_refs:
            raise ValueError("archive evidence items must keep at least one source_ref")
        if self.extraction_quality is not None:
            object.__setattr__(
                self,
                "extraction_quality",
                require_text(self.extraction_quality, field_name="extraction_quality"),
            )
        if self.caution is not None:
            object.__setattr__(self, "caution", require_text(self.caution, field_name="caution"))


@dataclass(frozen=True, slots=True)
class ClaimEvidenceLink:
    claim_text: str
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "claim_text", require_text(self.claim_text, field_name="claim_text"))
        object.__setattr__(self, "evidence_ids", normalize_text_list(self.evidence_ids, field_name="evidence_ids"))
        if not self.evidence_ids:
            raise ValueError("claim/evidence links must point to at least one evidence_id")


@dataclass(frozen=True, slots=True)
class SourceGrouping:
    group_name: str
    source_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "group_name", require_text(self.group_name, field_name="group_name"))
        object.__setattr__(self, "source_refs", normalize_text_list(self.source_refs, field_name="source_refs"))
        if not self.source_refs:
            raise ValueError("source groupings must keep at least one source_ref")


@dataclass(frozen=True, slots=True)
class ResearchArchiveArtifact:
    artifact_id: ArchiveArtifactId
    artifact_family: str
    project_id: str
    work_unit_id: str | None
    run_id: str | None
    title: str
    summary: str
    question_or_objective: str | None
    findings: tuple[str, ...]
    inference: tuple[str, ...]
    uncertainty: tuple[str, ...]
    source_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    generated_at: str
    effective_date: str | None = None
    effective_period: str | None = None
    staleness_sensitivity: str = "medium"
    derived_from_artifact_ids: tuple[str, ...] = ()
    schema_version: str = SCHEMA_VERSION
    comparison_targets: tuple[str, ...] = ()
    comparison_criteria: tuple[str, ...] = ()
    evidence_items: tuple[ArchiveEvidenceItem, ...] = ()
    claim_evidence_links: tuple[ClaimEvidenceLink, ...] = ()
    source_selection_scope: str | None = None
    source_ordering: tuple[str, ...] = ()
    source_groupings: tuple[SourceGrouping, ...] = ()
    freshness_posture: str | None = None
    previous_history_record_id: str | None = None
    next_history_record_id: str | None = None
    event_date: str | None = None
    observed_date: str | None = None
    event_framing: str | None = None
    support_only: bool = True

    def __post_init__(self) -> None:
        if self.artifact_family not in ARTIFACT_FAMILIES:
            raise ValueError(f"unsupported archive artifact_family: {self.artifact_family}")
        object.__setattr__(self, "artifact_id", coerce_archive_artifact_id(str(self.artifact_id)))
        object.__setattr__(self, "project_id", coerce_project_id(str(self.project_id)))
        if self.work_unit_id is not None:
            object.__setattr__(self, "work_unit_id", coerce_work_unit_id(str(self.work_unit_id)))
        if self.run_id is not None:
            object.__setattr__(self, "run_id", coerce_run_id(str(self.run_id)))
        object.__setattr__(self, "title", require_text(self.title, field_name="title"))
        object.__setattr__(self, "summary", require_text(self.summary, field_name="summary"))
        if self.question_or_objective is not None:
            object.__setattr__(
                self,
                "question_or_objective",
                require_text(self.question_or_objective, field_name="question_or_objective"),
            )
        object.__setattr__(self, "findings", normalize_text_list(self.findings, field_name="findings"))
        object.__setattr__(self, "inference", normalize_text_list(self.inference, field_name="inference"))
        object.__setattr__(self, "uncertainty", normalize_text_list(self.uncertainty, field_name="uncertainty"))
        object.__setattr__(self, "source_refs", normalize_text_list(self.source_refs, field_name="source_refs"))
        object.__setattr__(self, "evidence_refs", normalize_text_list(self.evidence_refs, field_name="evidence_refs"))
        object.__setattr__(self, "generated_at", require_text(self.generated_at, field_name="generated_at"))
        object.__setattr__(
            self,
            "derived_from_artifact_ids",
            normalize_text_list(self.derived_from_artifact_ids, field_name="derived_from_artifact_ids"),
        )
        object.__setattr__(
            self,
            "comparison_targets",
            normalize_text_list(self.comparison_targets, field_name="comparison_targets"),
        )
        object.__setattr__(
            self,
            "comparison_criteria",
            normalize_text_list(self.comparison_criteria, field_name="comparison_criteria"),
        )
        object.__setattr__(self, "source_ordering", normalize_text_list(self.source_ordering, field_name="source_ordering"))
        if self.effective_date is not None:
            object.__setattr__(self, "effective_date", require_text(self.effective_date, field_name="effective_date"))
        if self.effective_period is not None:
            object.__setattr__(
                self,
                "effective_period",
                require_text(self.effective_period, field_name="effective_period"),
            )
        if self.event_date is not None:
            object.__setattr__(self, "event_date", require_text(self.event_date, field_name="event_date"))
        if self.observed_date is not None:
            object.__setattr__(self, "observed_date", require_text(self.observed_date, field_name="observed_date"))
        if self.source_selection_scope is not None:
            object.__setattr__(
                self,
                "source_selection_scope",
                require_text(self.source_selection_scope, field_name="source_selection_scope"),
            )
        if self.event_framing is not None:
            object.__setattr__(self, "event_framing", require_text(self.event_framing, field_name="event_framing"))
        if self.freshness_posture is not None:
            object.__setattr__(
                self,
                "freshness_posture",
                require_text(self.freshness_posture, field_name="freshness_posture"),
            )
            if self.freshness_posture not in FRESHNESS_POSTURES:
                raise ValueError(f"unsupported freshness_posture: {self.freshness_posture}")
        if self.previous_history_record_id is not None:
            object.__setattr__(
                self,
                "previous_history_record_id",
                require_text(self.previous_history_record_id, field_name="previous_history_record_id"),
            )
        if self.next_history_record_id is not None:
            object.__setattr__(
                self,
                "next_history_record_id",
                require_text(self.next_history_record_id, field_name="next_history_record_id"),
            )
        if self.staleness_sensitivity not in STALENESS_SENSITIVITIES:
            raise ValueError(f"unsupported staleness_sensitivity: {self.staleness_sensitivity}")
        if self.support_only is not True:
            raise ValueError("research archive artifacts must remain support_only")
        if not self.source_refs:
            raise ValueError("research archive artifacts must keep at least one source_ref")
        if str(self.artifact_id) in self.derived_from_artifact_ids:
            raise ValueError("artifact cannot derive from itself")
        if self.run_id is not None and self.work_unit_id is None:
            raise ValueError("run_id requires work_unit_id in the shared scope block")

        evidence_ids = {item.evidence_id for item in self.evidence_items}
        if len(evidence_ids) != len(self.evidence_items):
            raise ValueError("evidence item ids must remain unique")
        if self.artifact_family == "evidence_bundle":
            if not self.evidence_items:
                raise ValueError("evidence_bundle requires evidence_items")
            if not self.evidence_refs:
                object.__setattr__(self, "evidence_refs", tuple(item.evidence_id for item in self.evidence_items))
            link_evidence_ids = {evidence_id for link in self.claim_evidence_links for evidence_id in link.evidence_ids}
            missing = sorted(link_evidence_ids - evidence_ids)
            if missing:
                raise ValueError(f"claim/evidence links reference unknown evidence ids: {missing}")

        if self.artifact_family == "research_brief":
            if self.question_or_objective is None:
                raise ValueError("research_brief requires question_or_objective")
            if not self.findings:
                raise ValueError("research_brief requires findings")

        if self.artifact_family == "research_comparison":
            if self.question_or_objective is None:
                raise ValueError("research_comparison requires question_or_objective")
            if len(self.comparison_targets) < 2:
                raise ValueError("research_comparison requires at least two comparison_targets")
            if not self.comparison_criteria:
                raise ValueError("research_comparison requires comparison_criteria")
            if not self.findings:
                raise ValueError("research_comparison requires findings")

        if self.artifact_family == "source_set":
            if self.source_selection_scope is None:
                raise ValueError("source_set requires source_selection_scope")
            unknown_ordered = sorted(set(self.source_ordering) - set(self.source_refs))
            if unknown_ordered:
                raise ValueError(f"source_set ordering references unknown source_refs: {unknown_ordered}")
            grouped_refs = {source_ref for group in self.source_groupings for source_ref in group.source_refs}
            unknown_grouped = sorted(grouped_refs - set(self.source_refs))
            if unknown_grouped:
                raise ValueError(f"source_set grouping references unknown source_refs: {unknown_grouped}")

        if self.artifact_family == "brief_history_record":
            if (self.effective_date is None) == (self.effective_period is None):
                raise ValueError("brief_history_record requires exactly one of effective_date or effective_period")
            if self.freshness_posture is None:
                raise ValueError("brief_history_record requires freshness_posture")

        if self.artifact_family == "event_history_record":
            if self.event_framing is None:
                raise ValueError("event_history_record requires event_framing")
            if (self.event_date is None) == (self.observed_date is None):
                raise ValueError("event_history_record requires exactly one of event_date or observed_date")
            if self.effective_period is not None:
                raise ValueError("event_history_record does not support effective_period")
            if self.freshness_posture is None:
                raise ValueError("event_history_record requires freshness_posture")
            if self.event_date is not None and self.effective_date not in {None, self.event_date}:
                raise ValueError("event_history_record effective_date must match event_date when provided")


def make_archive_artifact(
    *,
    artifact_id: str,
    artifact_family: str,
    project_id: str,
    work_unit_id: str | None,
    run_id: str | None,
    title: str,
    summary: str,
    question_or_objective: str | None,
    findings: tuple[str, ...],
    inference: tuple[str, ...],
    uncertainty: tuple[str, ...],
    source_refs: tuple[str, ...],
    evidence_refs: tuple[str, ...] = (),
    generated_at: str | None = None,
    effective_date: str | None = None,
    effective_period: str | None = None,
    staleness_sensitivity: str = "medium",
    derived_from_artifact_ids: tuple[str, ...] = (),
    schema_version: str = SCHEMA_VERSION,
    comparison_targets: tuple[str, ...] = (),
    comparison_criteria: tuple[str, ...] = (),
    evidence_items: tuple[ArchiveEvidenceItem, ...] = (),
    claim_evidence_links: tuple[ClaimEvidenceLink, ...] = (),
    source_selection_scope: str | None = None,
    source_ordering: tuple[str, ...] = (),
    source_groupings: tuple[SourceGrouping, ...] = (),
    freshness_posture: str | None = None,
    previous_history_record_id: str | None = None,
    next_history_record_id: str | None = None,
    event_date: str | None = None,
    observed_date: str | None = None,
    event_framing: str | None = None,
) -> ResearchArchiveArtifact:
    return ResearchArchiveArtifact(
        artifact_id=artifact_id,
        artifact_family=artifact_family,
        project_id=project_id,
        work_unit_id=work_unit_id,
        run_id=run_id,
        title=title,
        summary=summary,
        question_or_objective=question_or_objective,
        findings=findings,
        inference=inference,
        uncertainty=uncertainty,
        source_refs=source_refs,
        evidence_refs=evidence_refs,
        generated_at=generated_at or utc_now(),
        effective_date=effective_date,
        effective_period=effective_period,
        staleness_sensitivity=staleness_sensitivity,
        derived_from_artifact_ids=derived_from_artifact_ids,
        schema_version=schema_version,
        comparison_targets=comparison_targets,
        comparison_criteria=comparison_criteria,
        evidence_items=evidence_items,
        claim_evidence_links=claim_evidence_links,
        source_selection_scope=source_selection_scope,
        source_ordering=source_ordering,
        source_groupings=source_groupings,
        freshness_posture=freshness_posture,
        previous_history_record_id=previous_history_record_id,
        next_history_record_id=next_history_record_id,
        event_date=event_date,
        observed_date=observed_date,
        event_framing=event_framing,
    )


def artifact_to_payload(artifact: ResearchArchiveArtifact) -> dict[str, Any]:
    return {
        "artifact_id": str(artifact.artifact_id),
        "artifact_family": artifact.artifact_family,
        "project_id": str(artifact.project_id),
        "work_unit_id": None if artifact.work_unit_id is None else str(artifact.work_unit_id),
        "run_id": None if artifact.run_id is None else str(artifact.run_id),
        "title": artifact.title,
        "summary": artifact.summary,
        "question_or_objective": artifact.question_or_objective,
        "findings": list(artifact.findings),
        "inference": list(artifact.inference),
        "uncertainty": list(artifact.uncertainty),
        "source_refs": list(artifact.source_refs),
        "evidence_refs": list(artifact.evidence_refs),
        "generated_at": artifact.generated_at,
        "effective_date": artifact.effective_date,
        "effective_period": artifact.effective_period,
        "staleness_sensitivity": artifact.staleness_sensitivity,
        "derived_from_artifact_ids": list(artifact.derived_from_artifact_ids),
        "schema_version": artifact.schema_version,
        "comparison_targets": list(artifact.comparison_targets),
        "comparison_criteria": list(artifact.comparison_criteria),
        "evidence_items": [
            {
                "evidence_id": item.evidence_id,
                "claim": item.claim,
                "evidence_text": item.evidence_text,
                "source_refs": list(item.source_refs),
                "extraction_quality": item.extraction_quality,
                "caution": item.caution,
            }
            for item in artifact.evidence_items
        ],
        "claim_evidence_links": [
            {
                "claim_text": link.claim_text,
                "evidence_ids": list(link.evidence_ids),
            }
            for link in artifact.claim_evidence_links
        ],
        "source_selection_scope": artifact.source_selection_scope,
        "source_ordering": list(artifact.source_ordering),
        "source_groupings": [
            {
                "group_name": grouping.group_name,
                "source_refs": list(grouping.source_refs),
            }
            for grouping in artifact.source_groupings
        ],
        "freshness_posture": artifact.freshness_posture,
        "previous_history_record_id": artifact.previous_history_record_id,
        "next_history_record_id": artifact.next_history_record_id,
        "event_date": artifact.event_date,
        "observed_date": artifact.observed_date,
        "event_framing": artifact.event_framing,
        "support_only": artifact.support_only,
    }


def artifact_from_payload(payload: dict[str, Any]) -> ResearchArchiveArtifact:
    return ResearchArchiveArtifact(
        artifact_id=payload["artifact_id"],
        artifact_family=payload["artifact_family"],
        project_id=payload["project_id"],
        work_unit_id=payload.get("work_unit_id"),
        run_id=payload.get("run_id"),
        title=payload["title"],
        summary=payload["summary"],
        question_or_objective=payload.get("question_or_objective"),
        findings=tuple(payload.get("findings") or ()),
        inference=tuple(payload.get("inference") or ()),
        uncertainty=tuple(payload.get("uncertainty") or ()),
        source_refs=tuple(payload.get("source_refs") or ()),
        evidence_refs=tuple(payload.get("evidence_refs") or ()),
        generated_at=payload["generated_at"],
        effective_date=payload.get("effective_date"),
        effective_period=payload.get("effective_period"),
        staleness_sensitivity=payload.get("staleness_sensitivity", "medium"),
        derived_from_artifact_ids=tuple(payload.get("derived_from_artifact_ids") or ()),
        schema_version=payload.get("schema_version", SCHEMA_VERSION),
        comparison_targets=tuple(payload.get("comparison_targets") or ()),
        comparison_criteria=tuple(payload.get("comparison_criteria") or ()),
        evidence_items=tuple(
            ArchiveEvidenceItem(
                evidence_id=item["evidence_id"],
                claim=item["claim"],
                evidence_text=item["evidence_text"],
                source_refs=tuple(item.get("source_refs") or ()),
                extraction_quality=item.get("extraction_quality"),
                caution=item.get("caution"),
            )
            for item in payload.get("evidence_items") or ()
        ),
        claim_evidence_links=tuple(
            ClaimEvidenceLink(
                claim_text=link["claim_text"],
                evidence_ids=tuple(link.get("evidence_ids") or ()),
            )
            for link in payload.get("claim_evidence_links") or ()
        ),
        source_selection_scope=payload.get("source_selection_scope"),
        source_ordering=tuple(payload.get("source_ordering") or ()),
        source_groupings=tuple(
            SourceGrouping(
                group_name=grouping["group_name"],
                source_refs=tuple(grouping.get("source_refs") or ()),
            )
            for grouping in payload.get("source_groupings") or ()
        ),
        freshness_posture=payload.get("freshness_posture"),
        previous_history_record_id=payload.get("previous_history_record_id"),
        next_history_record_id=payload.get("next_history_record_id"),
        event_date=payload.get("event_date"),
        observed_date=payload.get("observed_date"),
        event_framing=payload.get("event_framing"),
        support_only=payload.get("support_only", True),
    )