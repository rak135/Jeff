"""Stable JSON-friendly operator views."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any

from jeff.cognitive import (
    ResearchArtifactRecord,
    ResearchSynthesisRuntimeError,
    validate_research_artifact_record,
)
from jeff.core.containers.models import Project, Run, WorkUnit
from jeff.memory import MemoryWriteDecision
from jeff.orchestrator import FlowRunResult

from .session import CliSession


def session_scope_json(session: CliSession) -> dict[str, Any]:
    return {
        "view": "scope",
        "session": {
            "project_id": session.scope.project_id,
            "work_unit_id": session.scope.work_unit_id,
            "run_id": session.scope.run_id,
            "output_mode": session.output_mode,
            "json_output": session.json_output,
        },
    }


def project_list_json(projects: tuple[Project, ...]) -> dict[str, Any]:
    return {
        "view": "project_list",
        "truth": {
            "projects": [
                {
                    "project_id": str(project.project_id),
                    "name": project.name,
                    "project_lifecycle_state": project.project_lifecycle_state,
                }
                for project in projects
            ]
        },
    }


def work_unit_list_json(project: Project) -> dict[str, Any]:
    return {
        "view": "work_unit_list",
        "truth": {
            "project_id": str(project.project_id),
            "work_units": [
                {
                    "work_unit_id": str(work_unit.work_unit_id),
                    "objective": work_unit.objective,
                    "work_unit_lifecycle_state": work_unit.work_unit_lifecycle_state,
                }
                for work_unit in project.work_units.values()
            ],
        },
    }


def run_list_json(project: Project, work_unit: WorkUnit) -> dict[str, Any]:
    return {
        "view": "run_list",
        "truth": {
            "project_id": str(project.project_id),
            "work_unit_id": str(work_unit.work_unit_id),
            "runs": [
                {
                    "run_id": str(run.run_id),
                    "run_lifecycle_state": run.run_lifecycle_state,
                }
                for run in work_unit.runs.values()
            ],
        },
    }


def run_show_json(
    *,
    project: Project,
    work_unit: WorkUnit,
    run: Run,
    flow_run: FlowRunResult | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "view": "run_show",
        "truth": {
            "project_id": str(project.project_id),
            "project_lifecycle_state": project.project_lifecycle_state,
            "work_unit_id": str(work_unit.work_unit_id),
            "work_unit_lifecycle_state": work_unit.work_unit_lifecycle_state,
            "run_id": str(run.run_id),
            "run_lifecycle_state": run.run_lifecycle_state,
        },
        "derived": {},
        "support": {},
        "telemetry": {},
    }
    if flow_run is None:
        payload["derived"] = {"flow_visible": False}
        return payload

    payload["derived"] = _flow_derived_json(flow_run)
    payload["support"] = {
        "routing_decision": routing_json(flow_run),
        "recent_events": trace_json(flow_run)["support"]["events"][-5:],
    }
    payload["telemetry"] = _telemetry_json(flow_run)
    return payload


def lifecycle_json(flow_run: FlowRunResult) -> dict[str, Any]:
    return {
        "view": "lifecycle",
        "derived": {
            "flow_id": flow_run.lifecycle.flow_id,
            "flow_family": flow_run.lifecycle.flow_family,
            "lifecycle_state": flow_run.lifecycle.lifecycle_state,
            "current_stage": flow_run.lifecycle.current_stage,
            "active_module": _module_for_stage(flow_run.lifecycle.current_stage),
            "reason_summary": flow_run.lifecycle.reason_summary,
        },
        "telemetry": _telemetry_json(flow_run),
    }


def trace_json(flow_run: FlowRunResult) -> dict[str, Any]:
    return {
        "view": "trace",
        "derived": {
            "flow_id": flow_run.lifecycle.flow_id,
            "flow_family": flow_run.lifecycle.flow_family,
            "run_id": flow_run.lifecycle.scope.run_id,
        },
        "support": {
            "events": [
                {
                    "ordinal": event.ordinal,
                    "stage": event.stage,
                    "event_type": event.event_type,
                    "summary": event.summary,
                    "emitted_at": event.emitted_at,
                }
                for event in flow_run.events
            ]
        },
        "telemetry": _telemetry_json(flow_run),
    }


def request_receipt_json(
    *,
    request_type: str,
    target: str,
    accepted: bool,
    scope: dict[str, str | None],
    note: str,
) -> dict[str, Any]:
    return {
        "view": "request_receipt",
        "derived": {
            "request_type": request_type,
            "target": target,
            "accepted": accepted,
            "effect_state": "request_accepted" if accepted else "request_rejected",
        },
        "session": scope,
        "support": {
            "note": note,
        },
    }


def research_result_json(
    *,
    project_id: str,
    work_unit_id: str,
    run_id: str,
    research_mode: str,
    handoff_memory_requested: bool,
    record: ResearchArtifactRecord,
    memory_handoff_result: MemoryWriteDecision | None,
    session: CliSession,
) -> dict[str, Any]:
    validate_research_artifact_record(record)
    source_index = {source.source_id: _project_research_source(source) for source in record.source_items}
    return {
        "view": "research_result",
        "truth": {
            "project_id": project_id,
            "work_unit_id": work_unit_id,
            "run_id": run_id,
        },
        "derived": {
            "research_mode": research_mode,
            "handoff_memory_requested": handoff_memory_requested,
            "memory_handoff_performed": memory_handoff_result is not None,
            "memory_handoff_result": _memory_handoff_json(memory_handoff_result),
        },
        "support": {
            "artifact_id": record.artifact_id,
            "question": record.question,
            "summary": record.summary,
            "findings": [
                {
                    "text": finding.text,
                    "source_refs": list(finding.source_refs),
                    "resolved_sources": [source_index[source_ref] for source_ref in finding.source_refs],
                }
                for finding in record.findings
            ],
            "uncertainties": list(record.uncertainties),
            "recommendation": record.recommendation,
            "source_ids": list(record.source_ids),
            "sources": [source_index[source.source_id] for source in record.source_items],
        },
        "session": {
            "project_id": session.scope.project_id,
            "work_unit_id": session.scope.work_unit_id,
            "run_id": session.scope.run_id,
            "output_mode": session.output_mode,
            "json_output": session.json_output,
        },
    }


def research_error_json(
    *,
    project_id: str | None,
    work_unit_id: str | None,
    run_id: str | None,
    research_mode: str | None,
    error: ResearchSynthesisRuntimeError,
    session: CliSession,
) -> dict[str, Any]:
    return {
        "view": "research_error",
        "truth": {
            "project_id": project_id,
            "work_unit_id": work_unit_id,
            "run_id": run_id,
        },
        "derived": {
            "research_mode": research_mode,
        },
        "support": error.to_payload(),
        "session": {
            "project_id": session.scope.project_id,
            "work_unit_id": session.scope.work_unit_id,
            "run_id": session.scope.run_id,
            "output_mode": session.output_mode,
            "json_output": session.json_output,
        },
    }


def routing_json(flow_run: FlowRunResult) -> dict[str, Any] | None:
    if flow_run.routing_decision is None:
        return None
    return {
        "route_kind": flow_run.routing_decision.route_kind,
        "routed_outcome": flow_run.routing_decision.routed_outcome,
        "source_stage": flow_run.routing_decision.source_stage,
        "reason_summary": flow_run.routing_decision.reason_summary,
    }


def _flow_derived_json(flow_run: FlowRunResult) -> dict[str, Any]:
    selection = flow_run.outputs.get("selection")
    governance = flow_run.outputs.get("governance")
    execution = flow_run.outputs.get("execution")
    outcome = flow_run.outputs.get("outcome")
    evaluation = flow_run.outputs.get("evaluation")
    transition = flow_run.outputs.get("transition")

    return {
        "flow_visible": True,
        "flow_id": flow_run.lifecycle.flow_id,
        "flow_family": flow_run.lifecycle.flow_family,
        "orchestrator_lifecycle_state": flow_run.lifecycle.lifecycle_state,
        "active_stage": flow_run.lifecycle.current_stage,
        "active_module": _module_for_stage(flow_run.lifecycle.current_stage),
        "selected_proposal_id": None if selection is None else _selected_proposal_id(selection),
        "governance_outcome": None if governance is None else governance.governance_outcome,
        "allowed_now": None if governance is None else governance.allowed_now,
        "approval_verdict": None if governance is None else governance.approval_verdict,
        "execution_status": None if execution is None else execution.execution_status,
        "outcome_state": None if outcome is None else outcome.outcome_state,
        "evaluation_verdict": None if evaluation is None else evaluation.evaluation_verdict,
        "transition_result": None if transition is None else transition.transition_result,
    }


def _telemetry_json(flow_run: FlowRunResult) -> dict[str, Any]:
    elapsed_seconds = None
    if len(flow_run.events) >= 2:
        started = datetime.fromisoformat(flow_run.events[0].emitted_at)
        ended = datetime.fromisoformat(flow_run.events[-1].emitted_at)
        elapsed_seconds = round((ended - started).total_seconds(), 3)
    return {
        "elapsed_seconds": elapsed_seconds,
        "events_seen": len(flow_run.events),
        "health_posture": _health_posture(flow_run),
    }


def _health_posture(flow_run: FlowRunResult) -> str:
    mapping = {
        "started": "ok",
        "active": "ok",
        "waiting": "blocked",
        "blocked": "blocked",
        "escalated": "escalated",
        "completed": "ok",
        "failed": "failed",
        "invalidated": "failed",
    }
    return mapping[flow_run.lifecycle.lifecycle_state]


def _module_for_stage(stage: str | None) -> str | None:
    if stage is None:
        return None
    mapping = {
        "context": "cognitive",
        "research": "cognitive",
        "proposal": "cognitive",
        "selection": "cognitive",
        "planning": "cognitive",
        "action": "contracts",
        "governance": "governance",
        "execution": "action",
        "outcome": "action",
        "evaluation": "cognitive",
        "memory": "memory",
        "transition": "core",
    }
    return mapping.get(stage)


def _selected_proposal_id(selection: Any) -> str | None:
    return None if selection.selected_proposal_id is None else str(selection.selected_proposal_id)


def _project_research_source(source: Any) -> dict[str, Any]:
    return {
        "source_id": source.source_id,
        "source_type": source.source_type,
        "title": source.title,
        "locator": source.locator,
        "snippet": source.snippet,
        "published_at": source.published_at,
    }


def _memory_handoff_json(memory_handoff_result: MemoryWriteDecision | None) -> dict[str, Any] | None:
    if memory_handoff_result is None:
        return None
    payload = {
        "write_outcome": memory_handoff_result.write_outcome,
        "candidate_id": str(memory_handoff_result.candidate_id),
        "memory_id": None if memory_handoff_result.memory_id is None else str(memory_handoff_result.memory_id),
        "reasons": list(memory_handoff_result.reasons),
    }
    if memory_handoff_result.committed_record is not None:
        payload["committed_record"] = {
            **asdict(memory_handoff_result.committed_record),
            "memory_id": str(memory_handoff_result.committed_record.memory_id),
        }
    else:
        payload["committed_record"] = None
    return payload
