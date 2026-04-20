import json
from pathlib import Path

import pytest

from jeff.bootstrap import build_startup_interface_context, build_infrastructure_runtime
from jeff.core.schemas import Scope
from jeff.core.transition import TransitionRequest
from jeff.infrastructure import AdapterFactoryConfig, AdapterProviderKind, ModelAdapterRuntimeConfig, PurposeOverrides
from jeff.interface import JeffCLI
from jeff.interface.commands import InterfaceContext


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
        research_archive_store=startup.research_archive_store,
        knowledge_store=startup.knowledge_store,
        memory_store=startup.memory_store,
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