from dataclasses import dataclass, field

from jeff.cognitive.context import ContextPackage
from jeff.cognitive.proposal import (
    ProposalPipelineFailure,
    ProposalPipelineSuccess,
    ProposalGenerationRequest,
    run_proposal_generation_pipeline,
)
from jeff.cognitive.research import ResearchArtifact, ResearchFinding
from jeff.cognitive.types import SupportInput, TriggerInput, TruthRecord
from jeff.core.schemas import Scope
from jeff.infrastructure import ModelInvocationStatus, ModelResponse, ModelUsage
from jeff.infrastructure.contract_runtime import ContractCallRequest
from jeff.infrastructure.model_adapters.errors import ModelTimeoutError


def test_successful_composed_pipeline_runs_end_to_end_without_retry_or_orchestrator_paths() -> None:
    request = _generation_request()
    runtime = _TrackingContractRuntime(
        response=_response(
            request_id="proposal-generation:project-1:wu-1:run-1:frame-bounded-options-for-the-current-blocker-state",
            output_text=(
                "PROPOSAL_COUNT: 1\n"
                "SCARCITY_REASON: Only one serious path is currently grounded.\n"
                "OPTION_1_TYPE: investigate\n"
                "OPTION_1_TITLE: Confirm the blocker directly\n"
                "OPTION_1_SUMMARY: Run one bounded investigation against the blocker.\n"
                "OPTION_1_WHY_NOW: The blocker still prevents a stronger proposal set.\n"
                "OPTION_1_ASSUMPTIONS: The blocker can be inspected quickly\n"
                "OPTION_1_RISKS: Investigation may confirm no viable path\n"
                "OPTION_1_CONSTRAINTS: Stay inside the current work unit\n"
                "OPTION_1_BLOCKERS: Direct change remains blocked\n"
                "OPTION_1_PLANNING_NEEDED: no\n"
                "OPTION_1_FEASIBILITY: Feasible with current evidence\n"
                "OPTION_1_REVERSIBILITY: Fully reversible\n"
                "OPTION_1_SUPPORT_REFS: ctx-1,research-2\n"
            ),
        )
    )

    result = run_proposal_generation_pipeline(
        request,
        infrastructure_services=_FakeServices(runtime),
    )

    assert isinstance(result, ProposalPipelineSuccess)
    assert result.status == "validated_success"
    assert runtime.invoke_with_request_calls == []
    assert len(runtime.invoke_calls) == 1
    assert result.proposal_result.request_id == result.raw_result.request_id
    assert len(result.proposal_result.options) == len(result.proposal_result.options)
    assert all(
        result.proposal_result.options[i].proposal_id == f"proposal-{i+1}"
        for i in range(len(result.proposal_result.options))
    )
    assert not hasattr(result, "handoff")
    assert not hasattr(result, "validated_result")


def test_runtime_failure_surface_is_preserved_explicitly() -> None:
    request = _generation_request()
    runtime = _TrackingContractRuntime(raised_exception=ModelTimeoutError("timed out"))

    result = run_proposal_generation_pipeline(
        request,
        infrastructure_services=_FakeServices(runtime),
    )

    assert isinstance(result, ProposalPipelineFailure)
    assert result.failure_stage == "runtime"
    assert result.status == "runtime_failure"
    assert result.prompt_bundle is not None
    assert result.raw_result is None
    assert result.parsed_result is None


def test_parse_failure_surface_is_preserved_explicitly() -> None:
    request = _generation_request()
    runtime = _TrackingContractRuntime(
        response=_response(
            request_id="proposal-generation:project-1:wu-1:run-1:frame-bounded-options-for-the-current-blocker-state",
            output_text="NOT_A_VALID_PROPOSAL_LINE",
        )
    )

    result = run_proposal_generation_pipeline(
        request,
        infrastructure_services=_FakeServices(runtime),
    )

    assert isinstance(result, ProposalPipelineFailure)
    assert result.failure_stage == "parse"
    assert result.status == "parse_failure"
    assert result.raw_result is not None
    assert result.parsed_result is None


