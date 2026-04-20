import json
from pathlib import Path
import sys

import pytest

import jeff.interface.commands.scope as command_scope

from jeff.action.execution import RepoLocalValidationPlan
from jeff.cognitive.research.archive import ResearchArchiveStore, create_research_brief, save_archive_artifact
from jeff.bootstrap import build_startup_interface_context, build_infrastructure_runtime
from jeff.core.schemas import Scope
from jeff.core.transition import TransitionRequest
from jeff.infrastructure import AdapterFactoryConfig, AdapterProviderKind, ModelAdapterRuntimeConfig, PurposeOverrides
from jeff.interface import JeffCLI
from jeff.interface.commands import InterfaceContext
from jeff.memory import InMemoryMemoryStore, LocalFileMemoryStore, MemorySupportRef, create_memory_candidate, write_memory_candidate
from jeff.knowledge import KnowledgeStore


def test_direct_proposal_success_and_restart_inspection(tmp_path: Path) -> None:
    cli = _scoped_cli(tmp_path, _runtime_context(tmp_path, _valid_proposal_text()))

    created = json.loads(cli.run_one_shot('/proposal "Frame bounded operator options"', json_output=True))
    shown = json.loads(cli.run_one_shot("/proposal show run-1", json_output=True))
    raw = json.loads(cli.run_one_shot("/proposal raw run-1", json_output=True))
    validated = json.loads(cli.run_one_shot("/proposal validate run-1", json_output=True))

    assert created["view"] == "proposal_run"
    assert created["derived"]["proposal_status"] == "success"
    assert created["proposal"]["proposal_count"] == 1
    assert created["proposal"]["retained_options"][0]["proposal_type"] == "direct_action"
    assert created["proposal_input_bundle"]["truth_snapshot"]["item_count"] == 3
    assert created["proposal_input_bundle"]["governance_relevant_support"]["item_count"] == 0
    assert created["proposal_input_bundle"]["current_execution_support"]["item_count"] == 0
    assert created["proposal_input_bundle"]["evidence_support"]["evidence_count"] == 0
    assert created["proposal_input_bundle"]["memory_support"]["summary_count"] == 0
    assert shown["truth"]["proposal_id"] == created["truth"]["proposal_id"]
    assert raw["attempts"][0]["attempt_kind"] == "initial"
    assert "PROPOSAL_COUNT: 1" in raw["attempts"][0]["raw_output_text"]
    assert validated["derived"]["parse_success"] is True
    assert validated["derived"]["validation_success"] is True

    reloaded_cli = _scoped_cli(tmp_path, build_startup_interface_context(base_dir=tmp_path))
    reloaded = json.loads(reloaded_cli.run_one_shot("/proposal show run-1", json_output=True))

    assert reloaded["truth"]["proposal_id"] == created["truth"]["proposal_id"]
    assert reloaded["artifacts"]["record_ref"] is not None
    assert reloaded["artifacts"]["initial_raw_ref"] is not None
    assert reloaded["artifacts"]["initial_parsed_ref"] is not None


def test_parse_failure_is_persisted_and_inspectable(tmp_path: Path) -> None:
    cli = _scoped_cli(tmp_path, _runtime_context(tmp_path, "NOT_A_VALID_PROPOSAL_LINE"))

    created = json.loads(cli.run_one_shot('/proposal "Trigger parse failure"', json_output=True))
    raw = json.loads(cli.run_one_shot("/proposal raw run-1", json_output=True))
    validated = json.loads(cli.run_one_shot("/proposal validate run-1", json_output=True))

    assert created["derived"]["proposal_status"] == "failed"
    assert created["derived"]["repair_attempted"] is True
    assert created["derived"]["final_failure_stage"] == "parse"
    assert created["proposal"]["summary_source"] == "none"
    assert len(raw["attempts"]) == 2
    assert raw["attempts"][0]["raw_output_text"] == "NOT_A_VALID_PROPOSAL_LINE"
    assert raw["attempts"][1]["raw_output_text"] == "NOT_A_VALID_PROPOSAL_LINE"
    assert validated["derived"]["parse_success"] is False
    assert "malformed proposal output line" in validated["support"]["parse_error"]


