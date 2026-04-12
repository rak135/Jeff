"""Bounded persistence for research artifacts as support records."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jeff.infrastructure import InfrastructureServices

from .contracts import (
    EvidenceItem,
    EvidencePack,
    ResearchArtifact,
    ResearchFinding,
    ResearchRequest,
    SourceItem,
    validate_research_provenance,
)
from .debug import ResearchDebugEmitter, emit_research_debug_event, finding_source_refs_summary, summarize_values
from .errors import ResearchProvenanceValidationError
from .documents import build_document_evidence_pack, collect_document_sources
from .synthesis import synthesize_research_with_runtime
from .web import build_web_evidence_pack, collect_web_sources


@dataclass(frozen=True, slots=True)
class ResearchArtifactRecord:
    artifact_id: str
    project_id: str | None
    work_unit_id: str | None
    run_id: str | None
    question: str
    source_mode: str
    summary: str
    findings: tuple[ResearchFinding, ...]
    inferences: tuple[str, ...]
    uncertainties: tuple[str, ...]
    recommendation: str | None
    source_ids: tuple[str, ...]
    source_items: tuple[SourceItem, ...]
    evidence_items: tuple[EvidenceItem, ...]
    created_at: str
    schema_version: str = "1.0"


class ResearchArtifactStore:
    def __init__(self, root_dir: Path | str) -> None:
        self.root_dir = Path(root_dir)
        self._artifacts_dir = self.root_dir / "research_artifacts"
        self._artifacts_dir.mkdir(parents=True, exist_ok=True)

    def save(self, record: ResearchArtifactRecord, *, debug_emitter: ResearchDebugEmitter | None = None) -> Path:
        emit_research_debug_event(
            debug_emitter,
            "artifact_store_save_started",
            artifact_id=record.artifact_id,
            source_item_count=len(record.source_items),
            artifact_source_ids=summarize_values(record.source_ids),
            finding_source_refs_summary=finding_source_refs_summary(record.findings),
        )
        validate_research_artifact_record(record)
        path = self._path_for(record.artifact_id)
        payload = _record_to_payload(record)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        emit_research_debug_event(
            debug_emitter,
            "artifact_store_save_succeeded",
            artifact_id=record.artifact_id,
            persisted_record_source_count=len(record.source_items),
            artifact_source_ids=summarize_values(record.source_ids),
        )
        return path

    def load(self, artifact_id: str, *, debug_emitter: ResearchDebugEmitter | None = None) -> ResearchArtifactRecord:
        emit_research_debug_event(
            debug_emitter,
            "artifact_store_load_started",
            artifact_id=artifact_id,
        )
        path = self._path_for(artifact_id)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            emit_research_debug_event(
                debug_emitter,
                "artifact_store_load_failed",
                artifact_id=artifact_id,
                reason="malformed persisted research artifact file",
            )
            raise ValueError(f"malformed persisted research artifact file: {artifact_id}") from exc
        try:
            record = _record_from_payload(payload)
        except ValueError as exc:
            emit_research_debug_event(
                debug_emitter,
                "artifact_store_load_failed",
                artifact_id=artifact_id,
                reason=str(exc),
            )
            raise
        emit_research_debug_event(
            debug_emitter,
            "artifact_store_load_succeeded",
            artifact_id=artifact_id,
            loaded_record_source_count=len(record.source_items),
            artifact_source_ids=summarize_values(record.source_ids),
            finding_source_refs_summary=finding_source_refs_summary(record.findings),
        )
        return record

    def list_records(
        self,
        project_id: str | None = None,
        work_unit_id: str | None = None,
        run_id: str | None = None,
    ) -> tuple[ResearchArtifactRecord, ...]:
        records = [self.load(path.stem) for path in sorted(self._artifacts_dir.glob("*.json"))]
        filtered = [
            record
            for record in records
            if (project_id is None or record.project_id == project_id)
            and (work_unit_id is None or record.work_unit_id == work_unit_id)
            and (run_id is None or record.run_id == run_id)
        ]
        filtered.sort(key=lambda record: (record.created_at, record.artifact_id), reverse=True)
        return tuple(filtered)

    def _path_for(self, artifact_id: str) -> Path:
        return self._artifacts_dir / f"{artifact_id}.json"


def build_research_artifact_record(
    research_request: ResearchRequest,
    evidence_pack: EvidencePack,
    artifact: ResearchArtifact,
    *,
    debug_emitter: ResearchDebugEmitter | None = None,
) -> ResearchArtifactRecord:
    emit_research_debug_event(
        debug_emitter,
        "artifact_record_build_started",
        source_item_count=len(evidence_pack.sources),
        artifact_source_ids=summarize_values(artifact.source_ids),
        finding_source_refs_summary=finding_source_refs_summary(artifact.findings),
    )
    try:
        validate_research_provenance(
            findings=artifact.findings,
            source_ids=artifact.source_ids,
            source_items=evidence_pack.sources,
            evidence_items=evidence_pack.evidence_items,
        )
        created_at = datetime.now(timezone.utc).isoformat(timespec="microseconds")
        nonce = time.time_ns()
        artifact_id = _artifact_id_for(
            research_request=research_request,
            evidence_pack=evidence_pack,
            artifact=artifact,
            created_at=created_at,
            nonce=nonce,
        )
        record = ResearchArtifactRecord(
            artifact_id=artifact_id,
            project_id=research_request.project_id,
            work_unit_id=research_request.work_unit_id,
            run_id=research_request.run_id,
            question=artifact.question,
            source_mode=research_request.source_mode,
            summary=artifact.summary,
            findings=artifact.findings,
            inferences=artifact.inferences,
            uncertainties=artifact.uncertainties,
            recommendation=artifact.recommendation,
            source_ids=artifact.source_ids,
            source_items=evidence_pack.sources,
            evidence_items=evidence_pack.evidence_items,
            created_at=created_at,
        )
        validate_research_artifact_record(record)
    except Exception as exc:
        emit_research_debug_event(
            debug_emitter,
            "artifact_record_build_failed",
            reason=str(exc),
            source_item_count=len(evidence_pack.sources),
            artifact_source_ids=summarize_values(artifact.source_ids),
            finding_source_refs_summary=finding_source_refs_summary(artifact.findings),
        )
        raise
    emit_research_debug_event(
        debug_emitter,
        "artifact_record_build_succeeded",
        artifact_id=record.artifact_id,
        source_item_count=len(record.source_items),
        artifact_source_ids=summarize_values(record.source_ids),
        finding_source_refs_summary=finding_source_refs_summary(record.findings),
    )
    return record


def validate_research_artifact_record(record: ResearchArtifactRecord) -> None:
    validate_research_provenance(
        findings=record.findings,
        source_ids=record.source_ids,
        source_items=record.source_items,
        evidence_items=record.evidence_items,
    )


def persist_research_artifact(
    research_request: ResearchRequest,
    evidence_pack: EvidencePack,
    artifact: ResearchArtifact,
    store: ResearchArtifactStore,
    *,
    debug_emitter: ResearchDebugEmitter | None = None,
) -> ResearchArtifactRecord:
    record = build_research_artifact_record(
        research_request=research_request,
        evidence_pack=evidence_pack,
        artifact=artifact,
        debug_emitter=debug_emitter,
    )
    store.save(record, debug_emitter=debug_emitter)
    return record


def run_and_persist_document_research(
    research_request: ResearchRequest,
    infrastructure_services: InfrastructureServices,
    store: ResearchArtifactStore,
    adapter_id: str | None = None,
    debug_emitter=None,
) -> ResearchArtifactRecord:
    sources = collect_document_sources(research_request)
    evidence_pack = build_document_evidence_pack(research_request, sources)
    artifact = synthesize_research_with_runtime(
        research_request=research_request,
        evidence_pack=evidence_pack,
        infrastructure_services=infrastructure_services,
        adapter_id=adapter_id,
        debug_emitter=debug_emitter,
    )
    return persist_research_artifact(
        research_request=research_request,
        evidence_pack=evidence_pack,
        artifact=artifact,
        store=store,
        debug_emitter=debug_emitter,
    )


def run_and_persist_web_research(
    research_request: ResearchRequest,
    infrastructure_services: InfrastructureServices,
    store: ResearchArtifactStore,
    adapter_id: str | None = None,
    debug_emitter=None,
) -> ResearchArtifactRecord:
    sources = collect_web_sources(research_request)
    evidence_pack = build_web_evidence_pack(research_request, sources)
    artifact = synthesize_research_with_runtime(
        research_request=research_request,
        evidence_pack=evidence_pack,
        infrastructure_services=infrastructure_services,
        adapter_id=adapter_id,
        debug_emitter=debug_emitter,
    )
    return persist_research_artifact(
        research_request=research_request,
        evidence_pack=evidence_pack,
        artifact=artifact,
        store=store,
        debug_emitter=debug_emitter,
    )


def _artifact_id_for(
    *,
    research_request: ResearchRequest,
    evidence_pack: EvidencePack,
    artifact: ResearchArtifact,
    created_at: str,
    nonce: int,
) -> str:
    payload = {
        "project_id": research_request.project_id,
        "work_unit_id": research_request.work_unit_id,
        "run_id": research_request.run_id,
        "question": artifact.question,
        "source_mode": research_request.source_mode,
        "summary": artifact.summary,
        "source_ids": artifact.source_ids,
        "evidence_items": [item.text for item in evidence_pack.evidence_items],
        "created_at": created_at,
        "nonce": nonce,
    }
    digest = hashlib.sha1(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    return f"research-{digest}"


def _record_to_payload(record: ResearchArtifactRecord) -> dict[str, Any]:
    payload = asdict(record)
    payload["findings"] = [asdict(item) for item in record.findings]
    payload["source_items"] = [asdict(item) for item in record.source_items]
    payload["evidence_items"] = [asdict(item) for item in record.evidence_items]
    return payload


def _record_from_payload(payload: dict[str, Any]) -> ResearchArtifactRecord:
    try:
        findings = tuple(ResearchFinding(**item) for item in payload["findings"])
        source_items = tuple(SourceItem(**item) for item in payload["source_items"])
        evidence_items = tuple(EvidenceItem(**item) for item in payload["evidence_items"])
        record = ResearchArtifactRecord(
            artifact_id=payload["artifact_id"],
            project_id=payload.get("project_id"),
            work_unit_id=payload.get("work_unit_id"),
            run_id=payload.get("run_id"),
            question=payload["question"],
            source_mode=payload["source_mode"],
            summary=payload["summary"],
            findings=findings,
            inferences=tuple(payload["inferences"]),
            uncertainties=tuple(payload["uncertainties"]),
            recommendation=payload.get("recommendation"),
            source_ids=tuple(payload["source_ids"]),
            source_items=source_items,
            evidence_items=evidence_items,
            created_at=payload["created_at"],
            schema_version=payload.get("schema_version", "1.0"),
        )
        validate_research_artifact_record(record)
        return record
    except (KeyError, TypeError, ValueError, ResearchProvenanceValidationError) as exc:
        raise ValueError("malformed persisted research artifact record") from exc
