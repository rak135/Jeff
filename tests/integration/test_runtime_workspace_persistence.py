import json
from pathlib import Path
import sys

import jeff.interface.command_scope as command_scope
import pytest
from jeff.action.execution import RepoLocalValidationPlan
from jeff.bootstrap import build_startup_interface_context
from jeff.cognitive import (
    EvidenceItem,
    EvidencePack,
    ResearchArtifact,
    ResearchArtifactStore,
    ResearchFinding,
    ResearchRequest,
    SourceItem,
    build_research_artifact_record,
)
from jeff.core.schemas import Scope
from jeff.core.transition import TransitionRequest
from jeff.governance import Approval, CurrentTruthSnapshot, Policy
from jeff.infrastructure import (
    AdapterFactoryConfig,
    AdapterProviderKind,
    ModelAdapterRuntimeConfig,
    PurposeOverrides,
    build_infrastructure_services,
)
from jeff.interface import InterfaceContext
from jeff.interface import JeffCLI
from jeff.runtime_persistence import PersistedRuntimeStore, RuntimeMutationLockError
from tests.fixtures.cli import build_flow_run
from tests.fixtures.entrypoint import run_jeff


def test_startup_initializes_persisted_runtime_home_when_missing(tmp_path: Path) -> None:
    context = build_startup_interface_context(base_dir=tmp_path)
    runtime_root = tmp_path / ".jeff_runtime"

    assert context.startup_summary == f"Startup is initializing empty runtime state under {runtime_root}."
    assert (runtime_root / "config" / "runtime.lock.json").exists()
    assert (runtime_root / "state" / "canonical_state.json").exists()
    assert (runtime_root / "state" / "transitions").exists()
    assert (runtime_root / "artifacts" / "research").exists()
    assert not any((runtime_root / "flows" / "flow_runs").glob("*.json"))
    assert not any((runtime_root / "reviews" / "selection_reviews").glob("*.json"))
    assert (runtime_root / "cache").exists()
    assert (runtime_root / "logs").exists()
    assert len(tuple((runtime_root / "state" / "transitions").glob("*.json"))) == 2


def test_startup_loads_persisted_canonical_state_instead_of_rebuilding_demo_world(tmp_path: Path) -> None:
    context = build_startup_interface_context(base_dir=tmp_path)
    runtime_store = context.runtime_store
    assert runtime_store is not None

    result = runtime_store.apply_transition(
        context.state,
        TransitionRequest(
            transition_id="transition-project-2",
            transition_type="create_project",
            basis_state_version=context.state.state_meta.state_version,
            scope=Scope(project_id="project-2"),
            payload={"name": "Persisted Project"},
        ),
    )

    reloaded = build_startup_interface_context(base_dir=tmp_path)

    assert result.transition_result == "committed"
    assert reloaded.startup_summary == f"Startup loaded persisted runtime state from {tmp_path / '.jeff_runtime'}."
    assert tuple(reloaded.state.projects.keys()) == ("project-1", "project-2")
    assert reloaded.state.state_meta.state_version == result.state.state_meta.state_version


def test_lawful_transition_updates_persisted_snapshot_and_transition_audit_record(tmp_path: Path) -> None:
    context = build_startup_interface_context(base_dir=tmp_path)
    runtime_store = context.runtime_store
    assert runtime_store is not None

    result = runtime_store.apply_transition(
        context.state,
        TransitionRequest(
            transition_id="transition-project-2",
            transition_type="create_project",
            basis_state_version=context.state.state_meta.state_version,
            scope=Scope(project_id="project-2"),
            payload={"name": "Persisted Project"},
        ),
    )
    canonical_payload = json.loads((tmp_path / ".jeff_runtime" / "state" / "canonical_state.json").read_text(encoding="utf-8"))
    transition_payload = json.loads(
        (tmp_path / ".jeff_runtime" / "state" / "transitions" / "transition-project-2.json").read_text(encoding="utf-8")
    )

    assert result.transition_result == "committed"
    assert canonical_payload["state"]["state_meta"]["state_version"] == 3
    assert canonical_payload["state"]["state_meta"]["last_transition_id"] == "transition-project-2"
    assert "project-2" in canonical_payload["state"]["projects"]
    assert transition_payload["request"]["transition_id"] == "transition-project-2"
    assert transition_payload["result"]["transition_result"] == "committed"


