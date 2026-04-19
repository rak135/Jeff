"""Public proposal contract surface."""

from .api import (
    ProposalPipelineFailure,
    ProposalPipelineFailureStage,
    ProposalPipelineResult,
    ProposalPipelineSuccess,
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
from .validation import (
    ProposalGenerationValidationError,
    ProposalValidationIssue,
    validate_proposal_generation_result,
)

__all__ = [
    "ParsedProposalGenerationResult",
    "ParsedProposalOption",
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
    "ProposalGenerationValidationError",
    "ProposalPipelineFailure",
    "ProposalPipelineFailureStage",
    "ProposalPipelineResult",
    "ProposalPipelineSuccess",
    "ProposalResult",
    "ProposalResultOption",
    "ProposalSupportConsumerError",
    "ProposalSupportConsumerIssue",
    "ProposalSupportConsumerRequest",
    "ProposalType",
    "ProposalValidationIssue",
    "build_and_run_proposal_generation",
    "build_proposal_generation_prompt_bundle",
    "consume_proposal_support_package",
    "invoke_proposal_generation_with_runtime",
    "parse_proposal_generation_result",
    "run_proposal_generation_pipeline",
    "validate_proposal_generation_result",
]
