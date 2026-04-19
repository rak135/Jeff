from pathlib import Path

import pytest

import jeff.interface.command_scope as command_scope

from jeff.cognitive.research import ResearchArtifactRecord, ResearchFinding
from jeff.core.schemas import Scope
from jeff.governance import Approval, CurrentTruthSnapshot, Policy
from jeff.infrastructure import (
    AdapterFactoryConfig,
    AdapterProviderKind,
    ModelAdapterRuntimeConfig,
    PurposeOverrides,
    build_infrastructure_services,
)
from jeff.interface import InterfaceContext, JeffCLI
from jeff.knowledge import KnowledgeStore, create_source_digest_from_research_record, create_topic_note, save_knowledge_artifact
from jeff.memory import InMemoryMemoryStore, MemorySupportRef, create_memory_candidate, write_memory_candidate
from jeff.cognitive.research.archive import ResearchArchiveStore, create_research_brief, save_archive_artifact

from tests.fixtures.cli import build_state_with_runs


def test_run_objective_launches_real_flow_and_calls_live_context_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cli = _build_cli_with_run_support(tmp_path, objective="What bounded rollout should execute now?")
    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")

    call_count = {"value": 0}
    original = command_scope.assemble_live_context_package

    def _counting_live_context(**kwargs):
        call_count["value"] += 1
        return original(**kwargs)

    monkeypatch.setattr(command_scope, "assemble_live_context_package", _counting_live_context)

    payload = cli.execute('/run "What bounded rollout should execute now?"', json_output=True).json_payload

    assert payload is not None
    assert call_count["value"] == 1
    assert payload["view"] == "run_show"
    assert payload["truth"]["run_id"] == "run-1"
    assert payload["derived"]["flow_visible"] is True
    assert payload["derived"]["flow_family"] == "bounded_proposal_selection_execution"
    assert payload["derived"]["execution_status"] == "completed"
    assert payload["derived"]["evaluation_verdict"] is not None
    assert payload["support"]["live_context"]["truth_families"][:3] == ["project", "work_unit", "run"]
    assert payload["support"]["proposal_summary"]["available"] is True
    assert cli.session.scope.run_id == "run-1"


def test_run_live_context_keeps_memory_ahead_of_compiled_knowledge_and_archive_is_project_scoped(tmp_path: Path) -> None:
    cli = _build_cli_with_run_support(tmp_path, objective="What direct evidence bounded rollout should execute now?")
    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")

    payload = cli.execute('/run "What direct evidence bounded rollout should execute now?"', json_output=True).json_payload
    assert payload is not None
    live_context = payload["support"]["live_context"]

    assert live_context["memory_support_count"] == 1
    assert live_context["compiled_knowledge_support_count"] == 1
    assert live_context["archive_support_count"] == 2
    assert live_context["ordered_support_source_families"][:3] == ["memory", "compiled_knowledge", "archive"]


def test_run_live_context_excludes_compiled_knowledge_when_current_state_is_requested(tmp_path: Path) -> None:
    cli = _build_cli_with_run_support(tmp_path, objective="What current state bounded rollout should execute now?")
    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")

    payload = cli.execute('/run "What current state bounded rollout should execute now?"', json_output=True).json_payload
    assert payload is not None
    live_context = payload["support"]["live_context"]

    assert live_context["governance_truth_count"] == 0
    assert live_context["memory_support_count"] == 1
    assert live_context["compiled_knowledge_support_count"] == 0
    assert live_context["archive_support_count"] == 0
    assert live_context["ordered_support_source_families"] == ["memory"]


