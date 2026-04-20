from jeff.cognitive.context import ContextPackage
from jeff.cognitive.proposal import (
    ProposalGenerationPromptBundle,
    ProposalGenerationRequest,
    build_proposal_input_bundle,
    build_proposal_generation_prompt_bundle,
)
from jeff.cognitive.research import ResearchArtifact, ResearchFinding
from jeff.cognitive.types import SupportInput, TriggerInput, TruthRecord
from jeff.core.schemas import Scope
from jeff.memory import CommittedMemoryRecord, MemorySupportRef


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
    assert "For PROPOSAL_COUNT 1, make SCARCITY_REASON name the specific narrowing factor" in bundle.prompt
    assert "For direct_action, name the concrete bounded target from the objective or support" in bundle.prompt
    assert "{{OBJECTIVE}}" not in bundle.prompt


def test_generation_request_building_includes_scope_truth_constraints_and_other_support() -> None:
    bundle = build_proposal_generation_prompt_bundle(_generation_request())

    assert bundle.request_id == "proposal-generation:project-1:wu-1:run-1:frame-bounded-options-for-the-current-blocker-state"
    assert "SCOPE_FRAME:\nproject_id=project-1; work_unit_id=wu-1; run_id=run-1" in bundle.prompt
    assert "TRUTH_SNAPSHOT:\ntruth_record_1|source=truth_snapshot:1|family=project|summary=project:project-1 Alpha [active]" in bundle.prompt
    assert "truth_record_2|source=truth_snapshot:2|family=work_unit|summary=work_unit:wu-1 Resolve bounded blocker [in_progress]" in bundle.prompt
    assert "GOVERNANCE_RELEVANT_SUPPORT:\ngovernance_support_1|source=visible_constraint:1|family=visible_constraint|summary=Must stay inside current project scope." in bundle.prompt
    assert "OTHER_SUPPORT:\nsupport_1|family=artifact|source_id=artifact-1|summary=Existing operator note confirms the blocker remains open." in bundle.prompt
    assert "EVIDENCE_SUPPORT:" in bundle.prompt
    assert "family=research|source_id=research-note-1|summary=Earlier research narrowed the issue but did not decide the path." in bundle.prompt
    assert "family=research_finding|source_id=NONE|summary=Dependency X remains unresolved." in bundle.prompt


def test_request_frame_and_current_execution_support_are_rendered_from_bundle() -> None:
    bundle = build_proposal_generation_prompt_bundle(
        _generation_request(
            current_execution_support=(
                "The active bounded action family is repo-local pytest validation.",
                "The only current executable direct_action path is the fixed repo-local validation plan.",
            )
        )
    )

    assert "REQUEST_FRAME:\nobjective=Frame bounded options for the current blocker state" in bundle.prompt
    assert "visible_constraint_1=Must stay inside current project scope." in bundle.prompt
    assert "CURRENT_EXECUTION_SUPPORT:\ncurrent_execution_support_1|source=current_execution_support:1|family=execution_support|summary=The active bounded action family is repo-local pytest validation." in bundle.prompt
    assert "current_execution_support_2|source=current_execution_support:2|family=execution_support|summary=The only current executable direct_action path is the fixed repo-local validation plan." in bundle.prompt


def test_proposal_input_bundle_keeps_memory_support_out_of_truth_snapshot() -> None:
    request = _generation_request(include_memory_support=True)
    bundle = request.proposal_input_bundle

    assert bundle is not None
    assert [item.truth_family for item in bundle.truth_snapshot.items] == ["project", "work_unit", "run"]
    assert bundle.current_execution_support.items == ()
    assert all(item.source_family != "memory" for item in bundle.governance_relevant_support.items)
    assert bundle.memory_support.memory_ids == ("memory-1",)
    assert bundle.memory_support.memory_summaries[0].source_family == "memory"


