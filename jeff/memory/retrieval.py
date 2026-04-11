"""Truth-first retrieval contracts for committed support memory."""

from __future__ import annotations

from dataclasses import dataclass

from jeff.core.schemas import MemoryId, Scope, coerce_memory_id

from .models import CommittedMemoryRecord
from .store import InMemoryMemoryStore
from .types import MEMORY_TYPES, normalize_text_list, normalized_identity, require_text


@dataclass(frozen=True, slots=True)
class MemoryRetrievalRequest:
    purpose: str
    scope: Scope
    query_text: str | None = None
    memory_type_filter: str | None = None
    result_limit: int = 3

    def __post_init__(self) -> None:
        object.__setattr__(self, "purpose", require_text(self.purpose, field_name="purpose"))
        if self.query_text is not None:
            object.__setattr__(
                self,
                "query_text",
                require_text(self.query_text, field_name="query_text"),
            )
        if self.memory_type_filter is not None and self.memory_type_filter not in MEMORY_TYPES:
            raise ValueError(f"unsupported memory_type_filter: {self.memory_type_filter}")
        if not isinstance(self.result_limit, int):
            raise TypeError("result_limit must be an integer")
        if self.result_limit <= 0 or self.result_limit > 10:
            raise ValueError("result_limit must stay between 1 and 10")


@dataclass(frozen=True, slots=True)
class MemoryRetrievalResult:
    request: MemoryRetrievalRequest
    records: tuple[CommittedMemoryRecord, ...]
    notes: tuple[str, ...] = ()
    support_only: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "notes", normalize_text_list(self.notes, field_name="notes"))
        if self.support_only is not True:
            raise ValueError("memory retrieval results must remain support_only")


@dataclass(frozen=True, slots=True)
class TruthFirstMemoryView:
    current_truth_summary: str
    memory_support: tuple[CommittedMemoryRecord, ...]
    notes: tuple[str, ...]
    truth_wins: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "current_truth_summary",
            require_text(self.current_truth_summary, field_name="current_truth_summary"),
        )
        object.__setattr__(self, "notes", normalize_text_list(self.notes, field_name="notes"))
        if self.truth_wins is not True:
            raise ValueError("current truth must remain authoritative over memory support")


def retrieve_memory(
    *,
    request: MemoryRetrievalRequest,
    store: InMemoryMemoryStore,
) -> MemoryRetrievalResult:
    if not isinstance(request, MemoryRetrievalRequest):
        raise TypeError("memory retrieval requires a MemoryRetrievalRequest")
    if not isinstance(store, InMemoryMemoryStore):
        raise TypeError("memory retrieval requires an InMemoryMemoryStore")

    records = [
        record
        for record in store.list_project_records(str(request.scope.project_id))
        if _scope_matches(request.scope, record.scope)
        and (request.memory_type_filter is None or record.memory_type == request.memory_type_filter)
        and _matches_query(record=record, query_text=request.query_text)
    ]
    records.sort(key=lambda record: _retrieval_rank(request.scope, record.scope))
    bounded_records = tuple(_dedupe_records(records)[: request.result_limit])

    notes = ["memory retrieval is support only; current truth still lives in state"]
    if any(record.conflict_posture != "aligned" for record in bounded_records):
        notes.append("returned memory includes stale or conflicting support and does not override truth")

    return MemoryRetrievalResult(
        request=request,
        records=bounded_records,
        notes=tuple(notes),
    )


def build_truth_first_memory_view(
    *,
    current_truth_summary: str,
    retrieval_result: MemoryRetrievalResult,
) -> TruthFirstMemoryView:
    if not isinstance(retrieval_result, MemoryRetrievalResult):
        raise TypeError("truth-first comparison requires a MemoryRetrievalResult")

    notes = list(retrieval_result.notes)
    if retrieval_result.records:
        notes.append("state wins for current-truth questions; memory remains support only")
    return TruthFirstMemoryView(
        current_truth_summary=current_truth_summary,
        memory_support=retrieval_result.records,
        notes=tuple(notes),
    )


def canonical_memory_link_for_state(
    *,
    memory_id: object,
    store: InMemoryMemoryStore,
) -> MemoryId:
    if not isinstance(memory_id, str):
        raise TypeError("canonical memory linkage requires a committed memory_id string")
    committed_memory_id = coerce_memory_id(memory_id)
    if store.get_committed(str(committed_memory_id)) is None:
        raise ValueError("canonical memory linkage requires an already committed memory_id")
    return committed_memory_id


def _scope_matches(request_scope: Scope, record_scope: Scope) -> bool:
    if request_scope.project_id != record_scope.project_id:
        return False

    if request_scope.work_unit_id is None:
        return record_scope.work_unit_id is None and record_scope.run_id is None

    if request_scope.run_id is None:
        return record_scope.run_id is None and record_scope.work_unit_id in {None, request_scope.work_unit_id}

    return (
        (record_scope.run_id == request_scope.run_id)
        or (record_scope.run_id is None and record_scope.work_unit_id == request_scope.work_unit_id)
        or (record_scope.run_id is None and record_scope.work_unit_id is None)
    )


def _matches_query(*, record: CommittedMemoryRecord, query_text: str | None) -> bool:
    if query_text is None:
        return True
    normalized_query = normalized_identity(query_text)
    haystack = " ".join([record.summary, record.why_it_matters, *record.remembered_points])
    return normalized_query in normalized_identity(haystack)


def _retrieval_rank(request_scope: Scope, record_scope: Scope) -> tuple[int, int, str]:
    if request_scope.run_id is not None and record_scope.run_id == request_scope.run_id:
        return (0, 0, str(record_scope.project_id))
    if request_scope.work_unit_id is not None and record_scope.work_unit_id == request_scope.work_unit_id:
        return (1, 0, str(record_scope.project_id))
    return (2, 0, str(record_scope.project_id))


def _dedupe_records(records: list[CommittedMemoryRecord]) -> list[CommittedMemoryRecord]:
    seen: set[tuple[str, str, str]] = set()
    deduped: list[CommittedMemoryRecord] = []
    for record in records:
        key = (
            record.memory_type,
            str(record.scope.project_id),
            normalized_identity(record.summary),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(record)
    return deduped
