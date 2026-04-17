"""Research contracts and bounded acquisition/synthesis paths."""

from .contracts import (
    EvidenceItem,
    EvidencePack,
    ResearchArtifact,
    ResearchFinding,
    ResearchRequest,
    SourceItem,
    validate_research_provenance,
)
from .debug import (
    ResearchDebugEmitter,
    emit_research_debug_event,
    finding_source_refs_summary,
    summarize_values,
)
from .documents import build_document_evidence_pack, collect_document_sources, run_document_research
from .errors import (
    ResearchProvenanceValidationError,
    ResearchSynthesisError,
    ResearchSynthesisRuntimeError,
    ResearchSynthesisValidationError,
)
from .memory_handoff import (
    ResearchMemoryHandoffInput,
    build_research_memory_handoff_input,
    handoff_persisted_research_record_to_memory,
    handoff_research_to_memory,
    should_handoff_research_to_memory,
)
from .persistence import (
    ResearchArtifactRecord,
    ResearchArtifactStore,
    build_research_artifact_record,
    persist_research_artifact,
    run_and_persist_document_research,
    run_and_persist_web_research,
    validate_research_artifact_record,
)
from .synthesis import build_research_model_request, synthesize_research, synthesize_research_with_runtime
from .web import build_web_evidence_pack, collect_web_sources, run_web_research

__all__ = [
    "EvidenceItem",
    "EvidencePack",
    "ResearchArtifact",
    "ResearchArtifactRecord",
    "ResearchArtifactStore",
    "ResearchDebugEmitter",
    "ResearchFinding",
    "ResearchMemoryHandoffInput",
    "ResearchProvenanceValidationError",
    "ResearchRequest",
    "ResearchSynthesisError",
    "ResearchSynthesisRuntimeError",
    "ResearchSynthesisValidationError",
    "SourceItem",
    "build_document_evidence_pack",
    "build_research_memory_handoff_input",
    "build_research_artifact_record",
    "build_research_model_request",
    "build_web_evidence_pack",
    "collect_document_sources",
    "collect_web_sources",
    "emit_research_debug_event",
    "finding_source_refs_summary",
    "handoff_persisted_research_record_to_memory",
    "handoff_research_to_memory",
    "persist_research_artifact",
    "run_and_persist_document_research",
    "run_and_persist_web_research",
    "run_document_research",
    "run_web_research",
    "should_handoff_research_to_memory",
    "summarize_values",
    "synthesize_research",
    "synthesize_research_with_runtime",
    "validate_research_artifact_record",
    "validate_research_provenance",
]