def test_research_artifacts_persist_under_runtime_artifacts_directory(tmp_path: Path) -> None:
    _write_runtime_config(tmp_path, artifact_store_root=".jeff_runtime/research_artifacts")
    context = build_startup_interface_context(base_dir=tmp_path)
    assert context.research_artifact_store is not None

    record = build_research_artifact_record(_research_request(), _evidence_pack(), _artifact())
    path = context.research_artifact_store.save(record)

    assert path.parent == tmp_path / ".jeff_runtime" / "artifacts" / "research"
    assert path.exists()


def test_startup_keeps_legacy_research_artifact_path_readable_while_writing_new_path(tmp_path: Path) -> None:
    legacy_root = tmp_path / ".jeff_runtime" / "research_artifacts"
    legacy_store = ResearchArtifactStore(legacy_root)
    legacy_record = build_research_artifact_record(_research_request(), _evidence_pack(), _artifact())
    legacy_store.save(legacy_record)
    _write_runtime_config(tmp_path, artifact_store_root=".jeff_runtime/research_artifacts")

    context = build_startup_interface_context(base_dir=tmp_path)
    assert context.research_artifact_store is not None

    loaded = context.research_artifact_store.load(legacy_record.artifact_id)
    listed = context.research_artifact_store.list_records(run_id="run-1")

    assert loaded == legacy_record
    assert listed == (legacy_record,)
    assert context.research_artifact_store.path_for(legacy_record.artifact_id).parent == (
        tmp_path / ".jeff_runtime" / "artifacts" / "research"
    )


def test_flow_run_support_records_persist_and_reload_without_becoming_canonical_truth(tmp_path: Path) -> None:
    _runtime_context_without_selection_review(tmp_path)
    reloaded = build_startup_interface_context(base_dir=tmp_path)
    canonical_payload = json.loads((tmp_path / ".jeff_runtime" / "state" / "canonical_state.json").read_text(encoding="utf-8"))

    assert "run-1" in reloaded.flow_runs
    assert reloaded.flow_runs["run-1"].lifecycle.flow_id == "flow-1"
    assert "flow_runs" not in canonical_payload
    assert "flows" not in canonical_payload["state"]


def test_selection_review_support_records_persist_and_reload_without_becoming_canonical_truth(tmp_path: Path) -> None:
    context, _selection_review_path = _runtime_context_without_selection_review(tmp_path)
    reloaded = build_startup_interface_context(base_dir=tmp_path)
    cli = JeffCLI(context=reloaded)
    canonical_payload = json.loads((tmp_path / ".jeff_runtime" / "state" / "canonical_state.json").read_text(encoding="utf-8"))

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")

    payload = json.loads(
        cli.run_one_shot(
            '/selection override proposal-2 --why "Use the persisted alternate option." run-1',
            json_output=True,
        )
    )

    assert "run-1" in context.flow_runs
    assert payload["override"]["chosen_proposal_id"] == "proposal-2"
    assert "selection_reviews" not in canonical_payload
    assert "reviews" not in canonical_payload["state"]


def test_cli_session_scope_is_not_persisted_as_canonical_truth(tmp_path: Path) -> None:
    context = build_startup_interface_context(base_dir=tmp_path)
    cli = JeffCLI(context=context)
    transitions_dir = tmp_path / ".jeff_runtime" / "state" / "transitions"
    initial_state_version = context.state.state_meta.state_version
    initial_transition_count = len(tuple(transitions_dir.glob("*.json")))

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")

    reloaded = build_startup_interface_context(base_dir=tmp_path)
    canonical_payload = json.loads((tmp_path / ".jeff_runtime" / "state" / "canonical_state.json").read_text(encoding="utf-8"))

    assert reloaded.state.state_meta.state_version == initial_state_version
    assert len(tuple(transitions_dir.glob("*.json"))) == initial_transition_count
    assert "active_context" not in canonical_payload["state"]


