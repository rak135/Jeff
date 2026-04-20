"""Research runtime/store guards and helper IDs."""

from __future__ import annotations

import hashlib
import re

from jeff.infrastructure import InfrastructureServices
from jeff.memory import MemoryStoreProtocol

from ..models import InterfaceContext

GENERAL_RESEARCH_PROJECT_ID = "general_research"


def require_research_infrastructure(context: InterfaceContext) -> InfrastructureServices:
    if context.infrastructure_services is None:
        raise ValueError(
            "research runtime is not configured for this CLI context. "
            "Add jeff.runtime.toml in the startup directory to enable research CLI."
        )
    return context.infrastructure_services


def require_research_store(context: InterfaceContext):
    if context.research_artifact_store is None:
        raise ValueError("research artifact persistence store is not configured for this CLI context")
    return context.research_artifact_store


def require_memory_store(context: InterfaceContext) -> MemoryStoreProtocol:
    if not context.research_memory_handoff_enabled:
        raise ValueError("research memory handoff is disabled by the current runtime config")
    if context.memory_store is None:
        raise ValueError("memory store is not configured for research handoff in this CLI context")
    return context.memory_store


def general_research_work_unit_id(*, mode: str, question: str) -> str:
    slug_parts = re.findall(r"[a-z0-9]+", question.lower())
    slug = "-".join(slug_parts[:8]) or "question"
    slug = slug[:48].strip("-")
    digest = hashlib.sha1(f"{mode}|{question}".encode("utf-8")).hexdigest()[:8]
    return f"research-{mode}-{slug}-{digest}"