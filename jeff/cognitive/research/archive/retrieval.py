"""Bounded retrieval for the research archive layer."""

from __future__ import annotations

from dataclasses import dataclass

from jeff.cognitive.types import normalize_text_list, require_text
from jeff.core.schemas import Scope

from .models import ARTIFACT_FAMILIES, HISTORY_FAMILIES, ResearchArchiveArtifact
from .registry import ResearchArchiveRegistry
from .telemetry import record_retrieval


@dataclass(frozen=True, slots=True)
class ResearchArchiveRetrievalRequest:
    purpose: str
    scope: Scope
    artifact_family_filter: str | None = None
    result_limit: int = 5
    effective_date: str | None = None
    effective_period: str | None = None
    observed_date: str | None = None
    history_only: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "purpose", require_text(self.purpose, field_name="purpose"))
        if self.artifact_family_filter is not None and self.artifact_family_filter not in ARTIFACT_FAMILIES:
            raise ValueError(f"unsupported artifact_family_filter: {self.artifact_family_filter}")
        if not isinstance(self.result_limit, int):
            raise TypeError("result_limit must be an integer")
        if self.result_limit <= 0 or self.result_limit > 25:
            raise ValueError("result_limit must stay between 1 and 25")
        if self.effective_date is not None:
            object.__setattr__(self, "effective_date", require_text(self.effective_date, field_name="effective_date"))
        if self.effective_period is not None:
            object.__setattr__(self, "effective_period", require_text(self.effective_period, field_name="effective_period"))
        if self.observed_date is not None:
            object.__setattr__(self, "observed_date", require_text(self.observed_date, field_name="observed_date"))


@dataclass(frozen=True, slots=True)
class ResearchArchiveRetrievalResult:
    request: ResearchArchiveRetrievalRequest
    records: tuple[ResearchArchiveArtifact, ...]
    notes: tuple[str, ...] = ()
    support_only: bool = True
    explicitly_historical: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "notes", normalize_text_list(self.notes, field_name="notes"))
        if self.support_only is not True:
            raise ValueError("archive retrieval results must remain support_only")


def retrieve_archive(
    *,
    request: ResearchArchiveRetrievalRequest,
    store,
) -> ResearchArchiveRetrievalResult:
    if not isinstance(request, ResearchArchiveRetrievalRequest):
        raise TypeError("archive retrieval requires a ResearchArchiveRetrievalRequest")

    registry = ResearchArchiveRegistry(store)
    entries = registry.list_entries(
        project_id=str(request.scope.project_id),
        artifact_family=request.artifact_family_filter,
    )
    records: list[ResearchArchiveArtifact] = []
    history_requested = bool(
        request.history_only
        or request.effective_date
        or request.effective_period
        or request.observed_date
        or request.artifact_family_filter in HISTORY_FAMILIES
    )
    for entry in entries:
        record = store.get_by_id(str(request.scope.project_id), entry.artifact_id)
        if record is None:
            continue
        if not _scope_matches(request.scope, record):
            continue
        if history_requested and record.artifact_family not in HISTORY_FAMILIES:
            continue
        if request.effective_date is not None and record.effective_date != request.effective_date:
            continue
        if request.effective_period is not None and record.effective_period != request.effective_period:
            continue
        if request.observed_date is not None and record.observed_date != request.observed_date:
            continue
        records.append(record)

    bounded = tuple(records[: request.result_limit])
    notes = [
        "research archive retrieval is support only; archive artifacts are not memory, compiled knowledge, or canonical truth",
    ]
    if history_requested:
        notes.append("history retrieval remains explicitly historical and does not collapse into current truth")
    record_retrieval(historical=history_requested)
    return ResearchArchiveRetrievalResult(
        request=request,
        records=bounded,
        notes=tuple(notes),
        explicitly_historical=history_requested,
    )


def _scope_matches(request_scope: Scope, record: ResearchArchiveArtifact) -> bool:
    if str(request_scope.project_id) != str(record.project_id):
        return False
    if request_scope.work_unit_id is None:
        return True
    if request_scope.run_id is None:
        return record.run_id is None and str(record.work_unit_id) in {"None", str(request_scope.work_unit_id)}
    return (
        str(record.run_id) == str(request_scope.run_id)
        or (record.run_id is None and str(record.work_unit_id) == str(request_scope.work_unit_id))
        or (record.run_id is None and record.work_unit_id is None)
    )