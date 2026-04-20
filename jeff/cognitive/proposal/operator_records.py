"""Durable operator-facing proposal attempt records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from jeff.cognitive.context import ContextPackage
from jeff.core.schemas import Scope

from .api import ProposalPipelineFailure, ProposalPipelineFailureStage, ProposalPipelineResult, ProposalPipelineSuccess
from .contracts import ProposalResult
from .generation import ProposalGenerationPromptBundle, ProposalGenerationRawResult, ProposalGenerationRequest
from .parsing import ParsedProposalGenerationResult
from .validation import ProposalValidationIssue

ProposalAttemptKind = Literal["initial", "repair"]
ProposalRecordStatus = Literal["success", "failed"]
ProposalValidationOutcome = Literal["passed", "failed", "not_reached"]


@dataclass(frozen=True, slots=True)
class ProposalPersistedAttempt:
    attempt_kind: ProposalAttemptKind
    prompt_bundle: ProposalGenerationPromptBundle | None = None
    raw_result: ProposalGenerationRawResult | None = None
    parsed_result: ParsedProposalGenerationResult | None = None
    parse_error: str | None = None
    validation_issues: tuple[ProposalValidationIssue, ...] = ()
    proposal_result: ProposalResult | None = None
    failure_stage: ProposalPipelineFailureStage | None = None
    error_message: str | None = None
    raw_artifact_ref: str | None = None
    parsed_artifact_ref: str | None = None
    validation_artifact_ref: str | None = None

    def __post_init__(self) -> None:
        if self.raw_result is not None and self.prompt_bundle is None:
            raise ValueError("persisted proposal attempts with raw output must preserve the prompt bundle")
        if self.parsed_result is not None and self.raw_result is None:
            raise ValueError("persisted proposal attempts with parsed output must preserve the raw result")
        if self.proposal_result is not None and self.parsed_result is None:
            raise ValueError("persisted proposal attempts with a proposal result must preserve the parsed result")
        if self.failure_stage == "parse" and self.raw_result is None:
            raise ValueError("parse failures must preserve the raw result")
        if self.failure_stage == "validation" and self.parsed_result is None:
            raise ValueError("validation failures must preserve the parsed result")
        if self.validation_issues and self.failure_stage != "validation":
            raise ValueError("validation issues are only lawful for validation failures")
        if self.parse_error is not None and self.failure_stage != "parse":
            raise ValueError("parse_error is only lawful for parse failures")

    @property
    def succeeded(self) -> bool:
        return self.proposal_result is not None and self.failure_stage is None


@dataclass(frozen=True, slots=True)
class ProposalOperatorRecord:
    proposal_id: str
    created_at: str
    objective: str
    scope: Scope
    context_package: ContextPackage
    visible_constraints: tuple[str, ...] = ()
    source_proposal_id: str | None = None
    initial_attempt: ProposalPersistedAttempt | None = None
    repair_attempt: ProposalPersistedAttempt | None = None
    status: ProposalRecordStatus = "failed"
    final_validation_outcome: ProposalValidationOutcome = "not_reached"
    final_failure_stage: ProposalPipelineFailureStage | None = None
    final_error_message: str | None = None
    final_proposal_result: ProposalResult | None = None
    record_ref: str | None = None

    def __post_init__(self) -> None:
        if self.initial_attempt is None:
            raise ValueError("proposal operator records must preserve the initial attempt")
        if self.context_package.scope != self.scope:
            raise ValueError("proposal operator record scope must match the preserved context package scope")
        if self.status == "success":
            if self.final_proposal_result is None:
                raise ValueError("successful proposal operator records must preserve the final proposal result")
            if self.final_validation_outcome != "passed":
                raise ValueError("successful proposal operator records must report passed validation")
            if self.final_failure_stage is not None or self.final_error_message is not None:
                raise ValueError("successful proposal operator records must not preserve terminal failure details")
        else:
            if self.final_proposal_result is not None:
                raise ValueError("failed proposal operator records must not preserve a final proposal result")
            if self.final_failure_stage is None or self.final_error_message is None:
                raise ValueError("failed proposal operator records must preserve terminal failure details")

    @property
    def repair_attempted(self) -> bool:
        return self.repair_attempt is not None

    @property
    def final_attempt(self) -> ProposalPersistedAttempt:
        return self.repair_attempt or self.initial_attempt


def proposal_attempt_from_pipeline_result(
    *,
    attempt_kind: ProposalAttemptKind,
    pipeline_result: ProposalPipelineResult,
) -> ProposalPersistedAttempt:
    if isinstance(pipeline_result, ProposalPipelineSuccess):
        return ProposalPersistedAttempt(
            attempt_kind=attempt_kind,
            prompt_bundle=pipeline_result.prompt_bundle,
            raw_result=pipeline_result.raw_result,
            parsed_result=pipeline_result.parsed_result,
            proposal_result=pipeline_result.proposal_result,
        )
    return ProposalPersistedAttempt(
        attempt_kind=attempt_kind,
        prompt_bundle=pipeline_result.prompt_bundle,
        raw_result=pipeline_result.raw_result,
        parsed_result=pipeline_result.parsed_result,
        parse_error=str(pipeline_result.error) if pipeline_result.failure_stage == "parse" else None,
        validation_issues=pipeline_result.validation_issues,
        failure_stage=pipeline_result.failure_stage,
        error_message=str(pipeline_result.error),
    )


def build_operator_record_from_pipeline_result(
    *,
    proposal_id: str,
    created_at: str,
    request: ProposalGenerationRequest,
    pipeline_result: ProposalPipelineResult,
    source_proposal_id: str | None = None,
) -> ProposalOperatorRecord:
    if isinstance(pipeline_result, ProposalPipelineSuccess):
        initial_attempt = proposal_attempt_from_pipeline_result(
            attempt_kind="initial",
            pipeline_result=(
                pipeline_result
                if not pipeline_result.repair_attempted
                else ProposalPipelineFailure(
                    request=request,
                    failure_stage=pipeline_result.initial_failure_stage or "parse",
                    error=pipeline_result.initial_error or ValueError("missing initial proposal failure"),
                    prompt_bundle=pipeline_result.initial_prompt_bundle,
                    raw_result=pipeline_result.initial_raw_result,
                    parsed_result=pipeline_result.initial_parsed_result,
                    validation_issues=pipeline_result.initial_validation_issues,
                    repair_attempted=False,
                    status=f"{pipeline_result.initial_failure_stage or 'parse'}_failure",
                )
            ),
        )
        repair_attempt = None
        if pipeline_result.repair_attempted:
            repair_attempt = proposal_attempt_from_pipeline_result(
                attempt_kind="repair",
                pipeline_result=ProposalPipelineSuccess(
                    request=request,
                    prompt_bundle=pipeline_result.prompt_bundle,
                    raw_result=pipeline_result.raw_result,
                    parsed_result=pipeline_result.parsed_result,
                    proposal_result=pipeline_result.proposal_result,
                ),
            )
        return ProposalOperatorRecord(
            proposal_id=proposal_id,
            source_proposal_id=source_proposal_id,
            created_at=created_at,
            objective=request.objective,
            scope=request.scope,
            context_package=request.context_package,
            visible_constraints=request.visible_constraints,
            initial_attempt=initial_attempt,
            repair_attempt=repair_attempt,
            status="success",
            final_validation_outcome="passed",
            final_proposal_result=pipeline_result.proposal_result,
        )

    initial_attempt = proposal_attempt_from_pipeline_result(
        attempt_kind="initial",
        pipeline_result=(
            pipeline_result
            if not pipeline_result.repair_attempted
            else ProposalPipelineFailure(
                request=request,
                failure_stage=pipeline_result.initial_failure_stage or "parse",
                error=pipeline_result.initial_error or ValueError("missing initial proposal failure"),
                prompt_bundle=pipeline_result.initial_prompt_bundle,
                raw_result=pipeline_result.initial_raw_result,
                parsed_result=pipeline_result.initial_parsed_result,
                validation_issues=pipeline_result.initial_validation_issues,
                repair_attempted=False,
                status=f"{pipeline_result.initial_failure_stage or 'parse'}_failure",
            )
        ),
    )
    repair_attempt = None
    if pipeline_result.repair_attempted:
        repair_attempt = proposal_attempt_from_pipeline_result(
            attempt_kind="repair",
            pipeline_result=ProposalPipelineFailure(
                request=request,
                failure_stage=pipeline_result.failure_stage,
                error=pipeline_result.error,
                prompt_bundle=pipeline_result.prompt_bundle,
                raw_result=pipeline_result.raw_result,
                parsed_result=pipeline_result.parsed_result,
                validation_issues=pipeline_result.validation_issues,
                repair_attempted=False,
                status=pipeline_result.status,
            ),
        )
    return ProposalOperatorRecord(
        proposal_id=proposal_id,
        source_proposal_id=source_proposal_id,
        created_at=created_at,
        objective=request.objective,
        scope=request.scope,
        context_package=request.context_package,
        visible_constraints=request.visible_constraints,
        initial_attempt=initial_attempt,
        repair_attempt=repair_attempt,
        status="failed",
        final_validation_outcome=("failed" if pipeline_result.failure_stage == "validation" else "not_reached"),
        final_failure_stage=pipeline_result.failure_stage,
        final_error_message=str(pipeline_result.error),
    )