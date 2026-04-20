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
    build_proposal_generation_repair_prompt_bundle,
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
    repair_attempted: bool = False
    initial_failure_stage: ProposalPipelineFailureStage | None = None
    initial_error: Exception | None = None
    initial_prompt_bundle: ProposalGenerationPromptBundle | None = None
    initial_raw_result: ProposalGenerationRawResult | None = None
    initial_parsed_result: ParsedProposalGenerationResult | None = None
    initial_validation_issues: tuple[ProposalValidationIssue, ...] = ()
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
        if not self.repair_attempted and any(
            value is not None for value in (self.initial_failure_stage, self.initial_error, self.initial_prompt_bundle, self.initial_raw_result, self.initial_parsed_result)
        ):
            raise ValueError("non-repaired proposal pipeline success must not preserve initial failure artifacts")


@dataclass(frozen=True, slots=True)
class ProposalPipelineFailure:
    request: ProposalGenerationRequest
    failure_stage: ProposalPipelineFailureStage
    error: Exception
    prompt_bundle: ProposalGenerationPromptBundle | None = None
    raw_result: ProposalGenerationRawResult | None = None
    parsed_result: ParsedProposalGenerationResult | None = None
    validation_issues: tuple[ProposalValidationIssue, ...] = ()
    repair_attempted: bool = False
    initial_failure_stage: ProposalPipelineFailureStage | None = None
    initial_error: Exception | None = None
    initial_prompt_bundle: ProposalGenerationPromptBundle | None = None
    initial_raw_result: ProposalGenerationRawResult | None = None
    initial_parsed_result: ParsedProposalGenerationResult | None = None
    initial_validation_issues: tuple[ProposalValidationIssue, ...] = ()
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
        if not self.repair_attempted and any(
            value is not None for value in (self.initial_failure_stage, self.initial_error, self.initial_prompt_bundle, self.initial_raw_result, self.initial_parsed_result)
        ):
            raise ValueError("non-repaired proposal pipeline failures must not preserve initial failure artifacts")


ProposalPipelineResult = ProposalPipelineSuccess | ProposalPipelineFailure


def run_proposal_generation_pipeline(
    request: ProposalGenerationRequest,
    *,
    infrastructure_services: InfrastructureServices,
    adapter_id: str | None = None,
) -> ProposalPipelineResult:
    prompt_bundle: ProposalGenerationPromptBundle
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

    first_attempt = _attempt_parse_and_validate(
        request=request,
        prompt_bundle=prompt_bundle,
        raw_result=raw_result,
    )
    if isinstance(first_attempt, ProposalPipelineSuccess):
        return first_attempt

    if first_attempt.failure_stage not in {"parse", "validation"}:
        return first_attempt

    repaired_attempt = run_proposal_repair_attempt(
        request,
        failure=first_attempt,
        infrastructure_services=infrastructure_services,
        adapter_id=adapter_id,
    )
    if isinstance(repaired_attempt, ProposalPipelineSuccess):
        return ProposalPipelineSuccess(
            request=request,
            prompt_bundle=repaired_attempt.prompt_bundle,
            raw_result=repaired_attempt.raw_result,
            parsed_result=repaired_attempt.parsed_result,
            proposal_result=repaired_attempt.proposal_result,
            repair_attempted=True,
            initial_failure_stage=first_attempt.failure_stage,
            initial_error=first_attempt.error,
            initial_prompt_bundle=first_attempt.prompt_bundle,
            initial_raw_result=first_attempt.raw_result,
            initial_parsed_result=first_attempt.parsed_result,
            initial_validation_issues=first_attempt.validation_issues,
        )
    return _finalize_repaired_failure_from_attempt(
        request=request,
        initial_failure=first_attempt,
        final_failure=repaired_attempt,
    )


