import json
from pathlib import Path

from jeff.cognitive.post_selection.action_formation import ActionFormationRequest, form_action_from_materialized_proposal
from jeff.cognitive.post_selection.action_resolution import SelectionActionResolutionRequest, resolve_selection_action_basis
from jeff.cognitive.post_selection.effective_proposal import SelectionEffectiveProposalRequest, materialize_effective_proposal
from jeff.cognitive.post_selection.governance_handoff import ActionGovernanceHandoffRequest, handoff_action_to_governance
from jeff.cognitive.proposal import ProposalResult, ProposalResultOption
from jeff.cognitive.selection import SelectionResult
from jeff.core.schemas import Scope
from jeff.governance import Approval, CurrentTruthSnapshot, Policy
from jeff.interface import InterfaceContext, JeffCLI
from jeff.interface.commands import SelectionReviewRecord
from jeff.knowledge import KnowledgeStore, create_source_digest_from_research_record, create_topic_note, save_knowledge_artifact
from jeff.memory import InMemoryMemoryStore, MemorySupportRef, create_memory_candidate, write_memory_candidate
from jeff.cognitive.research import ResearchArtifactRecord, ResearchFinding
from jeff.cognitive.research.archive import ResearchArchiveStore, create_research_brief, save_archive_artifact

from tests.fixtures.cli import build_flow_run, build_state_with_runs


def test_inspect_live_context_surfaces_truth_first_and_lawful_governance_support(tmp_path: Path) -> None:
    cli = _build_cli_with_live_context_support(
        tmp_path,
        objective="What bounded rollout follow-up is justified right now?",
        include_governance=True,
    )

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    text = cli.run_one_shot("/inspect")
    payload = json.loads(cli.run_one_shot("/inspect", json_output=True))

    assert "[truth] project_id=project-1 work_unit_id=wu-1" in text
    assert "[support][live_context] purpose=operator explanation proposal support What bounded rollout follow-up is justified right now?" in text
    assert "[support][live_context] truth_families=project,work_unit,run,governance_blocker,governance_constraint,governance_approval_dependency,governance_readiness" in text
    assert payload["truth"] == {
        "project_id": "project-1",
        "project_lifecycle_state": "active",
        "work_unit_id": "wu-1",
        "work_unit_lifecycle_state": "open",
        "run_id": "run-1",
        "run_lifecycle_state": "created",
    }
    assert "live_context" not in payload["truth"]
    assert payload["support"]["live_context"]["truth_families"][:3] == ["project", "work_unit", "run"]
    assert payload["support"]["live_context"]["governance_truth_count"] == 4
    assert payload["support"]["proposal_summary"]["available"] is True


def test_inspect_live_context_keeps_memory_ahead_of_compiled_knowledge_without_cross_project_leak(
    tmp_path: Path,
) -> None:
    cli = _build_cli_with_live_context_support(
        tmp_path,
        objective="What bounded rollout follow-up is justified right now?",
        include_governance=True,
    )

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    payload = json.loads(cli.run_one_shot("/inspect", json_output=True))

    live_context = payload["support"]["live_context"]

    assert live_context["memory_support_count"] == 1
    assert live_context["compiled_knowledge_support_count"] == 1
    assert live_context["archive_support_count"] == 0
    assert live_context["ordered_support_source_families"][:2] == ["memory", "compiled_knowledge"]


def test_inspect_live_context_excludes_compiled_knowledge_when_current_state_is_requested(tmp_path: Path) -> None:
    cli = _build_cli_with_live_context_support(
        tmp_path,
        objective="What current state follow-up is justified right now?",
        include_governance=False,
    )

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    payload = json.loads(cli.run_one_shot("/inspect", json_output=True))

    live_context = payload["support"]["live_context"]

    assert live_context["governance_truth_count"] == 0
    assert live_context["memory_support_count"] == 1
    assert live_context["compiled_knowledge_support_count"] == 0
    assert live_context["archive_support_count"] == 0
    assert live_context["ordered_support_source_families"] == ["memory"]


def test_inspect_live_context_includes_archive_when_direct_evidence_is_requested(tmp_path: Path) -> None:
    cli = _build_cli_with_live_context_support(
        tmp_path,
        objective="What direct evidence follow-up is justified right now?",
        include_governance=True,
    )

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    payload = json.loads(cli.run_one_shot("/inspect", json_output=True))

    live_context = payload["support"]["live_context"]

    assert live_context["memory_support_count"] == 1
    assert live_context["compiled_knowledge_support_count"] == 1
    assert live_context["archive_support_count"] == 2
    assert live_context["ordered_support_source_families"][:3] == ["memory", "compiled_knowledge", "archive"]


def _build_cli_with_live_context_support(
    tmp_path: Path,
    *,
    objective: str,
    include_governance: bool,
) -> JeffCLI:
    state, scope = build_state_with_runs(objective=objective)
    flow_run = build_flow_run(scope, current_stage="execution", lifecycle_state="active")
    memory_store = InMemoryMemoryStore()
    knowledge_store = KnowledgeStore(tmp_path / "knowledge")
    archive_store = ResearchArchiveStore(tmp_path / "archive")

    _seed_memory_support(memory_store)
    _seed_compiled_knowledge(knowledge_store, objective=objective)
    _seed_archive_support(archive_store)

    selection_reviews = {}
    if include_governance:
        selection_reviews[str(scope.run_id)] = _selection_review_record(scope)

    return JeffCLI(
        context=InterfaceContext(
            state=state,
            flow_runs={str(scope.run_id): flow_run},
            selection_reviews=selection_reviews,
            memory_store=memory_store,
            knowledge_store=knowledge_store,
            research_archive_store=archive_store,
        )
    )


