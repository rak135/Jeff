"""Memory-owned run-summary handoff pipeline."""

from __future__ import annotations

import hashlib

from jeff.cognitive.run_memory_handoff import RunMemoryHandoffInput
from jeff.core.schemas import Scope

from .candidate_builder import build_candidate
from .models import MemorySupportRef, MemoryWriteDecision
from .write_pipeline import process_candidate


def handoff_run_summary_to_memory(
    handoff_input: RunMemoryHandoffInput,
    *,
    store,
    embedder=None,
) -> MemoryWriteDecision:
    candidate = build_candidate(
        candidate_id=_candidate_id_for(handoff_input),
        memory_type="episodic",
        scope=Scope(
            project_id=handoff_input.project_id,
            work_unit_id=handoff_input.work_unit_id,
            run_id=handoff_input.run_id,
        ),
        summary=handoff_input.summary,
        remembered_points=handoff_input.remembered_points,
        why_it_matters=handoff_input.why_it_matters,
        support_refs=(
            MemorySupportRef(
                ref_kind="evaluation",
                ref_id=f"run:{handoff_input.run_id}:flow:{handoff_input.flow_id}",
                summary=handoff_input.support_summary,
            ),
        ),
        support_quality=handoff_input.support_quality,
        stability=handoff_input.stability,
    )
    return process_candidate(candidate=candidate, store=store, embedder=embedder).write_decision


def _candidate_id_for(handoff_input: RunMemoryHandoffInput) -> str:
    payload = "|".join(
        (
            handoff_input.project_id,
            handoff_input.work_unit_id or "none",
            handoff_input.run_id,
            handoff_input.flow_id,
            handoff_input.terminal_posture,
            handoff_input.summary,
            *handoff_input.remembered_points,
        )
    )
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
    return f"run-memory-{digest}"