def run_proposal_repair_attempt(
    request: ProposalGenerationRequest,
    *,
    failure: ProposalPipelineFailure,
    infrastructure_services: InfrastructureServices,
    adapter_id: str | None = None,
) -> ProposalPipelineResult:
    if failure.failure_stage not in {"parse", "validation"}:
        raise ValueError("proposal repair is only lawful for parse or validation failures")

    repair_context = _build_repair_context(failure)
    try:
        repair_prompt_bundle = build_proposal_generation_repair_prompt_bundle(
            request,
            failure_stage=repair_context.failure_stage,
            failure_reason=repair_context.failure_reason,
            validation_issues_text=repair_context.validation_issues_text,
            prior_output=repair_context.prior_output,
        )
    except (PromptFileNotFoundError, PromptFileMalformedError, PromptRenderError) as exc:
        return _finalize_repaired_failure(
            request=request,
            initial_failure=failure,
            failure_stage="prompt",
            error=exc,
        )

    try:
        repair_raw_result = invoke_proposal_generation_with_runtime(
            repair_prompt_bundle,
            infrastructure_services=infrastructure_services,
            adapter_id=adapter_id,
        )
    except ProposalGenerationRuntimeError as exc:
        return _finalize_repaired_failure(
            request=request,
            initial_failure=failure,
            failure_stage="runtime",
            error=exc,
            prompt_bundle=repair_prompt_bundle,
        )

    return _attempt_parse_and_validate(
        request=request,
        prompt_bundle=repair_prompt_bundle,
        raw_result=repair_raw_result,
    )


def _attempt_parse_and_validate(
    *,
    request: ProposalGenerationRequest,
    prompt_bundle: ProposalGenerationPromptBundle,
    raw_result: ProposalGenerationRawResult,
) -> ProposalPipelineResult:
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


@dataclass(frozen=True, slots=True)
class _RepairContext:
    failure_stage: ProposalPipelineFailureStage
    failure_reason: str
    validation_issues_text: str
    prior_output: str


def _build_repair_context(initial_failure: ProposalPipelineFailure) -> _RepairContext:
    prior_output = initial_failure.raw_result.raw_output_text if initial_failure.raw_result is not None else "no prior raw output preserved"
    validation_issues_text = "none"
    if initial_failure.validation_issues:
        validation_issues_text = "\n".join(
            f"issue_{index}={issue.code}|option_index={issue.option_index or 'n/a'}|message={issue.message}"
            for index, issue in enumerate(initial_failure.validation_issues, start=1)
        )
    return _RepairContext(
        failure_stage=initial_failure.failure_stage,
        failure_reason=str(initial_failure.error),
        validation_issues_text=validation_issues_text,
        prior_output=prior_output,
    )


def _finalize_repaired_failure_from_attempt(
    *,
    request: ProposalGenerationRequest,
    initial_failure: ProposalPipelineFailure,
    final_failure: ProposalPipelineFailure,
) -> ProposalPipelineFailure:
    return ProposalPipelineFailure(
        request=request,
        failure_stage=final_failure.failure_stage,
        error=final_failure.error,
        prompt_bundle=final_failure.prompt_bundle,
        raw_result=final_failure.raw_result,
        parsed_result=final_failure.parsed_result,
        validation_issues=final_failure.validation_issues,
        repair_attempted=True,
        initial_failure_stage=initial_failure.failure_stage,
        initial_error=initial_failure.error,
        initial_prompt_bundle=initial_failure.prompt_bundle,
        initial_raw_result=initial_failure.raw_result,
        initial_parsed_result=initial_failure.parsed_result,
        initial_validation_issues=initial_failure.validation_issues,
        status=final_failure.status,
    )


def _finalize_repaired_failure(
    *,
    request: ProposalGenerationRequest,
    initial_failure: ProposalPipelineFailure,
    failure_stage: ProposalPipelineFailureStage,
    error: Exception,
    prompt_bundle: ProposalGenerationPromptBundle | None = None,
    raw_result: ProposalGenerationRawResult | None = None,
    parsed_result: ParsedProposalGenerationResult | None = None,
    validation_issues: tuple[ProposalValidationIssue, ...] = (),
) -> ProposalPipelineFailure:
    return ProposalPipelineFailure(
        request=request,
        failure_stage=failure_stage,
        error=error,
        prompt_bundle=prompt_bundle,
        raw_result=raw_result,
        parsed_result=parsed_result,
        validation_issues=validation_issues,
        repair_attempted=True,
        initial_failure_stage=initial_failure.failure_stage,
        initial_error=initial_failure.error,
        initial_prompt_bundle=initial_failure.prompt_bundle,
        initial_raw_result=initial_failure.raw_result,
        initial_parsed_result=initial_failure.parsed_result,
        initial_validation_issues=initial_failure.validation_issues,
        status=f"{failure_stage}_failure",
    )
