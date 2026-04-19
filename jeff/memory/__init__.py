"""Memory-layer contracts for durable non-truth continuity.

Memory v1 is project-scoped only.  Global/system memory is hard-forbidden.
Only committed memory_ids may be referenced canonically.
"""

from .embedder import HashEmbedder, NullEmbedder, VectorEmbedder
from .models import (
    CommittedMemoryRecord,
    MemoryCandidate,
    MemorySupportRef,
    MemoryWriteDecision,
)
from .postgres_store import PostgresMemoryStore
from .retrieval import (
    MemoryRetrievalRequest,
    MemoryRetrievalResult,
    TruthFirstMemoryView,
    build_truth_first_memory_view,
    canonical_memory_link_for_state,
    retrieve_memory,
)
from .run_handoff import handoff_run_summary_to_memory
from .schemas import (
    MemoryLink,
    MemoryRetrievalEvent,
    MemoryWriteEvent,
    MemoryWriteResult,
    MaintenanceJobRecord,
)
from .store import InMemoryMemoryStore
from .store_protocol import MemoryStoreProtocol
from .types import (
    CandidateStatus,
    ConflictPosture,
    DeferReasonCode,
    FreshnessSensitivity,
    MemoryRecordStatus,
    MemoryType,
    RecordStabilityPosture,
    StabilityPosture,
    SupportQuality,
    WriteOutcome,
)
from .write_pipeline import (
    create_memory_candidate,
    merge_into_candidate,
    process_candidate,
    supersede_candidate,
    write_memory_candidate,
)

__all__ = [
    # Core models
    "CommittedMemoryRecord",
    "MemoryCandidate",
    "MemorySupportRef",
    "MemoryWriteDecision",
    # Extended schemas
    "MaintenanceJobRecord",
    "MemoryLink",
    "MemoryRetrievalEvent",
    "MemoryWriteEvent",
    "MemoryWriteResult",
    # Retrieval
    "MemoryRetrievalRequest",
    "MemoryRetrievalResult",
    "TruthFirstMemoryView",
    "build_truth_first_memory_view",
    "canonical_memory_link_for_state",
    "retrieve_memory",
    "handoff_run_summary_to_memory",
    # Store
    "InMemoryMemoryStore",
    "MemoryStoreProtocol",
    "PostgresMemoryStore",
    # Embedders
    "HashEmbedder",
    "NullEmbedder",
    "VectorEmbedder",
    # Types
    "CandidateStatus",
    "ConflictPosture",
    "DeferReasonCode",
    "FreshnessSensitivity",
    "MemoryRecordStatus",
    "MemoryType",
    "RecordStabilityPosture",
    "StabilityPosture",
    "SupportQuality",
    "WriteOutcome",
    # Write pipeline
    "create_memory_candidate",
    "merge_into_candidate",
    "process_candidate",
    "supersede_candidate",
    "write_memory_candidate",
]
