from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

import jeff.interface.command_scope as command_scope

from jeff.cognitive.research import ResearchArtifactRecord, ResearchFinding
from jeff.cognitive.proposal import (
    ParsedProposalGenerationResult,
    ParsedProposalOption,
    ProposalGenerationPromptBundle,
    ProposalGenerationRawResult,
    ProposalGenerationValidationError,
    ProposalPipelineFailure,
    ProposalValidationIssue,
)
from jeff.cognitive.selection import SelectionResult
from jeff.core.schemas import Scope
from jeff.core.transition import TransitionRequest, apply_transition
from jeff.governance import Approval, CurrentTruthSnapshot, Policy
from jeff.infrastructure import (
    AdapterFactoryConfig,
    AdapterProviderKind,
    ModelAdapterRuntimeConfig,
    PurposeOverrides,
    ModelUsage,
    build_infrastructure_services,
)
from jeff.action.execution import RepoLocalValidationPlan
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
    assert payload["truth"]["run_lifecycle_state"] == "completed"
    assert payload["truth"]["last_execution_status"] == "completed"
    assert payload["truth"]["last_outcome_state"] == "complete"
    assert payload["truth"]["last_evaluation_verdict"] == "acceptable"
    assert payload["derived"]["flow_visible"] is True
    assert payload["derived"]["flow_family"] == "bounded_proposal_selection_execution"
    assert payload["derived"]["execution_status"] == "completed"
    assert payload["derived"]["evaluation_verdict"] is not None
    assert payload["support"]["execution_summary"]["available"] is True
    assert payload["support"]["execution_summary"]["execution_family"] == "repo_local_validation"
    assert payload["support"]["execution_summary"]["execution_command_id"] == "smoke_quickstart_validation"
    assert payload["support"]["execution_summary"]["exit_code"] == 0
    assert "pytest" in (payload["support"]["execution_summary"]["executed_command"] or "")
    assert payload["support"]["live_context"]["truth_families"][:3] == ["project", "work_unit", "run"]
    assert payload["support"]["proposal_summary"]["available"] is True
    assert payload["derived"]["memory_handoff_attempted"] is True
    assert payload["derived"]["memory_handoff_result"]["write_outcome"] == "write"
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
    assert payload["truth"]["run_lifecycle_state"] == "approval_required"
    assert payload["truth"]["last_execution_status"] is None
    assert payload["derived"]["execution_status"] is None
    assert payload["support"]["execution_summary"]["available"] is False
    assert payload["support"]["routing_decision"]["routed_outcome"] == "approval_required"
    assert payload["derived"]["memory_handoff_attempted"] is True
    assert payload["derived"]["memory_handoff_result"]["write_outcome"] == "defer"
    assert "execution" not in flow_run.outputs


def test_run_surfaces_real_execution_failure_with_command_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cli = _build_cli_with_run_support(tmp_path, objective="Run the bounded validation path and surface failures truthfully.")
    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")

    failing_plan = RepoLocalValidationPlan(
        command_id="failing_validation_probe",
        argv=(
            sys.executable,
            "-c",
            "import sys; print('probe failed'); sys.stderr.write('bounded failure\\n'); raise SystemExit(5)",
        ),
        working_directory=str(tmp_path),
        description="Run a failing bounded validation probe.",
        timeout_seconds=30,
    )
    monkeypatch.setattr(command_scope, "_build_repo_local_validation_plan", lambda _context: failing_plan)

    payload = cli.execute('/run "Run the bounded validation path and surface failures truthfully."', json_output=True).json_payload

    assert payload is not None
    assert payload["truth"]["run_lifecycle_state"] == "completed"
    assert payload["derived"]["execution_status"] == "failed"
    assert payload["derived"]["outcome_state"] == "failed"
    assert payload["derived"]["evaluation_verdict"] == "unacceptable"
    assert payload["truth"]["last_execution_status"] == "failed"
    assert payload["truth"]["last_outcome_state"] == "failed"
    assert payload["truth"]["last_evaluation_verdict"] == "unacceptable"
    assert payload["support"]["execution_summary"]["available"] is True
    assert payload["support"]["execution_summary"]["execution_command_id"] == "failing_validation_probe"
    assert payload["support"]["execution_summary"]["exit_code"] == 5
    assert "probe failed" in (payload["support"]["execution_summary"]["stdout_excerpt"] or "")
    assert "bounded failure" in (payload["support"]["execution_summary"]["stderr_excerpt"] or "")


