import json
from pathlib import Path

import jeff.interface.commands as commands_module

from jeff.cognitive.research import ResearchArtifactRecord, ResearchFinding
from jeff.cognitive import ResearchArtifactStore
from jeff.cognitive.post_selection.action_formation import ActionFormationRequest, form_action_from_materialized_proposal
from jeff.cognitive.post_selection.action_resolution import SelectionActionResolutionRequest, resolve_selection_action_basis
from jeff.cognitive.post_selection.effective_proposal import SelectionEffectiveProposalRequest, materialize_effective_proposal
from jeff.cognitive.post_selection.governance_handoff import ActionGovernanceHandoffRequest, handoff_action_to_governance
from jeff.cognitive.research.archive import ResearchArchiveStore, create_research_brief, save_archive_artifact
from jeff.cognitive.proposal import ProposalResult, ProposalResultOption
from jeff.cognitive.selection import SelectionResult
from jeff.core.schemas import Scope
from jeff.governance import Approval, CurrentTruthSnapshot, Policy
from jeff.interface import InterfaceContext, JeffCLI
from jeff.interface.commands import SelectionReviewRecord
from jeff.knowledge import (
    KnowledgeStore,
    create_source_digest_from_research_record,
    create_topic_note,
    save_knowledge_artifact,
)
from jeff.memory import InMemoryMemoryStore, MemorySupportRef, create_memory_candidate, write_memory_candidate
from jeff.infrastructure import (
    AdapterFactoryConfig,
    AdapterProviderKind,
    ModelAdapterRuntimeConfig,
    PurposeOverrides,
    build_infrastructure_services,
)

from tests.fixtures.cli import build_state_with_runs


def test_research_command_assembles_live_context_and_runs_real_proposal_followup(
    tmp_path: Path,
    monkeypatch,
) -> None:
    question = "What bounded rollout follow-up is justified right now?"
    cli, document = _build_cli_with_live_followup_support(tmp_path, question=question)
    call_count = {"value": 0}
    original = commands_module.assemble_live_context_package

    def _counting_live_context(**kwargs):
        call_count["value"] += 1
        return original(**kwargs)

    monkeypatch.setattr(commands_module, "assemble_live_context_package", _counting_live_context)

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    result = cli.execute(f'/research docs "{question}" "{document}"')
    text = result.text
    assert result.json_payload is not None
    payload = result.json_payload

    assert call_count["value"] == 1
    assert "[support] live_context" in text
    assert "[support] proposal_followup" in text
    assert "proposal_followup=ran serious_option_count=1" in text
    assert "governance_truth_count=4" in text
    assert payload["truth"] == {"project_id": "project-1", "work_unit_id": "wu-1", "run_id": "run-1"}
    assert "live_context" not in payload["truth"]
    assert payload["support"]["live_context"]["truth_families"] == [
        "project",
        "work_unit",
        "run",
        "governance_blocker",
        "governance_constraint",
        "governance_approval_dependency",
        "governance_readiness",
    ]
    assert payload["support"]["live_context"]["governance_truth_count"] == 4
    assert payload["support"]["proposal_followup"]["proposal_generation_ran"] is True
    assert payload["support"]["proposal_followup"]["proposal_count"] == 1


def test_research_command_live_context_keeps_memory_ahead_of_compiled_knowledge(tmp_path: Path) -> None:
    question = "What bounded rollout follow-up is justified right now?"
    cli, document = _build_cli_with_live_followup_support(tmp_path, question=question)

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    payload = json.loads(cli.run_one_shot(f'/research docs "{question}" "{document}"', json_output=True))

    live_context = payload["support"]["live_context"]

    assert live_context["memory_support_count"] == 1
    assert live_context["compiled_knowledge_support_count"] == 1
    assert live_context["archive_support_count"] == 0
    assert live_context["ordered_support_source_families"][:2] == ["memory", "compiled_knowledge"]


def test_research_command_live_context_excludes_compiled_knowledge_when_current_state_is_requested(
    tmp_path: Path,
) -> None:
    question = "What current state follow-up is justified right now?"
    cli, document = _build_cli_with_live_followup_support(tmp_path, question=question)

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    payload = json.loads(cli.run_one_shot(f'/research docs "{question}" "{document}"', json_output=True))

    live_context = payload["support"]["live_context"]

    assert live_context["memory_support_count"] == 1
    assert live_context["compiled_knowledge_support_count"] == 0
    assert live_context["archive_support_count"] == 0
    assert live_context["ordered_support_source_families"] == ["memory"]
    assert payload["support"]["proposal_followup"]["proposal_generation_ran"] is True


