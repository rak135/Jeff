"""Shared CLI command-layer models and public interface context records."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from jeff.cognitive.post_selection.selection_review_record import SelectionReviewRecord

from ..session import CliSession

if TYPE_CHECKING:
    from jeff.cognitive import ProposalGenerationBridgeResult, ResearchArtifactStore
    from jeff.cognitive.research.archive import ResearchArchiveStore
    from jeff.core.schemas import Scope
    from jeff.core.state.models import GlobalState
    from jeff.infrastructure import InfrastructureServices
    from jeff.knowledge import KnowledgeStore
    from jeff.memory import MemoryStoreProtocol
    from jeff.orchestrator import FlowRunResult
    from jeff.runtime_persistence import PersistedRuntimeStore


@dataclass(frozen=True, slots=True)
class InterfaceContext:
    state: GlobalState
    flow_runs: Mapping[str, FlowRunResult] = field(default_factory=dict)
    selection_reviews: Mapping[str, SelectionReviewRecord] = field(default_factory=dict)
    infrastructure_services: InfrastructureServices | None = None
    research_artifact_store: ResearchArtifactStore | None = None
    research_archive_store: ResearchArchiveStore | None = None
    knowledge_store: KnowledgeStore | None = None
    memory_store: MemoryStoreProtocol | None = None
    research_memory_handoff_enabled: bool = True
    runtime_store: PersistedRuntimeStore | None = None
    startup_summary: str | None = None


@dataclass(frozen=True, slots=True)
class ResearchCommandSpec:
    mode: str
    question: str
    inputs: tuple[str, ...]
    handoff_memory: bool = False


@dataclass(frozen=True, slots=True)
class CommandResult:
    context: InterfaceContext
    session: CliSession
    text: str
    json_payload: dict[str, object] | None = None
    debug_events: tuple[dict[str, object], ...] = ()