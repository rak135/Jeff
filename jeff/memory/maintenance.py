"""Memory maintenance jobs — project-scoped, non-semantic, auditable.

Required job types per MEMORY_V1.md §22:
- embedding_refresh
- dedupe_audit
- supersession_audit
- stale_memory_review
- broken_link_audit
- retrieval_quality_evaluation
- index_consistency_audit
- compression_refresh
- quarantine_review

Maintenance rules:
- maintenance may improve indexes and labels
- maintenance must not silently rewrite memory meaning
- maintenance must not repair truth
- maintenance must remain project-scoped

All maintenance jobs are persisted via store.store_maintenance_job() so the
audit trail is durable in both in-memory and PostgreSQL paths.
"""

from __future__ import annotations

from dataclasses import dataclass

from .ids import MaintenanceJobId, coerce_maintenance_job_id
from .schemas import MaintenanceJobRecord
from .types import MAINTENANCE_JOB_TYPES, utc_now

_job_counter = 0


def _next_job_id() -> MaintenanceJobId:
    global _job_counter
    _job_counter += 1
    return coerce_maintenance_job_id(f"maint-{_job_counter}")


@dataclass(frozen=True, slots=True)
class MaintenanceJobRequest:
    job_type: str
    project_id: str

    def __post_init__(self) -> None:
        if self.job_type not in MAINTENANCE_JOB_TYPES:
            raise ValueError(f"unsupported maintenance job_type: {self.job_type}")
        if not self.project_id.strip():
            raise ValueError("project_id is required for maintenance jobs")


@dataclass(frozen=True, slots=True)
class MaintenanceJobResult:
    job: MaintenanceJobRecord
    records_inspected: int
    records_updated: int
    issues_found: int
    summary: str


def run_maintenance(
    *,
    request: MaintenanceJobRequest,
    store,
) -> MaintenanceJobResult:
    """Run a maintenance job against the store and persist the job record.

    Accepts any store satisfying MemoryStoreProtocol.  All jobs are project-scoped
    and non-semantic; meaning rewriting is forbidden.
    """
    now = utc_now()
    records = store.list_project_records(request.project_id)
    job_id = _next_job_id()

    inspected = len(records)
    updated = 0
    issues = 0

    if request.job_type == "stale_memory_review":
        issues = sum(1 for r in records if r.conflict_posture != "none")
        summary = (
            f"stale_memory_review: inspected {inspected} records, "
            f"found {issues} with non-neutral conflict posture"
        )

    elif request.job_type == "dedupe_audit":
        from .types import normalized_identity

        seen: dict[tuple[str, str], str] = {}
        for r in records:
            key = (r.memory_type, normalized_identity(r.summary))
            if key in seen:
                issues += 1
            else:
                seen[key] = str(r.memory_id)
        summary = (
            f"dedupe_audit: inspected {inspected} records, "
            f"found {issues} potential duplicates"
        )

    elif request.job_type == "supersession_audit":
        issues = sum(
            1
            for r in records
            if r.record_status == "active" and r.superseded_by_memory_id is not None
        )
        summary = (
            f"supersession_audit: inspected {inspected} records, "
            f"found {issues} active records with stale supersession links"
        )

    elif request.job_type == "broken_link_audit":
        # Verify that every link's memory_id still exists
        active_ids = {str(r.memory_id) for r in records}
        broken = 0
        for r in records:
            for link in store.get_links_for_memory(str(r.memory_id)):
                if str(link.memory_id) not in active_ids:
                    broken += 1
        issues = broken
        summary = f"broken_link_audit: inspected {inspected} records, found {issues} broken links"

    elif request.job_type in {"embedding_refresh", "index_consistency_audit"}:
        from .indexer import rebuild_project_index
        result = rebuild_project_index(request.project_id, store=store)
        issues = result.get("failures", 0)
        summary = (
            f"{request.job_type}: inspected {result['records_inspected']} records, "
            f"fts={result['records_fts_indexed']}, vector={result['records_vector_indexed']}, "
            f"failures={issues}"
        )

    else:
        summary = f"{request.job_type}: inspected {inspected} records"

    job = MaintenanceJobRecord(
        job_id=job_id,
        job_type=request.job_type,
        project_id=request.project_id,
        job_status="completed",
        created_at=now,
        updated_at=now,
        details={
            "inspected": str(inspected),
            "updated": str(updated),
            "issues": str(issues),
        },
    )

    # Persist the job record durably
    store.store_maintenance_job(job)

    return MaintenanceJobResult(
        job=job,
        records_inspected=inspected,
        records_updated=updated,
        issues_found=issues,
        summary=summary,
    )


@dataclass(frozen=True, slots=True)
class RefreshResult:
    project_id: str
    records_relabeled: int
    summary: str


def refresh_conflict_labels(
    *,
    project_id: str,
    store,
    truth_anchor: str | None = None,
) -> RefreshResult:
    """Refresh conflict labels for all active project records.

    Does not rewrite memory meaning.  Only updates conflict_posture labels.
    """
    from .conflict_labeler import apply_conflict_labels

    records = store.list_project_records(project_id)
    active = tuple(r for r in records if r.record_status == "active")
    labeled = apply_conflict_labels(records=active, truth_anchor=truth_anchor)
    relabeled = sum(
        1 for old, new in zip(active, labeled) if old.conflict_posture != new.conflict_posture
    )
    for record in labeled:
        store._store_committed_record(record)
    return RefreshResult(
        project_id=project_id,
        records_relabeled=relabeled,
        summary=(
            f"conflict labels refreshed for {len(labeled)} active records "
            f"in project '{project_id}'"
        ),
    )


@dataclass(frozen=True, slots=True)
class RebuildResult:
    project_id: str
    records_queued: int
    summary: str


def rebuild_indexes(
    *,
    project_id: str,
    store,
    embedder=None,
) -> RebuildResult:
    """Queue a full index rebuild for all project records."""
    from .indexer import rebuild_project_index

    result = rebuild_project_index(project_id, store=store, embedder=embedder)
    queued = result.get("records_inspected", 0)
    return RebuildResult(
        project_id=project_id,
        records_queued=queued,
        summary=(
            f"index rebuild completed for project '{project_id}': "
            f"fts={result['records_fts_indexed']}, "
            f"vector={result['records_vector_indexed']}, "
            f"failures={result['failures']}"
        ),
    )
