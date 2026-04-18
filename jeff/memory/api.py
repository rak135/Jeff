"""Public Memory API contract for other Jeff modules.

All methods require explicit project_id.
No method may expose global/system memory.
No method may return unbounded result sets by default.
Retrieval methods require a purpose.

API surface per MEMORY_V1.md §9:

Write-side:
  build_candidate(...)              -> MemoryCandidate
  evaluate_candidate(..)            -> MemoryWriteDecision   (true dry-run, no side effects)
  commit_candidate(..)              -> CommittedMemoryRecord
  process_candidate(..)             -> MemoryWriteResult
  supersede_candidate(..)           -> MemoryWriteResult
  merge_into_candidate(..)          -> MemoryWriteResult

Retrieval:
  retrieve(request)                           -> MemoryRetrievalResult
  get_by_id(project_id, memory_id)            -> CommittedMemoryRecord | None
  get_linked(project_id, target_ids, purpose) -> list[CommittedMemoryRecord]

Maintenance:
  run_maintenance(request)         -> MaintenanceJobResult
  refresh_conflict_labels(...)     -> RefreshResult
  rebuild_indexes(...)             -> RebuildResult
"""

from __future__ import annotations

from jeff.core.schemas import Scope

from .candidate_builder import build_candidate as _build_candidate
from .maintenance import (
    MaintenanceJobRequest,
    MaintenanceJobResult,
    RebuildResult,
    RefreshResult,
    rebuild_indexes as _rebuild_indexes,
    refresh_conflict_labels as _refresh_conflict_labels,
    run_maintenance as _run_maintenance,
)
from .models import CommittedMemoryRecord, MemoryCandidate, MemorySupportRef, MemoryWriteDecision
from .retrieval import (
    MemoryRetrievalRequest,
    MemoryRetrievalResult,
    retrieve_memory,
)
from .schemas import MemoryWriteResult
from .validator import validate_project_id_present
from .write_pipeline import (
    _run_pipeline,
    merge_into_candidate as _merge_into_candidate,
    process_candidate as _process_candidate,
    supersede_candidate as _supersede_candidate,
)


def build_candidate(
    *,
    candidate_id: str,
    memory_type: str,
    scope: Scope,
    summary: str,
    remembered_points: tuple[str, ...],
    why_it_matters: str,
    support_refs: tuple[MemorySupportRef, ...],
    support_quality: str = "moderate",
    stability: str = "tentative",
) -> MemoryCandidate:
    """Create a memory candidate from lawful support inputs.

    project_id must be present in scope and must not be a global/system sentinel.
    """
    validate_project_id_present(str(scope.project_id))
    return _build_candidate(
        candidate_id=candidate_id,
        memory_type=memory_type,
        scope=scope,
        summary=summary,
        remembered_points=remembered_points,
        why_it_matters=why_it_matters,
        support_refs=support_refs,
        support_quality=support_quality,
        stability=stability,
    )


def evaluate_candidate(
    candidate: MemoryCandidate,
    *,
    store,
    embedder=None,
) -> MemoryWriteDecision:
    """Run the write pipeline decision logic and return the decision without committing.

    This is a true dry-run: no records, links, events, or counter increments are
    persisted.  The returned decision's memory_id is a preview sentinel and must
    not be used as a canonical reference.
    """
    result = _run_pipeline(candidate=candidate, store=store, embedder=embedder, dry_run=True)
    return result.write_decision


def commit_candidate(
    candidate: MemoryCandidate,
    *,
    store,
    embedder=None,
) -> CommittedMemoryRecord:
    """Commit a candidate that was already validated/decided as 'write'.

    Raises ValueError if the pipeline defers or rejects the candidate.
    """
    result = _process_candidate(candidate=candidate, store=store, embedder=embedder)
    if result.write_outcome != "write":
        raise ValueError(
            f"candidate {candidate.candidate_id} was not committed: "
            f"{result.write_outcome} — {result.write_decision.reasons}"
        )
    assert result.committed_record is not None
    return result.committed_record