def test_run_defer_path_surfaces_deferred_not_completed_in_text_and_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cli = _build_cli_with_run_support(tmp_path, objective="Validate whether bounded execution should defer.")
    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")

    def _defer_selection(request):
        return SimpleNamespace(
            selection_result=SelectionResult(
                selection_id=request.selection_id,
                considered_proposal_ids=tuple(option.proposal_id for option in request.proposal_result.options),
                non_selection_outcome="defer",
                rationale="Selection deferred bounded execution for operator follow-up.",
            )
        )

    monkeypatch.setattr(command_scope, "build_and_run_selection", _defer_selection)

    result = cli.execute('/run "Validate whether bounded execution should defer."', json_output=True)
    payload = result.json_payload
    show_payload = cli.execute("/show", json_output=True).json_payload

    assert payload is not None
    assert show_payload is not None
    assert payload["truth"]["run_lifecycle_state"] == "deferred"
    assert payload["truth"]["last_execution_status"] is None
    assert payload["support"]["routing_decision"]["routed_outcome"] == "defer"
    assert payload["derived"]["memory_handoff_attempted"] is True
    assert payload["derived"]["memory_handoff_result"]["write_outcome"] == "defer"
    assert show_payload["truth"]["run_lifecycle_state"] == "deferred"
    assert show_payload["support"]["routing_decision"]["routed_outcome"] == "defer"


def test_run_proposal_validation_failure_is_operator_legible_and_stays_failed_before_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cli = _build_cli_with_run_support(tmp_path, objective="Validate repo-local execution wording.")
    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")

    def _validation_failure(request, *, infrastructure_services, adapter_id=None):
        prompt_bundle = ProposalGenerationPromptBundle(
            request_id="proposal-request-1",
            scope=request.scope,
            objective=request.objective,
            system_instructions="bounded system instructions",
            prompt="bounded proposal prompt",
        )
        raw_result = ProposalGenerationRawResult(
            prompt_bundle=prompt_bundle,
            request_id=prompt_bundle.request_id,
            scope=request.scope,
            raw_output_text="PROPOSAL_COUNT: 1",
            adapter_id="proposal-test",
            provider_name="fake",
            model_name="fake-proposal-model",
            usage=ModelUsage(input_tokens=1, output_tokens=1, total_tokens=2),
        )
        parsed_result = ParsedProposalGenerationResult(
            raw_result=raw_result,
            proposal_count=1,
            scarcity_reason="Only one bounded option was proposed.",
            options=(
                ParsedProposalOption(
                    option_index=1,
                    proposal_type="direct_action",
                    title="Execute the validation immediately",
                    summary="Execute the bounded validation now.",
                    why_now="The operator requested repo-local validation.",
                    assumptions=("The repo-local suite is available.",),
                    risks=("The suite may fail.",),
                    constraints=("Stay inside the current repo.",),
                    blockers=("None.",),
                    planning_needed=False,
                    feasibility="feasible",
                    reversibility="reversible",
                    support_refs=("S1",),
                ),
            ),
        )
        issues = (
            ProposalValidationIssue(
                code="authority_leakage",
                message="title contains forbidden authority language: execution",
                option_index=1,
            ),
        )
        return ProposalPipelineFailure(
            request=request,
            failure_stage="validation",
            error=ProposalGenerationValidationError(issues),
            prompt_bundle=prompt_bundle,
            raw_result=raw_result,
            parsed_result=parsed_result,
            validation_issues=issues,
            status="validation_failure",
        )

    monkeypatch.setattr(command_scope, "run_proposal_generation_pipeline", _validation_failure)

    result = cli.execute('/run "Validate repo-local execution wording."', json_output=True)
    payload = result.json_payload
    show_payload = cli.execute("/show", json_output=True).json_payload

    assert payload is not None
    assert show_payload is not None
    assert "proposal validation rejected live provider output (forbidden authority language)." in result.text
    assert payload["truth"]["run_lifecycle_state"] == "failed_before_execution"
    assert payload["truth"]["last_execution_status"] is None
    assert payload["support"]["flow_reason_summary"] == (
        "proposal validation rejected live provider output (forbidden authority language). "
        "/run cannot proceed; try /research docs for inspection instead."
    )
    assert payload["derived"]["memory_handoff_attempted"] is True
    assert payload["derived"]["memory_handoff_result"]["write_outcome"] == "defer"
    assert show_payload["truth"]["run_lifecycle_state"] == "failed_before_execution"
    assert show_payload["support"]["flow_reason_summary"] == payload["support"]["flow_reason_summary"]