def test_validation_failure_is_persisted_with_parsed_intermediate_detail(tmp_path: Path) -> None:
    cli = _scoped_cli(tmp_path, _runtime_context(tmp_path, _authority_leakage_text()))

    created = json.loads(cli.run_one_shot('/proposal "Trigger validation failure"', json_output=True))
    shown = json.loads(cli.run_one_shot("/proposal show run-1", json_output=True))
    validated = json.loads(cli.run_one_shot("/proposal validate run-1", json_output=True))

    assert created["derived"]["proposal_status"] == "failed"
    assert created["derived"]["final_failure_stage"] == "validation"
    assert created["derived"]["final_validation_outcome"] == "failed"
    assert shown["proposal"]["summary_source"] == "parsed_intermediate"
    assert shown["proposal"]["proposal_count"] == 1
    assert shown["proposal"]["retained_options"][0]["title"] == "Apply the bounded patch"
    assert validated["derived"]["parse_success"] is True
    assert validated["derived"]["validation_success"] is False
    assert validated["support"]["validation_issues"][0]["code"] == "authority_leakage"


def test_proposal_repair_can_succeed_from_persisted_failed_record(tmp_path: Path) -> None:
    failed_cli = _scoped_cli(tmp_path, _runtime_context(tmp_path, "NOT_A_VALID_PROPOSAL_LINE"))
    failed = json.loads(failed_cli.run_one_shot('/proposal "Repair this failure"', json_output=True))

    repair_cli = JeffCLI(context=_runtime_context(tmp_path, _valid_proposal_text()))
    repaired = json.loads(
        repair_cli.run_one_shot(f"/proposal repair {failed['truth']['proposal_id']}", json_output=True)
    )
    original = json.loads(repair_cli.run_one_shot(f"/proposal show {failed['truth']['proposal_id']}", json_output=True))

    assert original["derived"]["proposal_status"] == "failed"
    assert repaired["view"] == "proposal_repair"
    assert repaired["truth"]["source_proposal_id"] == failed["truth"]["proposal_id"]
    assert repaired["derived"]["proposal_status"] == "success"
    assert repaired["proposal"]["proposal_count"] == 1


def test_proposal_repair_can_fail_without_overwriting_original_record(tmp_path: Path) -> None:
    failed_cli = _scoped_cli(tmp_path, _runtime_context(tmp_path, _authority_leakage_text()))
    failed = json.loads(failed_cli.run_one_shot('/proposal "Keep failing repair"', json_output=True))

    repair_cli = JeffCLI(context=_runtime_context(tmp_path, _authority_leakage_text()))
    repaired = json.loads(
        repair_cli.run_one_shot(f"/proposal repair {failed['truth']['proposal_id']}", json_output=True)
    )

    assert repaired["truth"]["source_proposal_id"] == failed["truth"]["proposal_id"]
    assert repaired["derived"]["proposal_status"] == "failed"
    assert repaired["derived"]["final_failure_stage"] == "validation"
    assert repaired["proposal"]["summary_source"] == "parsed_intermediate"


def test_proposal_commands_report_missing_scope_and_ambiguous_run_ids(tmp_path: Path) -> None:
    cli = JeffCLI(context=_runtime_context(tmp_path, _valid_proposal_text()))

    with pytest.raises(ValueError, match="proposal show requires a current run"):
        cli.run_one_shot("/proposal show")

    _create_second_work_unit_with_same_run_id(tmp_path)
    ambiguous_cli = JeffCLI(context=_runtime_context(tmp_path, _valid_proposal_text()))
    ambiguous_cli.run_one_shot("/project use project-1")

    with pytest.raises(ValueError, match="ambiguous run_id: run-1 requires work_unit scope inside current project scope"):
        ambiguous_cli.run_one_shot("/proposal show run-1")


