"""Lawful adapters from upstream support objects into compiled knowledge inputs."""

from __future__ import annotations

from dataclasses import dataclass

from jeff.cognitive.research import ResearchArtifactRecord
from jeff.cognitive.research.archive import ResearchArchiveArtifact
from jeff.cognitive.types import normalize_text_list, require_text
from jeff.memory.types import normalized_identity

from .models import CompiledKnowledgeArtifact, KnowledgeProvenance


@dataclass(frozen=True, slots=True)
class SourceAwareSupport:
    project_id: str
    work_unit_id: str | None
    run_id: str | None
    title: str
    summary: str
    important_claims: tuple[str, ...]
    evidence_points: tuple[str, ...]
    uncertainties: tuple[str, ...]
    source_refs: tuple[str, ...]
    upstream_artifact_ids: tuple[str, ...]
    provenance: tuple[KnowledgeProvenance, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "title", require_text(self.title, field_name="title"))
        object.__setattr__(self, "summary", require_text(self.summary, field_name="summary"))
        object.__setattr__(
            self,
            "important_claims",
            normalize_text_list(self.important_claims, field_name="important_claims"),
        )
        object.__setattr__(self, "evidence_points", normalize_text_list(self.evidence_points, field_name="evidence_points"))
        object.__setattr__(self, "uncertainties", normalize_text_list(self.uncertainties, field_name="uncertainties"))
        object.__setattr__(self, "source_refs", normalize_text_list(self.source_refs, field_name="source_refs"))
        object.__setattr__(
            self,
            "upstream_artifact_ids",
            normalize_text_list(self.upstream_artifact_ids, field_name="upstream_artifact_ids"),
        )
        if not self.source_refs:
            raise ValueError("source-aware support must keep at least one source_ref")
        if not self.upstream_artifact_ids:
            raise ValueError("source-aware support must keep at least one upstream_artifact_id")


def support_from_research_record(record: ResearchArtifactRecord) -> SourceAwareSupport:
    project_id = require_text(record.project_id or "", field_name="project_id")
    important_claims = tuple(finding.text for finding in record.findings if finding.text)
    evidence_points = tuple(item.text for item in record.evidence_items if item.text)
    title = f"Research artifact {record.artifact_id}"
    return SourceAwareSupport(
        project_id=project_id,
        work_unit_id=record.work_unit_id,
        run_id=record.run_id,
        title=title,
        summary=record.summary,
        important_claims=important_claims,
        evidence_points=evidence_points,
        uncertainties=record.uncertainties,
        source_refs=record.source_ids,
        upstream_artifact_ids=(record.artifact_id,),
        provenance=(
            KnowledgeProvenance(
                upstream_kind="research_artifact_record",
                upstream_id=record.artifact_id,
                project_id=project_id,
                source_refs=record.source_ids,
                notes=(record.question,),
            ),
        ),
    )


def support_from_archive_artifact(artifact: ResearchArchiveArtifact) -> SourceAwareSupport:
    evidence_points = tuple(item.evidence_text for item in artifact.evidence_items if item.evidence_text)
    important_claims = artifact.findings or artifact.inference
    notes = [artifact.artifact_family]
    if artifact.question_or_objective is not None:
        notes.append(artifact.question_or_objective)
    return SourceAwareSupport(
        project_id=artifact.project_id,
        work_unit_id=artifact.work_unit_id,
        run_id=artifact.run_id,
        title=artifact.title,
        summary=artifact.summary,
        important_claims=important_claims,
        evidence_points=evidence_points,
        uncertainties=artifact.uncertainty,
        source_refs=artifact.source_refs,
        upstream_artifact_ids=(str(artifact.artifact_id),),
        provenance=(
            KnowledgeProvenance(
                upstream_kind="research_archive_artifact",
                upstream_id=str(artifact.artifact_id),
                project_id=artifact.project_id,
                source_refs=artifact.source_refs,
                notes=tuple(notes),
            ),
        ),
    )


def support_from_knowledge_artifact(artifact: CompiledKnowledgeArtifact) -> SourceAwareSupport:
    if artifact.artifact_family == "source_digest":
        summary = artifact.source_summary or artifact.title
        important_claims = artifact.important_claims
        evidence_points = artifact.evidence_points
        uncertainties = artifact.extraction_caveats
    else:
        summary = artifact.topic_framing or artifact.title
        important_claims = artifact.major_supported_points
        evidence_points = artifact.contested_points
        uncertainties = artifact.unresolved_items
    return SourceAwareSupport(
        project_id=artifact.project_id,
        work_unit_id=artifact.work_unit_id,
        run_id=artifact.run_id,
        title=artifact.title,
        summary=summary,
        important_claims=important_claims,
        evidence_points=evidence_points,
        uncertainties=uncertainties,
        source_refs=artifact.source_refs or artifact.relevant_source_refs,
        upstream_artifact_ids=(str(artifact.artifact_id),),
        provenance=(
            KnowledgeProvenance(
                upstream_kind="knowledge_artifact",
                upstream_id=str(artifact.artifact_id),
                project_id=artifact.project_id,
                source_refs=artifact.source_refs or artifact.relevant_source_refs,
                notes=(artifact.artifact_family, normalized_identity(artifact.title)),
            ),
        ),
    )


def derive_locality(supports: tuple[SourceAwareSupport, ...]) -> tuple[str | None, str | None]:
    if not supports:
        raise ValueError("at least one support input is required")
    project_ids = {item.project_id for item in supports}
    if len(project_ids) != 1:
        raise ValueError("compiled knowledge cannot cross project boundaries")
    work_unit_ids = {item.work_unit_id for item in supports}
    run_ids = {item.run_id for item in supports}
    work_unit_id = next(iter(work_unit_ids)) if len(work_unit_ids) == 1 else None
    run_id = next(iter(run_ids)) if len(run_ids) == 1 else None
    if run_id is not None and work_unit_id is None:
        run_id = None
    return work_unit_id, run_id


def collect_source_refs(supports: tuple[SourceAwareSupport, ...]) -> tuple[str, ...]:
    source_refs = {source_ref for support in supports for source_ref in support.source_refs}
    return tuple(sorted(source_refs))


def collect_provenance(supports: tuple[SourceAwareSupport, ...]) -> tuple[KnowledgeProvenance, ...]:
    seen: set[tuple[str, str]] = set()
    ordered: list[KnowledgeProvenance] = []
    for support in supports:
        for provenance in support.provenance:
            key = (provenance.upstream_kind, provenance.upstream_id)
            if key in seen:
                continue
            seen.add(key)
            ordered.append(provenance)
    return tuple(ordered)


def collect_supporting_ids(supports: tuple[SourceAwareSupport, ...]) -> tuple[str, ...]:
    supporting_ids = {artifact_id for support in supports for artifact_id in support.upstream_artifact_ids}
    return tuple(sorted(supporting_ids))