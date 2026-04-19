"""Small explicit command handlers over backend read surfaces and flow outputs."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass, field
import json
import re
import shlex
from typing import Mapping

from jeff.action.execution import ExecutionResult
from jeff.cognitive import (
    ContextPackage,
    ProposalGenerationBridgeResult,
    ProposalInputPackage,
    ResearchArtifactRecord,
    ResearchArtifact,
    ResearchFinding,
    ResearchArtifactStore,
    ResearchOperatorSurfaceError,
    ResearchRequest,
    ResearchSynthesisRuntimeError,
    ResearchSynthesisValidationError,
    assemble_context_package,
    SelectionResult,
    handoff_persisted_research_record_to_memory,
    run_and_persist_document_research,
    run_and_persist_web_research,
)
from jeff.cognitive.post_selection.action_formation import (
    ActionFormationRequest,
    FormedActionResult,
    form_action_from_materialized_proposal,
)
from jeff.cognitive.post_selection.action_resolution import (
    ResolvedSelectionActionBasis,
    SelectionActionResolutionRequest,
    resolve_selection_action_basis,
)
from jeff.cognitive.post_selection.effective_proposal import (
    MaterializedEffectiveProposal,
    SelectionEffectiveProposalRequest,
    materialize_effective_proposal,
)
from jeff.cognitive.post_selection.governance_handoff import (
    ActionGovernanceHandoffRequest,
    GovernedActionHandoffResult,
    handoff_action_to_governance,
)
from jeff.cognitive.post_selection.override import (
    OperatorSelectionOverride,
    OperatorSelectionOverrideRequest,
    build_operator_selection_override,
)
from jeff.cognitive.proposal import ProposalResult
from jeff.cognitive.proposal import (
    ProposalGenerationBridgeRequest,
    build_and_run_proposal_generation,
)
from jeff.cognitive.research.archive import ResearchArchiveStore
from jeff.cognitive.research.debug import finding_source_refs_summary, summarize_values
from jeff.cognitive.types import TriggerInput, require_text
from jeff.core.containers.models import Project, Run, WorkUnit
from jeff.core.schemas import Scope
from jeff.core.state.models import GlobalState
from jeff.core.transition import TransitionRequest, apply_transition
from jeff.governance import Approval, CurrentTruthSnapshot, Policy
from jeff.infrastructure import InfrastructureServices
from jeff.knowledge import KnowledgeStore
from jeff.memory import InMemoryMemoryStore, MemoryWriteDecision
from jeff.orchestrator import FlowRunResult
from jeff.runtime_persistence import PersistedRuntimeStore

from .json_views import (
    lifecycle_json,
    project_list_json,
    research_error_json,
    research_result_json,
    request_receipt_json,
    run_list_json,
    run_show_json,
    selection_override_receipt_json,
    selection_review_json,
    session_scope_json,
    trace_json,
    work_unit_list_json,
)
from .render import (
    render_help,
    render_lifecycle,
    render_project_list,
    render_research_result,
    render_request_receipt,
    render_research_debug_event,
    render_run_list,
    render_run_show,
    render_scope,
    render_selection_override_receipt,
    render_selection_review,
    render_trace,
    render_work_unit_list,
)
from .session import CliSession


@dataclass(frozen=True, slots=True)
class SelectionReviewRecord:
    selection_result: SelectionResult | None = None
    operator_override: OperatorSelectionOverride | None = None
    resolved_basis: ResolvedSelectionActionBasis | None = None
    materialized_effective_proposal: MaterializedEffectiveProposal | None = None
    formed_action_result: FormedActionResult | None = None
    governance_handoff_result: GovernedActionHandoffResult | None = None
    proposal_result: ProposalResult | None = None
    action_scope: Scope | None = None
    basis_state_version: int | None = None
    governance_policy: Policy | None = None
    governance_approval: Approval | None = None
    governance_truth: CurrentTruthSnapshot | None = None


@dataclass(frozen=True, slots=True)
class InterfaceContext:
    state: GlobalState
    flow_runs: Mapping[str, FlowRunResult] = field(default_factory=dict)
    selection_reviews: Mapping[str, SelectionReviewRecord] = field(default_factory=dict)
    infrastructure_services: InfrastructureServices | None = None
    research_artifact_store: ResearchArtifactStore | None = None
    research_archive_store: ResearchArchiveStore | None = None
    knowledge_store: KnowledgeStore | None = None
    memory_store: InMemoryMemoryStore | None = None
    research_memory_handoff_enabled: bool = True
    runtime_store: PersistedRuntimeStore | None = None
    startup_summary: str | None = None


@dataclass(frozen=True, slots=True)
class ResearchCommandSpec:
    mode: str
    question: str
    inputs: tuple[str, ...]
    handoff_memory: bool = False


@dataclass(frozen=True, slots=True)
class CommandResult:
    context: InterfaceContext
    session: CliSession
    text: str
    json_payload: dict[str, object] | None = None
    debug_events: tuple[dict[str, object], ...] = ()


def assemble_live_context_package(
    *,
    context: InterfaceContext,
    trigger_summary: str,
    purpose: str,
    scope: Scope,
    support_inputs=(),
    knowledge_topic_query: str | None = None,
) -> ContextPackage:
    selection_review = _selection_review_for_context(context=context, scope=scope)
    governance_readiness = None
    if (
        selection_review is not None
        and selection_review.governance_handoff_result is not None
        and selection_review.governance_handoff_result.governance_result is not None
    ):
        governance_readiness = selection_review.governance_handoff_result.governance_result.readiness

    return assemble_context_package(
        trigger=TriggerInput(trigger_summary=trigger_summary),
        purpose=purpose,
        scope=scope,
        state=context.state,
        support_inputs=tuple(support_inputs),
        memory_store=context.memory_store,
        knowledge_store=context.knowledge_store,
        archive_store=context.research_archive_store,
        knowledge_topic_query=knowledge_topic_query,
        governance_truth=None if selection_review is None else selection_review.governance_truth,
        governance_policy=None if selection_review is None else selection_review.governance_policy,
        governance_approval=None if selection_review is None else selection_review.governance_approval,
        governance_readiness=governance_readiness,
    )


def _selection_review_for_context(*, context: InterfaceContext, scope: Scope) -> SelectionReviewRecord | None:
    if scope.run_id is None:
        return None

    run_id = str(scope.run_id)
    return _materialize_selection_review_from_available_data(
        existing_review=context.selection_reviews.get(run_id),
        flow_run=context.flow_runs.get(run_id),
    )


def _proposal_followup_context_purpose(question: str) -> str:
    return f"proposal support {question}"


def _inspect_live_context_purpose(work_unit: WorkUnit) -> str:
    return f"operator explanation proposal support {work_unit.objective}"


def _build_inspect_live_context_package(
    *,
    context: InterfaceContext,
    project: Project,
    work_unit: WorkUnit,
    run: Run,
) -> ContextPackage:
    return assemble_live_context_package(
        context=context,
        trigger_summary=work_unit.objective,
        purpose=_inspect_live_context_purpose(work_unit),
        scope=Scope(
            project_id=str(project.project_id),
            work_unit_id=str(work_unit.work_unit_id),
            run_id=str(run.run_id),
        ),
        knowledge_topic_query=work_unit.objective,
    )


def _research_record_to_artifact(record: ResearchArtifactRecord) -> ResearchArtifact:
    return ResearchArtifact(
        question=record.question,
        summary=record.summary,
        findings=tuple(
            ResearchFinding(text=finding.text, source_refs=finding.source_refs) for finding in record.findings
        ),
        inferences=record.inferences,
        uncertainties=record.uncertainties,
        recommendation=record.recommendation,
        source_ids=record.source_ids,
    )


def _proposal_input_package_from_research_artifact(
    *,
    record: ResearchArtifactRecord,
    research_artifact: ResearchArtifact,
) -> ProposalInputPackage:
    return ProposalInputPackage(
        package_id=f"proposal-input:{record.artifact_id}",
        source_proposal_support_package_id=f"research-artifact:{record.artifact_id}",
        proposal_input_ready=True,
        supported_findings=tuple(finding.text for finding in research_artifact.findings),
        inference_points=research_artifact.inferences,
        uncertainty_points=research_artifact.uncertainties,
        contradiction_notes=(),
        recommendation_candidates=(
            () if research_artifact.recommendation is None else (research_artifact.recommendation,)
        ),
        missing_information_markers=(),
        provenance_refs=research_artifact.source_ids,
        summary=(
            "Proposal-input package built directly from the preserved research artifact for proposal generation only. "
            "It remains support-only and is not proposal output, not selection, not action, not permission, not "
            "governance, and not execution."
        ),
    )


def _build_live_context_proposal_followup(
    *,
    context: InterfaceContext,
    research_request: ResearchRequest,
    record: ResearchArtifactRecord,
) -> tuple[ContextPackage | None, ProposalGenerationBridgeResult | None, str | None]:
    if context.infrastructure_services is None:
        return None, None, "proposal follow-up requires configured InfrastructureServices"

    research_artifact = _research_record_to_artifact(record)
    context_package = assemble_live_context_package(
        context=context,
        trigger_summary=research_request.question,
        purpose=_proposal_followup_context_purpose(research_request.question),
        scope=research_request.scope,
    )
    try:
        proposal_input_package = _proposal_input_package_from_research_artifact(
            record=record,
            research_artifact=research_artifact,
        )
        bridge_result = build_and_run_proposal_generation(
            ProposalGenerationBridgeRequest(
                request_id=f"{record.artifact_id}:proposal-generation",
                proposal_input_package=proposal_input_package,
                context_package=context_package,
                research_artifact=research_artifact,
                infrastructure_services=context.infrastructure_services,
                bounded_objective=research_request.question,
                visible_constraints=research_request.constraints,
            )
        )
        return context_package, bridge_result, None
    except Exception as exc:
        return context_package, None, str(exc)


def _latest_research_checkpoint(debug_events: tuple[dict[str, object], ...]) -> str | None:
    for event in reversed(debug_events):
        checkpoint = event.get("checkpoint")
        if isinstance(checkpoint, str) and checkpoint.strip():
            return checkpoint
    return None


def _latest_research_count(debug_events: tuple[dict[str, object], ...], *field_names: str) -> int | None:
    for event in reversed(debug_events):
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        for field_name in field_names:
            value = payload.get(field_name)
            if isinstance(value, bool):
                continue
            if isinstance(value, int):
                return value
    return None


def _annotate_research_runtime_error(
    error: ResearchSynthesisRuntimeError,
    *,
    research_request: ResearchRequest,
    spec: ResearchCommandSpec,
    debug_events: tuple[dict[str, object], ...],
) -> None:
    setattr(error, "question", research_request.question)
    setattr(error, "provided_input_count", len(spec.inputs))
    setattr(error, "stage", "synthesis")
    checkpoint = _latest_research_checkpoint(debug_events)
    if checkpoint is not None:
        setattr(error, "checkpoint", checkpoint)
    resolved_source_count = _latest_research_count(
        debug_events,
        "projected_source_count",
        "source_item_count",
        "source_count",
    )
    if resolved_source_count is not None:
        setattr(error, "resolved_source_count", resolved_source_count)


def _research_surface_error_from_backend_failure(
    *,
    spec: ResearchCommandSpec,
    research_request: ResearchRequest,
    exc: Exception,
    debug_events: tuple[dict[str, object], ...],
) -> ResearchOperatorSurfaceError:
    reason = str(exc)
    failure_kind = "synthesis_problem"
    error_code = "synthesis_validation_error"
    stage = "synthesis"
    missing_inputs = tuple(getattr(exc, "missing_inputs", ()))

    if missing_inputs:
        failure_kind = "input_problem"
        error_code = "missing_input_paths"
        stage = "source_acquisition"
    elif _looks_like_source_acquisition_failure(reason):
        failure_kind = "source_acquisition_problem"
        error_code = "source_acquisition_failed"
        stage = "source_acquisition"
    elif isinstance(exc, (ResearchSynthesisValidationError, ValueError)):
        failure_kind = "synthesis_problem"
        error_code = "synthesis_validation_error"
        stage = "synthesis"

    return ResearchOperatorSurfaceError(
        failure_kind=failure_kind,
        error_code=error_code,
        reason=reason,
        research_mode=spec.mode,
        project_id=research_request.project_id,
        work_unit_id=research_request.work_unit_id,
        run_id=research_request.run_id,
        question=research_request.question,
        stage=stage,
        checkpoint=_latest_research_checkpoint(debug_events),
        provided_input_count=getattr(exc, "provided_input_count", len(spec.inputs)),
        resolved_source_count=_latest_research_count(
            debug_events,
            "projected_source_count",
            "source_item_count",
            "source_count",
        ),
        missing_inputs=missing_inputs,
    )


def _looks_like_source_acquisition_failure(reason: str) -> bool:
    markers = (
        "explicit document paths were missing",
        "document source collection requires explicit document_paths",
        "document discovery requires explicit document_paths",
        "no supported document sources were collected",
        "document evidence pack requires at least one document source",
        "no evidence items were extracted from collected documents",
        "web source collection requires explicit web_queries",
        "no supported web sources were collected",
        "web evidence pack requires at least one web source",
        "no evidence items were extracted from collected web sources",
    )
    return any(marker in reason for marker in markers)


GENERAL_RESEARCH_PROJECT_ID = "general_research"


def execute_command(
    *,
    command_line: str,
    session: CliSession,
    context: InterfaceContext,
    json_output: bool | None = None,
    live_debug_emitter: Callable[[str], None] | None = None,
) -> CommandResult:
    tokens = _parse(command_line)
    if not tokens:
        return CommandResult(context=context, session=session, text="")

    if tokens[0] == "help":
        return CommandResult(context=context, session=session, text=render_help())

    if tokens[0] == "project":
        return _project_command(tokens=tokens, session=session, context=context)
    if tokens[0] == "work":
        return _work_command(tokens=tokens, session=session, context=context)
    if tokens[0] == "run":
        return _run_command(tokens=tokens, session=session, context=context)
    if tokens[0] == "scope":
        return _scope_command(tokens=tokens, session=session, context=context)
    if tokens[0] == "mode":
        return _mode_command(tokens=tokens, session=session, context=context)
    if tokens[0] == "json":
        return _json_command(tokens=tokens, session=session, context=context)
    if tokens[0] == "inspect":
        result = _inspect_command(tokens=tokens, session=session, context=context)
        return _apply_json_mode(result, json_output=json_output)
    if tokens[0] == "show":
        result = _show_command(tokens=tokens, session=session, context=context)
        return _apply_json_mode(result, json_output=json_output)
    if tokens[0] == "selection":
        result = _selection_command(tokens=tokens, session=session, context=context)
        return _apply_json_mode(result, json_output=json_output)
    if tokens[0] == "trace":
        result = _trace_command(tokens=tokens, session=session, context=context)
        return _apply_json_mode(result, json_output=json_output)
    if tokens[0] == "lifecycle":
        result = _lifecycle_command(tokens=tokens, session=session, context=context)
        return _apply_json_mode(result, json_output=json_output)
    if tokens[0] == "research":
        try:
            result = _research_command(
                command_line=command_line,
                tokens=tokens,
                session=session,
                context=context,
                live_debug_emitter=live_debug_emitter,
            )
        except ResearchOperatorSurfaceError as exc:
            if not (json_output is True or (json_output is None and session.json_output)):
                raise
            payload = research_error_json(
                project_id=exc.project_id,
                work_unit_id=exc.work_unit_id,
                run_id=exc.run_id,
                research_mode=exc.research_mode,
                error=exc,
                session=session,
                debug_events=tuple(getattr(exc, "debug_events", ())),
            )
            payload = _with_debug_payload(payload, debug_events=getattr(exc, "debug_events", ()), session=session)
            return CommandResult(
                context=context,
                session=session,
                text=json.dumps(payload, sort_keys=True),
                json_payload=payload,
                debug_events=tuple(getattr(exc, "debug_events", ())),
            )
        except ResearchSynthesisRuntimeError as exc:
            if not (json_output is True or (json_output is None and session.json_output)):
                raise
            payload = research_error_json(
                project_id=exc.project_id,
                work_unit_id=exc.work_unit_id,
                run_id=exc.run_id,
                research_mode=exc.research_mode,
                error=exc,
                session=session,
                debug_events=tuple(getattr(exc, "debug_events", ())),
            )
            payload = _with_debug_payload(payload, debug_events=getattr(exc, "debug_events", ()), session=session)
            return CommandResult(
                context=context,
                session=session,
                text=json.dumps(payload, sort_keys=True),
                json_payload=payload,
                debug_events=tuple(getattr(exc, "debug_events", ())),
            )
        return _apply_json_mode(result, json_output=json_output)
    if tokens[0] in {"approve", "reject", "retry", "revalidate", "recover"}:
        result = _request_command(tokens=tokens, session=session, context=context)
        return _apply_json_mode(result, json_output=json_output)

    raise ValueError(
        f"unsupported command: {' '.join(tokens)}. "
        "Jeff CLI is command-driven; use /help to see supported slash commands."
    )


def _parse(command_line: str) -> list[str]:
    normalized = command_line.strip()
    if not normalized:
        return []
    if normalized.startswith("/"):
        normalized = normalized[1:]
    return shlex.split(normalized)


def _project_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    if len(tokens) < 2:
        raise ValueError("project command requires list or use")
    if tokens[1] == "list":
        projects = tuple(context.state.projects.values())
        payload = project_list_json(projects)
        return CommandResult(context=context, session=session, text=render_project_list(payload), json_payload=payload)
    if tokens[1] == "use" and len(tokens) == 3:
        project = _get_project(context, tokens[2])
        next_session = session.with_scope(project_id=str(project.project_id), work_unit_id=None, run_id=None)
        return CommandResult(
            context=context,
            session=next_session,
            text=f"session scope updated: project_id={project.project_id}",
        )
    raise ValueError("project command must be 'project list' or 'project use <project_id>'")


def _work_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    project = _require_scoped_project(session, context)
    if len(tokens) < 2:
        raise ValueError("work command requires list or use")
    if tokens[1] == "list":
        payload = work_unit_list_json(project)
        return CommandResult(context=context, session=session, text=render_work_unit_list(payload), json_payload=payload)
    if tokens[1] == "use" and len(tokens) == 3:
        work_unit = _get_work_unit(project, tokens[2])
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


def _run_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    project = _require_scoped_project(session, context)
    work_unit = _require_scoped_work_unit(session, project)
    if len(tokens) < 2:
        raise ValueError("run command must be 'run list' or 'run use <run_id>'")
    if tokens[1] == "list" and len(tokens) == 2:
        payload = run_list_json(project, work_unit)
        return CommandResult(context=context, session=session, text=render_run_list(payload), json_payload=payload)
    if len(tokens) != 3 or tokens[1] != "use":
        raise ValueError("run command must be 'run list' or 'run use <run_id>'")
    run = _get_run(work_unit, tokens[2])
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


def _scope_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    if len(tokens) != 2:
        raise ValueError("scope command must be 'scope show' or 'scope clear'")
    if tokens[1] == "show":
        payload = session_scope_json(session)
        return CommandResult(context=context, session=session, text=render_scope(payload), json_payload=payload)
    if tokens[1] == "clear":
        next_session = session.clear_scope()
        return CommandResult(context=context, session=next_session, text="session scope cleared")
    raise ValueError("scope command must be 'scope show' or 'scope clear'")


def _mode_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    if len(tokens) != 2 or tokens[1] not in {"compact", "debug"}:
        raise ValueError("mode command must be 'mode compact' or 'mode debug'")
    next_session = session.with_mode(tokens[1])  # type: ignore[arg-type]
    return CommandResult(context=context, session=next_session, text=f"output mode set to {tokens[1]}")


def _json_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    if len(tokens) != 2 or tokens[1] not in {"on", "off"}:
        raise ValueError("json command must be 'json on' or 'json off'")
    enabled = tokens[1] == "on"
    next_session = session.with_json_output(enabled)
    return CommandResult(context=context, session=next_session, text=f"json_output set to {enabled}")


def _inspect_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    if len(tokens) != 1:
        raise ValueError("inspect uses the current work_unit scope only. Use /show <run_id> for manual historical inspect.")
    project = _require_scoped_project(session, context)
    work_unit = _require_scoped_work_unit(session, project)
    run, next_session, next_context, notice = _resolve_or_create_active_run(
        session=session,
        context=context,
        project=project,
        work_unit=work_unit,
    )
    flow_run = next_context.flow_runs.get(str(run.run_id))
    next_context, selection_review = _ensure_selection_review_for_run(context=next_context, run=run, flow_run=flow_run)
    live_context_package = _build_inspect_live_context_package(
        context=next_context,
        project=project,
        work_unit=work_unit,
        run=run,
    )
    payload = run_show_json(
        project=project,
        work_unit=work_unit,
        run=run,
        flow_run=flow_run,
        selection_review=selection_review,
        live_context_package=live_context_package,
    )
    text = render_run_show(payload)
    if notice is not None:
        text = f"{notice}\n{text}"
    return CommandResult(context=next_context, session=next_session, text=text, json_payload=payload)


def _show_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    run, next_session, notice = _resolve_historical_run(
        tokens=tokens,
        session=session,
        context=context,
        command_name=tokens[0],
    )
    project = _require_project_for_run(context, run.project_id)
    work_unit = project.work_units[run.work_unit_id]
    flow_run = context.flow_runs.get(str(run.run_id))
    next_context, selection_review = _ensure_selection_review_for_run(context=context, run=run, flow_run=flow_run)
    payload = run_show_json(
        project=project,
        work_unit=work_unit,
        run=run,
        flow_run=flow_run,
        selection_review=selection_review,
    )
    text = render_run_show(payload)
    if notice is not None:
        text = f"{notice}\n{text}"
    return CommandResult(context=next_context, session=next_session, text=text, json_payload=payload)


def _selection_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    if len(tokens) < 2:
        raise ValueError(
            "selection command must be 'selection show [run_id]' or "
            "'selection override <proposal_id> --why \"operator rationale\" [run_id]'"
        )

    if tokens[1] == "show":
        return _selection_show_command(tokens=tokens, session=session, context=context)
    if tokens[1] == "override":
        return _selection_override_command(tokens=tokens, session=session, context=context)

    raise ValueError(
        "selection command must be 'selection show [run_id]' or "
        "'selection override <proposal_id> --why \"operator rationale\" [run_id]'"
    )


def _selection_show_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    if len(tokens) > 3:
        raise ValueError("selection show must be 'selection show [run_id]'")
    run, next_session, notice = _resolve_historical_run(
        tokens=["selection", *tokens[2:]],
        session=session,
        context=context,
        command_name="selection show",
    )
    project = _require_project_for_run(context, run.project_id)
    work_unit = project.work_units[run.work_unit_id]
    flow_run = context.flow_runs.get(str(run.run_id))
    next_context, selection_review = _ensure_selection_review_for_run(context=context, run=run, flow_run=flow_run)
    payload = selection_review_json(
        project=project,
        work_unit=work_unit,
        run=run,
        flow_run=flow_run,
        selection_review=selection_review,
    )
    text = render_selection_review(payload)
    if notice is not None:
        text = f"{notice}\n{text}"
    return CommandResult(context=next_context, session=next_session, text=text, json_payload=payload)


def _selection_override_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    proposal_id, operator_rationale, run_token = _parse_selection_override_tokens(tokens)
    run_tokens = ["selection override"] if run_token is None else ["selection override", run_token]
    run, next_session, notice = _resolve_historical_run(
        tokens=run_tokens,
        session=session,
        context=context,
        command_name="selection override",
    )
    run_id = str(run.run_id)
    flow_run = context.flow_runs.get(run_id)
    next_context, existing_review = _ensure_selection_review_for_run(context=context, run=run, flow_run=flow_run)
    if existing_review is None:
        raise ValueError(f"no selection review data is available for run {run_id}")

    selection_result = existing_review.selection_result
    if selection_result is None and flow_run is not None:
        candidate = flow_run.outputs.get("selection")
        if isinstance(candidate, SelectionResult):
            selection_result = candidate
    if selection_result is None:
        raise ValueError(f"no original SelectionResult is available for run {run_id}")

    operator_override = build_operator_selection_override(
        OperatorSelectionOverrideRequest(
            request_id=f"selection-override:{run_id}:{proposal_id}",
            selection_result=selection_result,
            chosen_proposal_id=proposal_id,
            operator_rationale=operator_rationale,
        )
    )
    updated_review = _recompute_selection_review_record(
        existing_review=existing_review,
        selection_result=selection_result,
        operator_override=operator_override,
    )
    next_context = _replace_selection_review(context=next_context, run_id=run_id, selection_review=updated_review)
    payload = selection_override_receipt_json(
        run_id=run_id,
        selection_review=updated_review,
    )
    text = render_selection_override_receipt(payload)
    if notice is not None:
        text = f"{notice}\n{text}"
    return CommandResult(context=next_context, session=next_session, text=text, json_payload=payload)


def _parse_selection_override_tokens(tokens: list[str]) -> tuple[str, str, str | None]:
    if len(tokens) not in {5, 6}:
        raise ValueError(
            "selection override must be 'selection override <proposal_id> --why \"operator rationale\" [run_id]'"
        )
    if tokens[3] != "--why":
        raise ValueError(
            "selection override must be 'selection override <proposal_id> --why \"operator rationale\" [run_id]'"
        )

    proposal_id = require_text(tokens[2], field_name="proposal_id")
    operator_rationale = require_text(tokens[4], field_name="operator_rationale")
    run_token = tokens[5] if len(tokens) == 6 else None
    return proposal_id, operator_rationale, run_token


def _ensure_selection_review_for_run(
    *,
    context: InterfaceContext,
    run: Run,
    flow_run: FlowRunResult | None,
) -> tuple[InterfaceContext, SelectionReviewRecord | None]:
    run_id = str(run.run_id)
    existing_review = context.selection_reviews.get(run_id)
    selection_review = _materialize_selection_review_from_available_data(
        existing_review=existing_review,
        flow_run=flow_run,
    )
    if selection_review is None:
        return context, None
    if existing_review == selection_review:
        return context, selection_review
    return _replace_selection_review(context=context, run_id=run_id, selection_review=selection_review), selection_review


def _materialize_selection_review_from_available_data(
    *,
    existing_review: SelectionReviewRecord | None,
    flow_run: FlowRunResult | None,
) -> SelectionReviewRecord | None:
    selection_result = None if existing_review is None else existing_review.selection_result
    if selection_result is None and flow_run is not None:
        candidate = flow_run.outputs.get("selection")
        if isinstance(candidate, SelectionResult):
            selection_result = candidate

    proposal_result = None if existing_review is None else existing_review.proposal_result
    if proposal_result is None and flow_run is not None:
        candidate = flow_run.outputs.get("proposal")
        if isinstance(candidate, ProposalResult):
            proposal_result = candidate

    if existing_review is None and selection_result is None and proposal_result is None:
        return None

    operator_override = None if existing_review is None else existing_review.operator_override
    resolved_basis = None if existing_review is None else existing_review.resolved_basis
    materialized_effective_proposal = None if existing_review is None else existing_review.materialized_effective_proposal
    formed_action_result = None if existing_review is None else existing_review.formed_action_result
    governance_handoff_result = None if existing_review is None else existing_review.governance_handoff_result

    governance_policy = None if existing_review is None else existing_review.governance_policy
    if governance_policy is None and flow_run is not None:
        candidate = flow_run.outputs.get("governance_policy")
        if isinstance(candidate, Policy):
            governance_policy = candidate

    governance_approval = None if existing_review is None else existing_review.governance_approval
    if governance_approval is None and flow_run is not None:
        candidate = flow_run.outputs.get("governance_approval")
        if isinstance(candidate, Approval):
            governance_approval = candidate

    governance_truth = None if existing_review is None else existing_review.governance_truth
    if governance_truth is None and flow_run is not None:
        candidate = flow_run.outputs.get("governance_truth")
        if isinstance(candidate, CurrentTruthSnapshot):
            governance_truth = candidate

    action_scope = None if existing_review is None else existing_review.action_scope
    if action_scope is None and proposal_result is not None:
        action_scope = proposal_result.scope
    basis_state_version = None if existing_review is None else existing_review.basis_state_version
    if governance_truth is not None and basis_state_version is None:
        basis_state_version = governance_truth.state_version

    execution_result = None
    if flow_run is not None:
        candidate = flow_run.outputs.get("execution")
        if isinstance(candidate, ExecutionResult):
            execution_result = candidate
    if execution_result is not None:
        if action_scope is None:
            action_scope = execution_result.governed_request.action.scope
        if basis_state_version is None:
            basis_state_version = execution_result.governed_request.action.basis_state_version

    if (
        selection_result is not None
        and resolved_basis is None
        and (flow_run is not None or proposal_result is not None or operator_override is not None)
    ):
        resolved_basis = resolve_selection_action_basis(
            SelectionActionResolutionRequest(
                request_id=f"selection-review-resolution:{selection_result.selection_id}",
                selection_result=selection_result,
                operator_override=operator_override,
            )
        )

    if proposal_result is not None and resolved_basis is not None and materialized_effective_proposal is None:
        materialized_effective_proposal = materialize_effective_proposal(
            SelectionEffectiveProposalRequest(
                request_id=f"selection-review-materialization:{selection_result.selection_id}",
                proposal_result=proposal_result,
                resolved_basis=resolved_basis,
            )
        )

    if (
        materialized_effective_proposal is not None
        and action_scope is not None
        and basis_state_version is not None
        and formed_action_result is None
    ):
        formed_action_result = form_action_from_materialized_proposal(
            ActionFormationRequest(
                request_id=f"selection-review-action-formation:{materialized_effective_proposal.selection_id}",
                materialized_effective_proposal=materialized_effective_proposal,
                scope=action_scope,
                basis_state_version=basis_state_version,
            )
        )

    if (
        formed_action_result is not None
        and governance_policy is not None
        and governance_truth is not None
        and governance_handoff_result is None
    ):
        governance_handoff_result = handoff_action_to_governance(
            ActionGovernanceHandoffRequest(
                request_id=f"selection-review-governance-handoff:{formed_action_result.selection_id}",
                formed_action_result=formed_action_result,
                policy=governance_policy,
                approval=governance_approval,
                truth=governance_truth,
            )
        )

    return SelectionReviewRecord(
        selection_result=selection_result,
        operator_override=operator_override,
        resolved_basis=resolved_basis,
        materialized_effective_proposal=materialized_effective_proposal,
        formed_action_result=formed_action_result,
        governance_handoff_result=governance_handoff_result,
        proposal_result=proposal_result,
        action_scope=action_scope,
        basis_state_version=basis_state_version,
        governance_policy=governance_policy,
        governance_approval=governance_approval,
        governance_truth=governance_truth,
    )


def _recompute_selection_review_record(
    *,
    existing_review: SelectionReviewRecord,
    selection_result: SelectionResult,
    operator_override: OperatorSelectionOverride,
) -> SelectionReviewRecord:
    resolved_basis = resolve_selection_action_basis(
        SelectionActionResolutionRequest(
            request_id=f"selection-review-resolution:{selection_result.selection_id}",
            selection_result=selection_result,
            operator_override=operator_override,
        )
    )

    proposal_result = existing_review.proposal_result
    action_scope = existing_review.action_scope
    materialized_effective_proposal = None
    formed_action_result = None
    governance_handoff_result = None

    if proposal_result is not None:
        materialized_effective_proposal = materialize_effective_proposal(
            SelectionEffectiveProposalRequest(
                request_id=f"selection-review-materialization:{selection_result.selection_id}",
                proposal_result=proposal_result,
                resolved_basis=resolved_basis,
            )
        )

        action_scope = action_scope or proposal_result.scope
        formed_action_result = form_action_from_materialized_proposal(
            ActionFormationRequest(
                request_id=f"selection-review-action-formation:{selection_result.selection_id}",
                materialized_effective_proposal=materialized_effective_proposal,
                scope=action_scope,
                basis_state_version=_selection_review_basis_state_version(existing_review),
            )
        )

        if existing_review.governance_policy is not None and existing_review.governance_truth is not None:
            governance_handoff_result = handoff_action_to_governance(
                ActionGovernanceHandoffRequest(
                    request_id=f"selection-review-governance-handoff:{selection_result.selection_id}",
                    formed_action_result=formed_action_result,
                    policy=existing_review.governance_policy,
                    approval=existing_review.governance_approval,
                    truth=existing_review.governance_truth,
                )
            )

    return SelectionReviewRecord(
        selection_result=selection_result,
        operator_override=operator_override,
        resolved_basis=resolved_basis,
        materialized_effective_proposal=materialized_effective_proposal,
        formed_action_result=formed_action_result,
        governance_handoff_result=governance_handoff_result,
        proposal_result=proposal_result,
        action_scope=action_scope,
        basis_state_version=_selection_review_basis_state_version(existing_review),
        governance_policy=existing_review.governance_policy,
        governance_approval=existing_review.governance_approval,
        governance_truth=existing_review.governance_truth,
    )


def _selection_review_basis_state_version(selection_review: SelectionReviewRecord) -> int:
    if selection_review.basis_state_version is not None:
        return selection_review.basis_state_version
    if (
        selection_review.formed_action_result is not None
        and selection_review.formed_action_result.action is not None
    ):
        return selection_review.formed_action_result.action.basis_state_version
    if (
        selection_review.governance_handoff_result is not None
        and selection_review.governance_handoff_result.action is not None
    ):
        return selection_review.governance_handoff_result.action.basis_state_version
    return 0


def _replace_selection_review(
    *,
    context: InterfaceContext,
    run_id: str,
    selection_review: SelectionReviewRecord,
) -> InterfaceContext:
    if context.runtime_store is not None:
        context.runtime_store.save_selection_review(run_id, selection_review)
    next_reviews = dict(context.selection_reviews)
    next_reviews[run_id] = selection_review
    return InterfaceContext(
        state=context.state,
        flow_runs=context.flow_runs,
        selection_reviews=next_reviews,
        infrastructure_services=context.infrastructure_services,
        research_artifact_store=context.research_artifact_store,
        research_archive_store=context.research_archive_store,
        knowledge_store=context.knowledge_store,
        memory_store=context.memory_store,
        research_memory_handoff_enabled=context.research_memory_handoff_enabled,
        runtime_store=context.runtime_store,
        startup_summary=context.startup_summary,
    )


def _trace_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    run, next_session, notice = _resolve_historical_run(
        tokens=tokens,
        session=session,
        context=context,
        command_name=tokens[0],
    )
    flow_run = _require_flow_run(context, str(run.run_id))
    payload = trace_json(flow_run)
    text = render_trace(payload)
    if notice is not None:
        text = f"{notice}\n{text}"
    return CommandResult(context=context, session=next_session, text=text, json_payload=payload)


def _lifecycle_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    run, next_session, notice = _resolve_historical_run(
        tokens=tokens,
        session=session,
        context=context,
        command_name=tokens[0],
    )
    flow_run = _require_flow_run(context, str(run.run_id))
    payload = lifecycle_json(flow_run)
    text = render_lifecycle(payload)
    if notice is not None:
        text = f"{notice}\n{text}"
    return CommandResult(context=context, session=next_session, text=text, json_payload=payload)


def _research_command(
    *,
    command_line: str,
    tokens: list[str],
    session: CliSession,
    context: InterfaceContext,
    live_debug_emitter: Callable[[str], None] | None = None,
) -> CommandResult:
    spec = _parse_research_command(command_line=command_line, tokens=tokens)
    project, work_unit, run, next_session, next_context, scope_notice = _resolve_research_scope(
        mode=spec.mode,
        question=spec.question,
        session=session,
        context=context,
    )
    research_request = ResearchRequest(
        question=spec.question,
        project_id=str(project.project_id),
        work_unit_id=str(work_unit.work_unit_id),
        run_id=str(run.run_id),
        source_mode="local_documents" if spec.mode == "docs" else "web",
        document_paths=spec.inputs if spec.mode == "docs" else (),
        web_queries=spec.inputs if spec.mode == "web" else (),
    )
    debug_collector = _ResearchDebugCollector(
        session=next_session,
        live_debug_emitter=live_debug_emitter if next_session.output_mode == "debug" else None,
    )
    try:
        try:
            record = _run_research_backend(
                spec=spec,
                research_request=research_request,
                context=next_context,
                debug_emitter=debug_collector.emit,
            )
        except ResearchSynthesisRuntimeError as exc:
            _annotate_research_runtime_error(
                exc,
                research_request=research_request,
                spec=spec,
                debug_events=tuple(debug_collector.events),
            )
            raise
        except Exception as exc:
            raise _research_surface_error_from_backend_failure(
                spec=spec,
                research_request=research_request,
                exc=exc,
                debug_events=tuple(debug_collector.events),
            ) from exc
        live_context_package = None
        proposal_followup_result = None
        proposal_followup_issue = None
        try:
            (
                live_context_package,
                proposal_followup_result,
                proposal_followup_issue,
            ) = _build_live_context_proposal_followup(
                context=next_context,
                research_request=research_request,
                record=record,
            )
        except Exception as exc:
            proposal_followup_issue = str(exc)
        memory_handoff_result = _maybe_handoff_research_record_to_memory(
            context=next_context,
            spec=spec,
            record=record,
        )
        debug_collector.emit(
            {
                "domain": "research",
                "checkpoint": "projection_started",
                "payload": {
                    "source_item_count": len(record.source_items),
                    "artifact_source_ids": summarize_values(tuple(record.source_ids)),
                    "finding_source_refs_summary": finding_source_refs_summary(record.findings),
                },
            }
        )
        try:
            artifact_store = _require_research_store(next_context)
            artifact_locator = str(artifact_store.path_for(record.artifact_id).resolve())
            payload = research_result_json(
                project_id=str(project.project_id),
                work_unit_id=str(work_unit.work_unit_id),
                run_id=str(run.run_id),
                research_mode=spec.mode,
                handoff_memory_requested=spec.handoff_memory,
                record=record,
                memory_handoff_result=memory_handoff_result,
                session=next_session,
                artifact_locator=artifact_locator,
                live_context_package=live_context_package,
                proposal_followup_result=proposal_followup_result,
                proposal_followup_issue=proposal_followup_issue,
            )
        except Exception as exc:
            debug_collector.emit(
                {
                    "domain": "research",
                    "checkpoint": "projection_failed",
                    "payload": {
                        "reason": str(exc),
                        "source_item_count": len(record.source_items),
                        "artifact_source_ids": summarize_values(tuple(record.source_ids)),
                        "finding_source_refs_summary": finding_source_refs_summary(record.findings),
                    },
                }
            )
            raise ResearchOperatorSurfaceError(
                failure_kind="projection_problem",
                error_code="projection_failed",
                reason=str(exc),
                research_mode=spec.mode,
                project_id=str(project.project_id),
                work_unit_id=str(work_unit.work_unit_id),
                run_id=str(run.run_id),
                question=research_request.question,
                stage="projection",
                checkpoint="projection_failed",
                provided_input_count=len(spec.inputs),
                resolved_source_count=len(record.source_items),
            ) from exc
        debug_collector.emit(
            {
                "domain": "research",
                "checkpoint": "projection_succeeded",
                "payload": {
                    "projected_source_count": len(payload["support"]["sources"]),
                    "artifact_source_ids": summarize_values(tuple(record.source_ids)),
                    "finding_source_refs_summary": finding_source_refs_summary(record.findings),
                },
            }
        )
        debug_collector.emit(
            {
                "domain": "research",
                "checkpoint": "render_started",
                "payload": {
                    "projected_source_count": len(payload["support"]["sources"]),
                },
            }
        )
        try:
            text = render_research_result(payload)
        except Exception as exc:
            debug_collector.emit(
                {
                    "domain": "research",
                    "checkpoint": "render_failed",
                    "payload": {
                        "reason": str(exc),
                        "projected_source_count": len(payload["support"]["sources"]),
                    },
                }
            )
            raise ResearchOperatorSurfaceError(
                failure_kind="render_problem",
                error_code="render_failed",
                reason=str(exc),
                research_mode=spec.mode,
                project_id=str(project.project_id),
                work_unit_id=str(work_unit.work_unit_id),
                run_id=str(run.run_id),
                question=research_request.question,
                stage="render",
                checkpoint="render_failed",
                provided_input_count=len(spec.inputs),
                resolved_source_count=len(payload["support"]["sources"]),
            ) from exc
        debug_collector.emit(
            {
                "domain": "research",
                "checkpoint": "render_succeeded",
                "payload": {
                    "projected_source_count": len(payload["support"]["sources"]),
                },
            }
        )
        if scope_notice is not None:
            text = f"{scope_notice}\n{text}"
        return CommandResult(
            context=next_context,
            session=next_session,
            text=text,
            json_payload=payload,
            debug_events=tuple(debug_collector.events),
        )
    except Exception as exc:
        if debug_collector.events:
            try:
                setattr(exc, "debug_events", tuple(debug_collector.events))
            except Exception:
                pass
        raise


def _request_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    request_type = tokens[0]
    target_run = _resolve_run_from_tokens(tokens=tokens, session=session, context=context, command_name=tokens[0])
    flow_run = _require_flow_run(context, str(target_run.run_id))
    routed_outcome = None if flow_run.routing_decision is None else flow_run.routing_decision.routed_outcome

    allowed_outcomes = {
        "approve": {"approval_required"},
        "reject": {"approval_required"},
        "retry": {"retry"},
        "revalidate": {"revalidate"},
        "recover": {"recover"},
    }
    if routed_outcome not in allowed_outcomes[request_type]:
        raise ValueError(
            f"{request_type} is not currently available for run {target_run.run_id}; "
            f"current routed_outcome is {routed_outcome or 'none'}"
        )

    note = (
        f"{request_type} request accepted for run {target_run.run_id}; "
        "this records request entry only and does not imply apply, completion, or truth mutation."
    )
    payload = request_receipt_json(
        request_type=request_type,
        target=str(target_run.run_id),
        accepted=True,
        scope={
            "project_id": session.scope.project_id,
            "work_unit_id": session.scope.work_unit_id,
            "run_id": session.scope.run_id,
        },
        note=note,
    )
    return CommandResult(context=context, session=session, text=render_request_receipt(payload), json_payload=payload)


def _apply_json_mode(result: CommandResult, *, json_output: bool | None) -> CommandResult:
    if not (result.json_payload and (json_output is True or (json_output is None and result.session.json_output))):
        return result
    payload = _with_debug_payload(result.json_payload, debug_events=result.debug_events, session=result.session)
    return CommandResult(
        context=result.context,
        session=result.session,
        text=json.dumps(payload, sort_keys=True),
        json_payload=payload,
        debug_events=result.debug_events,
    )


def _get_project(context: InterfaceContext, project_id: str) -> Project:
    try:
        return context.state.projects[project_id]
    except KeyError as exc:
        raise ValueError(
            f"unknown project_id: {project_id}. Use /project list to discover valid project_id values."
        ) from exc


def _require_scoped_project(session: CliSession, context: InterfaceContext) -> Project:
    if session.scope.project_id is None:
        raise ValueError(
            "current session scope has no project_id. "
            "Use /project list, then /project use <project_id>."
        )
    return _get_project(context, session.scope.project_id)


def _get_work_unit(project: Project, work_unit_id: str) -> WorkUnit:
    try:
        return project.work_units[work_unit_id]
    except KeyError as exc:
        raise ValueError(
            f"unknown work_unit_id: {work_unit_id}. Use /work list to discover valid work_unit_id values."
        ) from exc


def _require_scoped_work_unit(session: CliSession, project: Project) -> WorkUnit:
    if session.scope.work_unit_id is None:
        raise ValueError(
            "current session scope has no work_unit_id. "
            "Use /work list, then /work use <work_unit_id>."
        )
    return _get_work_unit(project, session.scope.work_unit_id)


def _get_run(work_unit: WorkUnit, run_id: str) -> Run:
    try:
        return work_unit.runs[run_id]
    except KeyError as exc:
        raise ValueError(
            f"unknown run_id: {run_id}. Use /run list to discover valid run_id values."
        ) from exc


def _resolve_run_from_tokens(
    *,
    tokens: list[str],
    session: CliSession,
    context: InterfaceContext,
    command_name: str,
) -> Run:
    run_id = tokens[1] if len(tokens) > 1 else session.scope.run_id
    if run_id is None:
        raise ValueError(_missing_run_message(command_name))
    if session.scope.project_id is not None:
        project = _get_project(context, session.scope.project_id)
        if session.scope.work_unit_id is not None:
            work_unit = _get_work_unit(project, session.scope.work_unit_id)
            return _get_run(work_unit, run_id)

        matches = [
            work_unit.runs[run_id]
            for work_unit in project.work_units.values()
            if run_id in work_unit.runs
        ]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ValueError(
                f"ambiguous run_id: {run_id} requires work_unit scope inside current project scope {project.project_id}. "
                "Use /work list, then /work use <work_unit_id>."
            )
        raise ValueError(
            f"unknown run_id: {run_id} in current project scope {project.project_id}. "
            "Use /work list or /run list to discover valid IDs."
        )

    matches = [
        work_unit.runs[run_id]
        for project in context.state.projects.values()
        for work_unit in project.work_units.values()
        if run_id in work_unit.runs
    ]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(
            f"ambiguous run_id: {run_id} requires project or work_unit scope. "
            "Use /project list, /project use <project_id>, and /work list to narrow scope."
        )
    raise ValueError(f"unknown run_id: {run_id}. Use /project list, /work list, or /run list to discover valid IDs.")


def _resolve_historical_run(
    *,
    tokens: list[str],
    session: CliSession,
    context: InterfaceContext,
    command_name: str,
) -> tuple[Run, CliSession, str | None]:
    if len(tokens) > 1:
        run = _resolve_run_from_tokens(tokens=tokens, session=session, context=context, command_name=command_name)
        return run, session, None
    if session.scope.run_id is not None:
        run = _resolve_run_from_tokens(tokens=tokens, session=session, context=context, command_name=command_name)
        return run, session, None
    if session.scope.project_id is None or session.scope.work_unit_id is None:
        raise ValueError(
            f"{command_name} requires a current run, an explicit <run_id>, or selected work_unit scope. "
            "Use /project list, /project use <project_id>, /work list, and /work use <work_unit_id>."
        )
    project = _get_project(context, session.scope.project_id)
    work_unit = _get_work_unit(project, session.scope.work_unit_id)
    run = _select_existing_run(work_unit)
    if run is None:
        raise ValueError(
            f"{command_name} found no existing run in work_unit {work_unit.work_unit_id}. "
            "Use /inspect to create and select a new run, or /run list to confirm history."
        )
    next_session = session.with_scope(
        project_id=str(project.project_id),
        work_unit_id=str(work_unit.work_unit_id),
        run_id=str(run.run_id),
    )
    return run, next_session, f"auto-selected current run: {run.run_id}"


def _parse_research_command(*, command_line: str, tokens: list[str]) -> ResearchCommandSpec:
    if len(tokens) < 2:
        raise ValueError("research command requires 'research docs' or 'research web'")

    mode = tokens[1]
    if mode not in {"docs", "web"}:
        raise ValueError("research mode must be 'docs' or 'web'")

    normalized = command_line.strip()
    if normalized.startswith("/"):
        normalized = normalized[1:]
    match = re.match(r"^research\s+(docs|web)\s+(?P<rest>.+)$", normalized)
    if match is None:
        raise ValueError("research command requires a quoted question/objective")

    rest = match.group("rest").lstrip()
    if not rest or rest[0] not in {'"', "'"}:
        raise ValueError("research command requires a quoted question/objective immediately after the mode")

    parsed_rest = shlex.split(rest)
    if not parsed_rest:
        raise ValueError("research command requires a quoted question/objective")

    question = parsed_rest[0].strip()
    if not question:
        raise ValueError("research question/objective must be non-empty")

    handoff_memory = False
    inputs = list(parsed_rest[1:])
    if "--handoff-memory" in inputs:
        if inputs.count("--handoff-memory") > 1 or inputs[-1] != "--handoff-memory":
            raise ValueError("research accepts only one trailing optional flag: --handoff-memory")
        handoff_memory = True
        inputs = inputs[:-1]

    unsupported_flags = [item for item in inputs if item.startswith("--")]
    if unsupported_flags:
        raise ValueError(f"unsupported research flag: {unsupported_flags[0]}")

    if mode == "docs" and not inputs:
        raise ValueError("research docs requires at least one explicit path after the quoted question/objective")
    if mode == "web" and not inputs:
        raise ValueError("research web requires at least one explicit query after the quoted question/objective")

    return ResearchCommandSpec(
        mode=mode,
        question=question,
        inputs=tuple(inputs),
        handoff_memory=handoff_memory,
    )


def _resolve_research_scope(
    *,
    mode: str,
    question: str,
    session: CliSession,
    context: InterfaceContext,
) -> tuple[Project, WorkUnit, Run, CliSession, InterfaceContext, str | None]:
    if session.scope.project_id is None:
        return _resolve_general_research_scope(
            mode=mode,
            question=question,
            session=session,
            context=context,
        )

    project = _require_scoped_project(session, context)
    if session.scope.work_unit_id is None:
        raise ValueError(
            "research requires current work_unit scope inside the selected project. "
            "Use /work list, then /work use <work_unit_id>; or /scope clear for ad-hoc general_research."
        )
    work_unit = _get_work_unit(project, session.scope.work_unit_id)
    run, next_session, next_context, notice = _resolve_or_create_active_run(
        session=session,
        context=context,
        project=project,
        work_unit=work_unit,
    )
    return project, work_unit, run, next_session, next_context, notice


def _resolve_general_research_scope(
    *,
    mode: str,
    question: str,
    session: CliSession,
    context: InterfaceContext,
) -> tuple[Project, WorkUnit, Run, CliSession, InterfaceContext, str]:
    next_context = context
    notices: list[str] = []

    project, next_context, created_project = _ensure_project_exists(
        context=next_context,
        project_id=GENERAL_RESEARCH_PROJECT_ID,
        name="General Research",
    )
    if created_project:
        notices.append(f"created built-in project: {GENERAL_RESEARCH_PROJECT_ID}")

    work_unit_id = _general_research_work_unit_id(mode=mode, question=question)
    objective = f"Ad-hoc {mode} research: {question}"
    work_unit, next_context, created_work_unit = _ensure_work_unit_exists(
        context=next_context,
        project=project,
        work_unit_id=work_unit_id,
        objective=objective,
    )
    if created_work_unit:
        notices.append(f"created ad-hoc research work_unit: {work_unit_id}")

    scoped_session = session.with_scope(
        project_id=str(project.project_id),
        work_unit_id=str(work_unit.work_unit_id),
        run_id=None,
    )
    run, next_session, next_context, run_notice = _resolve_or_create_active_run(
        session=scoped_session,
        context=next_context,
        project=project,
        work_unit=work_unit,
    )
    notices.insert(
        0,
        (
            "anchored ad-hoc research into "
            f"project_id={project.project_id} work_unit_id={work_unit.work_unit_id}"
        ),
    )
    if run_notice is not None:
        notices.append(run_notice)
    return project, work_unit, run, next_session, next_context, "\n".join(notices)


def _resolve_or_create_active_run(
    *,
    session: CliSession,
    context: InterfaceContext,
    project: Project,
    work_unit: WorkUnit,
) -> tuple[Run, CliSession, InterfaceContext, str | None]:
    if session.scope.run_id is not None and session.scope.work_unit_id == str(work_unit.work_unit_id):
        run = _get_run(work_unit, session.scope.run_id)
        return run, session, context, None

    existing_run = _select_existing_run(work_unit)
    if existing_run is not None:
        next_session = session.with_scope(
            project_id=str(project.project_id),
            work_unit_id=str(work_unit.work_unit_id),
            run_id=str(existing_run.run_id),
        )
        return existing_run, next_session, context, f"auto-selected current run: {existing_run.run_id}"

    created_run, next_context = _create_run_for_work_unit(context=context, project=project, work_unit=work_unit)
    next_session = session.with_scope(
        project_id=str(project.project_id),
        work_unit_id=str(work_unit.work_unit_id),
        run_id=str(created_run.run_id),
    )
    return created_run, next_session, next_context, f"created and selected new run: {created_run.run_id}"


def _select_existing_run(work_unit: WorkUnit) -> Run | None:
    runs = tuple(work_unit.runs.values())
    if not runs:
        return None
    return max(runs, key=_run_sort_key)


def _run_sort_key(run: Run) -> tuple[int, str]:
    run_id = str(run.run_id)
    match = re.fullmatch(r"run-(\d+)", run_id)
    if match is not None:
        return (int(match.group(1)), run_id)
    return (-1, run_id)


def _create_run_for_work_unit(
    *,
    context: InterfaceContext,
    project: Project,
    work_unit: WorkUnit,
) -> tuple[Run, InterfaceContext]:
    next_run_id = _next_run_id(work_unit)
    request = TransitionRequest(
        transition_id=f"transition-auto-create-run-{project.project_id}-{work_unit.work_unit_id}-{next_run_id}",
        transition_type="create_run",
        basis_state_version=context.state.state_meta.state_version,
        scope=Scope(project_id=str(project.project_id), work_unit_id=str(work_unit.work_unit_id)),
        payload={"run_id": next_run_id},
    )
    result = _apply_context_transition(context=context, request=request)
    if result.transition_result != "committed":
        issue = result.validation_errors[0].message if result.validation_errors else "unknown transition failure"
        raise ValueError(f"automatic run creation failed: {issue}")
    next_context = _replace_context_state(context, result.state)
    created_project = _get_project(next_context, str(project.project_id))
    created_work_unit = _get_work_unit(created_project, str(work_unit.work_unit_id))
    return _get_run(created_work_unit, next_run_id), next_context


def _ensure_project_exists(
    *,
    context: InterfaceContext,
    project_id: str,
    name: str,
) -> tuple[Project, InterfaceContext, bool]:
    if project_id in context.state.projects:
        return context.state.projects[project_id], context, False

    result = _apply_context_transition(
        context=context,
        request=TransitionRequest(
            transition_id=f"transition-auto-create-project-{project_id}",
            transition_type="create_project",
            basis_state_version=context.state.state_meta.state_version,
            scope=Scope(project_id=project_id),
            payload={"name": name},
        ),
    )
    if result.transition_result != "committed":
        issue = result.validation_errors[0].message if result.validation_errors else "unknown transition failure"
        raise ValueError(f"automatic project creation failed: {issue}")

    next_context = _replace_context_state(context, result.state)
    return _get_project(next_context, project_id), next_context, True


def _ensure_work_unit_exists(
    *,
    context: InterfaceContext,
    project: Project,
    work_unit_id: str,
    objective: str,
) -> tuple[WorkUnit, InterfaceContext, bool]:
    if work_unit_id in project.work_units:
        return project.work_units[work_unit_id], context, False

    result = _apply_context_transition(
        context=context,
        request=TransitionRequest(
            transition_id=f"transition-auto-create-work-unit-{project.project_id}-{work_unit_id}",
            transition_type="create_work_unit",
            basis_state_version=context.state.state_meta.state_version,
            scope=Scope(project_id=str(project.project_id)),
            payload={"work_unit_id": work_unit_id, "objective": objective},
        ),
    )
    if result.transition_result != "committed":
        issue = result.validation_errors[0].message if result.validation_errors else "unknown transition failure"
        raise ValueError(f"automatic work unit creation failed: {issue}")

    next_context = _replace_context_state(context, result.state)
    next_project = _get_project(next_context, str(project.project_id))
    return _get_work_unit(next_project, work_unit_id), next_context, True


def _run_research_backend(
    *,
    spec: ResearchCommandSpec,
    research_request: ResearchRequest,
    context: InterfaceContext,
    debug_emitter=None,
) -> ResearchArtifactRecord:
    infrastructure_services = _require_research_infrastructure(context)
    artifact_store = _require_research_store(context)
    try:
        if spec.mode == "docs":
            return run_and_persist_document_research(
                research_request,
                infrastructure_services,
                artifact_store,
                archive_store=context.research_archive_store,
                debug_emitter=debug_emitter,
            )
        return run_and_persist_web_research(
            research_request,
            infrastructure_services,
            artifact_store,
            archive_store=context.research_archive_store,
            debug_emitter=debug_emitter,
        )
    except ResearchSynthesisRuntimeError as exc:
        raise exc.with_context(
            research_mode=spec.mode,
            project_id=research_request.project_id,
            work_unit_id=research_request.work_unit_id,
            run_id=research_request.run_id,
        ) from exc


def _maybe_handoff_research_record_to_memory(
    *,
    context: InterfaceContext,
    spec: ResearchCommandSpec,
    record: ResearchArtifactRecord,
) -> MemoryWriteDecision | None:
    if not spec.handoff_memory:
        return None
    memory_store = _require_memory_store(context)
    return handoff_persisted_research_record_to_memory(record, memory_store)


def _require_research_infrastructure(context: InterfaceContext) -> InfrastructureServices:
    if context.infrastructure_services is None:
        raise ValueError(
            "research runtime is not configured for this CLI context. "
            "Add jeff.runtime.toml in the startup directory to enable research CLI."
        )
    return context.infrastructure_services


def _require_research_store(context: InterfaceContext) -> ResearchArtifactStore:
    if context.research_artifact_store is None:
        raise ValueError("research artifact persistence store is not configured for this CLI context")
    return context.research_artifact_store


def _require_memory_store(context: InterfaceContext) -> InMemoryMemoryStore:
    if not context.research_memory_handoff_enabled:
        raise ValueError("research memory handoff is disabled by the current runtime config")
    if context.memory_store is None:
        raise ValueError("memory store is not configured for research handoff in this CLI context")
    return context.memory_store


def _replace_context_state(context: InterfaceContext, state: GlobalState) -> InterfaceContext:
    return InterfaceContext(
        state=state,
        flow_runs=context.flow_runs,
        selection_reviews=context.selection_reviews,
        infrastructure_services=context.infrastructure_services,
        research_artifact_store=context.research_artifact_store,
        research_archive_store=context.research_archive_store,
        knowledge_store=context.knowledge_store,
        memory_store=context.memory_store,
        research_memory_handoff_enabled=context.research_memory_handoff_enabled,
        runtime_store=context.runtime_store,
        startup_summary=context.startup_summary,
    )


def _apply_context_transition(*, context: InterfaceContext, request: TransitionRequest):
    if context.runtime_store is not None:
        return context.runtime_store.apply_transition(context.state, request)
    return apply_transition(context.state, request)


def _with_debug_payload(
    payload: dict[str, object],
    *,
    debug_events: tuple[dict[str, object], ...],
    session: CliSession,
) -> dict[str, object]:
    if session.output_mode != "debug" or not debug_events:
        return payload
    return {**payload, "debug": {"events": [dict(event) for event in debug_events]}}


@dataclass(slots=True)
class _ResearchDebugCollector:
    session: CliSession
    live_debug_emitter: Callable[[str], None] | None = None
    events: list[dict[str, object]] = field(default_factory=list)

    def emit(self, event: dict[str, object]) -> None:
        self.events.append(event)
        if self.live_debug_emitter is None:
            return
        if self.session.json_output:
            self.live_debug_emitter(json.dumps({"view": "research_debug_event", "debug": event}, sort_keys=True))
            return
        self.live_debug_emitter(render_research_debug_event(event))


def _general_research_work_unit_id(*, mode: str, question: str) -> str:
    slug_parts = re.findall(r"[a-z0-9]+", question.lower())
    slug = "-".join(slug_parts[:8]) or "question"
    slug = slug[:48].strip("-")
    digest = hashlib.sha1(f"{mode}|{question}".encode("utf-8")).hexdigest()[:8]
    return f"research-{mode}-{slug}-{digest}"


def _next_run_id(work_unit: WorkUnit) -> str:
    numeric_suffixes = [
        int(match.group(1))
        for run in work_unit.runs.values()
        if (match := re.fullmatch(r"run-(\d+)", str(run.run_id))) is not None
    ]
    next_number = max(numeric_suffixes, default=0) + 1
    return f"run-{next_number}"


def _missing_run_message(command_name: str) -> str:
    return (
        f"{command_name} requires a current run or an explicit <run_id>. "
        "Use /run list, /run use <run_id>, or /scope show."
    )


def _require_project_for_run(context: InterfaceContext, project_id: str) -> Project:
    return _get_project(context, str(project_id))


def _require_flow_run(context: InterfaceContext, run_id: str) -> FlowRunResult:
    try:
        return context.flow_runs[run_id]
    except KeyError as exc:
        raise ValueError(f"no orchestrator flow result is available for run {run_id}") from exc
