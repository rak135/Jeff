"""Shared CLI command-layer models and public interface context records."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .session import CliSession

if TYPE_CHECKING:
    from jeff.cognitive import (
        ProposalGenerationBridgeResult,
        ResearchArtifactStore,
        SelectionResult,
    )
    from jeff.cognitive.post_selection.action_formation import FormedActionResult
    from jeff.cognitive.post_selection.action_resolution import ResolvedSelectionActionBasis
    from jeff.cognitive.post_selection.effective_proposal import MaterializedEffectiveProposal
    from jeff.cognitive.post_selection.governance_handoff import GovernedActionHandoffResult
    from jeff.cognitive.post_selection.override import OperatorSelectionOverride
    from jeff.cognitive.proposal import ProposalResult
    from jeff.cognitive.research.archive import ResearchArchiveStore
    from jeff.core.schemas import Scope
    from jeff.core.state.models import GlobalState
    from jeff.governance import Approval, CurrentTruthSnapshot, Policy
    from jeff.infrastructure import InfrastructureServices
    from jeff.knowledge import KnowledgeStore
    from jeff.memory import InMemoryMemoryStore
    from jeff.orchestrator import FlowRunResult
    from jeff.runtime_persistence import PersistedRuntimeStore


@dataclass(frozen=True, slots=True)
class SelectionReviewRecord:
    selection_result: SelectionResult | None = None
    operator_override: OperatorSelectionOverride | None = None
    resolved_basis: ResolvedSelectionActionBasis | None = None
    materialized_effective_proposal: MaterializedEffectiveProposal | None = None
    formed_action_result: FormedActionResult | None = None
    governance_handoff_result: GovernedActionHandoffResult | None = None
    proposal_result: ProposalResult | None = None
    action_scope: Scope | None = None
    basis_state_version: int | None = None
    governance_policy: Policy | None = None
    governance_approval: Approval | None = None
    governance_truth: CurrentTruthSnapshot | None = None


@dataclass(frozen=True, slots=True)
class InterfaceContext:
    state: GlobalState
    flow_runs: Mapping[str, FlowRunResult] = field(default_factory=dict)
    selection_reviews: Mapping[str, SelectionReviewRecord] = field(default_factory=dict)
    infrastructure_services: InfrastructureServices | None = None
    research_artifact_store: ResearchArtifactStore | None = None
    research_archive_store: ResearchArchiveStore | None = None
    knowledge_store: KnowledgeStore | None = None
    memory_store: InMemoryMemoryStore | None = None
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