"""Storage contract for memory persistence backends.

Both InMemoryMemoryStore and PostgresMemoryStore satisfy this Protocol.
All pipeline and retrieval code depends on this contract, not on any concrete store type.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from jeff.core.schemas import MemoryId

from .models import CommittedMemoryRecord

if TYPE_CHECKING:
    from .schemas import MaintenanceJobRecord, MemoryLink, MemoryRetrievalEvent, MemoryWriteEvent


@runtime_checkable
class MemoryStoreProtocol(Protocol):
    """The storage contract for committed memory records, links, and audit events.

    Implementations must scope all operations to a project — cross-project access
    is always the caller's responsibility to prevent, but the store enforces it on
    list_project_records and get_links_for_target.
    """

    # --- Record operations ---

    def allocate_memory_id(self) -> MemoryId:
        """Allocate and return a new unique memory_id without committing any record."""
        ...

    def get_committed(self, memory_id: str) -> CommittedMemoryRecord | None:
        """Retrieve a committed record by memory_id. Returns None if not found."""
        ...

    def list_project_records(self, project_id: str) -> tuple[CommittedMemoryRecord, ...]:
        """Return all records for project_id sorted by memory_id (all statuses)."""
        ...

    def _store_committed_record(self, record: CommittedMemoryRecord) -> None:
        """Persist a committed record. Upserts if memory_id already exists."""
        ...

    def _mark_superseded(
        self,
        *,
        superseded_memory_id: MemoryId,
        new_memory_id: MemoryId,
    ) -> None:
        """Mark an existing record as superseded by the given new record."""
        ...

    # --- Link operations ---

    def store_link(self, link: "MemoryLink") -> None:
        """Persist a thin-link record."""
        ...

    def get_links_for_target(self, target_id: str, project_id: str) -> tuple["MemoryLink", ...]:
        """Return links pointing to target_id whose source memory belongs to project_id."""
        ...

    def get_links_for_memory(self, memory_id: str) -> tuple["MemoryLink", ...]:
        """Return all links originating from the given memory_id."""
        ...

    # --- Retrieval search ---

    def search_lexical(
        self,
        project_id: str,
        query: str,
        *,
        memory_type_filter: str | None,
        limit: int,
    ) -> tuple[CommittedMemoryRecord, ...]:
        """Token/FTS search for active records within the given project."""
        ...

    def search_semantic(
        self,
        project_id: str,
        query_embedding: list[float],
        *,
        memory_type_filter: str | None,
        limit: int,
    ) -> tuple[CommittedMemoryRecord, ...]:
        """Vector similarity search for active records with stored embeddings.

        Returns an empty tuple when embeddings are unavailable or no records are indexed.
        Partial indexing must not suppress already-indexed records.
        """
        ...

    def store_embedding(self, memory_id: str, embedding: list[float]) -> None:
        """Associate a vector embedding with a committed record for semantic retrieval."""
        ...

    # --- Audit / event operations ---

    def store_write_event(self, event: "MemoryWriteEvent") -> None:
        """Persist a write-side audit event."""
        ...

    def store_retrieval_event(self, event: "MemoryRetrievalEvent") -> None:
        """Persist a retrieval audit event."""
        ...

    def store_maintenance_job(self, job: "MaintenanceJobRecord") -> None:
        """Persist a maintenance job record."""
        ...

    # --- Transaction control ---

    def atomic(self) -> AbstractContextManager[None]:
        """Context manager that groups mutations into one atomic operation.

        On PostgreSQL: commit succeeds only if all steps inside complete.
        On InMemoryMemoryStore: no-op (dict mutations are inherently atomic in CPython).
        """
        ...
