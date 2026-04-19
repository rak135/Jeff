"""Scope, run selection, and output-mode command handlers."""

from __future__ import annotations

from jeff.action import GovernedExecutionRequest, execute_governed_action, normalize_outcome
from jeff.cognitive import ContextPackage, evaluate_outcome
from jeff.cognitive.post_selection.action_formation import ActionFormationRequest, form_action_from_materialized_proposal
from jeff.cognitive.post_selection.action_resolution import SelectionActionResolutionRequest, resolve_selection_action_basis
from jeff.cognitive.post_selection.effective_proposal import SelectionEffectiveProposalRequest, materialize_effective_proposal
from jeff.cognitive.proposal import ProposalGenerationRequest, ProposalPipelineFailure, run_proposal_generation_pipeline
from jeff.cognitive.selection import SelectionBridgeRequest, build_and_run_selection
from jeff.cognitive.types import require_text
from jeff.core.schemas import Scope
from jeff.governance import evaluate_action_entry
from jeff.orchestrator import run_flow

from .command_common import (
    assemble_live_context_package,
    build_run_governance_inputs,
    create_run_for_work_unit,
    ensure_selection_review_for_run,
    get_project,
    get_run,
    get_work_unit,
    replace_flow_run,
    require_scoped_project,
    require_scoped_work_unit,
)
from .command_models import CommandResult, InterfaceContext
from .json_views import project_list_json, run_list_json, run_show_json, session_scope_json, work_unit_list_json
from .render import render_project_list, render_run_list, render_run_show, render_scope, render_work_unit_list
from .session import CliSession


def project_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    if len(tokens) < 2:
        raise ValueError("project command requires list or use")
    if tokens[1] == "list":
        projects = tuple(context.state.projects.values())
        payload = project_list_json(projects)
        return CommandResult(context=context, session=session, text=render_project_list(payload), json_payload=payload)
    if tokens[1] == "use" and len(tokens) == 3:
        project = get_project(context, tokens[2])
        next_session = session.with_scope(project_id=str(project.project_id), work_unit_id=None, run_id=None)
        return CommandResult(
            context=context,
            session=next_session,
            text=f"session scope updated: project_id={project.project_id}",
        )
    raise ValueError("project command must be 'project list' or 'project use <project_id>'")


def work_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    project = require_scoped_project(session, context)
    if len(tokens) < 2:
        raise ValueError("work command requires list or use")
    if tokens[1] == "list":
        payload = work_unit_list_json(project)
        return CommandResult(context=context, session=session, text=render_work_unit_list(payload), json_payload=payload)
    if tokens[1] == "use" and len(tokens) == 3:
        work_unit = get_work_unit(project, tokens[2])
        next_session = session.with_scope(
            project_id=str(project.project_id),
            work_unit_id=str(work_unit.work_unit_id),
            run_id=None,
        )
        return CommandResult(
            context=context,
            session=next_session,
            text=f"session scope updated: project_id={project.project_id} work_unit_id={work_unit.work_unit_id}",
        )
    raise ValueError("work command must be 'work list' or 'work use <work_unit_id>'")


def run_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    project = require_scoped_project(session, context)
    work_unit = require_scoped_work_unit(session, project)
    if len(tokens) < 2:
        raise ValueError("run command must be 'run list', 'run use <run_id>', or 'run <objective>'")
    if tokens[1] == "list" and len(tokens) == 2:
        payload = run_list_json(project, work_unit)
        return CommandResult(context=context, session=session, text=render_run_list(payload), json_payload=payload)
    if tokens[1] == "use":
        if len(tokens) != 3:
            raise ValueError("run command must be 'run list', 'run use <run_id>', or 'run <objective>'")
        run = get_run(work_unit, tokens[2])
        next_session = session.with_scope(
            project_id=str(project.project_id),
            work_unit_id=str(work_unit.work_unit_id),
            run_id=str(run.run_id),
        )
        return CommandResult(
            context=context,
            session=next_session,
            text=(
                f"session scope updated: project_id={project.project_id} "
                f"work_unit_id={work_unit.work_unit_id} run_id={run.run_id}"
            ),
        )
    return _run_objective_command(tokens=tokens, session=session, context=context, project=project, work_unit=work_unit)


