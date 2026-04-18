"""Memory-layer contracts for durable non-truth continuity.

Memory v1 is project-scoped only.  Global/system memory is hard-forbidden.
Only committed memory_ids may be referenced canonically.
"""

from .models import (
    CommittedMemoryRecord,
    MemoryCandidate,
    MemorySupportRef,
    MemoryWriteDecision,
)
from .retrieval import (
    MemoryRetrievalRequest,
    MemoryRetrievalResult,
    TruthFirstMemoryView,
    build_truth_first_memory_view,
    canonical_memory_link_for_state,
    retrieve_memory,
)
from .schemas import (
    MemoryLink,
    MemoryRetrievalEvent,
    MemoryWriteEvent,
    MemoryWriteResult,
    MaintenanceJobRecord,
)
from .store import InMemoryMemoryStore
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
    process_candidate,
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
    # Store
    "InMemoryMemoryStore",
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
    "process_candidate",
    "write_memory_candidate",
]
