"""Bounded persistence for research artifacts as support records."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jeff.infrastructure import InfrastructureServices

from .contracts import EvidenceItem, EvidencePack, ResearchArtifact, ResearchFinding, ResearchRequest, SourceItem
from .documents import collect_document_sources, build_document_evidence_pack, run_document_research
from .web import collect_web_sources, build_web_evidence_pack, run_web_research


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

    def save(self, record: ResearchArtifactRecord) -> Path:
        path = self._path_for(record.artifact_id)
        payload = _record_to_payload(record)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def load(self, artifact_id: str) -> ResearchArtifactRecord:
        path = self._path_for(artifact_id)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"malformed persisted research artifact file: {artifact_id}") from exc
        return _record_from_payload(payload)

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
) -> ResearchArtifactRecord:
    created_at = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    nonce = time.time_ns()
    artifact_id = _artifact_id_for(
        research_request=research_request,
        evidence_pack=evidence_pack,
        artifact=artifact,
        created_at=created_at,
        nonce=nonce,
    )
    return ResearchArtifactRecord(
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


def persist_research_artifact(
    research_request: ResearchRequest,
    evidence_pack: EvidencePack,
    artifact: ResearchArtifact,
    store: ResearchArtifactStore,
) -> ResearchArtifactRecord:
    record = build_research_artifact_record(
        research_request=research_request,
        evidence_pack=evidence_pack,
        artifact=artifact,
    )
    store.save(record)
    return record


def run_and_persist_document_research(
    research_request: ResearchRequest,
    infrastructure_services: InfrastructureServices,
    store: ResearchArtifactStore,
    adapter_id: str | None = None,
) -> ResearchArtifactRecord:
    sources = collect_document_sources(research_request)
    evidence_pack = build_document_evidence_pack(research_request, sources)
    artifact = run_document_research(
        research_request=research_request,
        infrastructure_services=infrastructure_services,
        adapter_id=adapter_id,
    )
    return persist_research_artifact(
        research_request=research_request,
        evidence_pack=evidence_pack,
        artifact=artifact,
        store=store,
    )


def run_and_persist_web_research(
    research_request: ResearchRequest,
    infrastructure_services: InfrastructureServices,
    store: ResearchArtifactStore,
    adapter_id: str | None = None,
) -> ResearchArtifactRecord:
    sources = collect_web_sources(research_request)
    evidence_pack = build_web_evidence_pack(research_request, sources)
    artifact = run_web_research(
        research_request=research_request,
        infrastructure_services=infrastructure_services,
        adapter_id=adapter_id,
    )
    return persist_research_artifact(
        research_request=research_request,
        evidence_pack=evidence_pack,
        artifact=artifact,
        store=store,
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
        return ResearchArtifactRecord(
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
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("malformed persisted research artifact record") from exc
