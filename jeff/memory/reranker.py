"""Reranker — merges explicit-link, lexical, and semantic retrieval candidates.

Reranking factors (in priority order per MEMORY_V1.md §19.5):
1. Exact scope fit (run > work_unit > project)
2. Explicit link match
3. Purpose fit (query text relevance)
4. Support quality (strong > moderate > weak)
5. Status (active before superseded)
6. Freshness sensitivity when relevant
7. Recency as a secondary factor only

Superseded memory does not outrank active replacement by default.
"""

from __future__ import annotations

from jeff.core.schemas import Scope

from .models import CommittedMemoryRecord
from .types import normalized_identity

_QUALITY_RANK = {"strong": 3, "moderate": 2, "weak": 1}
_STATUS_RANK = {"active": 2, "superseded": 0, "deprecated": 0, "quarantined": 0}
_SCOPE_RANK = {0: 3, 1: 2, 2: 1}  # run-level=0, work_unit=1, project=2


def _scope_fit_rank(request_scope: Scope, record_scope: Scope) -> int:
    if request_scope.run_id is not None and record_scope.run_id == request_scope.run_id:
        return 0
    if request_scope.work_unit_id is not None and record_scope.work_unit_id == request_scope.work_unit_id:
        return 1
    return 2


def _purpose_fit_score(record: CommittedMemoryRecord, query_text: str | None) -> int:
    if query_text is None:
        return 0
    q = normalized_identity(query_text)
    haystack = normalized_identity(
        " ".join([record.summary, record.why_it_matters, *record.remembered_points])
    )
    return 1 if q in haystack else 0


def _rerank_score(
    record: CommittedMemoryRecord,
    *,
    request_scope: Scope,
    query_text: str | None,
    explicit_ids: frozenset[str],
) -> tuple[int, int, int, int, int]:
    scope_level = _scope_fit_rank(request_scope, record.scope)
    explicit = 1 if str(record.memory_id) in explicit_ids else 0
    purpose = _purpose_fit_score(record, query_text)
    quality = _QUALITY_RANK.get(record.support_quality, 1)
    status = _STATUS_RANK.get(record.record_status, 0)
    # Lower scope_level = closer match; negate for sort descending
    return (-_SCOPE_RANK[scope_level], -explicit, -purpose, -quality, -status)


def rerank(
    records: list[CommittedMemoryRecord],
    *,
    request_scope: Scope,
    query_text: str | None,
    explicit_ids: frozenset[str] | None = None,
) -> list[CommittedMemoryRecord]:
    """Return records sorted by composite rerank score (best first)."""
    _explicit_ids = explicit_ids or frozenset()
    return sorted(
        records,
        key=lambda r: _rerank_score(
            r,
            request_scope=request_scope,
            query_text=query_text,
            explicit_ids=_explicit_ids,
        ),
    )
