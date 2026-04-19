from pathlib import Path

import pytest

from jeff.cognitive.context import assemble_context_package
from jeff.cognitive.research import ResearchArtifactRecord, ResearchFinding
from jeff.cognitive.types import TriggerInput
from jeff.contracts import Action
from jeff.core.schemas import Scope
from jeff.core.state import bootstrap_global_state
from jeff.core.transition import TransitionRequest, apply_transition
from jeff.governance import Approval, CurrentTruthSnapshot, Policy, evaluate_action_entry
from jeff.knowledge import (
    KnowledgeStore,
    create_source_digest_from_research_record,
    create_topic_note,
    save_knowledge_artifact,
)
from jeff.memory import InMemoryMemoryStore, MemorySupportRef, create_memory_candidate, write_memory_candidate


def _state_with_run(*, project_id: str = "project-1"):
    state = bootstrap_global_state()
    state = apply_transition(
        state,
        TransitionRequest(
            transition_id=f"{project_id}-transition-1",
            transition_type="create_project",
            basis_state_version=0,
            scope=Scope(project_id=project_id),
            payload={"name": f"Project {project_id}"},
        ),
    ).state
    state = apply_transition(
        state,
        TransitionRequest(
            transition_id=f"{project_id}-transition-2",
            transition_type="create_work_unit",
            basis_state_version=1,
            scope=Scope(project_id=project_id),
            payload={"work_unit_id": "wu-1", "objective": "Lawful context assembly"},
        ),
    ).state
    state = apply_transition(
        state,
        TransitionRequest(
            transition_id=f"{project_id}-transition-3",
            transition_type="create_run",
            basis_state_version=2,
            scope=Scope(project_id=project_id, work_unit_id="wu-1"),
            payload={"run_id": "run-1"},
        ),
    ).state
    return state


def _scope(*, project_id: str = "project-1") -> Scope:
    return Scope(project_id=project_id, work_unit_id="wu-1", run_id="run-1")


def _governance_truth(*, scope: Scope | None = None, project_id: str = "project-1") -> CurrentTruthSnapshot:
    return CurrentTruthSnapshot(
        scope=scope or Scope(project_id=project_id, work_unit_id="wu-1", run_id="run-1"),
        state_version=3,
        blocked_reasons=("approval review is still blocking start",),
        degraded_truth=True,
        truth_mismatch=True,
        requires_revalidation=True,
        target_available=False,
    )


def _persist_memory(store: InMemoryMemoryStore, *, scope: Scope) -> None:
    write_memory_candidate(
        candidate=create_memory_candidate(
            candidate_id="candidate-current",
            memory_type="semantic",
            scope=scope,
            summary="Memory support remains relevant for this bounded follow-up.",
            remembered_points=("Memory stays below governance-relevant current truth.",),
            why_it_matters="This continuity signal matters for the next bounded proposal.",
            support_refs=(
                MemorySupportRef(ref_kind="research", ref_id="research-current", summary="Current research."),
            ),
            support_quality="strong",
            stability="stable",
        ),
        store=store,
    )


def _persist_topic_note(store: KnowledgeStore, *, project_id: str = "project-1") -> None:
    record_a = ResearchArtifactRecord(
        artifact_id=f"research-{project_id}-a",
        project_id=project_id,
        work_unit_id="wu-1",
        run_id="run-1",
        question="What bounded topic support remains relevant?",
        source_mode="prepared_evidence",
        summary="Compiled knowledge remains support-only.",
        findings=(ResearchFinding(text="A bounded topic note remains helpful.", source_refs=("source-1",)),),
        inferences=("Compiled knowledge must remain below current truth.",),
        uncertainties=("Freshness still matters.",),
        recommendation=None,
        source_ids=("source-1",),
        source_items=(),
        evidence_items=(),
        created_at="2026-04-19T10:00:00+00:00",
    )
    record_b = ResearchArtifactRecord(
        artifact_id=f"research-{project_id}-b",
        project_id=project_id,
        work_unit_id="wu-1",
        run_id="run-1",
        question="What second bounded support remains relevant?",
        source_mode="prepared_evidence",
        summary="A second support source backs the topic note.",
        findings=(ResearchFinding(text="A second bounded support source exists.", source_refs=("source-2",)),),
        inferences=("Multiple support sources remain available.",),
        uncertainties=("None.",),
        recommendation=None,
        source_ids=("source-2",),
        source_items=(),
        evidence_items=(),
        created_at="2026-04-19T10:00:00+00:00",
    )
    digest_a = create_source_digest_from_research_record(record_a)
    digest_b = create_source_digest_from_research_record(record_b)
    save_knowledge_artifact(digest_a, store=store)
    save_knowledge_artifact(digest_b, store=store)
    save_knowledge_artifact(
        create_topic_note(
            topic="bounded proposal support",
            supports=(digest_a, digest_b),
            major_supported_points=("Compiled knowledge remains support-only background.",),
            topic_framing="Compiled knowledge supports later proposal follow-up without becoming truth.",
        ),
        store=store,
    )


