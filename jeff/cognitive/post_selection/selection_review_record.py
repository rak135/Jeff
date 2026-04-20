"""Shared post-selection review record type."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jeff.cognitive import SelectionResult
    from jeff.cognitive.post_selection.action_formation import FormedActionResult
    from jeff.cognitive.post_selection.action_resolution import ResolvedSelectionActionBasis
    from jeff.cognitive.post_selection.effective_proposal import MaterializedEffectiveProposal
    from jeff.cognitive.post_selection.governance_handoff import GovernedActionHandoffResult
    from jeff.cognitive.post_selection.override import OperatorSelectionOverride
    from jeff.cognitive.proposal import ProposalResult
    from jeff.core.schemas import Scope
    from jeff.governance import Approval, CurrentTruthSnapshot, Policy


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