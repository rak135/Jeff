"""Selective research-to-memory handoff using the current memory pipeline."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from jeff.core.schemas import Scope
from jeff.memory import MemoryStoreProtocol, MemorySupportRef, MemoryWriteDecision, create_memory_candidate, write_memory_candidate

from .contracts import ResearchArtifact, ResearchRequest
from .persistence import ResearchArtifactRecord


@dataclass(frozen=True, slots=True)
class ResearchMemoryHandoffInput:
    project_id: str | None
    work_unit_id: str | None
    run_id: str | None
    source_mode: str
    artifact_id: str | None
    summary: str
    findings: tuple[str, ...]
    inferences: tuple[str, ...]
    uncertainties: tuple[str, ...]
    recommendation: str | None
    source_ids: tuple[str, ...]
    why_it_matters: str


def build_research_memory_handoff_input(
    research_request: ResearchRequest,
    artifact: ResearchArtifact,
    artifact_record: ResearchArtifactRecord | None = None,
) -> ResearchMemoryHandoffInput:
    findings = tuple(finding.text for finding in artifact.findings[:3])
    inferences = tuple(artifact.inferences[:2])
    uncertainties = tuple(artifact.uncertainties[:2])
    recommendation = artifact.recommendation
    artifact_id = artifact_record.artifact_id if artifact_record is not None else None

    why_it_matters = _why_it_matters(
        source_mode=artifact_record.source_mode if artifact_record is not None else research_request.source_mode,
        recommendation=recommendation,
        uncertainties=uncertainties,
        findings=findings,
    )

    return ResearchMemoryHandoffInput(
        project_id=research_request.project_id,
        work_unit_id=research_request.work_unit_id,
        run_id=research_request.run_id,
        source_mode=artifact_record.source_mode if artifact_record is not None else research_request.source_mode,
        artifact_id=artifact_id,
        summary=artifact.summary,
        findings=findings,
        inferences=inferences,
        uncertainties=uncertainties,
        recommendation=recommendation,
        source_ids=artifact.source_ids,
        why_it_matters=why_it_matters,
    )


def build_research_memory_handoff_input_from_record(
    artifact_record: ResearchArtifactRecord,
) -> ResearchMemoryHandoffInput:
    findings = tuple(finding.text for finding in artifact_record.findings[:3])
    inferences = tuple(artifact_record.inferences[:2])
    uncertainties = tuple(artifact_record.uncertainties[:2])
    return ResearchMemoryHandoffInput(
        project_id=artifact_record.project_id,
        work_unit_id=artifact_record.work_unit_id,
        run_id=artifact_record.run_id,
        source_mode=artifact_record.source_mode,
        artifact_id=artifact_record.artifact_id,
        summary=artifact_record.summary,
        findings=findings,
        inferences=inferences,
        uncertainties=uncertainties,
        recommendation=artifact_record.recommendation,
        source_ids=artifact_record.source_ids,
        why_it_matters=_why_it_matters(
            source_mode=artifact_record.source_mode,
            recommendation=artifact_record.recommendation,
            uncertainties=uncertainties,
            findings=findings,
        ),
    )


def should_handoff_research_to_memory(
    artifact: ResearchArtifact,
    artifact_record: ResearchArtifactRecord | None = None,
) -> bool:
    text_fragments = [artifact.summary.lower(), *[item.lower() for item in artifact.inferences], *[item.lower() for item in artifact.uncertainties]]
    if artifact.recommendation is not None:
        return True
    if len(artifact.findings) >= 2:
        return True
    if artifact.uncertainties and any(
        marker in " ".join(text_fragments)
        for marker in ("caution", "risk", "warning", "uncertain", "contradiction", "conflict")
    ):
        return True
    if artifact_record is not None and len(artifact_record.source_ids) >= 2 and artifact.findings:
        return True
    if not artifact.findings:
        return False
    if artifact.summary.lower().startswith("no strong evidence found"):
        return False
    if len(artifact.findings) == 1 and artifact.recommendation is None and not artifact.uncertainties:
        return False
    return True


def handoff_research_to_memory(
    research_request: ResearchRequest,
    artifact: ResearchArtifact,
    memory_store: MemoryStoreProtocol,
    artifact_record: ResearchArtifactRecord | None = None,
) -> MemoryWriteDecision | None:
    if not should_handoff_research_to_memory(artifact=artifact, artifact_record=artifact_record):
        return None

    handoff_input = build_research_memory_handoff_input(
        research_request=research_request,
        artifact=artifact,
        artifact_record=artifact_record,
    )
    if handoff_input.project_id is None:
        return None

    candidate = create_memory_candidate(
        candidate_id=_candidate_id_for(handoff_input),
        memory_type="semantic",
        scope=Scope(
            project_id=handoff_input.project_id,
            work_unit_id=handoff_input.work_unit_id,
            run_id=handoff_input.run_id,
        ),
        summary=handoff_input.summary,
        remembered_points=_remembered_points(handoff_input),
        why_it_matters=handoff_input.why_it_matters,
        support_refs=(
            MemorySupportRef(
                ref_kind="research",
                ref_id=handoff_input.artifact_id or _candidate_id_for(handoff_input),
                summary=_support_summary(handoff_input),
            ),
        ),
        support_quality=_support_quality(handoff_input),
        stability=_stability(handoff_input),
    )
    return write_memory_candidate(candidate=candidate, store=memory_store)


def handoff_persisted_research_record_to_memory(
    artifact_record: ResearchArtifactRecord,
    memory_store: MemoryStoreProtocol,
) -> MemoryWriteDecision | None:
    artifact = ResearchArtifact(
        question=artifact_record.question,
        summary=artifact_record.summary,
        findings=artifact_record.findings,
        inferences=artifact_record.inferences,
        uncertainties=artifact_record.uncertainties,
        recommendation=artifact_record.recommendation,
        source_ids=artifact_record.source_ids,
    )
    research_request = ResearchRequest(
        question=artifact_record.question,
        project_id=artifact_record.project_id,
        work_unit_id=artifact_record.work_unit_id,
        run_id=artifact_record.run_id,
        source_mode=artifact_record.source_mode,
    )
    return handoff_research_to_memory(
        research_request=research_request,
        artifact=artifact,
        memory_store=memory_store,
        artifact_record=artifact_record,
    )


def _candidate_id_for(handoff_input: ResearchMemoryHandoffInput) -> str:
    payload = "|".join(
        (
            handoff_input.project_id or "none",
            handoff_input.work_unit_id or "none",
            handoff_input.run_id or "none",
            handoff_input.artifact_id or "none",
            handoff_input.summary,
            *handoff_input.findings,
            *handoff_input.inferences,
            *handoff_input.uncertainties,
            handoff_input.recommendation or "none",
        )
    )
    return f"research-memory-{hashlib.sha1(payload.encode('utf-8')).hexdigest()[:12]}"


def _remembered_points(handoff_input: ResearchMemoryHandoffInput) -> tuple[str, ...]:
    points = list(handoff_input.findings[:3])
    if handoff_input.recommendation is not None:
        points.append(f"Recommendation: {handoff_input.recommendation}")
    elif handoff_input.inferences:
        points.append(f"Inference: {handoff_input.inferences[0]}")
    if handoff_input.uncertainties:
        points.append(f"Caution: {handoff_input.uncertainties[0]}")
    return tuple(points[:5])


def _why_it_matters(
    *,
    source_mode: str,
    recommendation: str | None,
    uncertainties: tuple[str, ...],
    findings: tuple[str, ...],
) -> str:
    if recommendation is not None:
        return f"Research from {source_mode} produced a reusable directional recommendation."
    if uncertainties:
        return f"Research from {source_mode} exposed a caution worth preserving for later work."
    if findings:
        return f"Research from {source_mode} produced source-backed findings likely to matter later."
    return f"Research from {source_mode} may matter later."


def _support_summary(handoff_input: ResearchMemoryHandoffInput) -> str:
    source_count = len(handoff_input.source_ids)
    return f"Research artifact from {handoff_input.source_mode} with {source_count} linked sources"


def _support_quality(handoff_input: ResearchMemoryHandoffInput) -> str:
    if handoff_input.recommendation is not None and len(handoff_input.source_ids) >= 1:
        return "strong"
    if handoff_input.uncertainties and handoff_input.recommendation is None:
        return "weak"
    return "moderate"


def _stability(handoff_input: ResearchMemoryHandoffInput) -> str:
    if handoff_input.recommendation is not None:
        return "stable"
    if handoff_input.uncertainties:
        return "volatile"
    return "tentative"
