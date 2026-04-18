"""Scope enforcement — enforces v1 project-only scope law.

Hard rules:
- project_id is mandatory on every write
- global/system scope is hard-forbidden
- cross-project writes are forbidden (enforced at store level; signaled here)
- work_unit_id and run_id are optional locality refinements only
"""

from __future__ import annotations

from jeff.core.schemas import Scope

from .models import MemoryCandidate
from .types import assert_not_global_scope


def validate_scope(scope: Scope) -> None:
    """Raise ValueError if the scope violates v1 memory scope law."""
    project_id = str(scope.project_id)

    if not project_id.strip():
        raise ValueError("project_id is required on all memory write paths")

    # Hard-reject global/system sentinels
    assert_not_global_scope(project_id)

    # run_id without work_unit_id is structurally illegal (enforced by Scope itself)
    # but we add an explicit guard here for clarity
    if scope.run_id is not None and scope.work_unit_id is None:
        raise ValueError("run_id locality requires work_unit_id in memory scope")


def assert_candidate_scope(candidate: MemoryCandidate) -> None:
    """Raise if the candidate's scope violates v1 scope law."""
    validate_scope(candidate.scope)


def project_id_from_scope(scope: Scope) -> str:
    """Extract and validate the project_id from a scope."""
    validate_scope(scope)
    return str(scope.project_id)
