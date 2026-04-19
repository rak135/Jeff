"""Research command parsing, scope resolution, and execution wiring."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import json
import re
import shlex

from jeff.cognitive import (
    ContextPackage,
    ProposalGenerationBridgeResult,
    ProposalInputPackage,
    ResearchArtifact,
    ResearchArtifactRecord,
    ResearchFinding,
    ResearchOperatorSurfaceError,
    ResearchRequest,
    ResearchSynthesisRuntimeError,
    ResearchSynthesisValidationError,
    handoff_persisted_research_record_to_memory,
    run_and_persist_document_research,
    run_and_persist_web_research,
)
from jeff.cognitive.post_selection.action_formation import FormedActionResult
from jeff.cognitive.post_selection.action_resolution import ResolvedSelectionActionBasis
from jeff.cognitive.post_selection.effective_proposal import MaterializedEffectiveProposal
from jeff.cognitive.post_selection.governance_handoff import GovernedActionHandoffResult
from jeff.cognitive.proposal import ProposalGenerationBridgeRequest, ProposalResult, build_and_run_proposal_generation
from jeff.cognitive.research.debug import finding_source_refs_summary, summarize_values
from jeff.core.containers.models import Project, Run, WorkUnit

from .command_common import (
    GENERAL_RESEARCH_PROJECT_ID,
    ensure_project_exists,
    ensure_work_unit_exists,
    general_research_work_unit_id,
    get_work_unit,
    require_memory_store,
    require_research_infrastructure,
    require_research_store,
    require_scoped_project,
    resolve_or_create_active_run,
)
from .command_models import CommandResult, InterfaceContext, ResearchCommandSpec
from .json_views import research_result_json
from .render import render_research_debug_event, render_research_result
from .session import CliSession


def research_command(
    *,
    command_line: str,
    tokens: list[str],
    session: CliSession,
    context: InterfaceContext,
    assemble_live_context_package_fn: Callable[..., ContextPackage],
    live_debug_emitter: Callable[[str], None] | None = None,
) -> CommandResult:
    spec = parse_research_command(command_line=command_line, tokens=tokens)
    project, work_unit, run, next_session, next_context, scope_notice = resolve_research_scope(
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
            record = run_research_backend(
                spec=spec,
                research_request=research_request,
                context=next_context,
                debug_emitter=debug_collector.emit,
            )
        except ResearchSynthesisRuntimeError as exc:
            annotate_research_runtime_error(
                exc,
                research_request=research_request,
                spec=spec,
                debug_events=tuple(debug_collector.events),
            )
            raise
        except Exception as exc:
            raise research_surface_error_from_backend_failure(
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
            ) = build_live_context_proposal_followup(
                context=next_context,
                research_request=research_request,
                record=record,
                assemble_live_context_package_fn=assemble_live_context_package_fn,
            )
        except Exception as exc:
            proposal_followup_issue = str(exc)
        memory_handoff_result = maybe_handoff_research_record_to_memory(
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
            artifact_store = require_research_store(next_context)
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


def parse_research_command(*, command_line: str, tokens: list[str]) -> ResearchCommandSpec:
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


def resolve_research_scope(
    *,
    mode: str,
    question: str,
    session: CliSession,
    context: InterfaceContext,
) -> tuple[Project, WorkUnit, Run, CliSession, InterfaceContext, str | None]:
    if session.scope.project_id is None:
        return resolve_general_research_scope(
            mode=mode,
            question=question,
            session=session,
            context=context,
        )

    project = require_scoped_project(session, context)
    if session.scope.work_unit_id is None:
        raise ValueError(
            "research requires current work_unit scope inside the selected project. "
            "Use /work list, then /work use <work_unit_id>; or /scope clear for ad-hoc general_research."
        )
    work_unit = get_work_unit(project, session.scope.work_unit_id)
    run, next_session, next_context, notice = resolve_or_create_active_run(
        session=session,
        context=context,
        project=project,
        work_unit=work_unit,
    )
    return project, work_unit, run, next_session, next_context, notice


def resolve_general_research_scope(
    *,
    mode: str,
    question: str,
    session: CliSession,
    context: InterfaceContext,
) -> tuple[Project, WorkUnit, Run, CliSession, InterfaceContext, str]:
    next_context = context
    notices: list[str] = []

    project, next_context, created_project = ensure_project_exists(
        context=next_context,
        project_id=GENERAL_RESEARCH_PROJECT_ID,
        name="General Research",
    )
    if created_project:
        notices.append(f"created built-in project: {GENERAL_RESEARCH_PROJECT_ID}")

    work_unit_id = general_research_work_unit_id(mode=mode, question=question)
    objective = f"Ad-hoc {mode} research: {question}"
    work_unit, next_context, created_work_unit = ensure_work_unit_exists(
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
    run, next_session, next_context, run_notice = resolve_or_create_active_run(
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


def build_live_context_proposal_followup(
    *,
    context: InterfaceContext,
    research_request: ResearchRequest,
    record: ResearchArtifactRecord,
    assemble_live_context_package_fn: Callable[..., ContextPackage],
) -> tuple[ContextPackage | None, ProposalGenerationBridgeResult | None, str | None]:
    if context.infrastructure_services is None:
        return None, None, "proposal follow-up requires configured InfrastructureServices"

    research_artifact = research_record_to_artifact(record)
    context_package = assemble_live_context_package_fn(
        context=context,
        trigger_summary=research_request.question,
        purpose=proposal_followup_context_purpose(research_request.question),
        scope=research_request.scope,
    )
    try:
        proposal_input_package = proposal_input_package_from_research_artifact(
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


def proposal_followup_context_purpose(question: str) -> str:
    return f"proposal support {question}"


def research_record_to_artifact(record: ResearchArtifactRecord) -> ResearchArtifact:
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


def proposal_input_package_from_research_artifact(
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


def latest_research_checkpoint(debug_events: tuple[dict[str, object], ...]) -> str | None:
    for event in reversed(debug_events):
        checkpoint = event.get("checkpoint")
        if isinstance(checkpoint, str) and checkpoint.strip():
            return checkpoint
    return None


def latest_research_count(debug_events: tuple[dict[str, object], ...], *field_names: str) -> int | None:
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


def annotate_research_runtime_error(
    error: ResearchSynthesisRuntimeError,
    *,
    research_request: ResearchRequest,
    spec: ResearchCommandSpec,
    debug_events: tuple[dict[str, object], ...],
) -> None:
    setattr(error, "question", research_request.question)
    setattr(error, "provided_input_count", len(spec.inputs))
    setattr(error, "stage", "synthesis")
    checkpoint = latest_research_checkpoint(debug_events)
    if checkpoint is not None:
        setattr(error, "checkpoint", checkpoint)
    resolved_source_count = latest_research_count(
        debug_events,
        "projected_source_count",
        "source_item_count",
        "source_count",
    )
    if resolved_source_count is not None:
        setattr(error, "resolved_source_count", resolved_source_count)


def research_surface_error_from_backend_failure(
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
    elif looks_like_source_acquisition_failure(reason):
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
        checkpoint=latest_research_checkpoint(debug_events),
        provided_input_count=getattr(exc, "provided_input_count", len(spec.inputs)),
        resolved_source_count=latest_research_count(
            debug_events,
            "projected_source_count",
            "source_item_count",
            "source_count",
        ),
        missing_inputs=missing_inputs,
    )


def looks_like_source_acquisition_failure(reason: str) -> bool:
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


def run_research_backend(
    *,
    spec: ResearchCommandSpec,
    research_request: ResearchRequest,
    context: InterfaceContext,
    debug_emitter=None,
) -> ResearchArtifactRecord:
    infrastructure_services = require_research_infrastructure(context)
    artifact_store = require_research_store(context)
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


def maybe_handoff_research_record_to_memory(
    *,
    context: InterfaceContext,
    spec: ResearchCommandSpec,
    record: ResearchArtifactRecord,
):
    if not spec.handoff_memory:
        return None
    memory_store = require_memory_store(context)
    return handoff_persisted_research_record_to_memory(record, memory_store)


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