def test_second_mutation_lock_fails_fast_for_concurrent_writer(tmp_path: Path) -> None:
    store = PersistedRuntimeStore.from_base_dir(base_dir=tmp_path)
    first_lock = store.acquire_mutation_lock()

    try:
        competing_store = PersistedRuntimeStore.from_base_dir(base_dir=tmp_path)
        try:
            competing_store.acquire_mutation_lock()
        except RuntimeMutationLockError as exc:
            assert "persisted runtime mutation is already in progress" in str(exc)
        else:
            raise AssertionError("expected competing runtime mutation lock acquisition to fail")
    finally:
        first_lock.release()


def test_existing_persisted_runtime_remains_readable_while_mutation_lock_is_held(tmp_path: Path) -> None:
    build_startup_interface_context(base_dir=tmp_path)
    locked_store = PersistedRuntimeStore.from_base_dir(base_dir=tmp_path)
    first_lock = locked_store.acquire_mutation_lock()

    try:
        reloaded = build_startup_interface_context(base_dir=tmp_path)
    finally:
        first_lock.release()

    assert "project-1" in reloaded.state.projects
    assert reloaded.startup_summary == f"Startup loaded persisted runtime state from {tmp_path / '.jeff_runtime'}."


def test_missing_runtime_initialization_fails_fast_when_mutation_lock_is_held(tmp_path: Path) -> None:
    locked_store = PersistedRuntimeStore.from_base_dir(base_dir=tmp_path)
    first_lock = locked_store.acquire_mutation_lock()

    try:
        try:
            build_startup_interface_context(base_dir=tmp_path)
        except RuntimeMutationLockError as exc:
            assert "persisted runtime mutation is already in progress" in str(exc)
        else:
            raise AssertionError("expected startup initialization to fail while mutation lock is held")
    finally:
        first_lock.release()


def test_reset_runtime_home_uses_runtime_lock_contract_under_contention(tmp_path: Path) -> None:
    build_startup_interface_context(base_dir=tmp_path)
    locked_store = PersistedRuntimeStore.from_base_dir(base_dir=tmp_path)
    first_lock = locked_store.acquire_mutation_lock()

    try:
        competing_store = PersistedRuntimeStore.from_base_dir(base_dir=tmp_path)
        with pytest.raises(RuntimeMutationLockError, match="persisted runtime mutation is already in progress"):
            competing_store.reset_runtime_home()
    finally:
        first_lock.release()


def test_reset_runtime_cli_reports_truthful_lock_conflict_without_raw_os_error(tmp_path: Path) -> None:
    build_startup_interface_context(base_dir=tmp_path)
    locked_store = PersistedRuntimeStore.from_base_dir(base_dir=tmp_path)
    first_lock = locked_store.acquire_mutation_lock()

    try:
        result = run_jeff("--reset-runtime", cwd=tmp_path)
    finally:
        first_lock.release()

    assert result.returncode == 2
    assert "persisted runtime mutation is already in progress by another Jeff process" in result.stderr
    assert "WinError" not in result.stderr
    assert "PermissionError" not in result.stderr