def test_optional_research_support_is_rendered_as_support_only_not_authority() -> None:
    bundle = build_proposal_generation_prompt_bundle(_generation_request())

    assert "RESEARCH_SUPPORT:\ncontext_research_support_1|support_only|source_id=research-note-1|summary=Earlier research narrowed the issue but did not decide the path." in bundle.prompt
    assert "research_artifact_1|support_only|question=What does the evidence support?|summary=The available evidence supports only a bounded investigation." in bundle.prompt
    assert "research_artifact_1_findings|support_only|items=Dependency X remains unresolved." in bundle.prompt
    assert "research_artifact_1_uncertainties|support_only|items=Whether the dependency can be resolved today is unknown." in bundle.prompt
    assert "EVIDENCE_SUPPORT:" in bundle.prompt
    assert "family=research_finding|source_id=NONE|summary=Dependency X remains unresolved." in bundle.prompt
    assert "family=research_uncertainty|source_id=NONE|summary=Whether the dependency can be resolved today is unknown." in bundle.prompt
    assert "decision authority" not in bundle.prompt.lower()


def test_build_proposal_input_bundle_extracts_bounded_governance_evidence_and_memory_support() -> None:
    request = _generation_request(include_memory_support=True)
    bundle = build_proposal_input_bundle(
        objective=request.objective,
        scope=request.scope,
        context_package=request.context_package,
        visible_constraints=request.visible_constraints,
        research_artifacts=request.research_artifacts,
        committed_memory_records=(
            CommittedMemoryRecord(
                memory_id="memory-1",
                memory_type="operational",
                scope=request.scope,
                summary="Prior similar work succeeded when the blocker was isolated first.",
                remembered_points=(
                    "Lesson: isolate the blocker before widening scope.",
                    "Risk: avoid proposing rollout language while the blocker is unresolved.",
                    "Previous run worked once the blocker was verified directly.",
                ),
                why_it_matters="This scope has the same blocker shape.",
                support_quality="strong",
                stability="stable",
                created_at="2026-04-20T00:00:00+00:00",
                updated_at="2026-04-20T00:00:00+00:00",
                support_refs=(
                    MemorySupportRef(
                        ref_kind="artifact",
                        ref_id="artifact-1",
                        summary="Artifact note captured the same blocker pattern.",
                    ),
                ),
            ),
        ),
    )

    assert any(item.source_family == "governance_blocker_signal" for item in bundle.governance_relevant_support.items)
    assert bundle.evidence_support.evidence_summaries[0].source_family in {"research_finding", "research", "archive"}
    assert bundle.evidence_support.uncertainty_summaries[0].summary == "Whether the dependency can be resolved today is unknown."
    assert bundle.memory_support.memory_ids == ("memory-1",)
    assert bundle.memory_support.memory_lessons[0].summary == "Lesson: isolate the blocker before widening scope."
    assert bundle.memory_support.memory_risk_reminders[0].summary.startswith("Risk: avoid proposing rollout language")
    assert bundle.memory_support.memory_precedents[0].summary.startswith("Previous run worked")


def test_generation_bundle_is_local_prompt_surface_not_runtime_model_request() -> None:
    bundle = build_proposal_generation_prompt_bundle(_generation_request())

    assert isinstance(bundle, ProposalGenerationPromptBundle)
    assert not hasattr(bundle, "response_mode")
    assert not hasattr(bundle, "json_schema")


def _generation_request(
    *,
    current_execution_support: tuple[str, ...] = (),
    include_memory_support: bool = False,
) -> ProposalGenerationRequest:
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
            memory_support_inputs=(
                ()
                if not include_memory_support
                else (
                    SupportInput(
                        source_family="memory",
                        scope=scope,
                        source_id="memory-1",
                        summary="A prior similar investigation was eventually resolved by isolating the blocker first.",
                    ),
                )
            ),
        ),
        visible_constraints=("Must stay inside current project scope.",),
        current_execution_support=current_execution_support,
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
