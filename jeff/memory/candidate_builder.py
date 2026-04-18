"""Memory candidate builder — creates candidate objects from lawful support inputs.

Only Memory may create canonical memory candidates.
Upstream modules (research, execution, evaluation, operator) may provide
structured support inputs.  They must not create candidate objects directly.
"""

from __future__ import annotations

from jeff.core.schemas import Scope

from .models import MemoryCandidate, MemorySupportRef, make_memory_candidate


def build_candidate(
    *,
    candidate_id: str,
    memory_type: str,
    scope: Scope,
    summary: str,
    remembered_points: tuple[str, ...],
    why_it_matters: str,
    support_refs: tuple[MemorySupportRef, ...],
    support_quality: str = "moderate",
    stability: str = "tentative",
) -> MemoryCandidate:
    """Build a memory candidate from lawful support inputs.

    This is the canonical entry point for candidate creation in v1.
    `make_memory_candidate` passes the internal origin token so the candidate
    guard in MemoryCandidate.__post_init__ is satisfied.
    """
    return make_memory_candidate(
        candidate_id=candidate_id,
        memory_type=memory_type,
        scope=scope,
        summary=summary,
        remembered_points=remembered_points,
        why_it_matters=why_it_matters,
        support_refs=support_refs,
        support_quality=support_quality,
        stability=stability,
    )


# Backward-compatible alias used by existing write_pipeline imports
create_memory_candidate = build_candidate