def test_runtime_home_can_be_reset_and_rebuilt_cleanly(tmp_path: Path) -> None:
    original = build_startup_interface_context(base_dir=tmp_path)
    runtime_store = original.runtime_store
    assert runtime_store is not None
    runtime_root = tmp_path / ".jeff_runtime"
    stale_file = runtime_root / "cache" / "stale.txt"
    stale_file.write_text("stale runtime residue", encoding="utf-8")
    assert runtime_root.exists()

    runtime_store.reset_runtime_home()

    assert runtime_root.exists()
    assert not stale_file.exists()
    assert (runtime_root / "config" / "runtime.lock.json").exists()
    assert not (runtime_root / "state" / "canonical_state.json").exists()

    rebuilt = build_startup_interface_context(base_dir=tmp_path)

    assert rebuilt.startup_summary == f"Startup is initializing empty runtime state under {runtime_root}."
    assert (runtime_root / "state" / "canonical_state.json").exists()


def test_run_execution_evidence_persists_and_reloads_cleanly(tmp_path: Path, monkeypatch) -> None:
    import jeff.bootstrap as bootstrap_module
    from jeff.memory import InMemoryMemoryStore

    (tmp_path / "jeff.runtime.toml").write_text(
        """
[runtime]
default_adapter_id = "fake-default"

[research]
artifact_store_root = "artifacts/research"
enable_memory_handoff = true

[research.memory]
backend = "postgres"
postgres_dsn = "postgresql://user:pass@localhost:5432/jeff_test"

[[adapters]]
adapter_id = "fake-default"
provider_kind = "fake"
model_name = "fake-model"
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(bootstrap_module, "_build_postgres_memory_store", lambda _config: InMemoryMemoryStore())

    startup = build_startup_interface_context(base_dir=tmp_path)
    assert startup.runtime_store is not None

    cli = JeffCLI(
        context=InterfaceContext(
            state=startup.state,
            flow_runs=startup.flow_runs,
            selection_reviews=startup.selection_reviews,
            infrastructure_services=_run_infrastructure_services(),
            memory_store=startup.memory_store,
            runtime_store=startup.runtime_store,
            startup_summary=startup.startup_summary,
        )
    )
    monkeypatch.setattr(
        command_scope,
        "_build_repo_local_validation_plan",
        lambda _context: RepoLocalValidationPlan(
            command_id="reload_validation_probe",
            argv=(sys.executable, "-c", "print('persisted validation ok')"),
            working_directory=str(tmp_path),
            description="Run a persisted validation probe.",
            timeout_seconds=30,
        ),
    )

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    created_payload = cli.execute('/run "Persist execution evidence across reload."', json_output=True).json_payload

    assert created_payload is not None
    assert created_payload["truth"]["run_id"] == "run-1"
    assert created_payload["truth"]["run_lifecycle_state"] == "completed"
    assert created_payload["truth"]["last_execution_status"] == "completed"
    assert created_payload["support"]["execution_summary"]["execution_command_id"] == "reload_validation_probe"

    reloaded = build_startup_interface_context(base_dir=tmp_path)
    flow_run = reloaded.flow_runs["run-1"]
    execution = flow_run.outputs["execution"]

    assert execution.execution_command_id == "reload_validation_probe"
    assert execution.execution_family == "repo_local_validation"
    assert execution.exit_code == 0
    assert "persisted validation ok" in (execution.stdout_excerpt or "")

    reloaded_cli = JeffCLI(context=reloaded)
    reloaded_cli.run_one_shot("/project use project-1")
    reloaded_cli.run_one_shot("/work use wu-1")
    reloaded_cli.run_one_shot("/run use run-1")
    reloaded_payload = json.loads(reloaded_cli.run_one_shot("/show", json_output=True))

    assert reloaded_payload["truth"]["run_lifecycle_state"] == "completed"
    assert reloaded_payload["truth"]["last_execution_status"] == "completed"
    assert reloaded_payload["truth"]["last_outcome_state"] == "complete"
    assert reloaded_payload["truth"]["last_evaluation_verdict"] == "acceptable"
    assert reloaded_payload["derived"]["memory_handoff_attempted"] is True
    assert reloaded_payload["derived"]["memory_handoff_result"]["write_outcome"] == "write"
    assert reloaded_payload["support"]["execution_summary"]["execution_command_id"] == "reload_validation_probe"
    assert reloaded_payload["support"]["execution_summary"]["exit_code"] == 0


def test_bound_approval_record_and_revalidate_route_persist_and_reload(tmp_path: Path, monkeypatch) -> None:
    startup = build_startup_interface_context(base_dir=tmp_path)
    assert startup.runtime_store is not None

    cli = JeffCLI(
        context=InterfaceContext(
            state=startup.state,
            flow_runs=startup.flow_runs,
            selection_reviews=startup.selection_reviews,
            infrastructure_services=_run_infrastructure_services(),
            runtime_store=startup.runtime_store,
            startup_summary=startup.startup_summary,
        )
    )
    monkeypatch.setattr(
        command_scope,
        "build_run_governance_inputs",
        lambda *, context, scope: (
            Policy(approval_required=True),
            Approval.absent(),
            CurrentTruthSnapshot(scope=scope, state_version=context.state.state_meta.state_version),
        ),
    )

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    created_payload = cli.execute('/run "Persist approval state across reload."', json_output=True).json_payload
    approve_payload = cli.execute("/approve", json_output=True).json_payload

    assert created_payload is not None
    assert approve_payload is not None
    assert created_payload["truth"]["run_id"] == "run-1"
    assert approve_payload["derived"]["effect_state"] == "approval_recorded"

    reloaded = build_startup_interface_context(base_dir=tmp_path)

    assert reloaded.selection_reviews["run-1"].governance_approval is not None
    assert reloaded.selection_reviews["run-1"].governance_approval.approval_verdict == "granted"
    assert reloaded.flow_runs["run-1"].routing_decision is not None
    assert reloaded.flow_runs["run-1"].routing_decision.routed_outcome == "revalidate"


def test_show_read_path_materializes_support_without_persisting_selection_review(tmp_path: Path) -> None:
    context, selection_review_path = _runtime_context_without_selection_review(tmp_path)
    cli = JeffCLI(context=context)

    payload = json.loads(cli.run_one_shot("/show run-1", json_output=True))

    assert payload["view"] == "run_show"
    assert payload["support"]["proposal_summary"]["available"] is True
    assert payload["support"]["proposal_summary"]["selected_proposal_id"] == "proposal-1"
    assert not selection_review_path.exists()


def test_inspect_read_path_materializes_support_without_persisting_selection_review(tmp_path: Path) -> None:
    context, selection_review_path = _runtime_context_without_selection_review(tmp_path)
    cli = JeffCLI(context=context)
    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")

    payload = json.loads(cli.run_one_shot("/inspect", json_output=True))

    assert payload["view"] == "run_show"
    assert payload["support"]["live_context"]["purpose"].startswith("operator explanation proposal support ")
    assert payload["support"]["proposal_summary"]["available"] is True
    assert not selection_review_path.exists()


def test_selection_show_read_path_materializes_support_without_persisting_selection_review(tmp_path: Path) -> None:
    context, selection_review_path = _runtime_context_without_selection_review(tmp_path)
    cli = JeffCLI(context=context)

    payload = json.loads(cli.run_one_shot("/selection show run-1", json_output=True))

    assert payload["view"] == "selection_review"
    assert payload["selection"]["selected_proposal_id"] == "proposal-1"
    assert payload["action_formation"]["action_formed"] is True
    assert payload["support"]["selection_review_attached"] is True
    assert payload["support"]["materialized_effective_proposal_available"] is True
    assert not selection_review_path.exists()


def test_read_only_commands_do_not_collide_with_mutation_lock(tmp_path: Path) -> None:
    context, selection_review_path = _runtime_context_without_selection_review(tmp_path)
    locked_store = PersistedRuntimeStore.from_base_dir(base_dir=tmp_path)
    first_lock = locked_store.acquire_mutation_lock()

    try:
        show_cli = JeffCLI(context=context)
        inspect_cli = JeffCLI(context=context)
        inspect_cli.run_one_shot("/project use project-1")
        inspect_cli.run_one_shot("/work use wu-1")

        show_payload = json.loads(show_cli.run_one_shot("/show run-1", json_output=True))
        selection_payload = json.loads(show_cli.run_one_shot("/selection show run-1", json_output=True))
        inspect_payload = json.loads(inspect_cli.run_one_shot("/inspect", json_output=True))
    finally:
        first_lock.release()

    assert show_payload["truth"]["run_id"] == "run-1"
    assert selection_payload["truth"]["run_id"] == "run-1"
    assert inspect_payload["truth"]["run_id"] == "run-1"
    assert not selection_review_path.exists()


def test_selection_override_persists_materialized_review_on_mutating_path(tmp_path: Path) -> None:
    context, selection_review_path = _runtime_context_without_selection_review(tmp_path)
    cli = JeffCLI(context=context)

    payload = json.loads(
        cli.run_one_shot(
            '/selection override proposal-2 --why "Use the alternate bounded option." run-1',
            json_output=True,
        )
    )

    assert payload["view"] == "selection_override_receipt"
    assert payload["override"]["chosen_proposal_id"] == "proposal-2"
    assert selection_review_path.exists()


def test_approve_persists_derived_selection_review_on_lawful_mutating_path(tmp_path: Path) -> None:
    context, selection_review_path = _approval_required_runtime_context_without_selection_review(tmp_path)
    cli = JeffCLI(context=context)
    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    cli.run_one_shot("/run use run-1")

    payload = json.loads(cli.run_one_shot("/approve", json_output=True))
    reloaded = build_startup_interface_context(base_dir=tmp_path)

    assert payload["derived"]["effect_state"] == "approval_recorded"
    assert selection_review_path.exists()
    assert reloaded.selection_reviews["run-1"].governance_approval is not None
    assert reloaded.selection_reviews["run-1"].governance_approval.approval_verdict == "granted"


def _write_runtime_config(tmp_path: Path, *, artifact_store_root: str) -> Path:
    config_path = tmp_path / "jeff.runtime.toml"
    config_path.write_text(
        f"""
[runtime]
default_adapter_id = "fake-default"

[research]
artifact_store_root = "{artifact_store_root}"
enable_memory_handoff = true

[[adapters]]
adapter_id = "fake-default"
provider_kind = "fake"
model_name = "fake-model"

[[adapters]]
adapter_id = "fake-research"
provider_kind = "fake"
model_name = "fake-research-model"

[purpose_overrides]
research = "fake-research"
""".strip(),
        encoding="utf-8",
    )


def _runtime_context_without_selection_review(tmp_path: Path) -> tuple[InterfaceContext, Path]:
    startup = build_startup_interface_context(base_dir=tmp_path)
    assert startup.runtime_store is not None
    startup.runtime_store.apply_transition(
        startup.state,
        TransitionRequest(
            transition_id="transition-run-1",
            transition_type="create_run",
            basis_state_version=startup.state.state_meta.state_version,
            scope=Scope(project_id="project-1", work_unit_id="wu-1"),
            payload={"run_id": "run-1"},
        ),
    )
    reloaded = build_startup_interface_context(base_dir=tmp_path)
    flow_run = build_flow_run(Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1"))
    reloaded.runtime_store.save_flow_run("run-1", flow_run)
    selection_review_path = startup.runtime_store.home.selection_reviews_dir / "run-1.json"
    if selection_review_path.exists():
        selection_review_path.unlink()
    return (
        InterfaceContext(
            state=reloaded.state,
            flow_runs={"run-1": flow_run},
            selection_reviews={},
            infrastructure_services=reloaded.infrastructure_services,
            research_artifact_store=reloaded.research_artifact_store,
            research_archive_store=reloaded.research_archive_store,
            knowledge_store=reloaded.knowledge_store,
            memory_store=reloaded.memory_store,
            research_memory_handoff_enabled=reloaded.research_memory_handoff_enabled,
            runtime_store=reloaded.runtime_store,
            startup_summary=reloaded.startup_summary,
        ),
        selection_review_path,
    )


def _approval_required_runtime_context_without_selection_review(tmp_path: Path) -> tuple[InterfaceContext, Path]:
    startup = build_startup_interface_context(base_dir=tmp_path)
    assert startup.runtime_store is not None
    startup.runtime_store.apply_transition(
        startup.state,
        TransitionRequest(
            transition_id="transition-run-1",
            transition_type="create_run",
            basis_state_version=startup.state.state_meta.state_version,
            scope=Scope(project_id="project-1", work_unit_id="wu-1"),
            payload={"run_id": "run-1"},
        ),
    )
    reloaded = build_startup_interface_context(base_dir=tmp_path)
    run_scope = Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1")
    approval_flow_run = build_flow_run(
        run_scope,
        lifecycle_state="waiting",
        current_stage="governance",
        approval_required=True,
        approval_granted=False,
        routed_outcome="approval_required",
        route_reason="required approval is absent",
    )
    reloaded.runtime_store.save_flow_run("run-1", approval_flow_run)
    selection_review_path = reloaded.runtime_store.home.selection_reviews_dir / "run-1.json"
    if selection_review_path.exists():
        selection_review_path.unlink()
    return (
        InterfaceContext(
            state=reloaded.state,
            flow_runs={"run-1": approval_flow_run},
            selection_reviews={},
            infrastructure_services=reloaded.infrastructure_services,
            research_artifact_store=reloaded.research_artifact_store,
            research_archive_store=reloaded.research_archive_store,
            knowledge_store=reloaded.knowledge_store,
            memory_store=reloaded.memory_store,
            research_memory_handoff_enabled=reloaded.research_memory_handoff_enabled,
            runtime_store=reloaded.runtime_store,
            startup_summary=reloaded.startup_summary,
        ),
        selection_review_path,
    )
    return config_path


def _run_infrastructure_services():
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
        "OPTION_1_TITLE: Run the bounded validation suite\n"
        "OPTION_1_SUMMARY: Run the smallest truthful repo-local validation step now.\n"
        "OPTION_1_WHY_NOW: The lawful live context already supports immediate bounded validation.\n"
        "OPTION_1_ASSUMPTIONS: Current support remains stable\n"
        "OPTION_1_RISKS: Validation may reveal bounded regressions\n"
        "OPTION_1_CONSTRAINTS: Stay inside the current project scope\n"
        "OPTION_1_BLOCKERS: NONE\n"
        "OPTION_1_PLANNING_NEEDED: no\n"
        "OPTION_1_FEASIBILITY: High under the current bounded support\n"
        "OPTION_1_REVERSIBILITY: Straightforward rerun\n"
        "OPTION_1_SUPPORT_REFS: ctx-1\n"
    )


def _research_request() -> ResearchRequest:
    return ResearchRequest(
        question="What does the bounded plan support?",
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        source_mode="local_documents",
    )


def _evidence_pack() -> EvidencePack:
    return EvidencePack(
        question="What does the bounded plan support?",
        sources=(
            SourceItem(
                source_id="source-1",
                source_type="document",
                title="Plan",
                locator="doc://plan",
                snippet="Bounded plan snippet",
            ),
        ),
        evidence_items=(EvidenceItem(text="Bounded plan evidence", source_refs=("source-1",)),),
    )


def _artifact() -> ResearchArtifact:
    return ResearchArtifact(
        question="What does the bounded plan support?",
        summary="The bounded plan supports a narrow rollout.",
        findings=(ResearchFinding(text="The plan stays narrow.", source_refs=("source-1",)),),
        inferences=("A bounded rollout is better supported.",),
        uncertainties=("No external validation.",),
        recommendation="Proceed carefully.",
        source_ids=("source-1",),
    )