def test_direct_proposal_auto_selects_single_run_from_project_and_work_scope(tmp_path: Path) -> None:
    _create_run(tmp_path, "run-1")
    cli = _project_and_work_cli(_runtime_context(tmp_path, _valid_proposal_text()))

    created = json.loads(cli.run_one_shot('/proposal "Frame bounded operator options"', json_output=True))

    assert created["truth"]["scope"]["run_id"] == "run-1"
    assert created["proposal_input_bundle"]["truth_snapshot"]["item_count"] == 3
    assert created["proposal_input_bundle"]["truth_snapshot"]["items"][-1]["truth_family"] == "run"


def test_direct_proposal_without_explicit_run_fails_when_multiple_runs_exist(tmp_path: Path) -> None:
    _create_run(tmp_path, "run-1")
    _create_run(tmp_path, "run-2")
    cli = _project_and_work_cli(_runtime_context(tmp_path, _valid_proposal_text()))

    with pytest.raises(ValueError, match="proposal found multiple runs in work_unit wu-1"):
        cli.run_one_shot('/proposal "Frame bounded operator options"', json_output=True)


def test_direct_proposal_includes_archive_and_memory_support_when_scope_matched(tmp_path: Path) -> None:
    _create_run(tmp_path, "run-1")
    context = _runtime_context(tmp_path, _valid_proposal_text())
    assert isinstance(context.memory_store, LocalFileMemoryStore)
    _seed_direct_proposal_support(context)
    cli = _project_and_work_cli(context)

    created = json.loads(cli.run_one_shot('/proposal "What is Jeff architecture?"', json_output=True))

    assert created["truth"]["scope"]["run_id"] == "run-1"
    assert created["proposal_input_bundle"]["evidence_support"]["evidence_count"] > 0
    assert created["proposal_input_bundle"]["evidence_support"]["artifact_refs"]
    assert created["proposal_input_bundle"]["memory_support"]["summary_count"] > 0
    assert created["proposal_input_bundle"]["memory_support"]["memory_ids"]
    assert created["proposal_input_bundle"]["memory_support"]["memory_summaries"][0]["source_id"]
    assert [item["truth_family"] for item in created["proposal_input_bundle"]["truth_snapshot"]["items"]] == [
        "project",
        "work_unit",
        "run",
    ]

    reloaded_cli = _project_and_work_cli(build_startup_interface_context(base_dir=tmp_path))
    shown = json.loads(reloaded_cli.run_one_shot("/proposal show run-1", json_output=True))

    assert shown["proposal_input_bundle"]["evidence_support"]["evidence_count"] > 0
    assert shown["proposal_input_bundle"]["memory_support"]["summary_count"] > 0
    assert shown["proposal_input_bundle"]["memory_support"]["memory_summaries"][0]["source_id"] in shown["proposal_input_bundle"]["memory_support"]["memory_ids"]
    assert [item["truth_family"] for item in shown["proposal_input_bundle"]["truth_snapshot"]["items"]] == [
        "project",
        "work_unit",
        "run",
    ]


def test_run_persists_proposal_record_for_operator_inspection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cli = _scoped_cli(tmp_path, _runtime_context(tmp_path, _valid_proposal_text()))
    validation_plan = RepoLocalValidationPlan(
        command_id="bounded_validation_probe",
        argv=(sys.executable, "-c", "print('bounded probe ok')"),
        working_directory=str(tmp_path),
        description="Run a tiny bounded validation probe.",
        timeout_seconds=30,
    )
    monkeypatch.setattr(command_scope, "_build_repo_local_validation_plan", lambda _context: validation_plan)

    run_payload = json.loads(cli.run_one_shot('/run "What bounded rollout should execute now?"', json_output=True))
    run_id = run_payload["truth"]["run_id"]
    proposal_payload = json.loads(cli.run_one_shot(f"/proposal show {run_id}", json_output=True))

    assert run_id is not None
    assert run_payload["truth"]["last_execution_status"] == "completed"
    assert proposal_payload["derived"]["proposal_status"] == "success"
    assert proposal_payload["truth"]["scope"]["run_id"] == run_id
    assert proposal_payload["proposal"]["proposal_count"] == 1
    assert proposal_payload["proposal_input_bundle"]["current_execution_support"]["item_count"] == 2
    assert "evidence_support" in proposal_payload["proposal_input_bundle"]
    assert "memory_support" in proposal_payload["proposal_input_bundle"]
    assert proposal_payload["proposal_input_bundle"]["current_execution_support"]["items"][0]["summary"].startswith(
        "The current /run path is limited to one bounded repo-local validation plan"
    )