def test_research_command_live_context_includes_archive_for_direct_evidence_without_cross_project_leak(
    tmp_path: Path,
) -> None:
    question = "What direct evidence follow-up is justified right now?"
    cli, document = _build_cli_with_live_followup_support(tmp_path, question=question)

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    payload = json.loads(cli.run_one_shot(f'/research docs "{question}" "{document}"', json_output=True))

    live_context = payload["support"]["live_context"]

    assert live_context["memory_support_count"] == 1
    assert live_context["compiled_knowledge_support_count"] == 1
    assert live_context["archive_support_count"] == 2
    assert live_context["ordered_support_source_families"][:3] == ["memory", "compiled_knowledge", "archive"]
    assert payload["support"]["proposal_followup"]["proposal_generation_ran"] is True


def _build_cli_with_live_followup_support(tmp_path: Path, *, question: str) -> tuple[JeffCLI, Path]:
    state, _ = build_state_with_runs(run_specs=())
    document = tmp_path / "plan.md"
    document.parent.mkdir(parents=True, exist_ok=True)
    document.write_text(
        "The bounded rollout should stay project-scoped.\n"
        "The current state still uses the bounded rollout path.\n"
        "Direct evidence remains available when the operator asks for it.\n",
        encoding="utf-8",
    )

    memory_store = InMemoryMemoryStore()
    knowledge_store = KnowledgeStore(tmp_path / "knowledge")
    archive_store = ResearchArchiveStore(tmp_path / "archive")

    _seed_memory_support(memory_store)
    _seed_archive_support(archive_store)
    _seed_compiled_knowledge(knowledge_store)

    return (
        JeffCLI(
            context=InterfaceContext(
                state=state,
                infrastructure_services=_infrastructure_services(),
                research_artifact_store=ResearchArtifactStore(tmp_path / "research_artifacts"),
                research_archive_store=archive_store,
                knowledge_store=knowledge_store,
                memory_store=memory_store,
                selection_reviews={"run-1": _selection_review_record()},
            )
        ),
        document,
    )


def _selection_review_record() -> SelectionReviewRecord:
    scope = Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1")
    proposal_result = ProposalResult(
        request_id="proposal-request-1",
        scope=scope,
        options=(
            ProposalResultOption(
                option_index=1,
                proposal_id="proposal-1",
                proposal_type="direct_action",
                title="Advance the bounded rollout",
                why_now="The bounded path remains the active next step.",
                summary="Advance the bounded rollout now.",
            ),
        ),
        scarcity_reason="Only one serious bounded option is currently justified.",
    )
    selection_result = SelectionResult(
        selection_id="selection-1",
        considered_proposal_ids=("proposal-1",),
        selected_proposal_id="proposal-1",
        rationale="The bounded rollout remains the current choice.",
    )
    resolved_basis = resolve_selection_action_basis(
        SelectionActionResolutionRequest(
            request_id="selection-resolution-1",
            selection_result=selection_result,
            operator_override=None,
        )
    )
    materialized = materialize_effective_proposal(
        SelectionEffectiveProposalRequest(
            request_id="selection-materialization-1",
            proposal_result=proposal_result,
            resolved_basis=resolved_basis,
        )
    )
    formed_action = form_action_from_materialized_proposal(
        ActionFormationRequest(
            request_id="selection-action-formation-1",
            materialized_effective_proposal=materialized,
            scope=scope,
            basis_state_version=3,
        )
    )
    truth = CurrentTruthSnapshot(
        scope=scope,
        state_version=3,
        blocked_reasons=("approval review is still blocking start",),
        requires_revalidation=True,
        target_available=False,
    )
    governance_handoff = handoff_action_to_governance(
        ActionGovernanceHandoffRequest(
            request_id="selection-governance-handoff-1",
            formed_action_result=formed_action,
            policy=Policy(approval_required=True),
            approval=Approval.absent(),
            truth=truth,
        )
    )
    return SelectionReviewRecord(
        selection_result=selection_result,
        resolved_basis=resolved_basis,
        materialized_effective_proposal=materialized,
        formed_action_result=formed_action,
        governance_handoff_result=governance_handoff,
        proposal_result=proposal_result,
        action_scope=scope,
        basis_state_version=3,
        governance_policy=Policy(approval_required=True),
        governance_approval=Approval.absent(),
        governance_truth=truth,
    )


