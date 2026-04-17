"""Proposal Step 1 generation-entry surface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, TYPE_CHECKING

from jeff.core.schemas import Scope
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

from ..context import ContextPackage
from ..research.contracts import ResearchArtifact
from ..types import normalized_identity, normalize_text_list, require_text
from .prompt_files import load_prompt_file, render_prompt

if TYPE_CHECKING:
    from jeff.infrastructure import InfrastructureServices


@dataclass(frozen=True, slots=True)
class ProposalGenerationRequest:
    objective: str
    scope: Scope
    context_package: ContextPackage
    research_artifacts: tuple[ResearchArtifact, ...] = ()
    visible_constraints: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "objective", require_text(self.objective, field_name="objective"))
        object.__setattr__(
            self,
            "visible_constraints",
            normalize_text_list(self.visible_constraints, field_name="visible_constraints"),
        )
        object.__setattr__(self, "research_artifacts", tuple(self.research_artifacts))
        if self.context_package.scope != self.scope:
            raise ValueError("proposal generation request scope must match the context-package scope")
        for artifact in self.research_artifacts:
            if not isinstance(artifact, ResearchArtifact):
                raise TypeError("research_artifacts must contain ResearchArtifact instances")


@dataclass(frozen=True, slots=True)
class ProposalGenerationPromptBundle:
    request_id: str
    scope: Scope
    objective: str
    system_instructions: str
    prompt: str
    prompt_file: str = "STEP1_GENERATION.md"

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", require_text(self.request_id, field_name="request_id"))
        object.__setattr__(self, "objective", require_text(self.objective, field_name="objective"))
        object.__setattr__(
            self,
            "system_instructions",
            require_text(self.system_instructions, field_name="system_instructions"),
        )
        object.__setattr__(self, "prompt", require_text(self.prompt, field_name="prompt"))
        object.__setattr__(self, "prompt_file", require_text(self.prompt_file, field_name="prompt_file"))


class ProposalGenerationRuntimeError(RuntimeError):
    """Raised when the bounded Proposal Step 1 runtime handoff fails."""


@dataclass(frozen=True, slots=True)
class ProposalGenerationRawResult:
    prompt_bundle: ProposalGenerationPromptBundle
    request_id: str
    scope: Scope
    raw_output_text: str
    adapter_id: str
    provider_name: str
    model_name: str
    usage: ModelUsage
    warnings: tuple[str, ...] = ()
    raw_response_ref: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", require_text(self.request_id, field_name="request_id"))
        object.__setattr__(self, "raw_output_text", require_text(self.raw_output_text, field_name="raw_output_text"))
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


def build_proposal_generation_prompt_bundle(
    request: ProposalGenerationRequest,
) -> ProposalGenerationPromptBundle:
    system_instructions, template = load_prompt_file("STEP1_GENERATION.md")
    prompt = render_prompt(
        template,
        OBJECTIVE=_format_objective_block(request),
        SCOPE=_format_scope(request.scope),
        TRUTH_SNAPSHOT=_format_truth_snapshot(request.context_package),
        CURRENT_CONSTRAINTS=_format_constraints(request.visible_constraints),
        RESEARCH_SUPPORT=_format_research_support(request),
        OTHER_SUPPORT=_format_other_support(request.context_package),
        UNCERTAINTIES=_format_uncertainties(request.research_artifacts),
    )
    return ProposalGenerationPromptBundle(
        request_id=_build_request_id(request),
        scope=request.scope,
        objective=request.objective,
        system_instructions=system_instructions,
        prompt=prompt,
    )


def invoke_proposal_generation_with_runtime(
    prompt_bundle: ProposalGenerationPromptBundle,
    *,
    infrastructure_services: InfrastructureServices,
    adapter_id: str | None = None,
) -> ProposalGenerationRawResult:
    runtime_call = _build_runtime_call(prompt_bundle, adapter_id=adapter_id)
    try:
        response = infrastructure_services.contract_runtime.invoke(runtime_call)
    except ModelAdapterError as exc:
        raise ProposalGenerationRuntimeError(
            f"proposal step1 runtime handoff failed: {exc}",
        ) from exc
    return _raw_result_from_response(prompt_bundle, response)


def _build_request_id(request: ProposalGenerationRequest) -> str:
    objective_slug = normalized_identity(request.objective).replace(" ", "-")
    return (
        "proposal-generation:"
        f"{request.scope.project_id}:"
        f"{request.scope.work_unit_id or 'none'}:"
        f"{request.scope.run_id or 'none'}:"
        f"{objective_slug or 'objective'}"
    )


def _format_objective_block(request: ProposalGenerationRequest) -> str:
    return "\n".join(
        [
            f"objective={request.objective}",
            f"trigger={request.context_package.trigger.trigger_summary}",
            f"purpose={request.context_package.purpose}",
        ]
    )


def _format_scope(scope: Scope) -> str:
    return (
        f"project_id={scope.project_id}; "
        f"work_unit_id={scope.work_unit_id or 'NONE'}; "
        f"run_id={scope.run_id or 'NONE'}"
    )


def _format_truth_snapshot(context_package: ContextPackage) -> str:
    return "\n".join(
        f"truth_record_{index}|family={truth_record.truth_family}|summary={truth_record.summary}"
        for index, truth_record in enumerate(context_package.truth_records, start=1)
    )


def _format_constraints(visible_constraints: tuple[str, ...]) -> str:
    if not visible_constraints:
        return "NONE"
    return "\n".join(
        f"constraint_{index}|text={constraint}"
        for index, constraint in enumerate(visible_constraints, start=1)
    )


def _format_research_support(request: ProposalGenerationRequest) -> str:
    lines: list[str] = []

    research_support_inputs = [
        support_input
        for support_input in request.context_package.support_inputs
        if support_input.source_family == "research"
    ]
    for index, support_input in enumerate(research_support_inputs, start=1):
        lines.append(
            "context_research_support_"
            f"{index}|support_only|source_id={support_input.source_id or 'NONE'}|summary={support_input.summary}"
        )

    for index, artifact in enumerate(request.research_artifacts, start=1):
        findings_summary = _join_with_semicolons(finding.text for finding in artifact.findings)
        uncertainty_summary = _join_with_semicolons(artifact.uncertainties)
        lines.append(
            "research_artifact_"
            f"{index}|support_only|question={artifact.question}|summary={artifact.summary}"
        )
        lines.append(f"research_artifact_{index}_findings|support_only|items={findings_summary}")
        lines.append(f"research_artifact_{index}_uncertainties|support_only|items={uncertainty_summary}")

    return "\n".join(lines) if lines else "NONE"


def _format_other_support(context_package: ContextPackage) -> str:
    non_research_support = [
        support_input
        for support_input in context_package.support_inputs
        if support_input.source_family != "research"
    ]
    if not non_research_support:
        return "NONE"
    return "\n".join(
        "support_"
        f"{index}|family={support_input.source_family}|source_id={support_input.source_id or 'NONE'}|summary={support_input.summary}"
        for index, support_input in enumerate(non_research_support, start=1)
    )


def _format_uncertainties(research_artifacts: tuple[ResearchArtifact, ...]) -> str:
    uncertainty_lines: list[str] = []
    for artifact_index, artifact in enumerate(research_artifacts, start=1):
        for uncertainty_index, uncertainty in enumerate(artifact.uncertainties, start=1):
            uncertainty_lines.append(
                "research_uncertainty_"
                f"{artifact_index}_{uncertainty_index}|support_only|text={uncertainty}"
            )
    return "\n".join(uncertainty_lines) if uncertainty_lines else "NONE"


def _join_with_semicolons(values: Iterable[str]) -> str:
    normalized_values = [require_text(str(value), field_name="value") for value in values]
    return "; ".join(normalized_values) if normalized_values else "NONE"


def _build_runtime_call(
    prompt_bundle: ProposalGenerationPromptBundle,
    *,
    adapter_id: str | None,
) -> ContractCallRequest:
    return ContractCallRequest(
        purpose="proposal_generation_step1",
        routing_purpose=Purpose.PROPOSAL,
        output_strategy=OutputStrategy.BOUNDED_TEXT_THEN_PARSE,
        prompt=prompt_bundle.prompt,
        system_instructions=prompt_bundle.system_instructions,
        request_id=prompt_bundle.request_id,
        adapter_id=adapter_id,
        project_id=str(prompt_bundle.scope.project_id),
        work_unit_id=str(prompt_bundle.scope.work_unit_id) if prompt_bundle.scope.work_unit_id is not None else None,
        run_id=str(prompt_bundle.scope.run_id) if prompt_bundle.scope.run_id is not None else None,
        response_mode=ModelResponseMode.TEXT,
        timeout_seconds=None,
        max_output_tokens=1800,
        reasoning_effort="medium",
        metadata={
            "prompt_file": prompt_bundle.prompt_file,
            "expected_output_shape": "proposal_step1_generation_text_v1",
            "stage": "proposal_step1_generation",
        },
    )


def _raw_result_from_response(
    prompt_bundle: ProposalGenerationPromptBundle,
    response: ModelResponse,
) -> ProposalGenerationRawResult:
    if response.status is not ModelInvocationStatus.COMPLETED:
        raise ProposalGenerationRuntimeError(
            f"proposal step1 runtime handoff failed with status={response.status.value}",
        )
    if response.output_text is None:
        raise ProposalGenerationRuntimeError(
            "proposal step1 runtime handoff requires raw text output",
        )

    return ProposalGenerationRawResult(
        prompt_bundle=prompt_bundle,
        request_id=response.request_id,
        scope=prompt_bundle.scope,
        raw_output_text=response.output_text,
        adapter_id=response.adapter_id,
        provider_name=response.provider_name,
        model_name=response.model_name,
        usage=response.usage,
        warnings=response.warnings,
        raw_response_ref=response.raw_response_ref,
    )
