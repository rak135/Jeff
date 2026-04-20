"""Public post-selection downstream bridge surface."""

from .action_formation import ActionFormationError, ActionFormationIssue, ActionFormationRequest, FormedActionResult, form_action_from_materialized_proposal
from .action_resolution import (
    ResolvedSelectionActionBasis,
    SelectionActionResolutionError,
    SelectionActionResolutionIssue,
    SelectionActionResolutionRequest,
    SelectionActionResolutionSource,
    resolve_selection_action_basis,
)
from .effective_proposal import (
    MaterializedEffectiveProposal,
    SelectionEffectiveProposalMaterializationError,
    SelectionEffectiveProposalMaterializationIssue,
    SelectionEffectiveProposalRequest,
    materialize_effective_proposal,
)
from .governance_handoff import (
    ActionGovernanceHandoffError,
    ActionGovernanceHandoffIssue,
    ActionGovernanceHandoffRequest,
    GovernedActionHandoffResult,
    handoff_action_to_governance,
)
from .next_stage_resolution import (
    NextStageResolutionError,
    NextStageResolutionIssue,
    NextStageResolutionRequest,
    NextStageResolutionResult,
    NextStageTarget,
    resolve_next_stage,
)
from .override import (
    OperatorSelectionOverride,
    OperatorSelectionOverrideRequest,
    OperatorSelectionOverrideValidationError,
    OperatorSelectionOverrideValidationIssue,
    build_operator_selection_override,
    validate_operator_selection_override,
)
from .plan_action_bridge import (
    PlanActionBridgeError,
    PlanActionBridgeIssue,
    PlanActionBridgeRequest,
    PlannedActionBridgeResult,
    bridge_plan_to_action,
)
from .selection_review_record import SelectionReviewRecord
from .research_output_sufficiency_bridge import (
    ResearchOutputSufficiencyError,
    ResearchOutputSufficiencyIssue,
    ResearchOutputSufficiencyRequest,
    ResearchOutputSufficiencyResult,
    evaluate_research_output_sufficiency,
)
from .research_to_decision_support_bridge import (
    ResearchDecisionSupportError,
    ResearchDecisionSupportHandoff,
    ResearchDecisionSupportIssue,
    ResearchDecisionSupportRequest,
    build_research_decision_support_handoff,
)
from .research_to_proposal_consumer import (
    ProposalSupportPackage,
    ResearchProposalConsumerError,
    ResearchProposalConsumerIssue,
    ResearchProposalConsumerRequest,
    consume_research_for_proposal_support,
)

__all__ = [
    "ActionFormationError",
    "ActionFormationIssue",
    "ActionFormationRequest",
    "ActionGovernanceHandoffError",
    "ActionGovernanceHandoffIssue",
    "ActionGovernanceHandoffRequest",
    "FormedActionResult",
    "GovernedActionHandoffResult",
    "MaterializedEffectiveProposal",
    "NextStageResolutionError",
    "NextStageResolutionIssue",
    "NextStageResolutionRequest",
    "NextStageResolutionResult",
    "NextStageTarget",
    "OperatorSelectionOverride",
    "OperatorSelectionOverrideRequest",
    "OperatorSelectionOverrideValidationError",
    "OperatorSelectionOverrideValidationIssue",
    "PlanActionBridgeError",
    "PlanActionBridgeIssue",
    "PlanActionBridgeRequest",
    "PlannedActionBridgeResult",
    "ProposalSupportPackage",
    "ResearchDecisionSupportError",
    "ResearchDecisionSupportHandoff",
    "ResearchDecisionSupportIssue",
    "ResearchDecisionSupportRequest",
    "ResearchProposalConsumerError",
    "ResearchProposalConsumerIssue",
    "ResearchProposalConsumerRequest",
    "ResearchOutputSufficiencyError",
    "ResearchOutputSufficiencyIssue",
    "ResearchOutputSufficiencyRequest",
    "ResearchOutputSufficiencyResult",
    "ResolvedSelectionActionBasis",
    "SelectionReviewRecord",
    "SelectionActionResolutionError",
    "SelectionActionResolutionIssue",
    "SelectionActionResolutionRequest",
    "SelectionActionResolutionSource",
    "SelectionEffectiveProposalMaterializationError",
    "SelectionEffectiveProposalMaterializationIssue",
    "SelectionEffectiveProposalRequest",
    "build_research_decision_support_handoff",
    "build_operator_selection_override",
    "bridge_plan_to_action",
    "consume_research_for_proposal_support",
    "evaluate_research_output_sufficiency",
    "form_action_from_materialized_proposal",
    "handoff_action_to_governance",
    "materialize_effective_proposal",
    "resolve_next_stage",
    "resolve_selection_action_basis",
    "validate_operator_selection_override",
]
