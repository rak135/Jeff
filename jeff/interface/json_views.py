"""Stable JSON-friendly operator views."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any

from jeff.cognitive import (
    ContextPackage,
    ProposalOperatorRecord,
    ProposalGenerationBridgeResult,
    ResearchArtifactRecord,
    ResearchOperatorSurfaceError,
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
        "support": {
            "scope_model": "session-local/process-local only",
            "one_shot_scope_flags": ["--project", "--work", "--run"],
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
    selection_review: object | None = None,
    live_context_package: ContextPackage | None = None,
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
            "last_execution_status": run.last_execution_status,
            "last_outcome_state": run.last_outcome_state,
            "last_evaluation_verdict": run.last_evaluation_verdict,
        },
        "derived": {},
        "support": {},
        "telemetry": {},
    }
    if flow_run is None:
        payload["derived"] = {"flow_visible": False}
        payload["support"] = {
            "live_context": _live_context_summary_json(live_context_package),
            "execution_summary": _execution_summary_json(flow_run=None),
            "proposal_summary": _proposal_summary_json(selection_review=selection_review, flow_run=None),
            "evaluation_summary": _evaluation_summary_json(flow_run=None),
        }
        return payload

    payload["derived"] = _flow_derived_json(flow_run)
    payload["support"] = {
        "flow_reason_summary": flow_run.lifecycle.reason_summary,
        "routing_decision": routing_json(flow_run),
        "request_entry_hint": _request_entry_hint_json(flow_run=flow_run, selection_review=selection_review),
        "live_context": _live_context_summary_json(live_context_package),
        "execution_summary": _execution_summary_json(flow_run=flow_run),
        "proposal_summary": _proposal_summary_json(selection_review=selection_review, flow_run=flow_run),
        "evaluation_summary": _evaluation_summary_json(flow_run=flow_run),
        "recent_events": trace_json(flow_run)["support"]["events"][-5:],
    }
    payload["telemetry"] = _telemetry_json(flow_run)
    return payload


def selection_review_json(
    *,
    project: Project,
    work_unit: WorkUnit,
    run: Run,
    flow_run: FlowRunResult | None,
    selection_review: object | None,
) -> dict[str, Any]:
    selection_result = None
    if selection_review is not None:
        selection_result = getattr(selection_review, "selection_result", None)
    if selection_result is None and flow_run is not None:
        selection_result = flow_run.outputs.get("selection")

    operator_override = None if selection_review is None else getattr(selection_review, "operator_override", None)
    resolved_basis = None if selection_review is None else getattr(selection_review, "resolved_basis", None)
    materialized = None if selection_review is None else getattr(selection_review, "materialized_effective_proposal", None)
    formed_action = None if selection_review is None else getattr(selection_review, "formed_action_result", None)
    governance_handoff = None if selection_review is None else getattr(selection_review, "governance_handoff_result", None)
    proposal_result = None if selection_review is None else getattr(selection_review, "proposal_result", None)

    return {
        "view": "selection_review",
        "truth": {
            "project_id": str(project.project_id),
            "work_unit_id": str(work_unit.work_unit_id),
            "run_id": str(run.run_id),
        },
        "selection": {
            "available": selection_result is not None,
            "selection_id": None if selection_result is None else str(selection_result.selection_id),
            "disposition": None if selection_result is None else selection_result.disposition,
            "selected_proposal_id": None if selection_result is None or selection_result.selected_proposal_id is None else str(selection_result.selected_proposal_id),
            "non_selection_outcome": None if selection_result is None else selection_result.non_selection_outcome,
            "rationale": None if selection_result is None else selection_result.rationale,
            "missing_reason": None if selection_result is not None else "no selection result is visible for this run",
        },
        "override": {
            "available": selection_review is not None,
            "exists": operator_override is not None,
            "override_id": None if operator_override is None else operator_override.override_id,
            "chosen_proposal_id": None if operator_override is None else str(operator_override.chosen_proposal_id),
            "operator_rationale": None if operator_override is None else operator_override.operator_rationale,
            "missing_reason": _missing_review_reason(
                review_available=selection_review is not None,
                object_present=operator_override is not None,
                absent_reason="no override recorded",
            ),
        },
        "resolved_choice": {
            "available": resolved_basis is not None,
            "effective_source": None if resolved_basis is None else resolved_basis.effective_source,
            "effective_proposal_id": None if resolved_basis is None or resolved_basis.effective_proposal_id is None else str(resolved_basis.effective_proposal_id),
            "operator_override_present": None if resolved_basis is None else resolved_basis.operator_override_present,
            "non_selection_outcome": None if resolved_basis is None else resolved_basis.non_selection_outcome,
            "summary": None if resolved_basis is None else resolved_basis.summary,
            "missing_reason": _missing_review_reason(
                review_available=selection_review is not None,
                object_present=resolved_basis is not None,
                absent_reason="no resolved downstream basis available",
            ),
        },
        "action_formation": {
            "available": formed_action is not None,
            "action_formed": None if formed_action is None else formed_action.action_formed,
            "proposal_type": None if formed_action is None else formed_action.proposal_type,
            "action_id": None if formed_action is None or formed_action.action is None else str(formed_action.action.action_id),
            "effective_source": None if formed_action is None else formed_action.effective_source,
            "no_action_reason": None if formed_action is None else formed_action.no_action_reason,
            "summary": None if formed_action is None else formed_action.summary,
            "missing_reason": _missing_review_reason(
                review_available=selection_review is not None,
                object_present=formed_action is not None,
                absent_reason="no Action formation result available",
            ),
        },
        "governance_handoff": {
            "available": governance_handoff is not None,
            "governance_evaluated": None if governance_handoff is None else governance_handoff.governance_evaluated,
            "governance_outcome": (
                None
                if governance_handoff is None or governance_handoff.governance_result is None
                else governance_handoff.governance_result.governance_outcome
            ),
            "allowed_now": (
                None
                if governance_handoff is None or governance_handoff.governance_result is None
                else governance_handoff.governance_result.allowed_now
            ),
            "approval_verdict": (
                None
                if governance_handoff is None or governance_handoff.governance_result is None
                else governance_handoff.governance_result.approval_verdict
            ),
            "no_governance_reason": None if governance_handoff is None else governance_handoff.no_governance_reason,
            "summary": None if governance_handoff is None else governance_handoff.summary,
            "missing_reason": _missing_review_reason(
                review_available=selection_review is not None,
                object_present=governance_handoff is not None,
                absent_reason="governance handoff has not been recorded",
            ),
        },
        "proposal": _proposal_summary_json(selection_review=selection_review, flow_run=flow_run),
        "support": {
            "flow_visible": flow_run is not None,
            "selection_review_attached": selection_review is not None,
            "materialized_effective_proposal_available": materialized is not None,
            "materialized_effective_proposal_id": (
                None
                if materialized is None or materialized.effective_proposal_id is None
                else str(materialized.effective_proposal_id)
            ),
            "materialized_effective_source": None if materialized is None else materialized.effective_source,
            "materialized_missing_reason": _missing_review_reason(
                review_available=selection_review is not None,
                object_present=materialized is not None,
                absent_reason="no materialized effective proposal is available",
            ),
            "selection_rationale_summary": (
                None
                if selection_result is None
                else _truncate_text(selection_result.rationale, max_length=180)
            ),
        },
    }


def selection_override_receipt_json(
    *,
    run_id: str,
    selection_review: object,
) -> dict[str, Any]:
    selection_result = getattr(selection_review, "selection_result", None)
    operator_override = getattr(selection_review, "operator_override", None)
    resolved_basis = getattr(selection_review, "resolved_basis", None)
    formed_action = getattr(selection_review, "formed_action_result", None)
    governance_handoff = getattr(selection_review, "governance_handoff_result", None)

    return {
        "view": "selection_override_receipt",
        "truth": {
            "run_id": run_id,
            "selection_id": None if selection_result is None else str(selection_result.selection_id),
            "original_selection_disposition": None if selection_result is None else selection_result.disposition,
            "original_selected_proposal_id": (
                None
                if selection_result is None or selection_result.selected_proposal_id is None
                else str(selection_result.selected_proposal_id)
            ),
            "original_selection_unchanged": True,
        },
        "derived": {
            "override_created": operator_override is not None,
            "resolved_choice_updated": resolved_basis is not None,
            "action_formed": None if formed_action is None else formed_action.action_formed,
            "governance_evaluated": None if governance_handoff is None else governance_handoff.governance_evaluated,
        },
        "override": {
            "exists": operator_override is not None,
            "override_id": None if operator_override is None else operator_override.override_id,
            "chosen_proposal_id": None if operator_override is None else str(operator_override.chosen_proposal_id),
            "operator_rationale": None if operator_override is None else operator_override.operator_rationale,
        },
        "resolved_choice": {
            "available": resolved_basis is not None,
            "effective_source": None if resolved_basis is None else resolved_basis.effective_source,
            "effective_proposal_id": (
                None
                if resolved_basis is None or resolved_basis.effective_proposal_id is None
                else str(resolved_basis.effective_proposal_id)
            ),
            "missing_reason": None if resolved_basis is not None else "no resolved downstream basis available",
        },
        "action_formation": {
            "available": formed_action is not None,
            "action_formed": None if formed_action is None else formed_action.action_formed,
            "action_id": (
                None
                if formed_action is None or formed_action.action is None
                else str(formed_action.action.action_id)
            ),
            "no_action_reason": None if formed_action is None else formed_action.no_action_reason,
            "missing_reason": None if formed_action is not None else "no Action formation result available",
        },
        "governance_handoff": {
            "available": governance_handoff is not None,
            "governance_evaluated": None if governance_handoff is None else governance_handoff.governance_evaluated,
            "governance_outcome": (
                None
                if governance_handoff is None or governance_handoff.governance_result is None
                else governance_handoff.governance_result.governance_outcome
            ),
            "allowed_now": (
                None
                if governance_handoff is None or governance_handoff.governance_result is None
                else governance_handoff.governance_result.allowed_now
            ),
            "no_governance_reason": None if governance_handoff is None else governance_handoff.no_governance_reason,
            "missing_reason": None if governance_handoff is not None else "governance handoff has not been recorded",
        },
        "support": {
            "note": (
                "Override recorded as a separate downstream support object. "
                "Original SelectionResult remains unchanged, and no execution starts here."
            ),
        },
    }


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
    effect_state: str | None = None,
    scope: dict[str, str | None],
    note: str,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "view": "request_receipt",
        "derived": {
            "request_type": request_type,
            "target": target,
            "accepted": accepted,
            "effect_state": effect_state or ("request_accepted" if accepted else "request_rejected"),
        },
        "session": scope,
        "support": {
            "note": note,
            "detail": {} if detail is None else detail,
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
    memory_handoff_result: object | None,
    session: CliSession,
    artifact_locator: str | None = None,
    live_context_package: ContextPackage | None = None,
    proposal_followup_result: ProposalGenerationBridgeResult | None = None,
    proposal_followup_issue: str | None = None,
) -> dict[str, Any]:
    validate_research_artifact_record(record)
    source_index = {source.source_id: _project_research_source(source) for source in record.source_items}
    persistence_note = _research_persistence_note(artifact_locator)
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
            "artifact_locator": artifact_locator,
            "question": record.question,
            "summary": record.summary,
            "source_count": len(record.source_items),
            "persistence_note": persistence_note,
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
            "live_context": _live_context_summary_json(live_context_package),
            "proposal_followup": _proposal_followup_summary_json(
                proposal_followup_result=proposal_followup_result,
                proposal_followup_issue=proposal_followup_issue,
            ),
        },
        "session": {
            "project_id": session.scope.project_id,
            "work_unit_id": session.scope.work_unit_id,
            "run_id": session.scope.run_id,
            "output_mode": session.output_mode,
            "json_output": session.json_output,
        },
    }


def _live_context_summary_json(context_package: ContextPackage | None) -> dict[str, Any] | None:
    if context_package is None:
        return None

    return {
        "assembled": True,
        "purpose": context_package.purpose,
        "truth_families": [record.truth_family for record in context_package.ordered_truth_records],
        "truth_record_count": len(context_package.ordered_truth_records),
        "governance_truth_count": len(context_package.governance_truth_records),
        "memory_support_count": len(context_package.memory_support_inputs),
        "compiled_knowledge_support_count": len(context_package.compiled_knowledge_support_inputs),
        "archive_support_count": len(context_package.archive_support_inputs),
        "direct_support_count": len(context_package.support_inputs),
        "ordered_support_source_families": [
            support_input.source_family for support_input in context_package.ordered_support_inputs
        ],
    }


def _proposal_followup_summary_json(
    *,
    proposal_followup_result: ProposalGenerationBridgeResult | None,
    proposal_followup_issue: str | None,
) -> dict[str, Any] | None:
    if proposal_followup_result is None and proposal_followup_issue is None:
        return None

    if proposal_followup_result is None:
        return {
            "attempted": True,
            "proposal_request_built": False,
            "proposal_generation_ran": False,
            "proposal_count": None,
            "no_generation_reason": proposal_followup_issue,
            "summary": None,
        }

    return {
        "attempted": True,
        "proposal_request_built": proposal_followup_result.proposal_request_built,
        "proposal_generation_ran": proposal_followup_result.proposal_generation_ran,
        "proposal_count": proposal_followup_result.proposal_count,
        "no_generation_reason": proposal_followup_result.no_generation_reason or proposal_followup_issue,
        "summary": proposal_followup_result.summary,
    }


def research_error_json(
    *,
    project_id: str | None,
    work_unit_id: str | None,
    run_id: str | None,
    research_mode: str | None,
    error: ResearchSynthesisRuntimeError | ResearchOperatorSurfaceError,
    session: CliSession,
    debug_events: tuple[dict[str, object], ...] = (),
) -> dict[str, Any]:
    support = dict(error.to_payload())
    if support.get("checkpoint") is None:
        checkpoint = _latest_research_checkpoint(debug_events)
        if checkpoint is not None:
            support["checkpoint"] = checkpoint
    if support.get("resolved_source_count") is None:
        resolved_source_count = _latest_research_count(
            debug_events,
            "projected_source_count",
            "source_item_count",
            "loaded_record_source_count",
            "persisted_record_source_count",
            "source_count",
        )
        if resolved_source_count is not None:
            support["resolved_source_count"] = resolved_source_count
    return {
        "view": "research_error",
        "truth": {
            "project_id": project_id,
            "work_unit_id": work_unit_id,
            "run_id": run_id,
        },
        "derived": {
            "research_mode": research_mode,
            "failure_kind": support.get("failure_kind"),
        },
        "support": support,
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


def _request_entry_hint_json(*, flow_run: FlowRunResult, selection_review: object | None) -> dict[str, Any] | None:
    routing = flow_run.routing_decision
    if routing is None:
        return None

    run_id = flow_run.lifecycle.scope.run_id
    if run_id is None:
        return None

    approval = None if selection_review is None else getattr(selection_review, "governance_approval", None)
    approval_verdict = None if approval is None else getattr(approval, "approval_verdict", None)

    conditional_commands: list[str] = []
    receipt_only_commands: list[str] = []
    if routing.routed_outcome == "approval_required":
        conditional_commands = [f"/approve {run_id}", f"/reject {run_id}"]
    elif routing.routed_outcome == "revalidate":
        conditional_commands = [f"/reject {run_id}"]
        if approval_verdict == "granted":
            conditional_commands.append(f"/revalidate {run_id}")
    elif routing.routed_outcome == "retry":
        receipt_only_commands = [f"/retry {run_id}"]
    elif routing.routed_outcome == "recover":
        receipt_only_commands = [f"/recover {run_id}"]

    if not conditional_commands and not receipt_only_commands:
        return None

    return {
        "available": True,
        "current_routed_outcome": routing.routed_outcome,
        "conditional_commands": conditional_commands,
        "receipt_only_commands": receipt_only_commands,
        "state_summary": f"current run routed to {routing.routed_outcome}",
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
        "memory_handoff_attempted": flow_run.memory_handoff_attempted,
        "memory_handoff_result": _memory_handoff_json(flow_run.memory_handoff_result),
        "memory_handoff_note": flow_run.memory_handoff_note,
    }


def _proposal_summary_json(*, selection_review: object | None, flow_run: FlowRunResult | None) -> dict[str, Any]:
    proposal_result = None if selection_review is None else getattr(selection_review, "proposal_result", None)
    if proposal_result is None and flow_run is not None:
        candidate = flow_run.outputs.get("proposal")
        if candidate is not None:
            proposal_result = candidate

    selection_result = None if selection_review is None else getattr(selection_review, "selection_result", None)
    if selection_result is None and flow_run is not None:
        candidate = flow_run.outputs.get("selection")
        if candidate is not None:
            selection_result = candidate

    if proposal_result is None:
        return {
            "available": False,
            "serious_option_count": None,
            "selected_proposal_id": None if selection_result is None or selection_result.selected_proposal_id is None else str(selection_result.selected_proposal_id),
            "non_selection_outcome": None if selection_result is None else selection_result.non_selection_outcome,
            "scarcity_reason": None,
            "retained_options": [],
            "missing_reason": "no proposal summary is available for this run",
        }

    return {
        "available": True,
        "serious_option_count": proposal_result.proposal_count,
        "selected_proposal_id": None if selection_result is None or selection_result.selected_proposal_id is None else str(selection_result.selected_proposal_id),
        "non_selection_outcome": None if selection_result is None else selection_result.non_selection_outcome,
        "scarcity_reason": proposal_result.scarcity_reason,
        "retained_options": [
            {
                "proposal_id": str(option.proposal_id),
                "proposal_type": option.proposal_type,
                "summary": option.summary,
                "assumption_count": len(option.assumptions),
                "risk_count": len(option.main_risks),
            }
            for option in proposal_result.options[:3]
        ],
        "missing_reason": None,
    }


def proposal_record_json(
    *,
    record: ProposalOperatorRecord,
    view: str = "proposal_show",
) -> dict[str, Any]:
    summary = _proposal_record_summary(record)
    return {
        "view": view,
        "truth": {
            "proposal_id": record.proposal_id,
            "source_proposal_id": record.source_proposal_id,
            "objective": record.objective,
            "scope": {
                "project_id": str(record.scope.project_id),
                "work_unit_id": None if record.scope.work_unit_id is None else str(record.scope.work_unit_id),
                "run_id": None if record.scope.run_id is None else str(record.scope.run_id),
            },
            "created_at": record.created_at,
        },
        "derived": {
            "proposal_status": record.status,
            "repair_attempted": record.repair_attempted,
            "repair_used": record.repair_attempted,
            "final_validation_outcome": record.final_validation_outcome,
            "final_failure_stage": record.final_failure_stage,
            "final_error_message": record.final_error_message,
            "terminal_attempt_kind": record.final_attempt.attempt_kind,
        },
        "proposal": {
            "proposal_count": summary["proposal_count"],
            "scarcity_reason": summary["scarcity_reason"],
            "retained_options": summary["retained_options"],
            "summary_source": summary["summary_source"],
            "final_result_available": record.final_proposal_result is not None,
            "parsed_intermediate_available": summary["parsed_intermediate_available"],
        },
        "attempts": {
            "initial": _proposal_attempt_json(record.initial_attempt),
            "repair": None if record.repair_attempt is None else _proposal_attempt_json(record.repair_attempt),
        },
        "artifacts": {
            "record_ref": record.record_ref,
            "initial_raw_ref": record.initial_attempt.raw_artifact_ref,
            "initial_parsed_ref": record.initial_attempt.parsed_artifact_ref,
            "repair_raw_ref": None if record.repair_attempt is None else record.repair_attempt.raw_artifact_ref,
            "repair_parsed_ref": None if record.repair_attempt is None else record.repair_attempt.parsed_artifact_ref,
        },
    }


def proposal_raw_json(record: ProposalOperatorRecord) -> dict[str, Any]:
    return {
        "view": "proposal_raw",
        "truth": {
            "proposal_id": record.proposal_id,
            "source_proposal_id": record.source_proposal_id,
            "run_id": None if record.scope.run_id is None else str(record.scope.run_id),
            "objective": record.objective,
        },
        "attempts": [
            _proposal_raw_attempt_json(record.initial_attempt),
            *(
                [] if record.repair_attempt is None else [_proposal_raw_attempt_json(record.repair_attempt)]
            ),
        ],
    }


def proposal_validation_json(
    *,
    record: ProposalOperatorRecord,
    attempt_kind: str,
    parse_error: str | None,
    validation_issues: tuple[object, ...],
    proposal_result: object | None,
) -> dict[str, Any]:
    attempt = record.final_attempt if record.final_attempt.attempt_kind == attempt_kind else record.initial_attempt
    summary = _proposal_summary_from_result(proposal_result)
    return {
        "view": "proposal_validate",
        "truth": {
            "proposal_id": record.proposal_id,
            "source_proposal_id": record.source_proposal_id,
            "run_id": None if record.scope.run_id is None else str(record.scope.run_id),
        },
        "derived": {
            "attempt_kind": attempt_kind,
            "parse_success": parse_error is None,
            "validation_success": parse_error is None and not validation_issues,
        },
        "support": {
            "parse_error": parse_error,
            "validation_issues": [
                {
                    "code": issue.code,
                    "message": issue.message,
                    "option_index": issue.option_index,
                }
                for issue in validation_issues
            ],
            "proposal_count": summary["proposal_count"],
            "scarcity_reason": summary["scarcity_reason"],
            "retained_options": summary["retained_options"],
        },
        "artifacts": {
            "raw_ref": attempt.raw_artifact_ref,
            "parsed_ref": attempt.parsed_artifact_ref,
            "validation_ref": attempt.validation_artifact_ref,
        },
    }


def _proposal_attempt_json(attempt: object) -> dict[str, Any]:
    return {
        "attempt_kind": attempt.attempt_kind,
        "prompt_file": None if attempt.prompt_bundle is None else attempt.prompt_bundle.prompt_file,
        "request_id": None if attempt.prompt_bundle is None else attempt.prompt_bundle.request_id,
        "raw_available": attempt.raw_result is not None,
        "parsed_available": attempt.parsed_result is not None,
        "proposal_result_available": attempt.proposal_result is not None,
        "failure_stage": attempt.failure_stage,
        "error_message": attempt.error_message,
        "parse_error": attempt.parse_error,
        "validation_issue_count": len(attempt.validation_issues),
        "raw_artifact_ref": attempt.raw_artifact_ref,
        "parsed_artifact_ref": attempt.parsed_artifact_ref,
        "validation_artifact_ref": attempt.validation_artifact_ref,
    }


def _proposal_raw_attempt_json(attempt: object) -> dict[str, Any]:
    return {
        "attempt_kind": attempt.attempt_kind,
        "prompt_file": None if attempt.prompt_bundle is None else attempt.prompt_bundle.prompt_file,
        "request_id": None if attempt.prompt_bundle is None else attempt.prompt_bundle.request_id,
        "raw_available": attempt.raw_result is not None,
        "raw_artifact_ref": attempt.raw_artifact_ref,
        "raw_output_text": None if attempt.raw_result is None else attempt.raw_result.raw_output_text,
        "missing_reason": None if attempt.raw_result is not None else attempt.error_message or "no raw output preserved",
    }


def _proposal_record_summary(record: ProposalOperatorRecord) -> dict[str, Any]:
    if record.final_proposal_result is not None:
        summary = _proposal_summary_from_result(record.final_proposal_result)
        summary["summary_source"] = "final_proposal_result"
        summary["parsed_intermediate_available"] = record.final_attempt.parsed_result is not None
        return summary
    if record.final_attempt.parsed_result is not None:
        summary = _proposal_summary_from_parsed(record.final_attempt.parsed_result)
        summary["summary_source"] = "parsed_intermediate"
        summary["parsed_intermediate_available"] = True
        return summary
    return {
        "proposal_count": None,
        "scarcity_reason": None,
        "retained_options": [],
        "summary_source": "none",
        "parsed_intermediate_available": False,
    }


def _proposal_summary_from_result(proposal_result: object | None) -> dict[str, Any]:
    if proposal_result is None:
        return {
            "proposal_count": None,
            "scarcity_reason": None,
            "retained_options": [],
        }
    return {
        "proposal_count": proposal_result.proposal_count,
        "scarcity_reason": proposal_result.scarcity_reason,
        "retained_options": [
            {
                "proposal_id": str(option.proposal_id),
                "proposal_type": option.proposal_type,
                "title": option.title,
                "summary": option.summary,
                "why_now": option.why_now,
                "assumptions": list(option.assumptions),
                "main_risks": list(option.main_risks),
                "constraints": list(option.constraints),
                "blockers": list(option.blockers),
                "support_refs": list(option.support_refs),
                "planning_needed": option.planning_needed,
            }
            for option in proposal_result.options
        ],
    }


def _proposal_summary_from_parsed(parsed_result: object) -> dict[str, Any]:
    return {
        "proposal_count": parsed_result.proposal_count,
        "scarcity_reason": parsed_result.scarcity_reason,
        "retained_options": [
            {
                "proposal_id": f"proposal-{option.option_index}",
                "proposal_type": option.proposal_type,
                "title": option.title,
                "summary": option.summary,
                "why_now": option.why_now,
                "assumptions": list(option.assumptions),
                "main_risks": list(option.risks),
                "constraints": list(option.constraints),
                "blockers": list(option.blockers),
                "support_refs": list(option.support_refs),
                "planning_needed": option.planning_needed,
            }
            for option in parsed_result.options
        ],
    }


def _evaluation_summary_json(*, flow_run: FlowRunResult | None) -> dict[str, Any]:
    if flow_run is None:
        return {
            "available": False,
            "evaluation_verdict": None,
            "strongest_reason_summary": None,
            "evidence_posture_summary": None,
            "recommended_next_step": None,
            "missing_reason": "no evaluation summary is available for this run",
        }

    evaluation = flow_run.outputs.get("evaluation")
    if evaluation is None:
        return {
            "available": False,
            "evaluation_verdict": None,
            "strongest_reason_summary": None,
            "evidence_posture_summary": None,
            "recommended_next_step": None,
            "missing_reason": "no evaluation summary is available for this run",
        }

    override_reasons = getattr(evaluation, "deterministic_override_reasons", ())
    rationale = getattr(evaluation, "rationale", None)
    strongest_reason_summary = None
    if override_reasons:
        strongest_reason_summary = override_reasons[0]
    elif isinstance(rationale, str):
        strongest_reason_summary = _truncate_text(rationale, max_length=180)

    return {
        "available": True,
        "evaluation_verdict": evaluation.evaluation_verdict,
        "strongest_reason_summary": strongest_reason_summary,
        "evidence_posture_summary": _extract_evidence_posture_summary(rationale if isinstance(rationale, str) else None),
        "recommended_next_step": evaluation.recommended_next_step,
        "missing_reason": None,
    }


def _execution_summary_json(*, flow_run: FlowRunResult | None) -> dict[str, Any]:
    if flow_run is None:
        return {
            "available": False,
            "execution_family": None,
            "execution_command_id": None,
            "executed_command": None,
            "working_directory": None,
            "exit_code": None,
            "output_summary": None,
            "stdout_excerpt": None,
            "stderr_excerpt": None,
            "missing_reason": "no execution summary is available for this run",
        }

    execution = flow_run.outputs.get("execution")
    if execution is None:
        return {
            "available": False,
            "execution_family": None,
            "execution_command_id": None,
            "executed_command": None,
            "working_directory": None,
            "exit_code": None,
            "output_summary": None,
            "stdout_excerpt": None,
            "stderr_excerpt": None,
            "missing_reason": "no execution summary is available for this run",
        }

    return {
        "available": True,
        "execution_family": execution.execution_family,
        "execution_command_id": execution.execution_command_id,
        "executed_command": execution.executed_command,
        "working_directory": execution.working_directory,
        "exit_code": execution.exit_code,
        "output_summary": execution.output_summary,
        "stdout_excerpt": execution.stdout_excerpt,
        "stderr_excerpt": execution.stderr_excerpt,
        "missing_reason": None,
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


def _memory_handoff_json(memory_handoff_result: object | None) -> dict[str, Any] | None:
    if memory_handoff_result is None:
        return None
    payload = {
        "write_outcome": memory_handoff_result.write_outcome,
        "candidate_id": str(memory_handoff_result.candidate_id),
        "memory_id": None if memory_handoff_result.memory_id is None else str(memory_handoff_result.memory_id),
        "reasons": list(memory_handoff_result.reasons),
    }
    committed_record = getattr(memory_handoff_result, "committed_record", None)
    if committed_record is not None:
        payload["committed_record"] = {
            **asdict(committed_record),
            "memory_id": str(committed_record.memory_id),
        }
    else:
        payload["committed_record"] = None
    return payload


def _missing_review_reason(*, review_available: bool, object_present: bool, absent_reason: str) -> str | None:
    if object_present:
        return None
    if not review_available:
        return "no selection review chain is available for this run"
    return absent_reason


def _extract_evidence_posture_summary(rationale: str | None) -> str | None:
    if rationale is None:
        return None
    match = "with evidence quality "
    if match not in rationale:
        return None
    suffix = rationale.split(match, 1)[1]
    return suffix.rstrip(".")


def _truncate_text(text: str, *, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return f"{text[: max_length - 3].rstrip()}..."


def _research_persistence_note(artifact_locator: str | None) -> str:
    if artifact_locator is None:
        return "research artifact persisted as support"
    return f"research artifact persisted as support at {artifact_locator}"


def _latest_research_checkpoint(debug_events: tuple[dict[str, object], ...]) -> str | None:
    for event in reversed(debug_events):
        checkpoint = event.get("checkpoint")
        if isinstance(checkpoint, str) and checkpoint.strip():
            return checkpoint
    return None


def _latest_research_count(
    debug_events: tuple[dict[str, object], ...],
    *field_names: str,
) -> int | None:
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
