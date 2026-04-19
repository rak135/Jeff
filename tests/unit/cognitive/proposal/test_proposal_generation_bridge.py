from jeff.cognitive import (
    ContextPackage,
    ProposalGenerationBridgeError,
    ProposalGenerationBridgeRequest,
    ProposalResult,
    ResearchArtifact,
    ResearchFinding,
    build_and_run_proposal_generation,
)
from jeff.cognitive.post_selection import (
    ResearchDecisionSupportRequest,
    ResearchOutputSufficiencyResult,
    ResearchProposalConsumerRequest,
    build_research_decision_support_handoff,
    consume_research_for_proposal_support,
)
from jeff.cognitive.proposal import ProposalSupportConsumerRequest, consume_proposal_support_package
from jeff.cognitive.types import SupportInput, TriggerInput, TruthRecord
from jeff.core.schemas import Scope
from jeff.infrastructure import (
    AdapterFactoryConfig,
    AdapterProviderKind,
    ModelAdapterRuntimeConfig,
    PurposeOverrides,
    build_infrastructure_services,
)


def test_lawful_proposal_input_package_builds_request_and_runs_generation() -> None:
    request = ProposalGenerationBridgeRequest(
        request_id="proposal-generation-bridge-1",
        proposal_input_package=_proposal_input_package(),
        context_package=_context_package(),
        research_artifact=_research_artifact(),
        infrastructure_services=_infrastructure_services(_one_option_output_text()),
        bounded_objective="Frame bounded follow-up options from the preserved research",
        visible_constraints=("Stay inside the current project scope.",),
    )

    result = build_and_run_proposal_generation(request)

    assert result.proposal_request_built is True
    assert result.proposal_generation_ran is True
    assert result.proposal_generation_request is not None
    assert result.proposal_generation_request.objective == "Frame bounded follow-up options from the preserved research"
    assert result.proposal_generation_request.visible_constraints == ("Stay inside the current project scope.",)
    assert result.proposal_pipeline_result is not None
    assert result.proposal_result is not None
    assert isinstance(result.proposal_result, ProposalResult)
    assert result.proposal_count == 1
    assert result.proposal_result.options[0].proposal_type == "clarify"
    assert "proposal-only" in result.summary


def test_not_ready_proposal_input_package_refuses_to_run_generation() -> None:
    proposal_input_package = _proposal_input_package()
    object.__setattr__(proposal_input_package, "proposal_input_ready", False)

    try:
        build_and_run_proposal_generation(
            ProposalGenerationBridgeRequest(
                request_id="proposal-generation-bridge-2",
                proposal_input_package=proposal_input_package,
                context_package=_context_package(),
                research_artifact=_research_artifact(),
                infrastructure_services=_infrastructure_services(_one_option_output_text()),
            )
        )
        raise AssertionError("expected ProposalGenerationBridgeError")
    except ProposalGenerationBridgeError as exc:
        assert tuple(issue.code for issue in exc.issues) == ("proposal_input_not_ready",)


def test_missing_or_malformed_proposal_input_package_fails_closed() -> None:
    try:
        build_and_run_proposal_generation(
            ProposalGenerationBridgeRequest(
                request_id="proposal-generation-bridge-3",
                proposal_input_package=None,
                context_package=_context_package(),
                research_artifact=_research_artifact(),
                infrastructure_services=_infrastructure_services(_one_option_output_text()),
            )
        )
        raise AssertionError("expected ProposalGenerationBridgeError")
    except ProposalGenerationBridgeError as exc:
        assert tuple(issue.code for issue in exc.issues) == ("missing_proposal_input_package",)


def test_blank_request_id_raises_typed_error() -> None:
    try:
        build_and_run_proposal_generation(
            ProposalGenerationBridgeRequest(
                request_id="   ",
                proposal_input_package=_proposal_input_package(),
                context_package=_context_package(),
                research_artifact=_research_artifact(),
                infrastructure_services=_infrastructure_services(_one_option_output_text()),
            )
        )
        raise AssertionError("expected ProposalGenerationBridgeError")
    except ProposalGenerationBridgeError as exc:
        assert tuple(issue.code for issue in exc.issues) == ("invalid_request_id",)


def test_missing_required_additional_generation_inputs_returns_truthful_non_generation_result() -> None:
    result = build_and_run_proposal_generation(
        ProposalGenerationBridgeRequest(
            request_id="proposal-generation-bridge-4",
            proposal_input_package=_proposal_input_package(),
            context_package=_context_package(),
            research_artifact=_research_artifact(),
            infrastructure_services=None,
        )
    )

    assert result.proposal_request_built is False
    assert result.proposal_generation_ran is False
    assert result.proposal_result is None
    assert result.no_generation_reason == "proposal generation requires InfrastructureServices and no runtime services were provided"
    assert "proposal-input package remains the truthful boundary" in result.summary