def test_validation_failure_surface_is_preserved_explicitly() -> None:
    request = _generation_request()
    runtime = _TrackingContractRuntime(
        response=_response(
            request_id="proposal-generation:project-1:wu-1:run-1:frame-bounded-options-for-the-current-blocker-state",
            output_text=(
                "PROPOSAL_COUNT: 1\n"
                "SCARCITY_REASON: Only one serious path is currently grounded.\n"
                "OPTION_1_TYPE: clarify\n"
                "OPTION_1_TITLE: Clarify the scope edge\n"
                "OPTION_1_SUMMARY: Ask one bounded clarifying question.\n"
                "OPTION_1_WHY_NOW: Scope ambiguity still blocks stronger framing.\n"
                "OPTION_1_ASSUMPTIONS: NONE\n"
                "OPTION_1_RISKS: NONE\n"
                "OPTION_1_CONSTRAINTS: NONE\n"
                "OPTION_1_BLOCKERS: NONE\n"
                "OPTION_1_PLANNING_NEEDED: no\n"
                "OPTION_1_FEASIBILITY: Feasible once clarified\n"
                "OPTION_1_REVERSIBILITY: Fully reversible\n"
                "OPTION_1_SUPPORT_REFS: ctx-1\n"
            ),
        )
    )

    result = run_proposal_generation_pipeline(
        request,
        infrastructure_services=_FakeServices(runtime),
    )

    assert isinstance(result, ProposalPipelineFailure)
    assert result.failure_stage == "validation"
    assert result.status == "validation_failure"
    assert result.parsed_result is not None
    assert tuple(issue.code for issue in result.validation_issues) == (
        "missing_assumptions",
        "missing_risks",
        "missing_constraints_or_blockers",
    )


def test_validated_success_returns_consolidated_primary_proposal_result_shape() -> None:
    request = _generation_request()
    runtime = _TrackingContractRuntime(
        response=_response(
            request_id="proposal-generation:project-1:wu-1:run-1:frame-bounded-options-for-the-current-blocker-state",
            output_text=(
                "PROPOSAL_COUNT: 2\n"
                "SCARCITY_REASON: NONE\n"
                "OPTION_1_TYPE: direct_action\n"
                "OPTION_1_TITLE: Apply the bounded patch\n"
                "OPTION_1_SUMMARY: Apply the smallest safe patch now.\n"
                "OPTION_1_WHY_NOW: Current support already bounds the change.\n"
                "OPTION_1_ASSUMPTIONS: The failing edge is already reproduced\n"
                "OPTION_1_RISKS: Small regression risk remains\n"
                "OPTION_1_CONSTRAINTS: Stay inside the current project scope\n"
                "OPTION_1_BLOCKERS: NONE\n"
                "OPTION_1_PLANNING_NEEDED: no\n"
                "OPTION_1_FEASIBILITY: Feasible with current evidence\n"
                "OPTION_1_REVERSIBILITY: Straightforward rollback\n"
                "OPTION_1_SUPPORT_REFS: ctx-1,research-1\n"
                "OPTION_2_TYPE: investigate\n"
                "OPTION_2_TITLE: Gather one more signal\n"
                "OPTION_2_SUMMARY: Check the unresolved edge case first.\n"
                "OPTION_2_WHY_NOW: Remaining uncertainty still matters.\n"
                "OPTION_2_ASSUMPTIONS: The signal can be collected quickly\n"
                "OPTION_2_RISKS: Progress slows while evidence is gathered\n"
                "OPTION_2_CONSTRAINTS: Keep the investigation inside current scope\n"
                "OPTION_2_BLOCKERS: NONE\n"
                "OPTION_2_PLANNING_NEEDED: no\n"
                "OPTION_2_FEASIBILITY: Feasible with current tools\n"
                "OPTION_2_REVERSIBILITY: Investigation only\n"
                "OPTION_2_SUPPORT_REFS: ctx-1,research-3\n"
            ),
        )
    )

    result = run_proposal_generation_pipeline(
        request,
        infrastructure_services=_FakeServices(runtime),
    )

    assert isinstance(result, ProposalPipelineSuccess)
    assert result.proposal_result.request_id == result.raw_result.request_id
    assert result.proposal_result.scope == request.scope
    assert result.proposal_result.proposal_count == 2
    assert result.proposal_result.options[0].title == "Apply the bounded patch"
    assert result.proposal_result.options[0].summary == "Apply the smallest safe patch now."