def test_run_memory_handoff_survives_restart_and_direct_proposal_reads_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cli = _scoped_cli(tmp_path, _runtime_context(tmp_path, _valid_proposal_text()))
    validation_plan = RepoLocalValidationPlan(
        command_id="memory_persistence_probe",
        argv=(sys.executable, "-c", "print('memory persistence ok')"),
        working_directory=str(tmp_path),
        description="Run a tiny bounded validation probe for memory persistence.",
        timeout_seconds=30,
    )
    monkeypatch.setattr(command_scope, "_build_repo_local_validation_plan", lambda _context: validation_plan)

    run_payload = json.loads(cli.run_one_shot('/run "What bounded rollout should execute now?"', json_output=True))
    run_id = run_payload["truth"]["run_id"]

    reloaded_context = _runtime_context(tmp_path, _valid_proposal_text())
    assert isinstance(reloaded_context.memory_store, LocalFileMemoryStore)
    assert reloaded_context.memory_store.get_committed("memory-1") is not None

    reloaded_cli = _project_and_work_cli(reloaded_context)
    reloaded_cli.run_one_shot(f"/run use {run_id}")
    proposal_payload = json.loads(
        reloaded_cli.run_one_shot('/proposal "What bounded rollout should execute now?"', json_output=True)
    )

    assert run_id is not None
    assert proposal_payload["truth"]["scope"]["run_id"] == run_id
    assert proposal_payload["proposal_input_bundle"]["memory_support"]["summary_count"] > 0
    assert proposal_payload["proposal_input_bundle"]["memory_support"]["memory_ids"] == ["memory-1"]
    assert [item["truth_family"] for item in proposal_payload["proposal_input_bundle"]["truth_snapshot"]["items"]] == [
        "project",
        "work_unit",
        "run",
    ]


def _runtime_context(tmp_path: Path, proposal_text: str) -> InterfaceContext:
    startup = build_startup_interface_context(base_dir=tmp_path)
    services = build_infrastructure_runtime(
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
                    fake_text_response=proposal_text,
                ),
            ),
            purpose_overrides=PurposeOverrides(proposal="fake-proposal"),
        )
    )
    return InterfaceContext(
        state=startup.state,
        flow_runs=startup.flow_runs,
        selection_reviews=startup.selection_reviews,
        infrastructure_services=services,
        research_artifact_store=startup.research_artifact_store,
        research_archive_store=startup.research_archive_store or ResearchArchiveStore(tmp_path / "archive"),
        knowledge_store=startup.knowledge_store or KnowledgeStore(tmp_path / "knowledge"),
        memory_store=startup.memory_store or LocalFileMemoryStore(tmp_path / ".jeff_runtime" / "memory"),
        research_memory_handoff_enabled=startup.research_memory_handoff_enabled,
        runtime_store=startup.runtime_store,
        startup_summary=startup.startup_summary,
    )


def _scoped_cli(tmp_path: Path, context: InterfaceContext) -> JeffCLI:
    cli = JeffCLI(context=context)
    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    cli.run_one_shot("/inspect")
    return cli


def _project_and_work_cli(context: InterfaceContext) -> JeffCLI:
    cli = JeffCLI(context=context)
    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    return cli


def _create_run(tmp_path: Path, run_id: str) -> None:
    context = build_startup_interface_context(base_dir=tmp_path)
    assert context.runtime_store is not None
    state = context.state
    result = context.runtime_store.apply_transition(
        state,
        TransitionRequest(
            transition_id=f"transition-create-{run_id}",
            transition_type="create_run",
            basis_state_version=state.state_meta.state_version,
            scope=Scope(project_id="project-1", work_unit_id="wu-1"),
            payload={"run_id": run_id},
        ),
    )
    assert result.transition_result == "committed"


