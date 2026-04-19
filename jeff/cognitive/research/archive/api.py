"""Public API for the research-owned archive submodule."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from jeff.core.schemas import Scope

from .artifact_builder import (
    create_evidence_bundle,
    create_research_brief,
    create_research_comparison,
    create_source_set,
)
from .history_builder import create_brief_history_record, create_event_history_record
from .lineage import refresh_archive_artifact
from .models import ArchiveEvidenceItem, ClaimEvidenceLink, ResearchArchiveArtifact, SourceGrouping
from .retrieval import ResearchArchiveRetrievalRequest, ResearchArchiveRetrievalResult, retrieve_archive
from .telemetry import record_cross_project_rejection, record_save

if TYPE_CHECKING:
    from ..persistence import ResearchArtifactRecord

_COMPARISON_CRITERIA_DELIMITERS = (" on ", " for ", " by ", " using ", " under ", " across ")
_DIFFERENCE_BETWEEN_PATTERN = re.compile(
    r"(?is)^difference\s+between\s+(?P<left>.+?)\s+and\s+(?P<right>.+?)(?:[?.!]|$)",
)
_EVENT_KEYWORDS = (
    " announced ",
    " launched ",
    " released ",
    " rolled out ",
    " shipped ",
    " published ",
    " reported ",
    " confirmed ",
    " introduced ",
    " updated ",
    " changed ",
    " incident ",
    " outage ",
    " breach ",
    " deprecated ",
    " deprecation ",
    " sunset ",
    " acquired ",
    " acquisition ",
    " merger ",
)
_OBSERVED_EVENT_HINTS = (
    " observed ",
    " observation ",
    " detected ",
    " noted ",
    " seen ",
    " reported ",
    " monitoring ",
)


def save_archive_artifact(artifact, *, store):
    path = store.save(artifact)
    record_save()
    return path


def archive_research_record(
    record: "ResearchArtifactRecord",
    *,
    store,
    target_project_id: str | None = None,
    effective_date: str | None = None,
    effective_period: str | None = None,
    freshness_posture: str | None = None,
) -> tuple[ResearchArchiveArtifact, ...]:
    artifacts = _build_archive_artifacts_for_record(
        record,
        target_project_id=target_project_id,
        effective_date=effective_date,
        effective_period=effective_period,
        freshness_posture=freshness_posture,
    )
    for artifact in artifacts:
        save_archive_artifact(artifact, store=store)
    return artifacts


def get_archive_artifact_by_id(
    project_id: str,
    artifact_id: str,
    *,
    store,
):
    record = store.get_by_id(project_id, artifact_id)
    if record is None:
        return None
    if str(record.project_id) != project_id:
        record_cross_project_rejection()
        return None
    return record


def retrieve_project_archive(
    *,
    purpose: str,
    project_id: str,
    store,
    work_unit_id: str | None = None,
    run_id: str | None = None,
    artifact_family_filter: str | None = None,
    effective_date: str | None = None,
    effective_period: str | None = None,
    observed_date: str | None = None,
    history_only: bool = False,
    result_limit: int = 5,
) -> ResearchArchiveRetrievalResult:
    scope = Scope(project_id=project_id, work_unit_id=work_unit_id, run_id=run_id)
    request = ResearchArchiveRetrievalRequest(
        purpose=purpose,
        scope=scope,
        artifact_family_filter=artifact_family_filter,
        effective_date=effective_date,
        effective_period=effective_period,
        observed_date=observed_date,
        history_only=history_only,
        result_limit=result_limit,
    )
    return retrieve_archive(request=request, store=store)


__all__ = [
    "ResearchArchiveRetrievalRequest",
    "ResearchArchiveRetrievalResult",
    "archive_research_record",
    "create_brief_history_record",
    "create_event_history_record",
    "create_evidence_bundle",
    "create_research_brief",
    "create_research_comparison",
    "create_source_set",
    "get_archive_artifact_by_id",
    "refresh_archive_artifact",
    "retrieve_project_archive",
    "save_archive_artifact",
]


def _build_archive_artifacts_for_record(
    record: "ResearchArtifactRecord",
    *,
    target_project_id: str | None,
    effective_date: str | None,
    effective_period: str | None,
    freshness_posture: str | None,
) -> tuple[ResearchArchiveArtifact, ...]:
    project_id = _require_project_scope(record=record, target_project_id=target_project_id)
    all_source_refs = tuple(source.source_id for source in record.source_items)
    source_refs = record.source_ids or all_source_refs
    findings = tuple(finding.text for finding in record.findings)
    lineage = (record.artifact_id,)
    comparison_shape = _parse_comparison_shape(record.question)
    if comparison_shape is None:
        primary = create_research_brief(
            project_id=project_id,
            work_unit_id=record.work_unit_id,
            run_id=record.run_id,
            title=record.question,
            summary=record.summary,
            question_or_objective=record.question,
            findings=findings,
            inference=record.inferences,
            uncertainty=record.uncertainties,
            source_refs=source_refs,
            derived_from_artifact_ids=lineage,
            generated_at=record.created_at,
        )
    else:
        primary = create_research_comparison(
            project_id=project_id,
            work_unit_id=record.work_unit_id,
            run_id=record.run_id,
            title=record.question,
            summary=record.summary,
            question_or_objective=record.question,
            comparison_targets=comparison_shape[0],
            comparison_criteria=comparison_shape[1],
            findings=findings,
            inference=record.inferences,
            uncertainty=record.uncertainties,
            source_refs=source_refs,
            derived_from_artifact_ids=lineage,
            generated_at=record.created_at,
        )

    evidence_bundle = create_evidence_bundle(
        project_id=project_id,
        work_unit_id=record.work_unit_id,
        run_id=record.run_id,
        title=f"Evidence bundle: {record.question}",
        summary="Evidence extracted for this bounded research output remains inspectable with provenance preserved.",
        question_or_objective=record.question,
        source_refs=all_source_refs,
        evidence_items=_archive_evidence_items(record),
        claim_evidence_links=_claim_evidence_links(record),
        findings=findings,
        inference=record.inferences,
        uncertainty=record.uncertainties,
        derived_from_artifact_ids=lineage,
        generated_at=record.created_at,
    )
    source_set = create_source_set(
        project_id=project_id,
        work_unit_id=record.work_unit_id,
        run_id=record.run_id,
        title=f"Source set: {record.question}",
        summary="The bounded source selection for this research run remains reproducible and project-scoped.",
        question_or_objective=record.question,
        source_refs=all_source_refs,
        source_selection_scope=f"Bounded source set captured from {record.source_mode} for: {record.question}",
        source_ordering=all_source_refs,
        source_groupings=_source_groupings(record),
        derived_from_artifact_ids=lineage,
        generated_at=record.created_at,
    )

    artifacts: list[ResearchArchiveArtifact] = [primary, evidence_bundle, source_set]
    history_record = _maybe_build_history_record(
        record=record,
        project_id=project_id,
        source_refs=source_refs,
        findings=findings,
        primary=primary,
        effective_date=effective_date,
        effective_period=effective_period,
        freshness_posture=freshness_posture,
    )
    if history_record is not None:
        artifacts.append(history_record)
    return tuple(artifacts)


def _require_project_scope(*, record: "ResearchArtifactRecord", target_project_id: str | None) -> str:
    project_id = None if record.project_id is None else str(record.project_id).strip()
    if not project_id:
        raise ValueError("research archive persistence requires a project-scoped research record")
    if target_project_id is not None and target_project_id.strip() != project_id:
        raise ValueError("research archive persistence cannot write across projects")
    return project_id


def _archive_evidence_items(record: "ResearchArtifactRecord") -> tuple[ArchiveEvidenceItem, ...]:
    archive_items: list[ArchiveEvidenceItem] = []
    for index, item in enumerate(record.evidence_items, start=1):
        archive_items.append(
            ArchiveEvidenceItem(
                evidence_id=f"{record.artifact_id}:evidence:{index}",
                claim=_claim_for_evidence_item(record, item.source_refs),
                evidence_text=item.text,
                source_refs=item.source_refs,
            )
        )
    return tuple(archive_items)


def _claim_evidence_links(record: "ResearchArtifactRecord") -> tuple[ClaimEvidenceLink, ...]:
    evidence_items = _archive_evidence_items(record)
    links: list[ClaimEvidenceLink] = []
    for finding in record.findings:
        linked_ids = tuple(
            item.evidence_id
            for item in evidence_items
            if set(item.source_refs) & set(finding.source_refs)
        )
        if linked_ids:
            links.append(ClaimEvidenceLink(claim_text=finding.text, evidence_ids=linked_ids))
    return tuple(links)


def _claim_for_evidence_item(record: "ResearchArtifactRecord", source_refs: tuple[str, ...]) -> str:
    for finding in record.findings:
        if set(finding.source_refs) & set(source_refs):
            return finding.text
    return record.question


def _source_groupings(record: "ResearchArtifactRecord") -> tuple[SourceGrouping, ...]:
    grouped: dict[str, list[str]] = {}
    for source in record.source_items:
        grouped.setdefault(source.source_type, []).append(source.source_id)
    return tuple(
        SourceGrouping(group_name=group_name, source_refs=tuple(source_refs))
        for group_name, source_refs in grouped.items()
    )


def _maybe_build_history_record(
    *,
    record: "ResearchArtifactRecord",
    project_id: str,
    source_refs: tuple[str, ...],
    findings: tuple[str, ...],
    primary: ResearchArchiveArtifact,
    effective_date: str | None,
    effective_period: str | None,
    freshness_posture: str | None,
) -> ResearchArchiveArtifact | None:
    event_history = _maybe_build_event_history_record(
        record=record,
        project_id=project_id,
        source_refs=source_refs,
        findings=findings,
        primary=primary,
        effective_date=effective_date,
        freshness_posture=freshness_posture,
    )
    if event_history is not None:
        return event_history

    if effective_date is None and effective_period is None and freshness_posture is None:
        return None
    if freshness_posture is None:
        raise ValueError("brief history archive persistence requires freshness_posture")
    return create_brief_history_record(
        project_id=project_id,
        work_unit_id=record.work_unit_id,
        run_id=record.run_id,
        title=record.question,
        summary=record.summary,
        source_refs=source_refs,
        question_or_objective=record.question,
        findings=findings,
        inference=record.inferences,
        uncertainty=record.uncertainties,
        freshness_posture=freshness_posture,
        effective_date=effective_date,
        effective_period=effective_period,
        derived_from_artifact_ids=(record.artifact_id, str(primary.artifact_id)),
        generated_at=record.created_at,
    )


def _maybe_build_event_history_record(
    *,
    record: "ResearchArtifactRecord",
    project_id: str,
    source_refs: tuple[str, ...],
    findings: tuple[str, ...],
    primary: ResearchArchiveArtifact,
    effective_date: str | None,
    freshness_posture: str | None,
) -> ResearchArchiveArtifact | None:
    if not _is_event_shaped(record):
        return None
    event_date = _event_date_for_record(record, explicit_effective_date=effective_date)
    observed_date = None
    if event_date is None:
        observed_date = _observed_date_for_record(record)
    if event_date is None and observed_date is None:
        return None
    return create_event_history_record(
        project_id=project_id,
        work_unit_id=record.work_unit_id,
        run_id=record.run_id,
        title=record.question,
        summary=record.summary,
        event_framing=record.question,
        source_refs=source_refs,
        question_or_objective=record.question,
        findings=findings,
        inference=record.inferences,
        uncertainty=record.uncertainties,
        event_date=event_date,
        observed_date=observed_date,
        effective_date=event_date,
        freshness_posture=freshness_posture,
        derived_from_artifact_ids=(record.artifact_id, str(primary.artifact_id)),
        generated_at=record.created_at,
    )


def _is_event_shaped(record: "ResearchArtifactRecord") -> bool:
    if _parse_comparison_shape(record.question) is not None:
        return False
    combined_text = _combined_record_text(record)
    return any(keyword in combined_text for keyword in _EVENT_KEYWORDS)


def _event_date_for_record(record: "ResearchArtifactRecord", *, explicit_effective_date: str | None) -> str | None:
    if explicit_effective_date is not None:
        return explicit_effective_date
    published_dates = sorted(
        {
            source.published_at[:10]
            for source in record.source_items
            if source.published_at is not None and _looks_like_iso_date_prefix(source.published_at)
        }
    )
    if len(published_dates) == 1:
        return published_dates[0]
    return None


def _observed_date_for_record(record: "ResearchArtifactRecord") -> str | None:
    combined_text = _combined_record_text(record)
    if not any(keyword in combined_text for keyword in _OBSERVED_EVENT_HINTS):
        return None
    if not _looks_like_iso_date_prefix(record.created_at):
        return None
    return record.created_at[:10]


def _combined_record_text(record: "ResearchArtifactRecord") -> str:
    parts = [record.question, record.summary, *[finding.text for finding in record.findings], *record.inferences]
    return f" {' '.join(parts).lower()} "


def _looks_like_iso_date_prefix(value: str) -> bool:
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}", value.strip()))


def _parse_comparison_shape(question: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
    normalized = question.strip()
    lowered = normalized.lower()
    if " vs " in lowered or " versus " in lowered:
        return _parse_vs_style_comparison(normalized)
    match = _DIFFERENCE_BETWEEN_PATTERN.match(normalized)
    if match is None:
        return None
    left = _clean_phrase(match.group("left"))
    right = _clean_phrase(match.group("right"))
    if not left or not right:
        return None
    return ((left, right), ("overall fit",))


def _parse_vs_style_comparison(question: str) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
    candidate = question.strip()
    lowered = candidate.lower()
    separator = " versus " if " versus " in lowered else " vs "
    left, right = candidate.split(separator, maxsplit=1)
    left = re.sub(r"(?is)^compare\s+", "", left).strip()
    right_target = right.strip()
    criteria_segment = ""
    lowered_right = right_target.lower()
    for delimiter in _COMPARISON_CRITERIA_DELIMITERS:
        if delimiter in lowered_right:
            split_at = lowered_right.index(delimiter)
            criteria_segment = right_target[split_at + len(delimiter):]
            right_target = right_target[:split_at]
            break
    first_target = _clean_phrase(left)
    second_target = _clean_phrase(right_target)
    if not first_target or not second_target:
        return None
    criteria = _split_criteria(criteria_segment) if criteria_segment.strip() else ("overall fit",)
    return ((first_target, second_target), criteria)


def _split_criteria(value: str) -> tuple[str, ...]:
    cleaned = re.sub(r"(?i)^criteria\s*[:=-]?\s*", "", value).strip(" .?!")
    if not cleaned:
        return ("overall fit",)
    parts = [part.strip(" .?!") for part in re.split(r",|\band\b|/", cleaned) if part.strip(" .?!")]
    return tuple(parts) or ("overall fit",)


def _clean_phrase(value: str) -> str:
    return value.strip().strip(" .?!,:;\"'()[]{}")