def process_candidate(
    candidate: MemoryCandidate,
    *,
    store,
    embedder=None,
) -> MemoryWriteResult:
    """Run the full write pipeline and return the combined result."""
    validate_project_id_present(str(candidate.scope.project_id))
    return _process_candidate(candidate=candidate, store=store, embedder=embedder)


def supersede_candidate(
    candidate: MemoryCandidate,
    supersedes_memory_id: str,
    *,
    store,
    embedder=None,
) -> MemoryWriteResult:
    """Commit a new record and mark the superseded record as superseded.

    Use after reviewing a deferred dedupe_ambiguity candidate.
    """
    validate_project_id_present(str(candidate.scope.project_id))
    return _supersede_candidate(
        candidate=candidate,
        supersedes_memory_id=supersedes_memory_id,
        store=store,
        embedder=embedder,
    )


def merge_into_candidate(
    candidate: MemoryCandidate,
    merge_target_id: str,
    *,
    store,
    embedder=None,
) -> MemoryWriteResult:
    """Merge a candidate's points into an existing record.

    Use after reviewing a deferred dedupe_ambiguity candidate.
    """
    validate_project_id_present(str(candidate.scope.project_id))
    return _merge_into_candidate(
        candidate=candidate,
        merge_target_id=merge_target_id,
        store=store,
        embedder=embedder,
    )


def retrieve(
    request: MemoryRetrievalRequest,
    *,
    store,
    embedder=None,
) -> MemoryRetrievalResult:
    """Retrieve bounded memory support for a purpose.

    project_id must be present; cross-project retrieval is hard-forbidden.
    """
    validate_project_id_present(str(request.scope.project_id))
    return retrieve_memory(request=request, store=store, embedder=embedder)


def get_by_id(
    project_id: str,
    memory_id: str,
    *,
    store,
) -> CommittedMemoryRecord | None:
    """Retrieve a single committed record by memory_id, scoped to project_id."""
    validate_project_id_present(project_id)
    record = store.get_committed(memory_id)
    if record is None:
        return None
    if str(record.scope.project_id) != project_id:
        return None  # cross-project access forbidden
    return record


def get_linked(
    project_id: str,
    linked_target_ids: list[str],
    purpose: str,
    *,
    store,
) -> list[CommittedMemoryRecord]:
    """Retrieve committed memory records linked to a set of target IDs.

    Looks up thin-links by target_id and returns the source memory records,
    scoped to project_id.  Cross-project access is hard-forbidden.
    """
    validate_project_id_present(project_id)
    records: list[CommittedMemoryRecord] = []
    seen: set[str] = set()
    for target_id in linked_target_ids:
        links = store.get_links_for_target(target_id, project_id)
        for link in links:
            mid = str(link.memory_id)
            if mid in seen:
                continue
            record = store.get_committed(mid)
            if record is not None and str(record.scope.project_id) == project_id:
                records.append(record)
                seen.add(mid)
    return records


def run_maintenance(
    request: MaintenanceJobRequest,
    *,
    store,
) -> MaintenanceJobResult:
    """Run a maintenance job scoped to the request's project_id."""
    validate_project_id_present(request.project_id)
    return _run_maintenance(request=request, store=store)


def refresh_conflict_labels(
    project_id: str,
    *,
    store,
    truth_anchor: str | None = None,
) -> RefreshResult:
    """Refresh conflict labels for active project memory against a truth anchor."""
    validate_project_id_present(project_id)
    return _refresh_conflict_labels(project_id=project_id, store=store, truth_anchor=truth_anchor)


def rebuild_indexes(
    project_id: str,
    *,
    store,
    embedder=None,
) -> RebuildResult:
    """Queue a full index rebuild for a project."""
    validate_project_id_present(project_id)
    return _rebuild_indexes(project_id=project_id, store=store, embedder=embedder)