def _seed_direct_proposal_support(context: InterfaceContext) -> None:
    assert context.research_archive_store is not None
    assert context.memory_store is not None

    archive_artifact = create_research_brief(
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        title="Jeff architecture evidence brief",
        summary="Jeff architecture remains documented in bounded research artifacts for this run.",
        question_or_objective="What is Jeff architecture?",
        findings=("Jeff is a CLI-first persisted-runtime backbone.",),
        inference=("Proposal support can reuse this evidence as support-only context.",),
        uncertainty=("Some architectural details may still require source review.",),
        source_refs=("source-1",),
    )
    save_archive_artifact(archive_artifact, store=context.research_archive_store)

    write_memory_candidate(
        candidate=create_memory_candidate(
            candidate_id="candidate-architecture-memory",
            memory_type="semantic",
            scope=Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1"),
            summary="Jeff architecture questions previously benefited from archived evidence and CLI-runtime framing.",
            remembered_points=(
                "Remember to ground Jeff architecture answers in archived evidence.",
            ),
            why_it_matters="The current proposal asks the same architecture question in the same scope.",
            support_refs=(
                MemorySupportRef(
                    ref_kind="research",
                    ref_id=str(archive_artifact.artifact_id),
                    summary="Architecture brief grounded this memory.",
                ),
            ),
            support_quality="strong",
            stability="stable",
        ),
        store=context.memory_store,
    )


def _create_second_work_unit_with_same_run_id(tmp_path: Path) -> None:
    context = build_startup_interface_context(base_dir=tmp_path)
    assert context.runtime_store is not None
    state = context.state
    result = context.runtime_store.apply_transition(
        state,
        TransitionRequest(
            transition_id="transition-run-1-primary",
            transition_type="create_run",
            basis_state_version=state.state_meta.state_version,
            scope=Scope(project_id="project-1", work_unit_id="wu-1"),
            payload={"run_id": "run-1"},
        ),
    )
    state = result.state
    result = context.runtime_store.apply_transition(
        state,
        TransitionRequest(
            transition_id="transition-work-unit-2",
            transition_type="create_work_unit",
            basis_state_version=state.state_meta.state_version,
            scope=Scope(project_id="project-1"),
            payload={"work_unit_id": "wu-2", "objective": "Secondary bounded work"},
        ),
    )
    state = result.state
    context.runtime_store.apply_transition(
        state,
        TransitionRequest(
            transition_id="transition-run-2",
            transition_type="create_run",
            basis_state_version=state.state_meta.state_version,
            scope=Scope(project_id="project-1", work_unit_id="wu-2"),
            payload={"run_id": "run-1"},
        ),
    )


def _valid_proposal_text() -> str:
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
        "OPTION_1_BLOCKERS: No explicit blockers identified from the provided support.\n"
        "OPTION_1_PLANNING_NEEDED: no\n"
        "OPTION_1_FEASIBILITY: High under the current bounded support\n"
        "OPTION_1_REVERSIBILITY: Straightforward rollback\n"
        "OPTION_1_SUPPORT_REFS: ctx-1\n"
    )


def _authority_leakage_text() -> str:
    return (
        "PROPOSAL_COUNT: 1\n"
        "SCARCITY_REASON: Only one serious path is currently grounded.\n"
        "OPTION_1_TYPE: direct_action\n"
        "OPTION_1_TITLE: Apply the bounded patch\n"
        "OPTION_1_SUMMARY: Apply the change now because approval is implied.\n"
        "OPTION_1_WHY_NOW: Current support already bounds the change.\n"
        "OPTION_1_ASSUMPTIONS: The failing edge is already reproduced\n"
        "OPTION_1_RISKS: Small regression risk remains\n"
        "OPTION_1_CONSTRAINTS: Stay inside the current project scope\n"
        "OPTION_1_BLOCKERS: No explicit blockers identified from the provided support.\n"
        "OPTION_1_PLANNING_NEEDED: no\n"
        "OPTION_1_FEASIBILITY: Feasible with current evidence\n"
        "OPTION_1_REVERSIBILITY: Straightforward rollback\n"
        "OPTION_1_SUPPORT_REFS: ctx-1\n"
    )
