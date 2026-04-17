"""Thin Proposal-local end-to-end composition entry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TYPE_CHECKING

from .contracts import ProposalResult
from .generation import (
    ProposalGenerationPromptBundle,
    ProposalGenerationRawResult,
    ProposalGenerationRequest,
    ProposalGenerationRuntimeError,
    build_proposal_generation_prompt_bundle,
    invoke_proposal_generation_with_runtime,
)
from .parsing import (
    ParsedProposalGenerationResult,
    ProposalGenerationParseError,
    parse_proposal_generation_result,
)
from .prompt_files import PromptFileMalformedError, PromptFileNotFoundError, PromptRenderError
from .validation import (
    ProposalGenerationValidationError,
    ProposalValidationIssue,
    validate_proposal_generation_result,
)

if TYPE_CHECKING:
    from jeff.infrastructure import InfrastructureServices

ProposalPipelineFailureStage = Literal["prompt", "runtime", "parse", "validation"]


@dataclass(frozen=True, slots=True)
class ProposalPipelineSuccess:
    request: ProposalGenerationRequest
    prompt_bundle: ProposalGenerationPromptBundle
    raw_result: ProposalGenerationRawResult
    parsed_result: ParsedProposalGenerationResult
    proposal_result: ProposalResult
    status: Literal["validated_success"] = "validated_success"

    def __post_init__(self) -> None:
        if self.request.scope != self.prompt_bundle.scope:
            raise ValueError("proposal pipeline success must preserve request scope in prompt_bundle")
        if self.raw_result.prompt_bundle != self.prompt_bundle:
            raise ValueError("proposal pipeline success must preserve prompt_bundle linkage")
        if self.parsed_result.raw_result != self.raw_result:
            raise ValueError("proposal pipeline success must preserve raw_result linkage")
        if self.proposal_result.request_id != self.raw_result.request_id:
            raise ValueError("proposal pipeline success must preserve request_id linkage")
        if self.proposal_result.scope != self.request.scope:
            raise ValueError("proposal pipeline success must preserve scope linkage")


@dataclass(frozen=True, slots=True)
class ProposalPipelineFailure:
    request: ProposalGenerationRequest
    failure_stage: ProposalPipelineFailureStage
    error: Exception
    prompt_bundle: ProposalGenerationPromptBundle | None = None
    raw_result: ProposalGenerationRawResult | None = None
    parsed_result: ParsedProposalGenerationResult | None = None
    validation_issues: tuple[ProposalValidationIssue, ...] = ()
    status: Literal["prompt_failure", "runtime_failure", "parse_failure", "validation_failure"] = "prompt_failure"

    def __post_init__(self) -> None:
        expected_status = f"{self.failure_stage}_failure"
        if self.status != expected_status:
            raise ValueError("proposal pipeline failure status must match failure_stage")
        if self.failure_stage == "prompt":
            if self.prompt_bundle is not None or self.raw_result is not None or self.parsed_result is not None:
                raise ValueError("prompt-stage failures must not include downstream artifacts")
        if self.failure_stage == "runtime":
            if self.prompt_bundle is None:
                raise ValueError("runtime-stage failures must preserve prompt_bundle")
            if self.raw_result is not None or self.parsed_result is not None:
                raise ValueError("runtime-stage failures must not include parse artifacts")
        if self.failure_stage == "parse":
            if self.prompt_bundle is None or self.raw_result is None:
                raise ValueError("parse-stage failures must preserve prompt_bundle and raw_result")
            if self.parsed_result is not None:
                raise ValueError("parse-stage failures must not include parsed_result")
        if self.failure_stage == "validation":
            if self.prompt_bundle is None or self.raw_result is None or self.parsed_result is None:
                raise ValueError("validation-stage failures must preserve prompt_bundle, raw_result, and parsed_result")
            if not self.validation_issues:
                raise ValueError("validation-stage failures must include validation_issues")
        elif self.validation_issues:
            raise ValueError("only validation-stage failures may include validation_issues")


ProposalPipelineResult = ProposalPipelineSuccess | ProposalPipelineFailure


def run_proposal_generation_pipeline(
    request: ProposalGenerationRequest,
    *,
    infrastructure_services: InfrastructureServices,
    adapter_id: str | None = None,
) -> ProposalPipelineResult:
    try:
        prompt_bundle = build_proposal_generation_prompt_bundle(request)
    except (PromptFileNotFoundError, PromptFileMalformedError, PromptRenderError) as exc:
        return ProposalPipelineFailure(
            request=request,
            failure_stage="prompt",
            error=exc,
            status="prompt_failure",
        )

    try:
        raw_result = invoke_proposal_generation_with_runtime(
            prompt_bundle,
            infrastructure_services=infrastructure_services,
            adapter_id=adapter_id,
        )
    except ProposalGenerationRuntimeError as exc:
        return ProposalPipelineFailure(
            request=request,
            failure_stage="runtime",
            error=exc,
            prompt_bundle=prompt_bundle,
            status="runtime_failure",
        )

    try:
        parsed_result = parse_proposal_generation_result(raw_result)
    except ProposalGenerationParseError as exc:
        return ProposalPipelineFailure(
            request=request,
            failure_stage="parse",
            error=exc,
            prompt_bundle=prompt_bundle,
            raw_result=raw_result,
            status="parse_failure",
        )

    try:
        proposal_result = validate_proposal_generation_result(parsed_result)
    except ProposalGenerationValidationError as exc:
        return ProposalPipelineFailure(
            request=request,
            failure_stage="validation",
            error=exc,
            prompt_bundle=prompt_bundle,
            raw_result=raw_result,
            parsed_result=parsed_result,
            validation_issues=exc.issues,
            status="validation_failure",
        )

    return ProposalPipelineSuccess(
        request=request,
        prompt_bundle=prompt_bundle,
        raw_result=raw_result,
        parsed_result=parsed_result,
        proposal_result=proposal_result,
    )
