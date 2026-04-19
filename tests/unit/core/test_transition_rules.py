from jeff.core.schemas import Scope
from jeff.core.state import bootstrap_global_state
from jeff.core.transition import TransitionRequest, apply_transition
from jeff.core.transition.validator import validate_candidate_state


def test_invalid_transition_requests_reject_cleanly() -> None:
    state = bootstrap_global_state()
    request = TransitionRequest(
        transition_id="transition-1",
        transition_type="create_work_unit",
        basis_state_version=0,
        scope=Scope(project_id="missing-project"),
        payload={"work_unit_id": "wu-1", "objective": "Do work"},
    )

    result = apply_transition(state, request)

    assert result.transition_result == "rejected"
    assert result.state is state
    assert result.state_after_version == 0
    assert result.validation_errors[0].code == "unknown_project"


def test_rejected_transition_does_not_change_state() -> None:
    state = bootstrap_global_state()
    request = TransitionRequest(
        transition_id="transition-1",
        transition_type="create_project",
        basis_state_version=0,
        scope=Scope(project_id="project-1"),
        payload={},
    )

    result = apply_transition(state, request)

    assert result.transition_result == "rejected"
    assert result.state is state
    assert result.changed_paths == ()
    assert result.state.projects == {}


def test_stale_basis_rejects_without_state_change() -> None:
    state = bootstrap_global_state()
    committed = apply_transition(
        state,
        TransitionRequest(
            transition_id="transition-1",
            transition_type="create_project",
            basis_state_version=0,
            scope=Scope(project_id="project-1"),
            payload={"name": "Alpha"},
        ),
    )

    stale_request = TransitionRequest(
        transition_id="transition-2",
        transition_type="create_project",
        basis_state_version=0,
        scope=Scope(project_id="project-2"),
        payload={"name": "Beta"},
    )
    rejected = apply_transition(committed.state, stale_request)

    assert committed.transition_result == "committed"
    assert rejected.transition_result == "rejected"
    assert rejected.state_after_version == committed.state.state_meta.state_version
    assert rejected.state.projects == committed.state.projects
    assert rejected.validation_errors[0].code == "stale_basis_state_version"


def test_lawful_transitions_create_valid_linked_objects() -> None:
    state = bootstrap_global_state()

    project_result = apply_transition(
        state,
        TransitionRequest(
            transition_id="transition-1",
            transition_type="create_project",
            basis_state_version=0,
            scope=Scope(project_id="project-1"),
            payload={"name": "Alpha"},
        ),
    )
    work_unit_result = apply_transition(
        project_result.state,
        TransitionRequest(
            transition_id="transition-2",
            transition_type="create_work_unit",
            basis_state_version=1,
            scope=Scope(project_id="project-1"),
            payload={"work_unit_id": "wu-1", "objective": "Ship the backbone"},
        ),
    )
    run_result = apply_transition(
        work_unit_result.state,
        TransitionRequest(
            transition_id="transition-3",
            transition_type="create_run",
            basis_state_version=2,
            scope=Scope(project_id="project-1", work_unit_id="wu-1"),
            payload={"run_id": "run-1"},
        ),
    )

    assert project_result.transition_result == "committed"
    assert work_unit_result.transition_result == "committed"
    assert run_result.transition_result == "committed"
    assert run_result.state.state_meta.state_version == 3
    assert run_result.changed_paths == ("projects.project-1.work_units.wu-1.runs.run-1",)
    assert (
        run_result.state.projects["project-1"]
        .work_units["wu-1"]
        .runs["run-1"]
        .project_id
        == "project-1"
    )
    assert validate_candidate_state(run_result.state) == ()


def test_illegal_scope_linkage_rejects_create_run() -> None:
    state = bootstrap_global_state()
    project_result = apply_transition(
        state,
        TransitionRequest(
            transition_id="transition-1",
            transition_type="create_project",
            basis_state_version=0,
            scope=Scope(project_id="project-1"),
            payload={"name": "Alpha"},
        ),
    )
    rejected = apply_transition(
        project_result.state,
        TransitionRequest(
            transition_id="transition-2",
            transition_type="create_run",
            basis_state_version=1,
            scope=Scope(project_id="project-1", work_unit_id="missing-wu"),
            payload={"run_id": "run-1"},
        ),
    )

    assert rejected.transition_result == "rejected"
    assert rejected.state == project_result.state
    assert rejected.changed_paths == ()
    assert rejected.validation_errors[0].code == "unknown_work_unit"


def test_update_run_commits_canonical_progression_fields() -> None:
    state = bootstrap_global_state()
    project_result = apply_transition(
        state,
        TransitionRequest(
            transition_id="transition-1",
            transition_type="create_project",
            basis_state_version=0,
            scope=Scope(project_id="project-1"),
            payload={"name": "Alpha"},
        ),
    )
    work_unit_result = apply_transition(
        project_result.state,
        TransitionRequest(
            transition_id="transition-2",
            transition_type="create_work_unit",
            basis_state_version=1,
            scope=Scope(project_id="project-1"),
            payload={"work_unit_id": "wu-1", "objective": "Ship the backbone"},
        ),
    )
    run_result = apply_transition(
        work_unit_result.state,
        TransitionRequest(
            transition_id="transition-3",
            transition_type="create_run",
            basis_state_version=2,
            scope=Scope(project_id="project-1", work_unit_id="wu-1"),
            payload={"run_id": "run-1"},
        ),
    )

    updated = apply_transition(
        run_result.state,
        TransitionRequest(
            transition_id="transition-4",
            transition_type="update_run",
            basis_state_version=3,
            scope=Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1"),
            payload={
                "run_lifecycle_state": "completed",
                "last_execution_status": "completed",
                "last_outcome_state": "complete",
                "last_evaluation_verdict": "acceptable",
            },
        ),
    )

    run = updated.state.projects["project-1"].work_units["wu-1"].runs["run-1"]
    assert updated.transition_result == "committed"
    assert run.run_lifecycle_state == "completed"
    assert run.last_execution_status == "completed"
    assert run.last_outcome_state == "complete"
    assert run.last_evaluation_verdict == "acceptable"


def test_update_run_rejects_without_run_scope() -> None:
    state = bootstrap_global_state()
    project_result = apply_transition(
        state,
        TransitionRequest(
            transition_id="transition-1",
            transition_type="create_project",
            basis_state_version=0,
            scope=Scope(project_id="project-1"),
            payload={"name": "Alpha"},
        ),
    )
    work_unit_result = apply_transition(
        project_result.state,
        TransitionRequest(
            transition_id="transition-2",
            transition_type="create_work_unit",
            basis_state_version=1,
            scope=Scope(project_id="project-1"),
            payload={"work_unit_id": "wu-1", "objective": "Ship the backbone"},
        ),
    )

    rejected = apply_transition(
        work_unit_result.state,
        TransitionRequest(
            transition_id="transition-3",
            transition_type="update_run",
            basis_state_version=2,
            scope=Scope(project_id="project-1", work_unit_id="wu-1"),
            payload={"run_lifecycle_state": "blocked"},
        ),
    )

    assert rejected.transition_result == "rejected"
    assert rejected.validation_errors[0].code == "missing_run_scope"