def test_approve_then_revalidate_continues_bounded_execution_lawfully(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cli = _build_cli_with_run_support(tmp_path, objective="What bounded rollout should execute now?")
    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")

    monkeypatch.setattr(command_scope, "build_run_governance_inputs", _approval_required_only_inputs)

    run_payload = cli.execute('/run "What bounded rollout should execute now?"', json_output=True).json_payload
    approve_payload = cli.execute("/approve", json_output=True).json_payload
    revalidate_payload = cli.execute("/revalidate", json_output=True).json_payload
    show_payload = cli.execute("/show", json_output=True).json_payload

    assert run_payload is not None
    assert approve_payload is not None
    assert revalidate_payload is not None
    assert show_payload is not None
    assert run_payload["support"]["routing_decision"]["routed_outcome"] == "approval_required"
    assert approve_payload["derived"]["effect_state"] == "approval_recorded"
    assert approve_payload["support"]["detail"]["next_routed_outcome"] == "revalidate"
    assert revalidate_payload["derived"]["effect_state"] == "continued_to_execution"
    assert revalidate_payload["support"]["detail"]["execution_status"] == "completed"
    assert show_payload["truth"]["run_lifecycle_state"] == "completed"
    assert show_payload["truth"]["last_execution_status"] == "completed"
    assert show_payload["derived"]["approval_verdict"] == "granted"
    assert show_payload["derived"]["execution_status"] == "completed"
    assert show_payload["support"]["execution_summary"]["available"] is True


def test_revalidate_fails_closed_when_approval_basis_becomes_stale(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cli = _build_cli_with_run_support(tmp_path, objective="What bounded rollout should execute now?")
    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")

    monkeypatch.setattr(command_scope, "build_run_governance_inputs", _approval_required_only_inputs)

    cli.execute('/run "What bounded rollout should execute now?"', json_output=True)
    cli.execute("/approve", json_output=True)

    stale_state = apply_transition(
        cli.context.state,
        TransitionRequest(
            transition_id="transition-stale-approval-project-2",
            transition_type="create_project",
            basis_state_version=cli.context.state.state_meta.state_version,
            scope=Scope(project_id="project-2"),
            payload={"name": "Stale Approval Trigger"},
        ),
    ).state
    cli._context = InterfaceContext(
        state=stale_state,
        flow_runs=cli.context.flow_runs,
        selection_reviews=cli.context.selection_reviews,
        infrastructure_services=cli.context.infrastructure_services,
        research_artifact_store=cli.context.research_artifact_store,
        research_archive_store=cli.context.research_archive_store,
        knowledge_store=cli.context.knowledge_store,
        memory_store=cli.context.memory_store,
        research_memory_handoff_enabled=cli.context.research_memory_handoff_enabled,
        runtime_store=cli.context.runtime_store,
        startup_summary=cli.context.startup_summary,
    )

    revalidate_payload = cli.execute("/revalidate", json_output=True).json_payload
    show_payload = cli.execute("/show", json_output=True).json_payload

    assert revalidate_payload is not None
    assert show_payload is not None
    assert revalidate_payload["derived"]["effect_state"] == "continuation_blocked"
    assert revalidate_payload["support"]["detail"]["governance_outcome"] == "deferred_pending_revalidation"
    assert show_payload["derived"]["approval_verdict"] == "stale"
    assert show_payload["support"]["routing_decision"]["routed_outcome"] == "revalidate"
    assert show_payload["truth"]["last_execution_status"] is None


def test_reject_makes_approval_required_run_terminal_and_truthful(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cli = _build_cli_with_run_support(tmp_path, objective="What bounded rollout should execute now?")
    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")

    monkeypatch.setattr(command_scope, "build_run_governance_inputs", _approval_required_only_inputs)

    cli.execute('/run "What bounded rollout should execute now?"', json_output=True)
    reject_payload = cli.execute("/reject", json_output=True).json_payload
    show_payload = cli.execute("/show", json_output=True).json_payload

    assert reject_payload is not None
    assert show_payload is not None
    assert reject_payload["derived"]["effect_state"] == "continuation_rejected"
    assert reject_payload["support"]["detail"]["approval_verdict"] == "denied"
    assert show_payload["derived"]["approval_verdict"] == "denied"
    assert show_payload["support"]["routing_decision"]["routed_outcome"] == "blocked"
    assert show_payload["truth"]["last_execution_status"] is None


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


def _approval_required_only_inputs(*, context: InterfaceContext, scope: Scope):
    return (
        Policy(approval_required=True),
        Approval.absent(),
        CurrentTruthSnapshot(
            scope=scope,
            state_version=context.state.state_meta.state_version,
        ),
    )