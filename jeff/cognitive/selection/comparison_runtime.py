"""Selection-local raw runtime handoff for model comparison."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from jeff.infrastructure import (
    ContractCallRequest,
    ModelAdapterError,
    ModelInvocationStatus,
    ModelResponse,
    ModelResponseMode,
    ModelUsage,
    OutputStrategy,
    Purpose,
)

from ..types import normalize_text_list, require_text
from .comparison import (
    SelectionComparisonPromptBundle,
    SelectionComparisonRequest,
    build_selection_comparison_prompt_bundle,
)

if TYPE_CHECKING:
    from jeff.infrastructure import InfrastructureServices


class SelectionComparisonRuntimeError(RuntimeError):
    """Raised when the bounded Selection comparison runtime handoff fails."""


@dataclass(frozen=True, slots=True)
class SelectionRawComparisonResult:
    """Raw Selection comparison output from one runtime call without interpretation."""

    prompt_bundle: SelectionComparisonPromptBundle
    request_id: str
    model_output_text: str
    adapter_id: str
    provider_name: str
    model_name: str
    usage: ModelUsage
    warnings: tuple[str, ...] = ()
    raw_response_ref: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", require_text(self.request_id, field_name="request_id"))
        object.__setattr__(self, "model_output_text", require_text(self.model_output_text, field_name="model_output_text"))
        object.__setattr__(self, "adapter_id", require_text(self.adapter_id, field_name="adapter_id"))
        object.__setattr__(self, "provider_name", require_text(self.provider_name, field_name="provider_name"))
        object.__setattr__(self, "model_name", require_text(self.model_name, field_name="model_name"))
        object.__setattr__(self, "warnings", normalize_text_list(self.warnings, field_name="warnings"))
        if self.raw_response_ref is not None:
            object.__setattr__(
                self,
                "raw_response_ref",
                require_text(self.raw_response_ref, field_name="raw_response_ref"),
            )


def run_selection_comparison(
    request: SelectionComparisonRequest,
    *,
    infrastructure_services: InfrastructureServices,
    adapter_id: str | None = None,
) -> SelectionRawComparisonResult:
    """Run one bounded Selection comparison model call and return raw text only."""

    prompt_bundle = build_selection_comparison_prompt_bundle(request)
    runtime_call = _build_runtime_call(prompt_bundle, adapter_id=adapter_id)
    try:
        response = infrastructure_services.contract_runtime.invoke(runtime_call)
    except ModelAdapterError as exc:
        raise SelectionComparisonRuntimeError(
            f"selection comparison runtime handoff failed: {exc}",
        ) from exc
    return _raw_result_from_response(prompt_bundle, response)


def _build_runtime_call(
    prompt_bundle: SelectionComparisonPromptBundle,
    *,
    adapter_id: str | None,
) -> ContractCallRequest:
    return ContractCallRequest(
        purpose="selection_comparison",
        routing_purpose=Purpose.SELECTION,
        output_strategy=OutputStrategy.BOUNDED_TEXT_THEN_PARSE,
        prompt=prompt_bundle.prompt_text,
        system_instructions=prompt_bundle.system_prompt,
        request_id=prompt_bundle.request_id,
        adapter_id=adapter_id,
        project_id=str(prompt_bundle.scope.project_id),
        work_unit_id=str(prompt_bundle.scope.work_unit_id) if prompt_bundle.scope.work_unit_id is not None else None,
        run_id=str(prompt_bundle.scope.run_id) if prompt_bundle.scope.run_id is not None else None,
        response_mode=ModelResponseMode.TEXT,
        timeout_seconds=None,
        max_output_tokens=1200,
        reasoning_effort="medium",
        metadata={
            "prompt_file": prompt_bundle.prompt_file,
            "expected_output_shape": "selection_comparison_text_v1",
            "stage": "selection_comparison",
        },
    )


def _raw_result_from_response(
    prompt_bundle: SelectionComparisonPromptBundle,
    response: ModelResponse,
) -> SelectionRawComparisonResult:
    if response.status is not ModelInvocationStatus.COMPLETED:
        raise SelectionComparisonRuntimeError(
            f"selection comparison runtime handoff failed with status={response.status.value}",
        )
    if response.output_text is None:
        raise SelectionComparisonRuntimeError(
            "selection comparison runtime handoff requires raw text output",
        )

    return SelectionRawComparisonResult(
        prompt_bundle=prompt_bundle,
        request_id=response.request_id,
        model_output_text=response.output_text,
        adapter_id=response.adapter_id,
        provider_name=response.provider_name,
        model_name=response.model_name,
        usage=response.usage,
        warnings=response.warnings,
        raw_response_ref=response.raw_response_ref,
    )