def test_run_surfaces_governance_truth_and_selection_review_without_flattening_support(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cli = _build_cli_with_run_support(tmp_path, objective="What bounded rollout should execute now?")
    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")

    monkeypatch.setattr(command_scope, "build_run_governance_inputs", _approval_required_inputs)

    run_payload = cli.execute('/run "What bounded rollout should execute now?"', json_output=True).json_payload
    selection_payload = cli.execute("/selection show", json_output=True).json_payload

    assert run_payload is not None
    assert selection_payload is not None
    assert run_payload["support"]["live_context"]["governance_truth_count"] == 3
    assert run_payload["support"]["live_context"]["truth_families"][-3:] == [
        "governance_integrity",
        "governance_constraint",
        "governance_approval_dependency",
    ]
    assert selection_payload["truth"] == {
        "project_id": "project-1",
        "work_unit_id": "wu-1",
        "run_id": "run-1",
    }
    assert selection_payload["governance_handoff"]["available"] is True
    assert selection_payload["proposal"]["available"] is True
    assert selection_payload["support"]["selection_review_attached"] is True


def test_run_respects_governance_gate_and_does_not_fake_execution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cli = _build_cli_with_run_support(tmp_path, objective="What bounded rollout should execute now?")
    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")

    monkeypatch.setattr(command_scope, "build_run_governance_inputs", _approval_required_inputs)

    payload = cli.execute('/run "What bounded rollout should execute now?"', json_output=True).json_payload
    flow_run = cli.context.flow_runs["run-1"]

    assert payload is not None
    assert payload["derived"]["allowed_now"] is False
    assert payload["derived"]["approval_verdict"] == "absent"
    assert payload["derived"]["execution_status"] is None
    assert payload["support"]["routing_decision"]["routed_outcome"] == "approval_required"
    assert "execution" not in flow_run.outputs


def _build_cli_with_run_support(tmp_path: Path, *, objective: str) -> JeffCLI:
    state, _ = build_state_with_runs(objective=objective, run_specs=())
    memory_store = InMemoryMemoryStore()
    knowledge_store = KnowledgeStore(tmp_path / "knowledge")
    archive_store = ResearchArchiveStore(tmp_path / "archive")

    _seed_memory_support(memory_store)
    _seed_compiled_knowledge(knowledge_store, objective=objective)
    _seed_archive_support(archive_store)

    return JeffCLI(
        context=InterfaceContext(
            state=state,
            memory_store=memory_store,
            knowledge_store=knowledge_store,
            research_archive_store=archive_store,
            infrastructure_services=_infrastructure_services(),
        )
    )


def _seed_memory_support(memory_store: InMemoryMemoryStore) -> None:
    write_memory_candidate(
        candidate=create_memory_candidate(
            candidate_id="candidate-1",
            memory_type="semantic",
            scope=Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1"),
            summary="The prior bounded run stayed inside the active project scope.",
            remembered_points=("Memory support stays ahead of compiled knowledge in live context.",),
            why_it_matters="This continuity signal remains relevant to the next bounded run.",
            support_refs=(
                MemorySupportRef(ref_kind="research", ref_id="research-record-project-1-a", summary="Grounded project support."),
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
            summary="Foreign-project memory must stay isolated.",
            remembered_points=("This must not bleed into project-1.",),
            why_it_matters="Cross-project isolation is binding.",
            support_refs=(
                MemorySupportRef(ref_kind="research", ref_id="research-record-project-2-a", summary="Foreign project support."),
            ),
            support_quality="strong",
            stability="stable",
        ),
        store=memory_store,
    )


def _seed_compiled_knowledge(knowledge_store: KnowledgeStore, *, objective: str) -> None:
    valid_digest_a = create_source_digest_from_research_record(_research_record(project_id="project-1", suffix="a"))
    valid_digest_b = create_source_digest_from_research_record(_research_record(project_id="project-1", suffix="b"))
    foreign_digest_a = create_source_digest_from_research_record(_research_record(project_id="project-2", suffix="a"))
    foreign_digest_b = create_source_digest_from_research_record(_research_record(project_id="project-2", suffix="b"))

    save_knowledge_artifact(valid_digest_a, store=knowledge_store)
    save_knowledge_artifact(valid_digest_b, store=knowledge_store)
    save_knowledge_artifact(foreign_digest_a, store=knowledge_store)
    save_knowledge_artifact(foreign_digest_b, store=knowledge_store)
    save_knowledge_artifact(
        create_topic_note(
            topic=objective,
            supports=(valid_digest_a, valid_digest_b),
            major_supported_points=("Compiled knowledge remains support-only in /run.",),
            topic_framing=f"{objective} current-project compiled support.",
        ),
        store=knowledge_store,
    )
    save_knowledge_artifact(
        create_topic_note(
            topic=objective,
            supports=(foreign_digest_a, foreign_digest_b),
            major_supported_points=("This note must stay outside project-1 retrieval.",),
            topic_framing=f"{objective} foreign-project support.",
        ),
        store=knowledge_store,
    )


def _seed_archive_support(archive_store: ResearchArchiveStore) -> None:
    save_archive_artifact(
        create_research_brief(
            project_id="project-1",
            work_unit_id="wu-1",
            run_id="run-1",
            title="Evidence brief A",
            summary="Direct evidence remains available for project-1.",
            question_or_objective="What direct evidence still matters?",
            findings=("Project-1 evidence remains available to bounded /run.",),
            inference=("Archive support remains support-only.",),
            uncertainty=("Evidence may need refresh.",),
            source_refs=("source-1",),
        ),
        store=archive_store,
    )
    save_archive_artifact(
        create_research_brief(
            project_id="project-1",
            work_unit_id="wu-1",
            run_id="run-1",
            title="Evidence brief B",
            summary="A second direct evidence item remains available for project-1.",
            question_or_objective="What direct evidence still matters?",
            findings=("A second project-1 evidence item remains available to bounded /run.",),
            inference=("Archive ordering remains after memory and compiled knowledge.",),
            uncertainty=("Evidence may still need confirmation.",),
            source_refs=("source-2",),
        ),
        store=archive_store,
    )
    save_archive_artifact(
        create_research_brief(
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
        ),
        store=archive_store,
    )


def _research_record(*, project_id: str, suffix: str) -> ResearchArtifactRecord:
    work_unit_id = "wu-1" if project_id == "project-1" else "wu-x"
    run_id = "run-1" if project_id == "project-1" else "run-x"
    source_id = f"source-{project_id}-{suffix}"
    return ResearchArtifactRecord(
        artifact_id=f"research-record-{project_id}-{suffix}",
        project_id=project_id,
        work_unit_id=work_unit_id,
        run_id=run_id,
        question="What support should /run surface?",
        source_mode="prepared_evidence",
        summary="The bounded run helper should reuse the lawful truth-first context assembler.",
        findings=(ResearchFinding(text="A bounded topic summary remains useful.", source_refs=(source_id,)),),
        inferences=("Compiled knowledge remains support-only.",),
        uncertainties=("Freshness should stay visible.",),
        recommendation=None,
        source_ids=(source_id,),
        source_items=(),
        evidence_items=(),
        created_at="2026-04-19T10:00:00+00:00",
    )


def _approval_required_inputs(*, context: InterfaceContext, scope: Scope):
    return (
        Policy(approval_required=True),
        Approval.absent(),
        CurrentTruthSnapshot(
            scope=scope,
            state_version=context.state.state_meta.state_version,
            degraded_truth=True,
            truth_mismatch=True,
            target_available=False,
        ),
    )


def _infrastructure_services():
    return build_infrastructure_services(
        ModelAdapterRuntimeConfig(
            default_adapter_id="fake-default",
            adapters=(
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id="fake-default",
                    model_name="default-model",
                    fake_text_response="unused default adapter",
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
        "OPTION_1_TYPE: direct_action\n"
        "OPTION_1_TITLE: Advance the bounded rollout\n"
        "OPTION_1_SUMMARY: Take the smallest truthful bounded next step now.\n"
        "OPTION_1_WHY_NOW: The lawful live context already supports immediate bounded action.\n"
        "OPTION_1_ASSUMPTIONS: Current support remains stable\n"
        "OPTION_1_RISKS: Small rollback cost\n"
        "OPTION_1_CONSTRAINTS: Stay inside the current project scope\n"
        "OPTION_1_BLOCKERS: NONE\n"
        "OPTION_1_PLANNING_NEEDED: no\n"
        "OPTION_1_FEASIBILITY: High under the current bounded support\n"
        "OPTION_1_REVERSIBILITY: Straightforward rollback\n"
        "OPTION_1_SUPPORT_REFS: ctx-1\n"
    )