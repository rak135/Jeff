from jeff.cognitive.context import ContextPackage
from jeff.cognitive.proposal import (
    ProposalGenerationPromptBundle,
    ProposalGenerationRequest,
    build_proposal_generation_prompt_bundle,
)
from jeff.cognitive.research import ResearchArtifact, ResearchFinding
from jeff.cognitive.types import SupportInput, TriggerInput, TruthRecord
from jeff.core.schemas import Scope


def test_build_proposal_generation_prompt_bundle_renders_canonical_step1_contract() -> None:
    bundle = build_proposal_generation_prompt_bundle(_generation_request())

    assert isinstance(bundle, ProposalGenerationPromptBundle)
    assert bundle.prompt_file == "STEP1_GENERATION.md"
    assert "TASK: bounded proposal generation" in bundle.prompt
    assert "Proposal generates candidate paths, not authority." in bundle.system_instructions
    assert "Direct_action is still only a candidate path under current support." in bundle.system_instructions
    assert "No additional scarcity explanation identified from the provided support." in bundle.prompt
    assert "CANONICAL EXAMPLE 0-OPTION:" in bundle.prompt
    assert "CANONICAL EXAMPLE 1-OPTION:" in bundle.prompt
    assert "Do not output NONE anywhere." in bundle.prompt
    assert "{{OBJECTIVE}}" not in bundle.prompt


def test_generation_request_building_includes_scope_truth_constraints_and_other_support() -> None:
    bundle = build_proposal_generation_prompt_bundle(_generation_request())

    assert bundle.request_id == "proposal-generation:project-1:wu-1:run-1:frame-bounded-options-for-the-current-blocker-state"
    assert "SCOPE:\nproject_id=project-1; work_unit_id=wu-1; run_id=run-1" in bundle.prompt
    assert "TRUTH_SNAPSHOT:\ntruth_record_1|family=project|summary=project:project-1 Alpha [active]" in bundle.prompt
    assert "truth_record_2|family=work_unit|summary=work_unit:wu-1 Resolve bounded blocker [in_progress]" in bundle.prompt
    assert "CURRENT_CONSTRAINTS:\nconstraint_1|text=Must stay inside current project scope." in bundle.prompt
    assert "OTHER_SUPPORT:\nsupport_1|family=artifact|source_id=artifact-1|summary=Existing operator note confirms the blocker remains open." in bundle.prompt


def test_optional_research_support_is_rendered_as_support_only_not_authority() -> None:
    bundle = build_proposal_generation_prompt_bundle(_generation_request())

    assert "RESEARCH_SUPPORT:\ncontext_research_support_1|support_only|source_id=research-note-1|summary=Earlier research narrowed the issue but did not decide the path." in bundle.prompt
    assert "research_artifact_1|support_only|question=What does the evidence support?|summary=The available evidence supports only a bounded investigation." in bundle.prompt
    assert "research_artifact_1_findings|support_only|items=Dependency X remains unresolved." in bundle.prompt
    assert "research_artifact_1_uncertainties|support_only|items=Whether the dependency can be resolved today is unknown." in bundle.prompt
    assert "decision authority" not in bundle.prompt.lower()


def test_generation_bundle_is_local_prompt_surface_not_runtime_model_request() -> None:
    bundle = build_proposal_generation_prompt_bundle(_generation_request())

    assert isinstance(bundle, ProposalGenerationPromptBundle)
    assert not hasattr(bundle, "response_mode")
    assert not hasattr(bundle, "json_schema")


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
