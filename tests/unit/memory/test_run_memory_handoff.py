from jeff.cognitive.run_memory_handoff import build_run_memory_handoff_input
from jeff.core.schemas import Scope
from jeff.memory import InMemoryMemoryStore, handoff_run_summary_to_memory

from tests.fixtures.cli import build_flow_run


def test_successful_run_handoff_builds_bounded_input_and_writes_memory() -> None:
    scope = Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1")
    flow_run = build_flow_run(scope)
    memory_store = InMemoryMemoryStore()

    handoff_input = build_run_memory_handoff_input(
        scope=scope,
        flow_run=flow_run,
        objective="Validate the bounded repo-local smoke path.",
    )
    decision = handoff_run_summary_to_memory(handoff_input, store=memory_store)

    assert len(handoff_input.summary) <= 200
    assert len(handoff_input.remembered_points) <= 5
    assert decision.write_outcome == "write"
    assert len(memory_store.list_project_records("project-1")) == 1


def test_pre_execution_hold_run_handoff_defers_in_memory_pipeline() -> None:
    scope = Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1")
    flow_run = build_flow_run(
        scope,
        lifecycle_state="waiting",
        current_stage="selection",
        approval_required=True,
        routed_outcome="defer",
        route_kind="hold",
        route_reason="Selection deferred bounded execution for operator follow-up.",
    )
    memory_store = InMemoryMemoryStore()

    handoff_input = build_run_memory_handoff_input(
        scope=scope,
        flow_run=flow_run,
        objective="Decide whether the bounded validation should proceed.",
    )
    decision = handoff_run_summary_to_memory(handoff_input, store=memory_store)

    assert handoff_input.support_quality == "weak"
    assert handoff_input.stability == "volatile"
    assert decision.write_outcome == "defer"
    assert len(memory_store.list_project_records("project-1")) == 0


def test_run_handoff_does_not_cross_project_dedupe_or_merge() -> None:
    scope_a = Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1")
    scope_b = Scope(project_id="project-2", work_unit_id="wu-2", run_id="run-2")
    flow_run_a = build_flow_run(scope_a)
    flow_run_b = build_flow_run(scope_b)
    memory_store = InMemoryMemoryStore()

    input_b = build_run_memory_handoff_input(
        scope=scope_b,
        flow_run=flow_run_b,
        objective="Validate the bounded repo-local smoke path.",
    )
    input_a = build_run_memory_handoff_input(
        scope=scope_a,
        flow_run=flow_run_a,
        objective="Validate the bounded repo-local smoke path.",
    )

    decision_b = handoff_run_summary_to_memory(input_b, store=memory_store)
    decision_a = handoff_run_summary_to_memory(input_a, store=memory_store)

    assert decision_b.write_outcome == "write"
    assert decision_a.write_outcome == "write"
    assert len(memory_store.list_project_records("project-1")) == 1
    assert len(memory_store.list_project_records("project-2")) == 1