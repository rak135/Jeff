"""Metadata registry view for the project-scoped research archive."""

from __future__ import annotations

from dataclasses import dataclass

from .models import ResearchArchiveArtifact


@dataclass(frozen=True, slots=True)
class ResearchArchiveRegistryEntry:
    artifact_id: str
    artifact_family: str
    project_id: str
    work_unit_id: str | None
    run_id: str | None
    title: str
    generated_at: str
    effective_date: str | None
    effective_period: str | None


class ResearchArchiveRegistry:
    def __init__(self, store) -> None:
        self.store = store

    def list_entries(
        self,
        *,
        project_id: str,
        artifact_family: str | None = None,
        work_unit_id: str | None = None,
        run_id: str | None = None,
    ) -> tuple[ResearchArchiveRegistryEntry, ...]:
        entries: list[ResearchArchiveRegistryEntry] = []
        for record in self.store.list_project_records(project_id):
            if artifact_family is not None and record.artifact_family != artifact_family:
                continue
            if work_unit_id is not None and str(record.work_unit_id) != work_unit_id:
                continue
            if run_id is not None and str(record.run_id) != run_id:
                continue
            entries.append(_entry_from_record(record))
        return tuple(entries)


def _entry_from_record(record: ResearchArchiveArtifact) -> ResearchArchiveRegistryEntry:
    return ResearchArchiveRegistryEntry(
        artifact_id=str(record.artifact_id),
        artifact_family=record.artifact_family,
        project_id=str(record.project_id),
        work_unit_id=None if record.work_unit_id is None else str(record.work_unit_id),
        run_id=None if record.run_id is None else str(record.run_id),
        title=record.title,
        generated_at=record.generated_at,
        effective_date=record.effective_date,
        effective_period=record.effective_period,
    )