def _seed_memory_support(memory_store: InMemoryMemoryStore) -> None:
    current_scope = Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1")
    other_scope = Scope(project_id="project-2", work_unit_id="wu-9", run_id="run-9")

    write_memory_candidate(
        candidate=create_memory_candidate(
            candidate_id="candidate-current",
            memory_type="semantic",
            scope=current_scope,
            summary="Bounded rollout support is already known to stay project-scoped.",
            remembered_points=("Memory support should enter proposal context before compiled knowledge.",),
            why_it_matters="This continuity matters for the next bounded proposal follow-up.",
            support_refs=(
                MemorySupportRef(ref_kind="research", ref_id="research-current", summary="Current-project research."),
            ),
            support_quality="strong",
            stability="stable",
        ),
        store=memory_store,
    )
    write_memory_candidate(
        candidate=create_memory_candidate(
            candidate_id="candidate-other",
            memory_type="semantic",
            scope=other_scope,
            summary="Other project support must never bleed into project-1 context.",
            remembered_points=("This should stay invisible to project-1 retrieval.",),
            why_it_matters="Cross-project memory bleed is forbidden.",
            support_refs=(
                MemorySupportRef(ref_kind="research", ref_id="research-other", summary="Other-project research."),
            ),
            support_quality="strong",
            stability="stable",
        ),
        store=memory_store,
    )


def _seed_archive_support(archive_store: ResearchArchiveStore) -> None:
    current_artifact = create_research_brief(
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        title="Direct evidence brief",
        summary="Direct evidence remains available for the bounded rollout.",
        question_or_objective="What direct evidence still matters for the bounded rollout?",
        findings=("One direct brief remains inspectable for project-1.",),
        inference=("Direct evidence should remain separate from thematic support.",),
        uncertainty=("The direct evidence may need refresh later.",),
        source_refs=("source-1",),
    )
    other_artifact = create_research_brief(
        project_id="project-2",
        work_unit_id="wu-9",
        run_id="run-9",
        title="Other project evidence brief",
        summary="This evidence belongs to another project.",
        question_or_objective="What direct evidence matters elsewhere?",
        findings=("Other-project evidence must not leak.",),
        inference=("Isolation remains hard.",),
        uncertainty=("None.",),
        source_refs=("source-9",),
    )
    save_archive_artifact(current_artifact, store=archive_store)
    save_archive_artifact(other_artifact, store=archive_store)