def _readiness_for(*, scope: Scope, truth: CurrentTruthSnapshot):
    action = Action(
        action_id="action-1",
        scope=scope,
        intent_summary="Attempt the bounded action",
        basis_state_version=3,
    )
    return evaluate_action_entry(
        action=action,
        policy=Policy(approval_required=True),
        approval=Approval.absent(),
        truth=truth,
    ).readiness


def test_governance_truth_is_filled_only_when_lawful_current_governance_truth_exists() -> None:
    state = _state_with_run()
    scope = _scope()

    with_truth = assemble_context_package(
        trigger=TriggerInput(trigger_summary="Prepare bounded proposal options"),
        purpose="proposal support",
        scope=scope,
        state=state,
        governance_truth=_governance_truth(scope=scope),
        governance_policy=Policy(approval_required=True),
    )
    without_truth = assemble_context_package(
        trigger=TriggerInput(trigger_summary="Prepare bounded proposal options"),
        purpose="proposal support",
        scope=scope,
        state=state,
    )

    assert with_truth.governance_truth_records
    assert without_truth.governance_truth_records == ()


def test_governance_truth_is_omitted_when_purpose_is_irrelevant() -> None:
    state = _state_with_run()
    scope = _scope()

    context = assemble_context_package(
        trigger=TriggerInput(trigger_summary="Continue thematic research"),
        purpose="research continuation",
        scope=scope,
        state=state,
        governance_truth=_governance_truth(scope=scope),
        governance_policy=Policy(approval_required=True),
    )

    assert context.governance_truth_records == ()


def test_governance_truth_stays_ahead_of_memory_and_compiled_knowledge(tmp_path: Path) -> None:
    state = _state_with_run()
    scope = _scope()
    memory_store = InMemoryMemoryStore()
    knowledge_store = KnowledgeStore(tmp_path)
    _persist_memory(memory_store, scope=scope)
    _persist_topic_note(knowledge_store)

    context = assemble_context_package(
        trigger=TriggerInput(trigger_summary="Prepare bounded proposal options"),
        purpose="proposal support",
        scope=scope,
        state=state,
        memory_store=memory_store,
        knowledge_store=knowledge_store,
        governance_truth=_governance_truth(scope=scope),
        governance_policy=Policy(approval_required=True),
    )

    assert context.governance_truth_records
    assert context.memory_support_inputs
    assert context.compiled_knowledge_support_inputs
    assert [record.truth_family for record in context.ordered_truth_records[:3]] == ["project", "work_unit", "run"]
    assert context.ordered_truth_records[3].truth_family.startswith("governance_")
    assert context.ordered_support_inputs[: len(context.memory_support_inputs)] == context.memory_support_inputs


def test_governance_truth_is_not_flattened_into_support_only_material() -> None:
    state = _state_with_run()
    scope = _scope()

    context = assemble_context_package(
        trigger=TriggerInput(trigger_summary="Explain the current bounded constraint"),
        purpose="operator explanation current constraint",
        scope=scope,
        state=state,
        governance_truth=_governance_truth(scope=scope),
        governance_policy=Policy(approval_required=True),
    )

    assert context.governance_truth_records
    assert all(item.source_family != "governance_truth" for item in context.ordered_support_inputs)
    assert all(record.truth_family.startswith("governance_") for record in context.governance_truth_records)


def test_governance_truth_summaries_preserve_blocker_integrity_and_constraint_behavior() -> None:
    state = _state_with_run()
    scope = _scope()
    truth = _governance_truth(scope=scope)
    readiness = _readiness_for(scope=scope, truth=truth)

    context = assemble_context_package(
        trigger=TriggerInput(trigger_summary="Explain the current bounded constraint"),
        purpose="operator explanation readiness approval constraint",
        scope=scope,
        state=state,
        governance_truth=truth,
        governance_policy=Policy(approval_required=True),
        governance_approval=Approval.absent(),
        governance_readiness=readiness,
    )

    summaries = {record.truth_family: record.summary for record in context.governance_truth_records}
    assert "approval review is still blocking start" in summaries["governance_blocker"]
    assert "degraded_truth" in summaries["governance_integrity"]
    assert "truth_mismatch" in summaries["governance_integrity"]
    assert "requires_revalidation" in summaries["governance_constraint"]
    assert "target_unavailable" in summaries["governance_constraint"]
    assert "current_approval=absent" in summaries["governance_approval_dependency"]
    assert "pending_revalidation" in summaries["governance_readiness"]


def test_cross_project_governance_truth_leakage_is_rejected() -> None:
    state = _state_with_run(project_id="project-1")

    with pytest.raises(ValueError, match="current project scope"):
        assemble_context_package(
            trigger=TriggerInput(trigger_summary="Prepare bounded proposal options"),
            purpose="proposal support",
            scope=_scope(project_id="project-1"),
            state=state,
            governance_truth=_governance_truth(project_id="project-2"),
        )