@dataclass
class _TrackingContractRuntime:
    response: ModelResponse | None = None
    raised_exception: Exception | None = None
    invoke_calls: list[ContractCallRequest] = field(default_factory=list)
    invoke_with_request_calls: list[tuple[object, str]] = field(default_factory=list)

    def invoke(self, call: ContractCallRequest) -> ModelResponse:
        self.invoke_calls.append(call)
        if self.raised_exception is not None:
            raise self.raised_exception
        assert self.response is not None
        return self.response

    def invoke_with_request(self, request: object, *, adapter_id: str) -> ModelResponse:
        self.invoke_with_request_calls.append((request, adapter_id))
        raise AssertionError("proposal slice G should not use invoke_with_request")


@dataclass
class _FakeServices:
    runtime: _TrackingContractRuntime

    @property
    def contract_runtime(self) -> _TrackingContractRuntime:
        return self.runtime


def _response(*, request_id: str, output_text: str) -> ModelResponse:
    return ModelResponse(
        request_id=request_id,
        adapter_id="tracking-adapter",
        provider_name="fake",
        model_name="tracking-model",
        status=ModelInvocationStatus.COMPLETED,
        output_text=output_text,
        output_json=None,
        usage=ModelUsage(input_tokens=1, output_tokens=1, total_tokens=2),
    )


def _generation_request() -> ProposalGenerationRequest:
    scope = Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1")
    return ProposalGenerationRequest(
        objective="Frame bounded options for the current blocker state",
        scope=scope,
        context_package=ContextPackage(
            purpose="proposal support",
            trigger=TriggerInput(trigger_summary="Operator asked for bounded options"),
            scope=scope,
            truth_records=(
                TruthRecord(
                    truth_family="project",
                    scope=Scope(project_id="project-1"),
                    summary="project:project-1 Alpha [active]",
                ),
                TruthRecord(
                    truth_family="work_unit",
                    scope=Scope(project_id="project-1", work_unit_id="wu-1"),
                    summary="work_unit:wu-1 Resolve bounded blocker [in_progress]",
                ),
                TruthRecord(
                    truth_family="run",
                    scope=scope,
                    summary="run:run-1 [active]",
                ),
            ),
            support_inputs=(
                SupportInput(
                    source_family="artifact",
                    scope=scope,
                    source_id="artifact-1",
                    summary="Existing operator note confirms the blocker remains open.",
                ),
                SupportInput(
                    source_family="research",
                    scope=scope,
                    source_id="research-note-1",
                    summary="Earlier research narrowed the issue but did not decide the path.",
                ),
            ),
        ),
        visible_constraints=("Must stay inside current project scope.",),
        research_artifacts=(
            ResearchArtifact(
                question="What does the evidence support?",
                summary="The available evidence supports only a bounded investigation.",
                findings=(
                    ResearchFinding(
                        text="Dependency X remains unresolved.",
                        source_refs=("source-a",),
                    ),
                ),
                inferences=("A stronger action path would overstate current support.",),
                uncertainties=("Whether the dependency can be resolved today is unknown.",),
                recommendation=None,
                source_ids=("source-a",),
            ),
        ),
    )