def _seed_compiled_knowledge(knowledge_store: KnowledgeStore) -> None:
    current_record_a = ResearchArtifactRecord(
        artifact_id="research-record-current-a",
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        question="What bounded rollout follow-up is justified right now?",
        source_mode="prepared_evidence",
        summary="Current-project thematic support remains available.",
        findings=(ResearchFinding(text="A bounded rollout remains the stable next move.", source_refs=("source-1",)),),
        inferences=("Compiled knowledge stays support-only.",),
        uncertainties=("Freshness should stay visible.",),
        recommendation=None,
        source_ids=("source-1",),
        source_items=(),
        evidence_items=(),
        created_at="2026-04-19T10:00:00+00:00",
    )
    current_record_b = ResearchArtifactRecord(
        artifact_id="research-record-current-b",
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        question="What bounded rollout support remains reusable?",
        source_mode="prepared_evidence",
        summary="A second current-project support source backs the topic note.",
        findings=(ResearchFinding(text="Project-1 has a second bounded support source.", source_refs=("source-2",)),),
        inferences=("Multiple current-project supports remain available.",),
        uncertainties=("None.",),
        recommendation=None,
        source_ids=("source-2",),
        source_items=(),
        evidence_items=(),
        created_at="2026-04-19T10:00:00+00:00",
    )
    other_record_a = ResearchArtifactRecord(
        artifact_id="research-record-other-a",
        project_id="project-2",
        work_unit_id="wu-9",
        run_id="run-9",
        question="What support belongs to another project?",
        source_mode="prepared_evidence",
        summary="Other-project thematic support must stay isolated.",
        findings=(ResearchFinding(text="This topic note must not bleed into project-1.", source_refs=("source-9",)),),
        inferences=("Isolation remains hard.",),
        uncertainties=("None.",),
        recommendation=None,
        source_ids=("source-9",),
        source_items=(),
        evidence_items=(),
        created_at="2026-04-19T10:00:01+00:00",
    )
    other_record_b = ResearchArtifactRecord(
        artifact_id="research-record-other-b",
        project_id="project-2",
        work_unit_id="wu-9",
        run_id="run-9",
        question="What additional support belongs elsewhere?",
        source_mode="prepared_evidence",
        summary="A second other-project support source must also stay isolated.",
        findings=(ResearchFinding(text="Other-project support must remain invisible here.", source_refs=("source-10",)),),
        inferences=("Isolation remains hard.",),
        uncertainties=("None.",),
        recommendation=None,
        source_ids=("source-10",),
        source_items=(),
        evidence_items=(),
        created_at="2026-04-19T10:00:01+00:00",
    )

    current_digest_a = create_source_digest_from_research_record(current_record_a)
    current_digest_b = create_source_digest_from_research_record(current_record_b)
    other_digest_a = create_source_digest_from_research_record(other_record_a)
    other_digest_b = create_source_digest_from_research_record(other_record_b)
    save_knowledge_artifact(current_digest_a, store=knowledge_store)
    save_knowledge_artifact(current_digest_b, store=knowledge_store)
    save_knowledge_artifact(other_digest_a, store=knowledge_store)
    save_knowledge_artifact(other_digest_b, store=knowledge_store)
    save_knowledge_artifact(
        create_topic_note(
            topic="What bounded rollout follow-up is justified right now?",
            supports=(current_digest_a, current_digest_b),
            major_supported_points=("Compiled knowledge can support the bounded rollout follow-up.",),
            topic_framing="What bounded rollout follow-up is justified right now? Current-project thematic support.",
        ),
        store=knowledge_store,
    )
    save_knowledge_artifact(
        create_topic_note(
            topic="other project thematic support",
            supports=(other_digest_a, other_digest_b),
            major_supported_points=("This note must stay outside project-1 retrieval.",),
            topic_framing="Other-project thematic support.",
        ),
        store=knowledge_store,
    )


def _infrastructure_services():
    return build_infrastructure_services(
        ModelAdapterRuntimeConfig(
            default_adapter_id="fake-research",
            adapters=(
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id="fake-research",
                    model_name="research-model",
                    fake_text_response=_research_generation_text(),
                ),
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id="fake-proposal",
                    model_name="proposal-model",
                    fake_text_response=_proposal_generation_text(),
                ),
            ),
            purpose_overrides=PurposeOverrides(proposal="fake-proposal"),
        )
    )


def _proposal_generation_text() -> str:
    return (
        "PROPOSAL_COUNT: 1\n"
        "SCARCITY_REASON: Only one serious bounded option is currently grounded.\n"
        "OPTION_1_TYPE: clarify\n"
        "OPTION_1_TITLE: Clarify the bounded rollout constraint\n"
        "OPTION_1_SUMMARY: Ask one bounded clarifying question before any later downstream review step.\n"
        "OPTION_1_WHY_NOW: Current research narrows the path but preserves one decisive uncertainty.\n"
        "OPTION_1_ASSUMPTIONS: The current rollout constraint can be clarified quickly\n"
        "OPTION_1_RISKS: Clarification may confirm there is still no stronger path\n"
        "OPTION_1_CONSTRAINTS: Stay inside the current project scope\n"
        "OPTION_1_BLOCKERS: Further downstream review remains outside this proposal slice\n"
        "OPTION_1_PLANNING_NEEDED: no\n"
        "OPTION_1_FEASIBILITY: Feasible with one bounded follow-up check\n"
        "OPTION_1_REVERSIBILITY: Fully reversible\n"
        "OPTION_1_SUPPORT_REFS: source-1\n"
    )


def _research_generation_text() -> str:
    return (
        "SUMMARY:\n"
        "The documents support a bounded rollout follow-up.\n\n"
        "FINDINGS:\n"
        "- text: A bounded rollout follow-up is the stable next move.\n"
        "  cites: S1\n\n"
        "INFERENCES:\n"
        "- Proposal follow-up should stay support-only and bounded.\n\n"
        "UNCERTAINTIES:\n"
        "- Whether one small rollout constraint still needs explicit operator clarification.\n\n"
        "RECOMMENDATION:\n"
        "Generate bounded follow-up proposals before any later selection.\n"
    )