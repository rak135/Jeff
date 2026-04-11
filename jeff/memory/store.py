"""Small in-memory repository for committed memory only."""

from __future__ import annotations

from jeff.core.schemas import MemoryId, coerce_memory_id, coerce_project_id

from .models import CommittedMemoryRecord


class InMemoryMemoryStore:
    def __init__(self) -> None:
        self._records: dict[MemoryId, CommittedMemoryRecord] = {}
        self._counter = 0

    def allocate_memory_id(self) -> MemoryId:
        self._counter += 1
        return coerce_memory_id(f"memory-{self._counter}")

    def get_committed(self, memory_id: str) -> CommittedMemoryRecord | None:
        return self._records.get(coerce_memory_id(memory_id))

    def list_project_records(self, project_id: str) -> tuple[CommittedMemoryRecord, ...]:
        normalized_project_id = coerce_project_id(project_id)
        records = [
            record
            for record in self._records.values()
            if record.scope.project_id == normalized_project_id
        ]
        records.sort(key=lambda record: str(record.memory_id))
        return tuple(records)

    def _store_committed_record(self, record: CommittedMemoryRecord) -> None:
        self._records[record.memory_id] = record
