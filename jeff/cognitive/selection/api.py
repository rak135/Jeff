"""Thin Selection-local end-to-end hybrid composition entry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TYPE_CHECKING

from .comparison import SelectionComparisonRequest
from .comparison_runtime import (
    SelectionComparisonRuntimeError,
    SelectionRawComparisonResult,
    run_selection_comparison,
)
from .contracts import SelectionRequest, SelectionResult
from .parsing import (
    ParsedSelectionComparison,
    SelectionComparisonParseError,
    parse_selection_comparison_result,
)
from .validation import (
    SelectionComparisonValidationError,
    SelectionComparisonValidationIssue,
    ValidatedSelectionComparison,
    validate_selection_comparison,
)

if TYPE_CHECKING:
    from jeff.infrastructure import InfrastructureServices

SelectionFailureStage = Literal["runtime", "parse", "validation"]


@dataclass(frozen=True, slots=True)
class SelectionRunSuccess:
    selection_request: SelectionRequest
    comparison_request: SelectionComparisonRequest
    raw_comparison_result: SelectionRawComparisonResult
    parsed_comparison: ParsedSelectionComparison
    validated_comparison: ValidatedSelectionComparison
    selection_result: SelectionResult
    status: Literal["validated_success"] = "validated_success"

    def __post_init__(self) -> None:
        if self.comparison_request.selection_request != self.selection_request:
            raise ValueError("selection success must preserve SelectionRequest linkage")
        if self.raw_comparison_result.request_id != self.selection_request.request_id:
            raise ValueError("selection success must preserve request_id linkage")
        if self.parsed_comparison.request_id != self.selection_request.request_id:
            raise ValueError("selection success must preserve parsed request_id linkage")
        if self.validated_comparison.request_id != self.selection_request.request_id:
            raise ValueError("selection success must preserve validated request_id linkage")
        if self.selection_result.considered_proposal_ids != self.selection_request.considered_proposal_ids:
            raise ValueError("selection success must preserve considered proposal ids")


@dataclass(frozen=True, slots=True)
class SelectionRunFailure:
    selection_request: SelectionRequest
    comparison_request: SelectionComparisonRequest
    failure_stage: SelectionFailureStage
    error: Exception
    raw_comparison_result: SelectionRawComparisonResult | None = None
    parsed_comparison: ParsedSelectionComparison | None = None
    validation_issues: tuple[SelectionComparisonValidationIssue, ...] = ()
    status: Literal["runtime_failure", "parse_failure", "validation_failure"] = "runtime_failure"

    def __post_init__(self) -> None:
        expected_status = f"{self.failure_stage}_failure"
        if self.status != expected_status:
            raise ValueError("selection failure status must match failure_stage")
        if self.failure_stage == "runtime":
            if self.raw_comparison_result is not None or self.parsed_comparison is not None:
                raise ValueError("runtime-stage failures must not include downstream artifacts")
            if self.validation_issues:
                raise ValueError("runtime-stage failures must not include validation_issues")
        if self.failure_stage == "parse":
            if self.raw_comparison_result is None:
                raise ValueError("parse-stage failures must preserve raw_comparison_result")
            if self.parsed_comparison is not None:
                raise ValueError("parse-stage failures must not include parsed_comparison")
            if self.validation_issues:
                raise ValueError("parse-stage failures must not include validation_issues")
        if self.failure_stage == "validation":
            if self.raw_comparison_result is None or self.parsed_comparison is None:
                raise ValueError("validation-stage failures must preserve raw and parsed comparison artifacts")
            if not self.validation_issues:
                raise ValueError("validation-stage failures must include validation_issues")


SelectionHybridResult = SelectionRunSuccess | SelectionRunFailure


def run_selection_hybrid(
    selection_request: SelectionRequest,
    *,
    selection_id: str,
    infrastructure_services: InfrastructureServices,
    adapter_id: str | None = None,
) -> SelectionHybridResult:
    comparison_request = SelectionComparisonRequest.from_selection_request(selection_request)

    try:
        raw_comparison_result = run_selection_comparison(
            comparison_request,
            infrastructure_services=infrastructure_services,
            adapter_id=adapter_id,
        )
    except SelectionComparisonRuntimeError as exc:
        return SelectionRunFailure(
            selection_request=selection_request,
            comparison_request=comparison_request,
            failure_stage="runtime",
            error=exc,
            status="runtime_failure",
        )

    try:
        parsed_comparison = parse_selection_comparison_result(raw_comparison_result)
    except SelectionComparisonParseError as exc:
        return SelectionRunFailure(
            selection_request=selection_request,
            comparison_request=comparison_request,
            failure_stage="parse",
            error=exc,
            raw_comparison_result=raw_comparison_result,
            status="parse_failure",
        )

    try:
        validated_comparison = validate_selection_comparison(
            parsed_comparison,
            request=comparison_request,
        )
    except SelectionComparisonValidationError as exc:
        return SelectionRunFailure(
            selection_request=selection_request,
            comparison_request=comparison_request,
            failure_stage="validation",
            error=exc,
            raw_comparison_result=raw_comparison_result,
            parsed_comparison=parsed_comparison,
            validation_issues=exc.issues,
            status="validation_failure",
        )

    selection_result = _build_selection_result(
        selection_id=selection_id,
        selection_request=selection_request,
        validated_comparison=validated_comparison,
    )
    return SelectionRunSuccess(
        selection_request=selection_request,
        comparison_request=comparison_request,
        raw_comparison_result=raw_comparison_result,
        parsed_comparison=parsed_comparison,
        validated_comparison=validated_comparison,
        selection_result=selection_result,
    )


def _build_selection_result(
    *,
    selection_id: str,
    selection_request: SelectionRequest,
    validated_comparison: ValidatedSelectionComparison,
) -> SelectionResult:
    selected_proposal_id = validated_comparison.selected_proposal_id
    non_selection_outcome = None if validated_comparison.disposition == "selected" else validated_comparison.disposition

    return SelectionResult(
        selection_id=selection_id,
        considered_proposal_ids=selection_request.considered_proposal_ids,
        selected_proposal_id=selected_proposal_id,
        non_selection_outcome=non_selection_outcome,  # type: ignore[arg-type]
        rationale=_build_selection_rationale(validated_comparison),
    )


def _build_selection_rationale(validated_comparison: ValidatedSelectionComparison) -> str:
    parts = [validated_comparison.primary_basis]

    if (
        validated_comparison.main_losing_alternative_id is not None
        and validated_comparison.main_losing_reason is not None
    ):
        parts.append(
            f"Main losing alternative {validated_comparison.main_losing_alternative_id}: "
            f"{validated_comparison.main_losing_reason}"
        )

    if validated_comparison.planning_insertion_recommended:
        parts.append("Planning insertion may still help later.")

    parts.append(f"Cautions: {validated_comparison.cautions}")
    return " ".join(parts)
