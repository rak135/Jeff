"""Builders for explicitly historical research archive records."""

from __future__ import annotations

from .ids import allocate_archive_artifact_id
from .models import ResearchArchiveArtifact, make_archive_artifact


def create_brief_history_record(
    *,
    project_id: str,
    title: str,
    summary: str,
    source_refs: tuple[str, ...],
    freshness_posture: str,
    effective_date: str | None = None,
    effective_period: str | None = None,
    question_or_objective: str | None = None,
    findings: tuple[str, ...] = (),
    inference: tuple[str, ...] = (),
    uncertainty: tuple[str, ...] = (),
    work_unit_id: str | None = None,
    run_id: str | None = None,
    staleness_sensitivity: str = "high",
    derived_from_artifact_ids: tuple[str, ...] = (),
    previous_history_record_id: str | None = None,
    next_history_record_id: str | None = None,
    artifact_id: str | None = None,
    generated_at: str | None = None,
) -> ResearchArchiveArtifact:
    return make_archive_artifact(
        artifact_id=artifact_id or str(allocate_archive_artifact_id()),
        artifact_family="brief_history_record",
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
        generated_at=generated_at,
        effective_date=effective_date,
        effective_period=effective_period,
        staleness_sensitivity=staleness_sensitivity,
        derived_from_artifact_ids=derived_from_artifact_ids,
        freshness_posture=freshness_posture,
        previous_history_record_id=previous_history_record_id,
        next_history_record_id=next_history_record_id,
    )


def create_event_history_record(
    *,
    project_id: str,
    title: str,
    summary: str,
    event_framing: str,
    source_refs: tuple[str, ...],
    event_date: str | None = None,
    observed_date: str | None = None,
    question_or_objective: str | None = None,
    findings: tuple[str, ...] = (),
    inference: tuple[str, ...] = (),
    uncertainty: tuple[str, ...] = (),
    work_unit_id: str | None = None,
    run_id: str | None = None,
    effective_date: str | None = None,
    staleness_sensitivity: str = "high",
    freshness_posture: str | None = None,
    derived_from_artifact_ids: tuple[str, ...] = (),
    previous_history_record_id: str | None = None,
    next_history_record_id: str | None = None,
    artifact_id: str | None = None,
    generated_at: str | None = None,
) -> ResearchArchiveArtifact:
    resolved_event_date = event_date
    resolved_observed_date = observed_date
    resolved_effective_date = effective_date
    if resolved_event_date is not None and resolved_effective_date is None:
        resolved_effective_date = resolved_event_date
    resolved_freshness_posture = freshness_posture or ("dated" if resolved_event_date is not None else "historical")
    return make_archive_artifact(
        artifact_id=artifact_id or str(allocate_archive_artifact_id()),
        artifact_family="event_history_record",
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
        generated_at=generated_at,
        effective_date=resolved_effective_date,
        staleness_sensitivity=staleness_sensitivity,
        derived_from_artifact_ids=derived_from_artifact_ids,
        freshness_posture=resolved_freshness_posture,
        previous_history_record_id=previous_history_record_id,
        next_history_record_id=next_history_record_id,
        event_date=resolved_event_date,
        observed_date=resolved_observed_date,
        event_framing=event_framing,
    )