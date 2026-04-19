"""Deterministic fail-closed bridge from preserved proposal input into proposal generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..context import ContextPackage
from ..research import ResearchArtifact
from ..types import SupportInput, normalize_text_list, require_text
from .api import ProposalPipelineFailure, ProposalPipelineResult, ProposalPipelineSuccess, run_proposal_generation_pipeline
from .contracts import ProposalResult
from .generation import ProposalGenerationRequest
from .proposal_support_package_consumer import ProposalInputPackage

if TYPE_CHECKING:
    from jeff.infrastructure import InfrastructureServices


@dataclass(frozen=True, slots=True)
class ProposalGenerationBridgeIssue:
    code: str
    message: str
    field_name: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", require_text(self.code, field_name="code"))
        object.__setattr__(self, "message", require_text(self.message, field_name="message"))
        if self.field_name is not None:
            object.__setattr__(self, "field_name", require_text(self.field_name, field_name="field_name"))


class ProposalGenerationBridgeError(ValueError):
    """Raised when proposal-input preservation is not lawful enough to attempt proposal generation."""

    def __init__(self, issues: tuple[ProposalGenerationBridgeIssue, ...]) -> None:
        if not issues:
            raise ValueError("proposal generation bridge errors must include at least one issue")
        self.issues = issues
        rendered = "; ".join(
            issue.message if issue.field_name is None else f"{issue.field_name}: {issue.message}"
            for issue in issues
        )
        super().__init__(f"proposal generation bridge failed: {rendered}")


@dataclass(frozen=True, slots=True)
class ProposalGenerationBridgeRequest:
    request_id: str
    proposal_input_package: ProposalInputPackage | None
    context_package: ContextPackage | None
    research_artifact: ResearchArtifact | None
    infrastructure_services: InfrastructureServices | None
    bounded_objective: str | None = None
    visible_constraints: tuple[str, ...] = ()
    adapter_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, str):
            raise TypeError("request_id must be a string")
        if self.proposal_input_package is not None and not isinstance(self.proposal_input_package, ProposalInputPackage):
            raise TypeError("proposal_input_package must be a ProposalInputPackage when provided")
        if self.context_package is not None and not isinstance(self.context_package, ContextPackage):
            raise TypeError("context_package must be a ContextPackage when provided")
        if self.research_artifact is not None and not isinstance(self.research_artifact, ResearchArtifact):
            raise TypeError("research_artifact must be a ResearchArtifact when provided")
        if self.infrastructure_services is not None and not isinstance(
            self.infrastructure_services,
            _infrastructure_services_type(),
        ):
            raise TypeError("infrastructure_services must be InfrastructureServices when provided")
        object.__setattr__(
            self,
            "visible_constraints",
            normalize_text_list(self.visible_constraints, field_name="visible_constraints"),
        )
        if self.bounded_objective is not None:
            object.__setattr__(
                self,
                "bounded_objective",
                require_text(self.bounded_objective, field_name="bounded_objective"),
            )
        if self.adapter_id is not None:
            object.__setattr__(self, "adapter_id", require_text(self.adapter_id, field_name="adapter_id"))


@dataclass(frozen=True, slots=True)
class ProposalGenerationBridgeResult:
    bridge_id: str
    proposal_input_package_id: str
    proposal_request_built: bool
    proposal_generation_ran: bool
    proposal_generation_request: ProposalGenerationRequest | None = None
    proposal_pipeline_result: ProposalPipelineResult | None = None
    proposal_result: ProposalResult | None = None
    proposal_count: int | None = None
    no_generation_reason: str | None = None
    summary: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "bridge_id", require_text(self.bridge_id, field_name="bridge_id"))
        object.__setattr__(
            self,
            "proposal_input_package_id",
            require_text(self.proposal_input_package_id, field_name="proposal_input_package_id"),
        )
        object.__setattr__(self, "summary", require_text(self.summary, field_name="summary"))
        if self.no_generation_reason is not None:
            object.__setattr__(
                self,
                "no_generation_reason",
                require_text(self.no_generation_reason, field_name="no_generation_reason"),
            )
        if self.proposal_generation_request is None and self.proposal_request_built:
            raise ValueError("proposal_request_built requires a preserved proposal_generation_request")
        if self.proposal_pipeline_result is not None and not self.proposal_generation_ran:
            raise ValueError("proposal_pipeline_result requires proposal_generation_ran")
        if self.proposal_result is not None:
            if self.proposal_pipeline_result is None:
                raise ValueError("proposal_result requires preserved proposal_pipeline_result")
            if not isinstance(self.proposal_pipeline_result, ProposalPipelineSuccess):
                raise ValueError("proposal_result requires ProposalPipelineSuccess")
            if self.proposal_result != self.proposal_pipeline_result.proposal_result:
                raise ValueError("proposal_result must match proposal_pipeline_result.proposal_result")
            if self.proposal_count != self.proposal_result.proposal_count:
                raise ValueError("proposal_count must match proposal_result.proposal_count")
            if self.no_generation_reason is not None:
                raise ValueError("proposal_result must not carry no_generation_reason")
        elif self.proposal_generation_ran and self.no_generation_reason is None:
            raise ValueError("proposal_generation_ran without proposal_result must preserve no_generation_reason")
        elif not self.proposal_generation_ran and not self.proposal_request_built and self.no_generation_reason is None:
            raise ValueError("non-generation bridge results must preserve no_generation_reason")


def build_and_run_proposal_generation(
    request: ProposalGenerationBridgeRequest,
) -> ProposalGenerationBridgeResult:
    issues = _collect_request_issues(request)
    if issues:
        raise ProposalGenerationBridgeError(tuple(issues))

    package = request.proposal_input_package
    assert package is not None

    no_generation_reason = _missing_generation_input_reason(request)
    if no_generation_reason is not None:
        return ProposalGenerationBridgeResult(
            bridge_id=f"proposal-generation-bridge:{request.request_id}",
            proposal_input_package_id=package.package_id,
            proposal_request_built=False,
            proposal_generation_ran=False,
            proposal_generation_request=None,
            proposal_pipeline_result=None,
            proposal_result=None,
            proposal_count=None,
            no_generation_reason=no_generation_reason,
            summary=(
                f"Proposal-generation bridge did not run. {no_generation_reason} "
                "The preserved proposal-input package remains the truthful boundary and no proposal output exists."
            ),
        )

    proposal_request = _build_generation_request(request)
    pipeline_result = run_proposal_generation_pipeline(
        proposal_request,
        infrastructure_services=request.infrastructure_services,
        adapter_id=request.adapter_id,
    )
    if isinstance(pipeline_result, ProposalPipelineFailure):
        no_output_reason = (
            f"proposal generation ran but no lawful proposal output exists because the pipeline ended at "
            f"{pipeline_result.failure_stage}: {pipeline_result.error}"
        )
        return ProposalGenerationBridgeResult(
            bridge_id=f"proposal-generation-bridge:{request.request_id}",
            proposal_input_package_id=package.package_id,
            proposal_request_built=True,
            proposal_generation_ran=True,
            proposal_generation_request=proposal_request,
            proposal_pipeline_result=pipeline_result,
            proposal_result=None,
            proposal_count=None,
            no_generation_reason=no_output_reason,
            summary=(
                "Proposal-generation bridge built a bounded proposal request and called the real proposal pipeline, "
                f"but {no_output_reason}. The preserved proposal-input package remains the truthful boundary."
            ),
        )

    proposal_result = pipeline_result.proposal_result
    return ProposalGenerationBridgeResult(
        bridge_id=f"proposal-generation-bridge:{request.request_id}",
        proposal_input_package_id=package.package_id,
        proposal_request_built=True,
        proposal_generation_ran=True,
        proposal_generation_request=proposal_request,
        proposal_pipeline_result=pipeline_result,
        proposal_result=proposal_result,
        proposal_count=proposal_result.proposal_count,
        no_generation_reason=None,
        summary=(
            "Proposal-generation bridge built a bounded proposal request, ran proposal generation, and preserved "
            f"proposal output with {proposal_result.proposal_count} serious option(s). Proposal output remains "
            "proposal-only and is not selection, not action, not permission, not governance, and not execution."
        ),
    )


def _collect_request_issues(
    request: ProposalGenerationBridgeRequest,
) -> tuple[ProposalGenerationBridgeIssue, ...]:
    issues: list[ProposalGenerationBridgeIssue] = []

    try:
        require_text(request.request_id, field_name="request_id")
    except (TypeError, ValueError):
        issues.append(
            ProposalGenerationBridgeIssue(
                code="invalid_request_id",
                message="request_id must be a non-empty string",
                field_name="request_id",
            )
        )

    package = request.proposal_input_package
    if package is None:
        issues.append(
            ProposalGenerationBridgeIssue(
                code="missing_proposal_input_package",
                message="proposal generation bridge requires a preserved proposal-input package",
                field_name="proposal_input_package",
            )
        )
        return tuple(issues)

    try:
        require_text(package.package_id, field_name="proposal_input_package.package_id")
    except (TypeError, ValueError):
        issues.append(
            ProposalGenerationBridgeIssue(
                code="missing_package_id",
                message="proposal-input package must preserve a non-empty package_id",
                field_name="proposal_input_package.package_id",
            )
        )

    if not package.proposal_input_ready:
        issues.append(
            ProposalGenerationBridgeIssue(
                code="proposal_input_not_ready",
                message="proposal generation may only run from a proposal-input-ready package",
                field_name="proposal_input_package.proposal_input_ready",
            )
        )

    issues.extend(
        _validate_text_items(
            package.supported_findings,
            field_name="proposal_input_package.supported_findings",
            missing_code="missing_supported_findings",
            missing_message="proposal-input package must preserve at least one supported finding",
            invalid_code="invalid_supported_finding",
            invalid_message="supported findings must be non-empty strings",
        )
    )
    issues.extend(
        _validate_text_items(
            package.inference_points,
            field_name="proposal_input_package.inference_points",
            missing_code=None,
            missing_message=None,
            invalid_code="invalid_inference_point",
            invalid_message="inference points must be non-empty strings",
        )
    )
    issues.extend(
        _validate_text_items(
            package.uncertainty_points,
            field_name="proposal_input_package.uncertainty_points",
            missing_code=None,
            missing_message=None,
            invalid_code="invalid_uncertainty_point",
            invalid_message="uncertainty points must be non-empty strings",
        )
    )
    issues.extend(
        _validate_text_items(
            package.contradiction_notes,
            field_name="proposal_input_package.contradiction_notes",
            missing_code=None,
            missing_message=None,
            invalid_code="invalid_contradiction_note",
            invalid_message="contradiction notes must be non-empty strings",
        )
    )
    issues.extend(
        _validate_text_items(
            package.recommendation_candidates,
            field_name="proposal_input_package.recommendation_candidates",
            missing_code=None,
            missing_message=None,
            invalid_code="invalid_recommendation_candidate",
            invalid_message="recommendation candidates must be non-empty strings",
        )
    )
    issues.extend(
        _validate_text_items(
            package.missing_information_markers,
            field_name="proposal_input_package.missing_information_markers",
            missing_code=None,
            missing_message=None,
            invalid_code="invalid_missing_information_marker",
            invalid_message="missing-information markers must be non-empty strings",
        )
    )
    issues.extend(
        _validate_text_items(
            package.provenance_refs,
            field_name="proposal_input_package.provenance_refs",
            missing_code="missing_provenance_refs",
            missing_message="proposal-input package must preserve at least one provenance ref",
            invalid_code="invalid_provenance_ref",
            invalid_message="provenance refs must be non-empty strings",
        )
    )

    research_artifact = request.research_artifact
    if research_artifact is not None:
        artifact_findings = {require_text(finding.text, field_name="research_artifact.findings") for finding in research_artifact.findings}
        artifact_uncertainties = {
            require_text(uncertainty, field_name="research_artifact.uncertainties")
            for uncertainty in research_artifact.uncertainties
        }
        artifact_sources = {
            require_text(source_id, field_name="research_artifact.source_ids")
            for source_id in research_artifact.source_ids
        }
        for index, finding in enumerate(package.supported_findings):
            if finding not in artifact_findings:
                issues.append(
                    ProposalGenerationBridgeIssue(
                        code="supported_finding_not_in_research_artifact",
                        message="supported findings must remain grounded in the preserved research artifact",
                        field_name=f"proposal_input_package.supported_findings[{index}]",
                    )
                )
        for index, uncertainty in enumerate(package.uncertainty_points):
            if uncertainty not in artifact_uncertainties:
                issues.append(
                    ProposalGenerationBridgeIssue(
                        code="uncertainty_point_not_in_research_artifact",
                        message="uncertainty points must remain grounded in the preserved research artifact",
                        field_name=f"proposal_input_package.uncertainty_points[{index}]",
                    )
                )
        for index, provenance_ref in enumerate(package.provenance_refs):
            if provenance_ref not in artifact_sources:
                issues.append(
                    ProposalGenerationBridgeIssue(
                        code="provenance_ref_not_in_research_artifact",
                        message="proposal-input provenance refs must remain grounded in the preserved research artifact",
                        field_name=f"proposal_input_package.provenance_refs[{index}]",
                    )
                )

    return tuple(issues)


def _missing_generation_input_reason(request: ProposalGenerationBridgeRequest) -> str | None:
    if request.context_package is None:
        return "proposal generation requires a preserved ContextPackage and none was provided"
    if request.research_artifact is None:
        return "proposal generation requires the preserved research artifact from this research-followup path"
    if request.infrastructure_services is None:
        return "proposal generation requires InfrastructureServices and no runtime services were provided"
    return None


def _build_generation_request(request: ProposalGenerationBridgeRequest) -> ProposalGenerationRequest:
    assert request.proposal_input_package is not None
    assert request.context_package is not None
    assert request.research_artifact is not None

    objective = (
        request.bounded_objective
        if request.bounded_objective is not None
        else require_text(
            request.context_package.trigger.trigger_summary,
            field_name="context_package.trigger.trigger_summary",
        )
    )
    return ProposalGenerationRequest(
        objective=objective,
        scope=request.context_package.scope,
        context_package=_context_with_proposal_input_support(
            context_package=request.context_package,
            proposal_input_package=request.proposal_input_package,
        ),
        research_artifacts=(request.research_artifact,),
        visible_constraints=request.visible_constraints,
    )


def _context_with_proposal_input_support(
    *,
    context_package: ContextPackage,
    proposal_input_package: ProposalInputPackage,
) -> ContextPackage:
    proposal_support_inputs: list[SupportInput] = list(context_package.support_inputs)
    proposal_support_inputs.extend(
        _support_inputs_for_items(
            proposal_input_package.supported_findings,
            scope=context_package.scope,
            source_id_prefix=f"{proposal_input_package.package_id}:supported-finding",
        )
    )
    proposal_support_inputs.extend(
        _support_inputs_for_items(
            proposal_input_package.inference_points,
            scope=context_package.scope,
            source_id_prefix=f"{proposal_input_package.package_id}:inference-point",
        )
    )
    proposal_support_inputs.extend(
        _support_inputs_for_items(
            proposal_input_package.uncertainty_points,
            scope=context_package.scope,
            source_id_prefix=f"{proposal_input_package.package_id}:uncertainty-point",
        )
    )
    proposal_support_inputs.extend(
        _support_inputs_for_items(
            proposal_input_package.contradiction_notes,
            scope=context_package.scope,
            source_id_prefix=f"{proposal_input_package.package_id}:contradiction-note",
        )
    )
    proposal_support_inputs.extend(
        _support_inputs_for_items(
            proposal_input_package.recommendation_candidates,
            scope=context_package.scope,
            source_id_prefix=f"{proposal_input_package.package_id}:recommendation-candidate",
        )
    )
    proposal_support_inputs.extend(
        _support_inputs_for_items(
            proposal_input_package.missing_information_markers,
            scope=context_package.scope,
            source_id_prefix=f"{proposal_input_package.package_id}:missing-information-marker",
        )
    )
    return ContextPackage(
        purpose=context_package.purpose,
        trigger=context_package.trigger,
        scope=context_package.scope,
        truth_records=context_package.truth_records,
        governance_truth_records=context_package.governance_truth_records,
        support_inputs=tuple(proposal_support_inputs),
        memory_support_inputs=context_package.memory_support_inputs,
        compiled_knowledge_support_inputs=context_package.compiled_knowledge_support_inputs,
        archive_support_inputs=context_package.archive_support_inputs,
    )


def _support_inputs_for_items(
    values: tuple[str, ...],
    *,
    scope,
    source_id_prefix: str,
) -> tuple[SupportInput, ...]:
    return tuple(
        SupportInput(
            source_family="research",
            scope=scope,
            source_id=f"{source_id_prefix}:{index}",
            summary=require_text(value, field_name="value"),
        )
        for index, value in enumerate(values, start=1)
    )


def _validate_text_items(
    values: tuple[str, ...],
    *,
    field_name: str,
    missing_code: str | None,
    missing_message: str | None,
    invalid_code: str,
    invalid_message: str,
) -> tuple[ProposalGenerationBridgeIssue, ...]:
    issues: list[ProposalGenerationBridgeIssue] = []
    if not values:
        if missing_code is not None and missing_message is not None:
            issues.append(
                ProposalGenerationBridgeIssue(
                    code=missing_code,
                    message=missing_message,
                    field_name=field_name,
                )
            )
        return tuple(issues)

    for index, value in enumerate(values):
        try:
            require_text(value, field_name=f"{field_name}[{index}]")
        except (TypeError, ValueError):
            issues.append(
                ProposalGenerationBridgeIssue(
                    code=invalid_code,
                    message=invalid_message,
                    field_name=f"{field_name}[{index}]",
                )
            )
    return tuple(issues)


def _infrastructure_services_type():
    from jeff.infrastructure import InfrastructureServices

    return InfrastructureServices
