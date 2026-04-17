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
    "ProposalGenerationValidationError",
    "ProposalPipelineFailure",
    "ProposalPipelineFailureStage",
    "ProposalPipelineResult",
    "ProposalPipelineSuccess",
    "ProposalResult",
    "ProposalResultOption",
    "ProposalType",
    "ProposalValidationIssue",
    "build_proposal_generation_prompt_bundle",
    "invoke_proposal_generation_with_runtime",
    "parse_proposal_generation_result",
    "run_proposal_generation_pipeline",
    "validate_proposal_generation_result",
]
