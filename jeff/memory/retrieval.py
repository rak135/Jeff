"""Truth-first retrieval pipeline for committed support memory.

Retrieval order per MEMORY_V1.md §19.3:
1. confirm scope and purpose
2. receive truth anchor from Context caller
3. explicit linked memory fetch
4. scoped lexical retrieval
5. scoped semantic retrieval
6. dedupe and merge candidates
7. rerank by scope fit, purpose fit, support quality, and recency
8. conflict labeling against truth anchor
9. budget trim
10. package output + emit retrieval event
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from jeff.core.schemas import MemoryId, Scope, coerce_memory_id

from .conflict_labeler import apply_conflict_labels, has_conflict
from .ids import coerce_retrieval_event_id
from .models import CommittedMemoryRecord
from .reranker import rerank
from .schemas import MemoryRetrievalEvent
from .types import MEMORY_TYPES, normalize_text_list, normalized_identity, require_text, utc_now
from .validator import validate_project_id_present


@dataclass(frozen=True, slots=True)
class MemoryRetrievalRequest:
    purpose: str
    scope: Scope
    query_text: str | None = None
    memory_type_filter: str | None = None
    result_limit: int = 3
    truth_anchor: str | None = None
    explicit_memory_ids: tuple[str, ...] = ()

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
        validate_project_id_present(str(self.scope.project_id))


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
    store,
    embedder=None,
) -> MemoryRetrievalResult:
    """Execute the truth-first retrieval pipeline.

    Memory retrieval is support retrieval, not truth retrieval.
    Cross-project retrieval is hard-forbidden; scope filter is applied first.
    Accepts any store satisfying MemoryStoreProtocol.
    An optional embedder enables the semantic retrieval stage.
    """
    if not isinstance(request, MemoryRetrievalRequest):
        raise TypeError("memory retrieval requires a MemoryRetrievalRequest")

    # Stage 3: explicit linked memory fetch
    explicit_ids: frozenset[str] = frozenset(request.explicit_memory_ids)
    explicit_records = _fetch_explicit(explicit_ids, store=store, request=request)

    # Stage 4: scoped lexical retrieval
    if request.query_text:
        lexical_records = list(store.search_lexical(
            str(request.scope.project_id),
            request.query_text,
            memory_type_filter=request.memory_type_filter,
            limit=request.result_limit * 3,
        ))
    else:
        lexical_records = _fetch_scoped_lexical(request=request, store=store)

    # Stage 5: scoped semantic retrieval (when embedder provided)
    semantic_records: list[CommittedMemoryRecord] = []
    if embedder is not None and request.query_text:
        try:
            query_emb = embedder.embed(request.query_text)
            semantic_records = list(store.search_semantic(
                str(request.scope.project_id),
                query_emb,
                memory_type_filter=request.memory_type_filter,
                limit=request.result_limit * 3,
            ))
        except Exception:
            # Semantic retrieval failure must not break the pipeline
            pass

    # Stage 6: dedupe and merge candidates
    all_records = _merge_and_dedupe(explicit_records, lexical_records, semantic_records)

    # Stage 7: rerank
    ranked = rerank(
        all_records,
        request_scope=request.scope,
        query_text=request.query_text,
        explicit_ids=explicit_ids,
    )

    # Stage 8: conflict labeling
    labeled = apply_conflict_labels(records=tuple(ranked), truth_anchor=request.truth_anchor)

    # Stage 9: budget trim (active records first)
    active = [r for r in labeled if r.record_status == "active"]
    bounded = tuple(active[: request.result_limit])

    # Stage 10: package output + emit retrieval event
    notes = ["memory retrieval is support only; current truth still lives in state"]
    if any(has_conflict(r) for r in bounded):
        notes.append(
            "returned memory includes stale or conflicting support and does not override truth"
        )

    _emit_retrieval_event(
        store=store,
        request=request,
        bounded=bounded,
        explicit_count=len(explicit_records),
        lexical_count=len(lexical_records),
        semantic_count=len(semantic_records),
    )

    return MemoryRetrievalResult(
        request=request,
        records=bounded,
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
    store,
) -> MemoryId:
    if not isinstance(memory_id, str):
        raise TypeError("canonical memory linkage requires a committed memory_id string")
    committed_memory_id = coerce_memory_id(memory_id)
    if store.get_committed(str(committed_memory_id)) is None:
        raise ValueError("canonical memory linkage requires an already committed memory_id")
    return committed_memory_id


# --- Internal retrieval helpers ---

def _fetch_explicit(
    explicit_ids: frozenset[str],
    *,
    store,
    request: MemoryRetrievalRequest,
) -> list[CommittedMemoryRecord]:
    if not explicit_ids:
        return []
    records = []
    for mid in explicit_ids:
        record = store.get_committed(mid)
        if record is not None and _scope_matches(request.scope, record.scope):
            records.append(record)
    return records


def _fetch_scoped_lexical(
    *,
    request: MemoryRetrievalRequest,
    store,
) -> list[CommittedMemoryRecord]:
    """Fallback lexical fetch when no query_text is present (returns all active project records)."""
    return [
        record
        for record in store.list_project_records(str(request.scope.project_id))
        if record.record_status == "active"
        and _scope_matches(request.scope, record.scope)
        and (
            request.memory_type_filter is None
            or record.memory_type == request.memory_type_filter
        )
        and _matches_query(record=record, query_text=request.query_text)
    ]


def _merge_and_dedupe(
    explicit: list[CommittedMemoryRecord],
    lexical: list[CommittedMemoryRecord],
    semantic: list[CommittedMemoryRecord],
) -> list[CommittedMemoryRecord]:
    seen: set[str] = set()
    merged: list[CommittedMemoryRecord] = []
    for record in explicit + lexical + semantic:
        key = str(record.memory_id)
        if key in seen:
            continue
        seen.add(key)
        merged.append(record)
    return merged


def _scope_matches(request_scope: Scope, record_scope: Scope) -> bool:
    if request_scope.project_id != record_scope.project_id:
        return False
    if request_scope.work_unit_id is None:
        return record_scope.work_unit_id is None and record_scope.run_id is None
    if request_scope.run_id is None:
        return record_scope.run_id is None and record_scope.work_unit_id in {
            None,
            request_scope.work_unit_id,
        }
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


def _emit_retrieval_event(
    *,
    store,
    request: MemoryRetrievalRequest,
    bounded: tuple[CommittedMemoryRecord, ...],
    explicit_count: int,
    lexical_count: int,
    semantic_count: int,
) -> None:
    from .conflict_labeler import has_conflict

    try:
        event = MemoryRetrievalEvent(
            retrieval_event_id=coerce_retrieval_event_id(f"re-{uuid.uuid4().hex[:12]}"),
            project_id=str(request.scope.project_id),
            purpose=request.purpose,
            returned_count=len(bounded),
            explicit_hit_count=explicit_count,
            lexical_hit_count=lexical_count,
            semantic_hit_count=semantic_count,
            contradiction_count=sum(1 for r in bounded if has_conflict(r)),
            created_at=utc_now(),
        )
        store.store_retrieval_event(event)
    except Exception:
        # Audit failure must not break retrieval
        pass
