"""Bounded compiled knowledge models for support-only artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from jeff.cognitive.types import normalize_text_list, require_text
from jeff.core.schemas import coerce_project_id, coerce_run_id, coerce_work_unit_id
from jeff.memory.types import assert_not_global_scope, normalized_identity

from .ids import KnowledgeArtifactId, coerce_knowledge_artifact_id

ARTIFACT_FAMILIES = {"source_digest", "topic_note"}
ARTIFACT_STATUSES = {
    "fresh",
    "stale_review_needed",
    "stale_rebuild_needed",
    "superseded",
    "quarantined",
}
PROVENANCE_KINDS = {
    "research_artifact_record",
    "research_archive_artifact",
    "knowledge_artifact",
    "source_ref",
}
SCHEMA_VERSION = "1.0"
CONTEXT_PRIORITY = (
    "canonical_truth",
    "governance_truth",
    "committed_memory",
    "compiled_knowledge",
    "raw_sources",
)


@dataclass(frozen=True, slots=True)
class KnowledgeProvenance:
    upstream_kind: str
    upstream_id: str
    project_id: str
    source_refs: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.upstream_kind not in PROVENANCE_KINDS:
            raise ValueError(f"unsupported provenance upstream_kind: {self.upstream_kind}")
        object.__setattr__(self, "upstream_id", require_text(self.upstream_id, field_name="upstream_id"))
        project_id = coerce_project_id(str(self.project_id))
        assert_not_global_scope(project_id)
        object.__setattr__(self, "project_id", project_id)
        object.__setattr__(self, "source_refs", normalize_text_list(self.source_refs, field_name="source_refs"))
        object.__setattr__(self, "notes", normalize_text_list(self.notes, field_name="notes"))


@dataclass(frozen=True, slots=True)
class MemoryHandoffSignal:
    signal_id: str
    signal_summary: str
    support_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "signal_id", require_text(self.signal_id, field_name="signal_id"))
        object.__setattr__(self, "signal_summary", require_text(self.signal_summary, field_name="signal_summary"))
        object.__setattr__(self, "support_refs", normalize_text_list(self.support_refs, field_name="support_refs"))
        if not self.support_refs:
            raise ValueError("memory handoff signals must keep at least one support_ref")


@dataclass(frozen=True, slots=True)
class CompiledKnowledgeArtifact:
    artifact_id: KnowledgeArtifactId
    artifact_family: str
    project_id: str
    work_unit_id: str | None
    run_id: str | None
    title: str
    generated_at: str
    updated_at: str
    status: str = "fresh"
    schema_version: str = SCHEMA_VERSION
    support_only: bool = True
    truth_posture: str = "support_only"
    derived_from_artifact_ids: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    provenance: tuple[KnowledgeProvenance, ...] = ()
    related_artifact_ids: tuple[str, ...] = ()
    supporting_artifact_ids: tuple[str, ...] = ()
    supersedes_artifact_id: str | None = None
    superseded_by_artifact_id: str | None = None
    topic_key: str | None = None
    memory_handoff_signal: MemoryHandoffSignal | None = None
    source_summary: str | None = None
    important_claims: tuple[str, ...] = ()
    evidence_points: tuple[str, ...] = ()
    extraction_caveats: tuple[str, ...] = ()
    topic_framing: str | None = None
    major_supported_points: tuple[str, ...] = ()
    contested_points: tuple[str, ...] = ()
    unresolved_items: tuple[str, ...] = ()
    relevant_source_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.artifact_family not in ARTIFACT_FAMILIES:
            raise ValueError(f"unsupported compiled knowledge artifact_family: {self.artifact_family}")
        object.__setattr__(self, "artifact_id", coerce_knowledge_artifact_id(str(self.artifact_id)))
        project_id = coerce_project_id(str(self.project_id))
        assert_not_global_scope(project_id)
        object.__setattr__(self, "project_id", project_id)
        if self.work_unit_id is not None:
            object.__setattr__(self, "work_unit_id", coerce_work_unit_id(str(self.work_unit_id)))
        if self.run_id is not None:
            object.__setattr__(self, "run_id", coerce_run_id(str(self.run_id)))
        if self.run_id is not None and self.work_unit_id is None:
            raise ValueError("run_id requires work_unit_id in the shared scope block")
        object.__setattr__(self, "title", require_text(self.title, field_name="title"))
        object.__setattr__(self, "generated_at", require_text(self.generated_at, field_name="generated_at"))
        object.__setattr__(self, "updated_at", require_text(self.updated_at, field_name="updated_at"))
        if self.status not in ARTIFACT_STATUSES:
            raise ValueError(f"unsupported compiled knowledge status: {self.status}")
        if self.support_only is not True or self.truth_posture != "support_only":
            raise ValueError("compiled knowledge artifacts must remain support-only")
        object.__setattr__(
            self,
            "derived_from_artifact_ids",
            normalize_text_list(self.derived_from_artifact_ids, field_name="derived_from_artifact_ids"),
        )
        object.__setattr__(self, "source_refs", normalize_text_list(self.source_refs, field_name="source_refs"))
        object.__setattr__(
            self,
            "related_artifact_ids",
            normalize_text_list(self.related_artifact_ids, field_name="related_artifact_ids"),
        )
        object.__setattr__(
            self,
            "supporting_artifact_ids",
            normalize_text_list(self.supporting_artifact_ids, field_name="supporting_artifact_ids"),
        )
        object.__setattr__(
            self,
            "important_claims",
            normalize_text_list(self.important_claims, field_name="important_claims"),
        )
        object.__setattr__(self, "evidence_points", normalize_text_list(self.evidence_points, field_name="evidence_points"))
        object.__setattr__(
            self,
            "extraction_caveats",
            normalize_text_list(self.extraction_caveats, field_name="extraction_caveats"),
        )
        object.__setattr__(
            self,
            "major_supported_points",
            normalize_text_list(self.major_supported_points, field_name="major_supported_points"),
        )
        object.__setattr__(
            self,
            "contested_points",
            normalize_text_list(self.contested_points, field_name="contested_points"),
        )
        object.__setattr__(
            self,
            "unresolved_items",
            normalize_text_list(self.unresolved_items, field_name="unresolved_items"),
        )
        object.__setattr__(
            self,
            "relevant_source_refs",
            normalize_text_list(self.relevant_source_refs, field_name="relevant_source_refs"),
        )
        if self.supersedes_artifact_id is not None:
            object.__setattr__(
                self,
                "supersedes_artifact_id",
                require_text(self.supersedes_artifact_id, field_name="supersedes_artifact_id"),
            )
        if self.superseded_by_artifact_id is not None:
            object.__setattr__(
                self,
                "superseded_by_artifact_id",
                require_text(self.superseded_by_artifact_id, field_name="superseded_by_artifact_id"),
            )
        if self.source_summary is not None:
            object.__setattr__(self, "source_summary", require_text(self.source_summary, field_name="source_summary"))
        if self.topic_framing is not None:
            object.__setattr__(self, "topic_framing", require_text(self.topic_framing, field_name="topic_framing"))
        if self.topic_key is None and self.artifact_family == "topic_note":
            object.__setattr__(self, "topic_key", normalized_identity(self.topic_framing or self.title))
        elif self.topic_key is not None:
            object.__setattr__(self, "topic_key", normalized_identity(self.topic_key))

        for provenance in self.provenance:
            if provenance.project_id != self.project_id:
                raise ValueError("compiled knowledge provenance must stay within the current project scope")
        if str(self.artifact_id) in self.derived_from_artifact_ids:
            raise ValueError("compiled knowledge artifact cannot derive from itself")
        if str(self.artifact_id) in self.related_artifact_ids:
            raise ValueError("compiled knowledge artifact cannot link to itself")

        if self.artifact_family == "source_digest":
            if self.source_summary is None:
                raise ValueError("source_digest requires source_summary")
            if not self.source_refs:
                raise ValueError("source_digest requires at least one source_ref")
            if not self.provenance:
                raise ValueError("source_digest requires provenance")
            if not self.important_claims and not self.evidence_points:
                raise ValueError("source_digest requires important_claims or evidence_points")

        if self.artifact_family == "topic_note":
            if self.topic_framing is None:
                raise ValueError("topic_note requires topic_framing")
            if len(self.supporting_artifact_ids) < 2:
                raise ValueError("topic_note requires multiple supporting_artifact_ids")
            if not self.provenance:
                raise ValueError("topic_note requires provenance")
            if not self.major_supported_points and not self.contested_points and not self.unresolved_items:
                raise ValueError(
                    "topic_note requires supported points, contested points, or unresolved items"
                )


def artifact_to_payload(artifact: CompiledKnowledgeArtifact) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "artifact_id": str(artifact.artifact_id),
        "artifact_family": artifact.artifact_family,
        "project_id": artifact.project_id,
        "work_unit_id": artifact.work_unit_id,
        "run_id": artifact.run_id,
        "title": artifact.title,
        "generated_at": artifact.generated_at,
        "updated_at": artifact.updated_at,
        "status": artifact.status,
        "schema_version": artifact.schema_version,
        "support_only": artifact.support_only,
        "truth_posture": artifact.truth_posture,
        "derived_from_artifact_ids": list(artifact.derived_from_artifact_ids),
        "source_refs": list(artifact.source_refs),
        "provenance": [
            {
                "upstream_kind": item.upstream_kind,
                "upstream_id": item.upstream_id,
                "project_id": item.project_id,
                "source_refs": list(item.source_refs),
                "notes": list(item.notes),
            }
            for item in artifact.provenance
        ],
        "related_artifact_ids": list(artifact.related_artifact_ids),
        "supporting_artifact_ids": list(artifact.supporting_artifact_ids),
        "supersedes_artifact_id": artifact.supersedes_artifact_id,
        "superseded_by_artifact_id": artifact.superseded_by_artifact_id,
        "topic_key": artifact.topic_key,
        "source_summary": artifact.source_summary,
        "important_claims": list(artifact.important_claims),
        "evidence_points": list(artifact.evidence_points),
        "extraction_caveats": list(artifact.extraction_caveats),
        "topic_framing": artifact.topic_framing,
        "major_supported_points": list(artifact.major_supported_points),
        "contested_points": list(artifact.contested_points),
        "unresolved_items": list(artifact.unresolved_items),
        "relevant_source_refs": list(artifact.relevant_source_refs),
    }
    if artifact.memory_handoff_signal is not None:
        payload["memory_handoff_signal"] = {
            "signal_id": artifact.memory_handoff_signal.signal_id,
            "signal_summary": artifact.memory_handoff_signal.signal_summary,
            "support_refs": list(artifact.memory_handoff_signal.support_refs),
        }
    return payload


def artifact_from_payload(payload: dict[str, Any]) -> CompiledKnowledgeArtifact:
    memory_handoff_payload = payload.get("memory_handoff_signal")
    memory_handoff_signal = None
    if isinstance(memory_handoff_payload, dict):
        memory_handoff_signal = MemoryHandoffSignal(
            signal_id=str(memory_handoff_payload["signal_id"]),
            signal_summary=str(memory_handoff_payload["signal_summary"]),
            support_refs=tuple(memory_handoff_payload.get("support_refs", ())),
        )
    provenance = tuple(
        KnowledgeProvenance(
            upstream_kind=str(item["upstream_kind"]),
            upstream_id=str(item["upstream_id"]),
            project_id=str(item["project_id"]),
            source_refs=tuple(item.get("source_refs", ())),
            notes=tuple(item.get("notes", ())),
        )
        for item in payload.get("provenance", ())
    )
    return CompiledKnowledgeArtifact(
        artifact_id=coerce_knowledge_artifact_id(str(payload["artifact_id"])),
        artifact_family=str(payload["artifact_family"]),
        project_id=str(payload["project_id"]),
        work_unit_id=payload.get("work_unit_id"),
        run_id=payload.get("run_id"),
        title=str(payload["title"]),
        generated_at=str(payload["generated_at"]),
        updated_at=str(payload["updated_at"]),
        status=str(payload.get("status", "fresh")),
        schema_version=str(payload.get("schema_version", SCHEMA_VERSION)),
        support_only=bool(payload.get("support_only", True)),
        truth_posture=str(payload.get("truth_posture", "support_only")),
        derived_from_artifact_ids=tuple(payload.get("derived_from_artifact_ids", ())),
        source_refs=tuple(payload.get("source_refs", ())),
        provenance=provenance,
        related_artifact_ids=tuple(payload.get("related_artifact_ids", ())),
        supporting_artifact_ids=tuple(payload.get("supporting_artifact_ids", ())),
        supersedes_artifact_id=payload.get("supersedes_artifact_id"),
        superseded_by_artifact_id=payload.get("superseded_by_artifact_id"),
        topic_key=payload.get("topic_key"),
        memory_handoff_signal=memory_handoff_signal,
        source_summary=payload.get("source_summary"),
        important_claims=tuple(payload.get("important_claims", ())),
        evidence_points=tuple(payload.get("evidence_points", ())),
        extraction_caveats=tuple(payload.get("extraction_caveats", ())),
        topic_framing=payload.get("topic_framing"),
        major_supported_points=tuple(payload.get("major_supported_points", ())),
        contested_points=tuple(payload.get("contested_points", ())),
        unresolved_items=tuple(payload.get("unresolved_items", ())),
        relevant_source_refs=tuple(payload.get("relevant_source_refs", ())),
    )