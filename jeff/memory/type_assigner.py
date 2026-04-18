"""Type assignment — enforces exactly one primary memory type per candidate.

In v1 the type is carried by the candidate builder.  This module validates
that assignment and provides a guard preventing fuzzy hybrid types.
"""

from __future__ import annotations

from .models import MemoryCandidate
from .types import MEMORY_TYPES


def assert_single_primary_type(candidate: MemoryCandidate) -> str:
    """Return the candidate's primary type or raise if the type is invalid.

    This is a validation-only step in v1.  The caller is responsible for
    providing exactly one primary type via the candidate builder.
    """
    if candidate.memory_type not in MEMORY_TYPES:
        raise ValueError(
            f"candidate carries unsupported memory type '{candidate.memory_type}'; "
            f"valid types are: {sorted(MEMORY_TYPES)}"
        )
    return candidate.memory_type


def requires_review_by_type(candidate: MemoryCandidate) -> bool:
    """Return True if the memory type mandates defer(review_required) per v1 policy.

    Directional memory is project-governance-shaping by nature and always
    requires review unless rejected first for low value.  Project-wide
    operational memory with non-strong support also requires review.
    """
    if candidate.memory_type == "directional":
        return True

    if candidate.memory_type == "operational":
        # Project-wide operational with non-strong support is behavior-shaping enough to review
        is_project_wide = candidate.scope.work_unit_id is None
        not_strong = candidate.support_quality != "strong"
        if is_project_wide and not_strong:
            return True

    return False
