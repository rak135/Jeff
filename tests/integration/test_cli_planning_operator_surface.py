from pathlib import Path
from types import SimpleNamespace

import pytest

import jeff.interface.commands.scope as command_scope
from jeff.bootstrap import build_startup_interface_context
from jeff.cognitive.proposal import ProposalResult, ProposalResultOption
from jeff.cognitive.selection import SelectionResult
from jeff.core.schemas import Scope
from jeff.infrastructure import (
    AdapterFactoryConfig,
    AdapterProviderKind,
    ModelAdapterRuntimeConfig,
    PurposeOverrides,
    build_infrastructure_services,
)
from jeff.interface import InterfaceContext, JeffCLI


def test_plan_surface_persists_checkpoint_progression_across_restart(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    context = build_startup_interface_context(base_dir=tmp_path)
    cli = JeffCLI(context=_with_infrastructure(context))

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")

    monkeypatch.setattr(command_scope, "_persist_run_proposal_record", lambda **kwargs: None)
    monkeypatch.setattr(command_scope, "run_proposal_generation_pipeline", _planning_pipeline_result)
    monkeypatch.setattr(command_scope, "build_and_run_selection", _planning_selection_result)

    run_payload = cli.execute('/run "Plan the bounded validation path before execution."', json_output=True).json_payload
    plan_payload = cli.execute("/plan show", json_output=True).json_payload
    steps_payload = cli.execute("/plan steps", json_output=True).json_payload
    checkpoint_payload = cli.execute("/plan checkpoint continue_next_step", json_output=True).json_payload

    assert run_payload is not None
    assert plan_payload is not None
    assert steps_payload is not None
    assert checkpoint_payload is not None
    assert run_payload["support"]["routing_decision"]["routed_outcome"] == "planning"
    assert run_payload["support"]["planning_summary"]["available"] is True
    assert plan_payload["plan"]["plan_status"] == "active"
    assert plan_payload["active_step"]["step_type"] == "review"
    assert steps_payload["steps"][0]["step_status"] == "active"
    assert checkpoint_payload["checkpoint"]["latest"]["decision"] == "continue_next_step"
    assert checkpoint_payload["checkpoint"]["active_step_id"].endswith("step-2")

    reloaded_cli = JeffCLI(context=build_startup_interface_context(base_dir=tmp_path))
    reloaded_cli.run_one_shot("/project use project-1")
    reloaded_cli.run_one_shot("/work use wu-1")
    reloaded_cli.run_one_shot("/run use run-1")

    reloaded_show = reloaded_cli.execute("/plan show", json_output=True).json_payload
    reloaded_checkpoint = reloaded_cli.execute("/plan checkpoint", json_output=True).json_payload

    assert reloaded_show is not None
    assert reloaded_checkpoint is not None
    assert reloaded_show["plan"]["active_step_id"].endswith("step-2")
    assert reloaded_show["candidate_action"]["available"] is True
    assert reloaded_show["candidate_action"]["intent_summary"] == "Prepare the bounded repo-local validation path"
    assert reloaded_checkpoint["checkpoint"]["latest"]["decision"] == "continue_next_step"


def test_run_without_planning_keeps_plan_surface_unavailable(tmp_path: Path) -> None:
    context = build_startup_interface_context(base_dir=tmp_path)
    cli = JeffCLI(context=_with_infrastructure(context))

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")

    show_payload = cli.execute('/run "What bounded rollout should execute now?"', json_output=True).json_payload

    assert show_payload is not None
    assert show_payload["support"]["planning_summary"]["available"] is False


def _with_infrastructure(context: InterfaceContext) -> InterfaceContext:
    return InterfaceContext(
        state=context.state,
        flow_runs=context.flow_runs,
        selection_reviews=context.selection_reviews,
        infrastructure_services=build_infrastructure_services(
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
                        fake_text_response="unused proposal adapter",
                    ),
                ),
                purpose_overrides=PurposeOverrides(proposal="fake-proposal"),
            )
        ),
        research_artifact_store=context.research_artifact_store,
        research_archive_store=context.research_archive_store,
        knowledge_store=context.knowledge_store,
        memory_store=context.memory_store,
        research_memory_handoff_enabled=context.research_memory_handoff_enabled,
        runtime_store=context.runtime_store,
        startup_summary=context.startup_summary,
    )


def _planning_pipeline_result(request, *, infrastructure_services):
    del infrastructure_services
    return SimpleNamespace(
        proposal_result=ProposalResult(
            request_id="proposal-run-1",
            scope=request.scope,
            scarcity_reason=None,
            options=(
                ProposalResultOption(
                    option_index=1,
                    proposal_id="proposal-1",
                    proposal_type="direct_action",
                    title="Execute now",
                    why_now="Immediate bounded action remains available.",
                    summary="Execute the bounded validation immediately",
                    planning_needed=False,
                ),
                ProposalResultOption(
                    option_index=2,
                    proposal_id="proposal-2",
                    proposal_type="planning_insertion",
                    title="Plan first",
                    why_now="This bounded path should be decomposed before action.",
                    summary="Prepare the bounded repo-local validation path",
                    constraints=("Stay inside the current repo.",),
                    blockers=("Review the current validation basis first.",),
                    main_risks=("A bounded validation run may fail and require replan.",),
                    planning_needed=True,
                ),
            ),
        )
    )


def _planning_selection_result(request):
    return SimpleNamespace(
        selection_result=SelectionResult(
            selection_id=request.selection_id,
            considered_proposal_ids=tuple(option.proposal_id for option in request.proposal_result.options),
            selected_proposal_id="proposal-2",
            rationale="The planning insertion path is selected for bounded decomposition.",
        )
    )