def test_proposal_output_is_preserved_in_bounded_inspectable_non_selection_form() -> None:
    result = build_and_run_proposal_generation(
        ProposalGenerationBridgeRequest(
            request_id="proposal-generation-bridge-5",
            proposal_input_package=_proposal_input_package(),
            context_package=_context_package(),
            research_artifact=_research_artifact(),
            infrastructure_services=_infrastructure_services(_one_option_output_text()),
        )
    )

    assert result.proposal_generation_request is not None
    assert any(
        support_input.source_id == "proposal-input:proposal-input-1:recommendation-candidate:1"
        for support_input in result.proposal_generation_request.context_package.support_inputs
    )
    assert result.proposal_result is not None
    assert result.proposal_result.proposal_count == 1
    assert not hasattr(result.proposal_result, "selected_proposal_id")
    assert result.proposal_result.options[0].proposal_id == "proposal-1"


def test_zero_option_proposal_output_remains_lawful_when_generation_returns_honest_scarcity() -> None:
    result = build_and_run_proposal_generation(
        ProposalGenerationBridgeRequest(
            request_id="proposal-generation-bridge-6",
            proposal_input_package=_proposal_input_package(),
            context_package=_context_package(),
            research_artifact=_research_artifact(),
            infrastructure_services=_infrastructure_services(
                "PROPOSAL_COUNT: 0\nSCARCITY_REASON: No honest serious option is currently supported by the bounded research."
            ),
        )
    )

    assert result.proposal_result is not None
    assert result.proposal_result.proposal_count == 0
    assert result.proposal_count == 0
    assert result.proposal_result.scarcity_reason == "No honest serious option is currently supported by the bounded research."


def _proposal_input_package():
    decision_support_handoff = build_research_decision_support_handoff(
        ResearchDecisionSupportRequest(
            request_id="research-decision-support-1",
            research_artifact=_research_artifact(),
            research_sufficiency_result=_research_sufficiency_result(),
        )
    )
    proposal_support_package = consume_research_for_proposal_support(
        ResearchProposalConsumerRequest(
            request_id="research-proposal-support-1",
            research_decision_support_handoff=decision_support_handoff,
        )
    )
    return consume_proposal_support_package(
        ProposalSupportConsumerRequest(
            request_id="proposal-input-1",
            proposal_support_package=proposal_support_package,
        )
    )


def _research_artifact() -> ResearchArtifact:
    return ResearchArtifact(
        question="What bounded follow-up proposal framing is justified by the current research?",
        summary="The current research narrows the bounded comparison without granting authority.",
        findings=(
            ResearchFinding(
                text="A narrow follow-up check can reduce the current uncertainty.",
                source_refs=("source-1",),
            ),
        ),
        inferences=("Research remains support-only in this flow.",),
        uncertainties=("whether the current export tier still allows the bounded batch path",),
        recommendation="Compare the bounded follow-up options before any later explicit selection step.",
        source_ids=("source-1",),
    )


def _research_sufficiency_result() -> ResearchOutputSufficiencyResult:
    return ResearchOutputSufficiencyResult(
        evaluation_id="research-output-sufficiency-1",
        sufficient_for_downstream_use=True,
        downstream_target="decision_support_ready",
        key_supported_points=("A narrow follow-up check can reduce the current uncertainty.",),
        unresolved_items=(),
        contradictions_present=False,
        insufficiency_reason=None,
        summary="Research is sufficient for bounded downstream decision support.",
    )


def _context_package() -> ContextPackage:
    scope = _scope()
    return ContextPackage(
        purpose="proposal support",
        trigger=TriggerInput(trigger_summary="Frame bounded follow-up options from the preserved research"),
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
                summary="work_unit:wu-1 Compare bounded export follow-up paths [in_progress]",
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
                summary="Operator note says the next move must remain bounded and non-authorizing.",
            ),
        ),
    )


def _infrastructure_services(fake_text_response: str):
    return build_infrastructure_services(
        ModelAdapterRuntimeConfig(
            default_adapter_id="fake-default",
            adapters=(
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id="fake-default",
                    model_name="default-model",
                    fake_text_response="wrong adapter",
                ),
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id="fake-proposal",
                    model_name="proposal-model",
                    fake_text_response=fake_text_response,
                ),
            ),
            purpose_overrides=PurposeOverrides(proposal="fake-proposal"),
        )
    )


def _one_option_output_text() -> str:
    return (
        "PROPOSAL_COUNT: 1\n"
        "SCARCITY_REASON: Only one serious bounded option is currently grounded.\n"
        "OPTION_1_TYPE: clarify\n"
        "OPTION_1_TITLE: Clarify the current export constraint\n"
        "OPTION_1_SUMMARY: Ask one bounded clarifying question before any later downstream review step.\n"
        "OPTION_1_WHY_NOW: Current research narrows the path but still preserves one decisive uncertainty.\n"
        "OPTION_1_ASSUMPTIONS: The current export constraint can be clarified quickly\n"
        "OPTION_1_RISKS: Clarification may confirm there is still no stronger path\n"
        "OPTION_1_CONSTRAINTS: Stay inside the current project scope\n"
        "OPTION_1_BLOCKERS: Further downstream review remains outside this proposal slice\n"
        "OPTION_1_PLANNING_NEEDED: no\n"
        "OPTION_1_FEASIBILITY: Feasible with one bounded follow-up check\n"
        "OPTION_1_REVERSIBILITY: Fully reversible\n"
        "OPTION_1_SUPPORT_REFS: artifact-1,source-1\n"
    )


def _scope() -> Scope:
    return Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1")