def _seed_memory_support(memory_store: InMemoryMemoryStore) -> None:
    write_memory_candidate(
        candidate=create_memory_candidate(
            candidate_id="candidate-1",
            memory_type="semantic",
            scope=Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1"),
            summary="The prior operator explanation kept the rollout bounded.",
            remembered_points=("Memory support stays ahead of compiled knowledge in live context.",),
            why_it_matters="This continuity signal is still relevant for the current inspect path.",
            support_refs=(
                MemorySupportRef(ref_kind="research", ref_id="research-record-1", summary="Grounded in project support."),
            ),
            support_quality="strong",
            stability="stable",
        ),
        store=memory_store,
    )
    write_memory_candidate(
        candidate=create_memory_candidate(
            candidate_id="candidate-foreign",
            memory_type="semantic",
            scope=Scope(project_id="project-2", work_unit_id="wu-x", run_id="run-x"),
            summary="Foreign-project memory must not leak into inspect.",
            remembered_points=("This must stay isolated.",),
            why_it_matters="Cross-project isolation is binding.",
            support_refs=(
                MemorySupportRef(
                    ref_kind="research",
                    ref_id="foreign-research-record",
                    summary="Foreign project support.",
                ),
            ),
            support_quality="strong",
            stability="stable",
        ),
        store=memory_store,
    )


def _seed_compiled_knowledge(knowledge_store: KnowledgeStore, *, objective: str) -> None:
    valid_digest = create_source_digest_from_research_record(_research_record(project_id="project-1"))
    valid_digest_b = create_source_digest_from_research_record(_research_record(project_id="project-1", suffix="b"))
    foreign_digest = create_source_digest_from_research_record(_research_record(project_id="project-2"))
    foreign_digest_b = create_source_digest_from_research_record(_research_record(project_id="project-2", suffix="b"))
    save_knowledge_artifact(valid_digest, store=knowledge_store)
    save_knowledge_artifact(valid_digest_b, store=knowledge_store)
    save_knowledge_artifact(foreign_digest, store=knowledge_store)
    save_knowledge_artifact(foreign_digest_b, store=knowledge_store)
    save_knowledge_artifact(
        create_topic_note(
            topic=objective,
            supports=(valid_digest, valid_digest_b),
            major_supported_points=("Compiled knowledge remains support-only in inspect.",),
            topic_framing=f"{objective} project-scoped compiled support.",
        ),
        store=knowledge_store,
    )
    save_knowledge_artifact(
        create_topic_note(
            topic=objective,
            supports=(foreign_digest, foreign_digest_b),
            major_supported_points=("This note must stay out of project-1 inspect.",),
            topic_framing=f"{objective} foreign project note.",
        ),
        store=knowledge_store,
    )


def _seed_archive_support(archive_store: ResearchArchiveStore) -> None:
    valid_a = create_research_brief(
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        title="Evidence brief A",
        summary="Direct evidence remains available for project-1.",
        question_or_objective="What direct evidence still matters?",
        findings=("Project-1 evidence remains inspectable.",),
        inference=("Archive support remains support-only.",),
        uncertainty=("Evidence may need refresh.",),
        source_refs=("source-1",),
    )
    valid_b = create_research_brief(
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        title="Evidence brief B",
        summary="A second direct evidence item remains available for project-1.",
        question_or_objective="What direct evidence still matters?",
        findings=("A second project-1 evidence item remains inspectable.",),
        inference=("Archive ordering remains after memory and compiled knowledge.",),
        uncertainty=("Evidence may still need confirmation.",),
        source_refs=("source-2",),
    )
    foreign = create_research_brief(
        project_id="project-2",
        work_unit_id="wu-x",
        run_id="run-x",
        title="Foreign evidence brief",
        summary="Foreign direct evidence must not leak.",
        question_or_objective="Foreign evidence only.",
        findings=("This must stay isolated.",),
        inference=("Cross-project archive isolation is binding.",),
        uncertainty=("Foreign uncertainty.",),
        source_refs=("source-x",),
    )
    save_archive_artifact(valid_a, store=archive_store)
    save_archive_artifact(valid_b, store=archive_store)
    save_archive_artifact(foreign, store=archive_store)


def _research_record(*, project_id: str, suffix: str = "a") -> ResearchArtifactRecord:
    work_unit_id = "wu-1" if project_id == "project-1" else "wu-x"
    run_id = "run-1" if project_id == "project-1" else "run-x"
    return ResearchArtifactRecord(
        artifact_id=f"research-record-{project_id}-{suffix}",
        project_id=project_id,
        work_unit_id=work_unit_id,
        run_id=run_id,
        question="What topic support should inspect surface?",
        source_mode="prepared_evidence",
        summary="The live inspect helper should reuse the same truth-first context assembler.",
        findings=(ResearchFinding(text="A bounded topic summary remains useful.", source_refs=("source-1",)),),
        inferences=("Compiled knowledge remains support-only.",),
        uncertainties=("Freshness should stay visible.",),
        recommendation=None,
        source_ids=("source-1",),
        source_items=(),
        evidence_items=(),
        created_at="2026-04-19T10:00:00+00:00",
    )


def _selection_review_record(scope: Scope) -> SelectionReviewRecord:
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