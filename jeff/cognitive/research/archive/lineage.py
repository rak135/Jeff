"""Lineage helpers for research archive rebuild and refresh flows."""

from __future__ import annotations

from dataclasses import replace

from jeff.memory.types import utc_now

from .ids import allocate_archive_artifact_id
from .models import ResearchArchiveArtifact

_UNCHANGED = object()


def refresh_archive_artifact(
    artifact: ResearchArchiveArtifact,
    *,
    artifact_id: str | None = None,
    generated_at: str | None = None,
    title: str | object = _UNCHANGED,
    summary: str | object = _UNCHANGED,
    question_or_objective: str | None | object = _UNCHANGED,
    findings: tuple[str, ...] | object = _UNCHANGED,
    inference: tuple[str, ...] | object = _UNCHANGED,
    uncertainty: tuple[str, ...] | object = _UNCHANGED,
    source_refs: tuple[str, ...] | object = _UNCHANGED,
    evidence_refs: tuple[str, ...] | object = _UNCHANGED,
    effective_date: str | None | object = _UNCHANGED,
    effective_period: str | None | object = _UNCHANGED,
    freshness_posture: str | None | object = _UNCHANGED,
    event_date: str | None | object = _UNCHANGED,
    observed_date: str | None | object = _UNCHANGED,
    event_framing: str | None | object = _UNCHANGED,
) -> ResearchArchiveArtifact:
    lineage = _refresh_lineage(artifact)
    return replace(
        artifact,
        artifact_id=artifact_id or str(allocate_archive_artifact_id()),
        generated_at=generated_at or utc_now(),
        derived_from_artifact_ids=lineage,
        title=artifact.title if title is _UNCHANGED else title,
        summary=artifact.summary if summary is _UNCHANGED else summary,
        question_or_objective=(
            artifact.question_or_objective if question_or_objective is _UNCHANGED else question_or_objective
        ),
        findings=artifact.findings if findings is _UNCHANGED else findings,
        inference=artifact.inference if inference is _UNCHANGED else inference,
        uncertainty=artifact.uncertainty if uncertainty is _UNCHANGED else uncertainty,
        source_refs=artifact.source_refs if source_refs is _UNCHANGED else source_refs,
        evidence_refs=artifact.evidence_refs if evidence_refs is _UNCHANGED else evidence_refs,
        effective_date=artifact.effective_date if effective_date is _UNCHANGED else effective_date,
        effective_period=artifact.effective_period if effective_period is _UNCHANGED else effective_period,
        freshness_posture=artifact.freshness_posture if freshness_posture is _UNCHANGED else freshness_posture,
        event_date=artifact.event_date if event_date is _UNCHANGED else event_date,
        observed_date=artifact.observed_date if observed_date is _UNCHANGED else observed_date,
        event_framing=artifact.event_framing if event_framing is _UNCHANGED else event_framing,
    )


def _refresh_lineage(artifact: ResearchArchiveArtifact) -> tuple[str, ...]:
    lineage: list[str] = list(artifact.derived_from_artifact_ids)
    if str(artifact.artifact_id) not in lineage:
        lineage.append(str(artifact.artifact_id))
    return tuple(lineage)