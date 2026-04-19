"""Builders for compiled source digests."""

from __future__ import annotations

from .compiler import SourceAwareSupport
from .ids import allocate_knowledge_artifact_id
from .models import CompiledKnowledgeArtifact, MemoryHandoffSignal
from jeff.memory.types import utc_now


def build_source_digest(
    support: SourceAwareSupport,
    *,
    artifact_id: str | None = None,
    generated_at: str | None = None,
    memory_handoff_signal: MemoryHandoffSignal | None = None,
) -> CompiledKnowledgeArtifact:
    timestamp = generated_at or utc_now()
    digest_title = f"Source digest: {support.title}"
    evidence_points = support.evidence_points or support.important_claims[:3]
    return CompiledKnowledgeArtifact(
        artifact_id=artifact_id or allocate_knowledge_artifact_id(),
        artifact_family="source_digest",
        project_id=support.project_id,
        work_unit_id=support.work_unit_id,
        run_id=support.run_id,
        title=digest_title,
        generated_at=timestamp,
        updated_at=timestamp,
        derived_from_artifact_ids=support.upstream_artifact_ids,
        source_refs=support.source_refs,
        provenance=support.provenance,
        supporting_artifact_ids=support.upstream_artifact_ids,
        memory_handoff_signal=memory_handoff_signal,
        source_summary=support.summary,
        important_claims=support.important_claims,
        evidence_points=evidence_points,
        extraction_caveats=support.uncertainties,
    )