def _run_objective_command(
    *,
    tokens: list[str],
    session: CliSession,
    context: InterfaceContext,
    project,
    work_unit,
) -> CommandResult:
    objective = require_text(" ".join(tokens[1:]), field_name="objective")
    if context.infrastructure_services is None:
        raise ValueError(
            "run objective launch requires configured InfrastructureServices. "
            "Add jeff.runtime.toml in the startup directory to enable the real bounded /run path."
        )

    run, next_context = create_run_for_work_unit(context=context, project=project, work_unit=work_unit)
    run_scope = Scope(
        project_id=str(project.project_id),
        work_unit_id=str(work_unit.work_unit_id),
        run_id=str(run.run_id),
    )
    governance_policy, governance_approval, governance_truth = build_run_governance_inputs(
        context=next_context,
        scope=run_scope,
    )
    live_context_package = assemble_live_context_package(
        context=next_context,
        trigger_summary=objective,
        purpose=_run_live_context_purpose(objective),
        scope=run_scope,
        knowledge_topic_query=objective,
        governance_truth=governance_truth,
        governance_policy=governance_policy,
        governance_approval=governance_approval,
    )
    flow_run = _run_bounded_execution_flow(
        context=next_context,
        run_scope=run_scope,
        objective=objective,
        live_context_package=live_context_package,
        governance_policy=governance_policy,
        governance_approval=governance_approval,
        governance_truth=governance_truth,
    )
    flow_run.outputs["governance_policy"] = governance_policy
    flow_run.outputs["governance_approval"] = governance_approval
    flow_run.outputs["governance_truth"] = governance_truth
    next_context = replace_flow_run(context=next_context, run_id=str(run.run_id), flow_run=flow_run)
    next_context, selection_review = ensure_selection_review_for_run(
        context=next_context,
        run=run,
        flow_run=flow_run,
    )

    payload = run_show_json(
        project=project,
        work_unit=work_unit,
        run=run,
        flow_run=flow_run,
        selection_review=selection_review,
        live_context_package=live_context_package,
    )
    next_session = session.with_scope(
        project_id=str(project.project_id),
        work_unit_id=str(work_unit.work_unit_id),
        run_id=str(run.run_id),
    )
    text = f"created and launched new run: {run.run_id}\n{render_run_show(payload)}"
    return CommandResult(context=next_context, session=next_session, text=text, json_payload=payload)


def _run_live_context_purpose(objective: str) -> str:
    return f"proposal support action preparation {objective}"


