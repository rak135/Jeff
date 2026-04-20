"""Public proposal contract surface."""

from .api import (
    ProposalPipelineFailure,
    ProposalPipelineFailureStage,
    ProposalPipelineResult,
    ProposalPipelineSuccess,
    run_proposal_repair_attempt,
    run_proposal_generation_pipeline,
)
from .contracts import ProposalResult, ProposalResultOption, ProposalType
from .generation import (
    ProposalGenerationPromptBundle,
    ProposalGenerationRawResult,
    ProposalGenerationRequest,
    build_proposal_generation_prompt_bundle,
    invoke_proposal_generation_with_runtime,
    ProposalGenerationRuntimeError,
)
from .proposal_generation_bridge import (
    ProposalGenerationBridgeError,
    ProposalGenerationBridgeIssue,
    ProposalGenerationBridgeRequest,
    ProposalGenerationBridgeResult,
    build_and_run_proposal_generation,
)
from .proposal_support_package_consumer import (
    ProposalInputPackage,
    ProposalSupportConsumerError,
    ProposalSupportConsumerIssue,
    ProposalSupportConsumerRequest,
    consume_proposal_support_package,
)
from .parsing import (
    ParsedProposalGenerationResult,
    ParsedProposalOption,
    ProposalGenerationParseError,
    parse_proposal_generation_result,
)
from .operator_records import (
    ProposalAttemptKind,
    ProposalOperatorRecord,
    ProposalPersistedAttempt,
    ProposalRecordStatus,
    ProposalValidationOutcome,
    build_operator_record_from_pipeline_result,
    proposal_attempt_from_pipeline_result,
)
from .validation import (
    ProposalGenerationValidationError,
    ProposalValidationIssue,
    validate_proposal_generation_result,
)

__all__ = [
    "ParsedProposalGenerationResult",
    "ParsedProposalOption",
    "ProposalAttemptKind",
    "ProposalGenerationPromptBundle",
    "ProposalGenerationParseError",
    "ProposalGenerationRawResult",
    "ProposalGenerationRequest",
    "ProposalGenerationRuntimeError",
    "ProposalGenerationBridgeError",
    "ProposalGenerationBridgeIssue",
    "ProposalGenerationBridgeRequest",
    "ProposalGenerationBridgeResult",
    "ProposalInputPackage",
    "ProposalOperatorRecord",
    "ProposalGenerationValidationError",
    "ProposalPipelineFailure",
    "ProposalPipelineFailureStage",
    "ProposalPipelineResult",
    "ProposalPipelineSuccess",
    "ProposalPersistedAttempt",
    "ProposalRecordStatus",
    "ProposalResult",
    "ProposalResultOption",
    "ProposalSupportConsumerError",
    "ProposalSupportConsumerIssue",
    "ProposalSupportConsumerRequest",
    "ProposalType",
    "ProposalValidationIssue",
    "ProposalValidationOutcome",
    "build_and_run_proposal_generation",
    "build_operator_record_from_pipeline_result",
    "build_proposal_generation_prompt_bundle",
    "consume_proposal_support_package",
    "invoke_proposal_generation_with_runtime",
    "parse_proposal_generation_result",
    "proposal_attempt_from_pipeline_result",
    "run_proposal_generation_pipeline",
    "run_proposal_repair_attempt",
    "validate_proposal_generation_result",
]