def _run_bounded_execution_flow(
    *,
    context: InterfaceContext,
    run_scope: Scope,
    objective: str,
    live_context_package: ContextPackage,
    governance_policy,
    governance_approval,
    governance_truth,
):
    proposal_output_holder: dict[str, object] = {}
    action_holder: dict[str, object] = {}

    def context_stage(_input):
        return live_context_package

    def proposal_stage(context_output):
        pipeline_result = run_proposal_generation_pipeline(
            ProposalGenerationRequest(
                objective=objective,
                scope=run_scope,
                context_package=context_output,
            ),
            infrastructure_services=context.infrastructure_services,
        )
        if isinstance(pipeline_result, ProposalPipelineFailure):
            raise ValueError(
                f"proposal generation ended at {pipeline_result.failure_stage}: {pipeline_result.error}"
            )
        proposal_output_holder["proposal"] = pipeline_result.proposal_result
        return pipeline_result.proposal_result

    def selection_stage(proposal_output):
        selection_result = build_and_run_selection(
            SelectionBridgeRequest(
                request_id=f"{run_scope.run_id}:proposal-output-to-selection",
                proposal_result=proposal_output,
                selection_id=f"{run_scope.run_id}:selection",
            )
        ).selection_result
        if selection_result is None:
            raise ValueError("selection bridge returned no SelectionResult")
        return selection_result

    def action_stage(selection_output):
        proposal_output = proposal_output_holder["proposal"]
        resolved_basis = resolve_selection_action_basis(
            SelectionActionResolutionRequest(
                request_id=f"{run_scope.run_id}:selection-action-resolution",
                selection_result=selection_output,
            )
        )
        materialized = materialize_effective_proposal(
            SelectionEffectiveProposalRequest(
                request_id=f"{run_scope.run_id}:selection-effective-proposal",
                proposal_result=proposal_output,
                resolved_basis=resolved_basis,
            )
        )
        formed_action = form_action_from_materialized_proposal(
            ActionFormationRequest(
                request_id=f"{run_scope.run_id}:action-formation",
                materialized_effective_proposal=materialized,
                scope=run_scope,
                basis_state_version=governance_truth.state_version,
            )
        )
        if not formed_action.action_formed or formed_action.action is None:
            raise ValueError(formed_action.no_action_reason or "selection did not yield a directly actionable proposal")
        action_holder["action"] = formed_action.action
        return formed_action.action

    def governance_stage(action_output):
        return evaluate_action_entry(
            action=action_output,
            policy=governance_policy,
            approval=governance_approval,
            truth=governance_truth,
        )

    def execution_stage(governance_output):
        return execute_governed_action(
            GovernedExecutionRequest(action=action_holder["action"], governance_decision=governance_output),
            output_summary=f"Execution recorded the bounded repo-local run objective: {objective}",
        )

    def outcome_stage(execution_output):
        return normalize_outcome(
            execution_result=execution_output,
            outcome_state="complete",
            observed_completion_posture=f"execution {execution_output.execution_status}",
            target_effect_posture="bounded objective advanced",
            artifact_posture="artifact not required",
            side_effect_posture="contained",
        )

    def evaluation_stage(outcome_output):
        return evaluate_outcome(
            objective_summary=objective,
            outcome=outcome_output,
            evidence_quality_posture="moderate",
        )

    return run_flow(
        flow_id=f"flow:{run_scope.run_id}",
        flow_family="bounded_proposal_selection_execution",
        scope=run_scope,
        stage_handlers={
            "context": context_stage,
            "proposal": proposal_stage,
            "selection": selection_stage,
            "action": action_stage,
            "governance": governance_stage,
            "execution": execution_stage,
            "outcome": outcome_stage,
            "evaluation": evaluation_stage,
        },
    )


def scope_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    if len(tokens) != 2:
        raise ValueError("scope command must be 'scope show' or 'scope clear'")
    if tokens[1] == "show":
        payload = session_scope_json(session)
        return CommandResult(context=context, session=session, text=render_scope(payload), json_payload=payload)
    if tokens[1] == "clear":
        next_session = session.clear_scope()
        return CommandResult(context=context, session=next_session, text="session scope cleared")
    raise ValueError("scope command must be 'scope show' or 'scope clear'")


def mode_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    if len(tokens) != 2 or tokens[1] not in {"compact", "debug"}:
        raise ValueError("mode command must be 'mode compact' or 'mode debug'")
    next_session = session.with_mode(tokens[1])  # type: ignore[arg-type]
    return CommandResult(context=context, session=next_session, text=f"output mode set to {tokens[1]}")


def json_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    if len(tokens) != 2 or tokens[1] not in {"on", "off"}:
        raise ValueError("json command must be 'json on' or 'json off'")
    enabled = tokens[1] == "on"
    next_session = session.with_json_output(enabled)
    return CommandResult(context=context, session=next_session, text=f"json_output set to {enabled}")