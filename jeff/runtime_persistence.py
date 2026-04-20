"""Persisted runtime home and JSON support stores for the Jeff v1 workspace slice."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import errno
import json
from pathlib import Path
import os
from contextlib import contextmanager
import shutil
import sys
from typing import Any, TYPE_CHECKING

from jeff.action.execution import ExecutionResult, GovernedExecutionRequest
from jeff.action.outcome import Outcome
from jeff.cognitive.context import ContextPackage
from jeff.cognitive.evaluation import EvaluationResult
from jeff.cognitive.post_selection.selection_review_record import SelectionReviewRecord
from jeff.cognitive.post_selection.override import OperatorSelectionOverride
from jeff.cognitive.proposal import (
    ParsedProposalGenerationResult,
    ParsedProposalOption,
    ProposalGenerationPromptBundle,
    ProposalGenerationRawResult,
    ProposalOperatorRecord,
    ProposalPersistedAttempt,
    ProposalResult,
    ProposalResultOption,
    ProposalValidationIssue,
)
from jeff.cognitive.run_memory_handoff import RunMemoryHandoffResultSummary
from jeff.cognitive.selection import SelectionResult
from jeff.cognitive.types import SupportInput, TriggerInput, TruthRecord
from jeff.contracts import Action
from jeff.core.containers.models import Project, Run, WorkUnit
from jeff.core.schemas import Scope
from jeff.core.state import GlobalState, SystemState
from jeff.core.state.models import StateMeta
from jeff.core.transition import TransitionRequest, TransitionResult, apply_transition
from jeff.governance import ActionEntryDecision, Approval, CurrentTruthSnapshot, Policy, Readiness
from jeff.infrastructure import ModelUsage
from jeff.orchestrator.lifecycle import FlowLifecycle
from jeff.orchestrator.routing import RoutingDecision
from jeff.orchestrator.runner import FlowRunResult
from jeff.orchestrator.trace import OrchestrationEvent

_SCHEMA_VERSION = "1.0"
_LAYOUT_VERSION = "runtime-home-v1"


class RuntimeMutationLockError(RuntimeError):
    """Raised when another live process already owns runtime mutation."""


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.tmp")
    temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temp_path.replace(path)


def _pid_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle == 0:
            error = ctypes.get_last_error()
            return error == 5
        try:
            exit_code = ctypes.c_ulong()
            if kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)) == 0:
                return False
            return exit_code.value == STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed persisted JSON file: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"persisted JSON file must contain an object: {path}")
    return payload


def _is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
    except ValueError:
        return False
    return True


def _clear_runtime_path(path: Path, *, preserved_paths: tuple[Path, ...]) -> None:
    resolved_path = path.resolve(strict=False)
    if resolved_path in preserved_paths:
        return

    if path.is_dir() and not path.is_symlink():
        preserved_descendants = tuple(
            preserved_path for preserved_path in preserved_paths if _is_relative_to(preserved_path, resolved_path)
        )
        if preserved_descendants:
            for child in path.iterdir():
                _clear_runtime_path(child, preserved_paths=preserved_paths)
            return
        shutil.rmtree(path)
        return

    path.unlink()


def _scope_to_payload(scope: Scope) -> dict[str, Any]:
    return {
        "project_id": str(scope.project_id),
        "work_unit_id": None if scope.work_unit_id is None else str(scope.work_unit_id),
        "run_id": None if scope.run_id is None else str(scope.run_id),
    }


def _scope_from_payload(payload: dict[str, Any]) -> Scope:
    return Scope(
        project_id=payload["project_id"],
        work_unit_id=payload.get("work_unit_id"),
        run_id=payload.get("run_id"),
    )


def _run_to_payload(run: Run) -> dict[str, Any]:
    return {
        "run_id": str(run.run_id),
        "project_id": str(run.project_id),
        "work_unit_id": str(run.work_unit_id),
        "run_lifecycle_state": run.run_lifecycle_state,
        "last_execution_status": run.last_execution_status,
        "last_outcome_state": run.last_outcome_state,
        "last_evaluation_verdict": run.last_evaluation_verdict,
    }


def _run_from_payload(payload: dict[str, Any]) -> Run:
    return Run(
        run_id=payload["run_id"],
        project_id=payload["project_id"],
        work_unit_id=payload["work_unit_id"],
        run_lifecycle_state=payload["run_lifecycle_state"],
        last_execution_status=payload.get("last_execution_status"),
        last_outcome_state=payload.get("last_outcome_state"),
        last_evaluation_verdict=payload.get("last_evaluation_verdict"),
    )


def _work_unit_to_payload(work_unit: WorkUnit) -> dict[str, Any]:
    return {
        "work_unit_id": str(work_unit.work_unit_id),
        "project_id": str(work_unit.project_id),
        "objective": work_unit.objective,
        "work_unit_lifecycle_state": work_unit.work_unit_lifecycle_state,
        "runs": {str(run_id): _run_to_payload(run) for run_id, run in work_unit.runs.items()},
    }


def _work_unit_from_payload(payload: dict[str, Any]) -> WorkUnit:
    runs = {run_id: _run_from_payload(run_payload) for run_id, run_payload in payload.get("runs", {}).items()}
    return WorkUnit(
        work_unit_id=payload["work_unit_id"],
        project_id=payload["project_id"],
        objective=payload["objective"],
        work_unit_lifecycle_state=payload["work_unit_lifecycle_state"],
        runs=runs,
    )


def _project_to_payload(project: Project) -> dict[str, Any]:
    return {
        "project_id": str(project.project_id),
        "name": project.name,
        "project_lifecycle_state": project.project_lifecycle_state,
        "work_units": {
            str(work_unit_id): _work_unit_to_payload(work_unit)
            for work_unit_id, work_unit in project.work_units.items()
        },
    }


def _project_from_payload(payload: dict[str, Any]) -> Project:
    work_units = {
        work_unit_id: _work_unit_from_payload(work_unit_payload)
        for work_unit_id, work_unit_payload in payload.get("work_units", {}).items()
    }
    return Project(
        project_id=payload["project_id"],
        name=payload["name"],
        project_lifecycle_state=payload["project_lifecycle_state"],
        work_units=work_units,
    )


def _state_to_payload(state: GlobalState) -> dict[str, Any]:
    return {
        "state_meta": {
            "state_version": state.state_meta.state_version,
            "last_transition_id": (
                None if state.state_meta.last_transition_id is None else str(state.state_meta.last_transition_id)
            ),
        },
        "system": {
            "system_lifecycle_state": state.system.system_lifecycle_state,
        },
        "projects": {str(project_id): _project_to_payload(project) for project_id, project in state.projects.items()},
    }


def _state_from_payload(payload: dict[str, Any]) -> GlobalState:
    projects = {
        project_id: _project_from_payload(project_payload)
        for project_id, project_payload in payload.get("projects", {}).items()
    }
    return GlobalState(
        state_meta=StateMeta(
            state_version=payload["state_meta"]["state_version"],
            last_transition_id=payload["state_meta"].get("last_transition_id"),
        ),
        system=SystemState(system_lifecycle_state=payload["system"]["system_lifecycle_state"]),
        projects=projects,
    )


def _policy_to_payload(policy: Policy) -> dict[str, Any]:
    return {
        "approval_required": policy.approval_required,
        "action_forbidden": policy.action_forbidden,
        "protected_surface": policy.protected_surface,
        "destructive": policy.destructive,
        "direction_sensitive": policy.direction_sensitive,
        "freshness_sensitive": policy.freshness_sensitive,
        "revalidation_required": policy.revalidation_required,
    }


def _policy_from_payload(payload: dict[str, Any]) -> Policy:
    return Policy(
        approval_required=payload.get("approval_required", False),
        action_forbidden=payload.get("action_forbidden", False),
        protected_surface=payload.get("protected_surface", False),
        destructive=payload.get("destructive", False),
        direction_sensitive=payload.get("direction_sensitive", False),
        freshness_sensitive=payload.get("freshness_sensitive", True),
        revalidation_required=payload.get("revalidation_required", False),
    )


def _approval_to_payload(approval: Approval) -> dict[str, Any]:
    return {
        "approval_verdict": approval.approval_verdict,
        "action_id": None if approval.action_id is None else str(approval.action_id),
        "action_binding_key": approval.action_binding_key,
        "basis_state_version": approval.basis_state_version,
    }


def _approval_from_payload(payload: dict[str, Any]) -> Approval:
    return Approval(
        approval_verdict=payload["approval_verdict"],
        action_id=payload.get("action_id"),
        action_binding_key=payload.get("action_binding_key"),
        basis_state_version=payload.get("basis_state_version"),
    )


def _truth_snapshot_to_payload(truth: CurrentTruthSnapshot) -> dict[str, Any]:
    return {
        "scope": _scope_to_payload(truth.scope),
        "state_version": truth.state_version,
        "blocked_reasons": list(truth.blocked_reasons),
        "degraded_truth": truth.degraded_truth,
        "truth_mismatch": truth.truth_mismatch,
        "direction_ok": truth.direction_ok,
        "target_available": truth.target_available,
        "requires_revalidation": truth.requires_revalidation,
    }


def _truth_snapshot_from_payload(payload: dict[str, Any]) -> CurrentTruthSnapshot:
    return CurrentTruthSnapshot(
        scope=_scope_from_payload(payload["scope"]),
        state_version=payload["state_version"],
        blocked_reasons=tuple(payload.get("blocked_reasons", ())),
        degraded_truth=payload.get("degraded_truth", False),
        truth_mismatch=payload.get("truth_mismatch", False),
        direction_ok=payload.get("direction_ok", True),
        target_available=payload.get("target_available", True),
        requires_revalidation=payload.get("requires_revalidation", False),
    )


def _readiness_to_payload(readiness: Readiness) -> dict[str, Any]:
    return {
        "action_id": str(readiness.action_id),
        "readiness_state": readiness.readiness_state,
        "checked_at_state_version": readiness.checked_at_state_version,
        "reasons": list(readiness.reasons),
        "cautions": list(readiness.cautions),
    }


def _readiness_from_payload(payload: dict[str, Any]) -> Readiness:
    return Readiness(
        action_id=payload["action_id"],
        readiness_state=payload["readiness_state"],
        checked_at_state_version=payload["checked_at_state_version"],
        reasons=tuple(payload.get("reasons", ())),
        cautions=tuple(payload.get("cautions", ())),
    )


def _action_entry_decision_to_payload(decision: ActionEntryDecision) -> dict[str, Any]:
    return {
        "action_id": decision.action_id,
        "action_binding_key": decision.action_binding_key,
        "policy_verdict": decision.policy_verdict,
        "approval_verdict": decision.approval_verdict,
        "readiness": _readiness_to_payload(decision.readiness),
        "governance_outcome": decision.governance_outcome,
        "allowed_now": decision.allowed_now,
    }


def _action_entry_decision_from_payload(payload: dict[str, Any]) -> ActionEntryDecision:
    return ActionEntryDecision(
        action_id=payload["action_id"],
        action_binding_key=payload["action_binding_key"],
        policy_verdict=payload["policy_verdict"],
        approval_verdict=payload["approval_verdict"],
        readiness=_readiness_from_payload(payload["readiness"]),
        governance_outcome=payload["governance_outcome"],
        allowed_now=payload["allowed_now"],
    )


def _action_to_payload(action: Action) -> dict[str, Any]:
    return {
        "action_id": str(action.action_id),
        "scope": _scope_to_payload(action.scope),
        "intent_summary": action.intent_summary,
        "target_summary": action.target_summary,
        "protected_surface": action.protected_surface,
        "basis_state_version": action.basis_state_version,
        "basis_label": action.basis_label,
    }


def _action_from_payload(payload: dict[str, Any]) -> Action:
    return Action(
        action_id=payload["action_id"],
        scope=_scope_from_payload(payload["scope"]),
        intent_summary=payload["intent_summary"],
        target_summary=payload.get("target_summary"),
        protected_surface=payload.get("protected_surface"),
        basis_state_version=payload.get("basis_state_version", 0),
        basis_label=payload.get("basis_label"),
    )


def _proposal_option_to_payload(option: ProposalResultOption) -> dict[str, Any]:
    return {
        "option_index": option.option_index,
        "proposal_id": str(option.proposal_id),
        "proposal_type": option.proposal_type,
        "title": option.title,
        "why_now": option.why_now,
        "summary": option.summary,
        "constraints": list(option.constraints),
        "feasibility": option.feasibility,
        "reversibility": option.reversibility,
        "support_refs": list(option.support_refs),
        "assumptions": list(option.assumptions),
        "main_risks": list(option.main_risks),
        "blockers": list(option.blockers),
        "planning_needed": option.planning_needed,
    }


def _proposal_option_from_payload(payload: dict[str, Any]) -> ProposalResultOption:
    return ProposalResultOption(
        option_index=payload["option_index"],
        proposal_id=payload["proposal_id"],
        proposal_type=payload["proposal_type"],
        title=payload["title"],
        why_now=payload["why_now"],
        summary=payload["summary"],
        constraints=tuple(payload.get("constraints", ())),
        feasibility=payload.get("feasibility"),
        reversibility=payload.get("reversibility"),
        support_refs=tuple(payload.get("support_refs", ())),
        assumptions=tuple(payload.get("assumptions", ())),
        main_risks=tuple(payload.get("main_risks", ())),
        blockers=tuple(payload.get("blockers", ())),
        planning_needed=payload.get("planning_needed", False),
    )


def _proposal_result_to_payload(proposal_result: ProposalResult) -> dict[str, Any]:
    return {
        "request_id": proposal_result.request_id,
        "scope": _scope_to_payload(proposal_result.scope),
        "options": [_proposal_option_to_payload(option) for option in proposal_result.options],
        "scarcity_reason": proposal_result.scarcity_reason,
    }


def _proposal_result_from_payload(payload: dict[str, Any]) -> ProposalResult:
    return ProposalResult(
        request_id=payload["request_id"],
        scope=_scope_from_payload(payload["scope"]),
        options=tuple(_proposal_option_from_payload(option_payload) for option_payload in payload["options"]),
        scarcity_reason=payload.get("scarcity_reason"),
    )


def _model_usage_to_payload(usage: ModelUsage) -> dict[str, Any]:
    return {
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "total_tokens": usage.total_tokens,
        "estimated_cost": usage.estimated_cost,
        "latency_ms": usage.latency_ms,
    }


def _model_usage_from_payload(payload: dict[str, Any]) -> ModelUsage:
    return ModelUsage(
        input_tokens=payload.get("input_tokens"),
        output_tokens=payload.get("output_tokens"),
        total_tokens=payload.get("total_tokens"),
        estimated_cost=payload.get("estimated_cost"),
        latency_ms=payload.get("latency_ms"),
    )


def _trigger_input_to_payload(trigger: TriggerInput) -> dict[str, Any]:
    return {
        "trigger_summary": trigger.trigger_summary,
        "trigger_family": trigger.trigger_family,
    }


def _trigger_input_from_payload(payload: dict[str, Any]) -> TriggerInput:
    return TriggerInput(
        trigger_summary=payload["trigger_summary"],
        trigger_family=payload.get("trigger_family", "operator_input"),
    )


def _truth_record_to_payload(record: TruthRecord) -> dict[str, Any]:
    return {
        "truth_family": record.truth_family,
        "scope": _scope_to_payload(record.scope),
        "summary": record.summary,
    }


def _truth_record_from_payload(payload: dict[str, Any]) -> TruthRecord:
    return TruthRecord(
        truth_family=payload["truth_family"],
        scope=_scope_from_payload(payload["scope"]),
        summary=payload["summary"],
    )


def _support_input_to_payload(support: SupportInput) -> dict[str, Any]:
    return {
        "source_family": support.source_family,
        "scope": _scope_to_payload(support.scope),
        "summary": support.summary,
        "source_id": support.source_id,
        "include_full_body": support.include_full_body,
    }


def _support_input_from_payload(payload: dict[str, Any]) -> SupportInput:
    return SupportInput(
        source_family=payload["source_family"],
        scope=_scope_from_payload(payload["scope"]),
        summary=payload["summary"],
        source_id=payload.get("source_id"),
        include_full_body=payload.get("include_full_body", False),
    )


def _context_package_to_payload(context_package: ContextPackage) -> dict[str, Any]:
    return {
        "purpose": context_package.purpose,
        "trigger": _trigger_input_to_payload(context_package.trigger),
        "scope": _scope_to_payload(context_package.scope),
        "truth_records": [_truth_record_to_payload(record) for record in context_package.truth_records],
        "support_inputs": [_support_input_to_payload(support) for support in context_package.support_inputs],
        "governance_truth_records": [
            _truth_record_to_payload(record) for record in context_package.governance_truth_records
        ],
        "memory_support_inputs": [
            _support_input_to_payload(support) for support in context_package.memory_support_inputs
        ],
        "compiled_knowledge_support_inputs": [
            _support_input_to_payload(support) for support in context_package.compiled_knowledge_support_inputs
        ],
        "archive_support_inputs": [
            _support_input_to_payload(support) for support in context_package.archive_support_inputs
        ],
    }


def _context_package_from_payload(payload: dict[str, Any]) -> ContextPackage:
    return ContextPackage(
        purpose=payload["purpose"],
        trigger=_trigger_input_from_payload(payload["trigger"]),
        scope=_scope_from_payload(payload["scope"]),
        truth_records=tuple(_truth_record_from_payload(record) for record in payload.get("truth_records", ())),
        support_inputs=tuple(_support_input_from_payload(support) for support in payload.get("support_inputs", ())),
        governance_truth_records=tuple(
            _truth_record_from_payload(record) for record in payload.get("governance_truth_records", ())
        ),
        memory_support_inputs=tuple(
            _support_input_from_payload(support) for support in payload.get("memory_support_inputs", ())
        ),
        compiled_knowledge_support_inputs=tuple(
            _support_input_from_payload(support)
            for support in payload.get("compiled_knowledge_support_inputs", ())
        ),
        archive_support_inputs=tuple(
            _support_input_from_payload(support) for support in payload.get("archive_support_inputs", ())
        ),
    )


def _proposal_prompt_bundle_to_payload(prompt_bundle: ProposalGenerationPromptBundle) -> dict[str, Any]:
    return {
        "request_id": prompt_bundle.request_id,
        "scope": _scope_to_payload(prompt_bundle.scope),
        "objective": prompt_bundle.objective,
        "system_instructions": prompt_bundle.system_instructions,
        "prompt": prompt_bundle.prompt,
        "prompt_file": prompt_bundle.prompt_file,
    }


def _proposal_prompt_bundle_from_payload(payload: dict[str, Any]) -> ProposalGenerationPromptBundle:
    return ProposalGenerationPromptBundle(
        request_id=payload["request_id"],
        scope=_scope_from_payload(payload["scope"]),
        objective=payload["objective"],
        system_instructions=payload["system_instructions"],
        prompt=payload["prompt"],
        prompt_file=payload.get("prompt_file", "STEP1_GENERATION.md"),
    )


def _proposal_raw_result_to_payload(raw_result: ProposalGenerationRawResult) -> dict[str, Any]:
    return {
        "prompt_bundle": _proposal_prompt_bundle_to_payload(raw_result.prompt_bundle),
        "request_id": raw_result.request_id,
        "scope": _scope_to_payload(raw_result.scope),
        "raw_output_text": raw_result.raw_output_text,
        "adapter_id": raw_result.adapter_id,
        "provider_name": raw_result.provider_name,
        "model_name": raw_result.model_name,
        "usage": _model_usage_to_payload(raw_result.usage),
        "warnings": list(raw_result.warnings),
        "raw_response_ref": raw_result.raw_response_ref,
    }


def _proposal_raw_result_from_payload(payload: dict[str, Any]) -> ProposalGenerationRawResult:
    prompt_bundle = _proposal_prompt_bundle_from_payload(payload["prompt_bundle"])
    return ProposalGenerationRawResult(
        prompt_bundle=prompt_bundle,
        request_id=payload["request_id"],
        scope=_scope_from_payload(payload["scope"]),
        raw_output_text=payload["raw_output_text"],
        adapter_id=payload["adapter_id"],
        provider_name=payload["provider_name"],
        model_name=payload["model_name"],
        usage=_model_usage_from_payload(payload["usage"]),
        warnings=tuple(payload.get("warnings", ())),
        raw_response_ref=payload.get("raw_response_ref"),
    )


def _parsed_proposal_option_to_payload(option: ParsedProposalOption) -> dict[str, Any]:
    return {
        "option_index": option.option_index,
        "proposal_type": option.proposal_type,
        "title": option.title,
        "summary": option.summary,
        "why_now": option.why_now,
        "assumptions": list(option.assumptions),
        "risks": list(option.risks),
        "constraints": list(option.constraints),
        "blockers": list(option.blockers),
        "planning_needed": option.planning_needed,
        "feasibility": option.feasibility,
        "reversibility": option.reversibility,
        "support_refs": list(option.support_refs),
    }


def _parsed_proposal_option_from_payload(payload: dict[str, Any]) -> ParsedProposalOption:
    return ParsedProposalOption(
        option_index=payload["option_index"],
        proposal_type=payload["proposal_type"],
        title=payload["title"],
        summary=payload["summary"],
        why_now=payload["why_now"],
        assumptions=tuple(payload.get("assumptions", ())),
        risks=tuple(payload.get("risks", ())),
        constraints=tuple(payload.get("constraints", ())),
        blockers=tuple(payload.get("blockers", ())),
        planning_needed=payload.get("planning_needed", False),
        feasibility=payload.get("feasibility"),
        reversibility=payload.get("reversibility"),
        support_refs=tuple(payload.get("support_refs", ())),
    )


def _parsed_proposal_generation_result_to_payload(parsed_result: ParsedProposalGenerationResult) -> dict[str, Any]:
    return {
        "raw_result": _proposal_raw_result_to_payload(parsed_result.raw_result),
        "proposal_count": parsed_result.proposal_count,
        "scarcity_reason": parsed_result.scarcity_reason,
        "options": [_parsed_proposal_option_to_payload(option) for option in parsed_result.options],
    }


def _parsed_proposal_generation_result_from_payload(payload: dict[str, Any]) -> ParsedProposalGenerationResult:
    raw_result = _proposal_raw_result_from_payload(payload["raw_result"])
    return ParsedProposalGenerationResult(
        raw_result=raw_result,
        proposal_count=payload["proposal_count"],
        scarcity_reason=payload.get("scarcity_reason"),
        options=tuple(_parsed_proposal_option_from_payload(option) for option in payload.get("options", ())),
    )


def _proposal_validation_issue_to_payload(issue: ProposalValidationIssue) -> dict[str, Any]:
    return {
        "code": issue.code,
        "message": issue.message,
        "option_index": issue.option_index,
    }


def _proposal_validation_issue_from_payload(payload: dict[str, Any]) -> ProposalValidationIssue:
    return ProposalValidationIssue(
        code=payload["code"],
        message=payload["message"],
        option_index=payload.get("option_index"),
    )


def _proposal_persisted_attempt_to_payload(attempt: ProposalPersistedAttempt) -> dict[str, Any]:
    return {
        "attempt_kind": attempt.attempt_kind,
        "prompt_bundle": (
            None if attempt.prompt_bundle is None else _proposal_prompt_bundle_to_payload(attempt.prompt_bundle)
        ),
        "raw_result": None if attempt.raw_result is None else _proposal_raw_result_to_payload(attempt.raw_result),
        "parsed_result": (
            None
            if attempt.parsed_result is None
            else _parsed_proposal_generation_result_to_payload(attempt.parsed_result)
        ),
        "parse_error": attempt.parse_error,
        "validation_issues": [_proposal_validation_issue_to_payload(issue) for issue in attempt.validation_issues],
        "proposal_result": (
            None if attempt.proposal_result is None else _proposal_result_to_payload(attempt.proposal_result)
        ),
        "failure_stage": attempt.failure_stage,
        "error_message": attempt.error_message,
        "raw_artifact_ref": attempt.raw_artifact_ref,
        "parsed_artifact_ref": attempt.parsed_artifact_ref,
        "validation_artifact_ref": attempt.validation_artifact_ref,
    }


def _proposal_persisted_attempt_from_payload(payload: dict[str, Any]) -> ProposalPersistedAttempt:
    return ProposalPersistedAttempt(
        attempt_kind=payload["attempt_kind"],
        prompt_bundle=(
            None if payload.get("prompt_bundle") is None else _proposal_prompt_bundle_from_payload(payload["prompt_bundle"])
        ),
        raw_result=(
            None if payload.get("raw_result") is None else _proposal_raw_result_from_payload(payload["raw_result"])
        ),
        parsed_result=(
            None
            if payload.get("parsed_result") is None
            else _parsed_proposal_generation_result_from_payload(payload["parsed_result"])
        ),
        parse_error=payload.get("parse_error"),
        validation_issues=tuple(
            _proposal_validation_issue_from_payload(issue) for issue in payload.get("validation_issues", ())
        ),
        proposal_result=(
            None if payload.get("proposal_result") is None else _proposal_result_from_payload(payload["proposal_result"])
        ),
        failure_stage=payload.get("failure_stage"),
        error_message=payload.get("error_message"),
        raw_artifact_ref=payload.get("raw_artifact_ref"),
        parsed_artifact_ref=payload.get("parsed_artifact_ref"),
        validation_artifact_ref=payload.get("validation_artifact_ref"),
    )


def _proposal_operator_record_to_payload(record: ProposalOperatorRecord) -> dict[str, Any]:
    return {
        "schema_version": _SCHEMA_VERSION,
        "record_class": "proposal_operator_record",
        "recorded_at": _utc_timestamp(),
        "proposal_id": record.proposal_id,
        "source_proposal_id": record.source_proposal_id,
        "created_at": record.created_at,
        "objective": record.objective,
        "scope": _scope_to_payload(record.scope),
        "context_package": _context_package_to_payload(record.context_package),
        "visible_constraints": list(record.visible_constraints),
        "initial_attempt": _proposal_persisted_attempt_to_payload(record.initial_attempt),
        "repair_attempt": (
            None if record.repair_attempt is None else _proposal_persisted_attempt_to_payload(record.repair_attempt)
        ),
        "status": record.status,
        "final_validation_outcome": record.final_validation_outcome,
        "final_failure_stage": record.final_failure_stage,
        "final_error_message": record.final_error_message,
        "final_proposal_result": (
            None if record.final_proposal_result is None else _proposal_result_to_payload(record.final_proposal_result)
        ),
        "record_ref": record.record_ref,
    }


def _proposal_operator_record_from_payload(payload: dict[str, Any]) -> ProposalOperatorRecord:
    return ProposalOperatorRecord(
        proposal_id=payload["proposal_id"],
        source_proposal_id=payload.get("source_proposal_id"),
        created_at=payload["created_at"],
        objective=payload["objective"],
        scope=_scope_from_payload(payload["scope"]),
        context_package=_context_package_from_payload(payload["context_package"]),
        visible_constraints=tuple(payload.get("visible_constraints", ())),
        initial_attempt=_proposal_persisted_attempt_from_payload(payload["initial_attempt"]),
        repair_attempt=(
            None
            if payload.get("repair_attempt") is None
            else _proposal_persisted_attempt_from_payload(payload["repair_attempt"])
        ),
        status=payload["status"],
        final_validation_outcome=payload.get("final_validation_outcome", "not_reached"),
        final_failure_stage=payload.get("final_failure_stage"),
        final_error_message=payload.get("final_error_message"),
        final_proposal_result=(
            None
            if payload.get("final_proposal_result") is None
            else _proposal_result_from_payload(payload["final_proposal_result"])
        ),
        record_ref=payload.get("record_ref"),
    )


def _selection_result_to_payload(selection_result: SelectionResult) -> dict[str, Any]:
    return {
        "selection_id": str(selection_result.selection_id),
        "considered_proposal_ids": [str(proposal_id) for proposal_id in selection_result.considered_proposal_ids],
        "selected_proposal_id": (
            None if selection_result.selected_proposal_id is None else str(selection_result.selected_proposal_id)
        ),
        "non_selection_outcome": selection_result.non_selection_outcome,
        "rationale": selection_result.rationale,
    }


def _selection_result_from_payload(payload: dict[str, Any]) -> SelectionResult:
    return SelectionResult(
        selection_id=payload["selection_id"],
        considered_proposal_ids=tuple(payload["considered_proposal_ids"]),
        selected_proposal_id=payload.get("selected_proposal_id"),
        non_selection_outcome=payload.get("non_selection_outcome"),
        rationale=payload["rationale"],
    )


def _operator_override_to_payload(operator_override: OperatorSelectionOverride) -> dict[str, Any]:
    return {
        "override_id": operator_override.override_id,
        "selection_id": str(operator_override.selection_id),
        "considered_proposal_ids": [str(proposal_id) for proposal_id in operator_override.considered_proposal_ids],
        "original_selection_disposition": operator_override.original_selection_disposition,
        "original_selected_proposal_id": (
            None
            if operator_override.original_selected_proposal_id is None
            else str(operator_override.original_selected_proposal_id)
        ),
        "chosen_proposal_id": str(operator_override.chosen_proposal_id),
        "operator_rationale": operator_override.operator_rationale,
    }


def _operator_override_from_payload(payload: dict[str, Any]) -> OperatorSelectionOverride:
    return OperatorSelectionOverride(
        override_id=payload["override_id"],
        selection_id=payload["selection_id"],
        considered_proposal_ids=tuple(payload["considered_proposal_ids"]),
        original_selection_disposition=payload["original_selection_disposition"],
        original_selected_proposal_id=payload.get("original_selected_proposal_id"),
        chosen_proposal_id=payload["chosen_proposal_id"],
        operator_rationale=payload["operator_rationale"],
    )


def _governed_execution_request_to_payload(request: GovernedExecutionRequest) -> dict[str, Any]:
    return {
        "action": _action_to_payload(request.action),
        "governance_decision": _action_entry_decision_to_payload(request.governance_decision),
    }


def _governed_execution_request_from_payload(payload: dict[str, Any]) -> GovernedExecutionRequest:
    return GovernedExecutionRequest(
        action=_action_from_payload(payload["action"]),
        governance_decision=_action_entry_decision_from_payload(payload["governance_decision"]),
    )


def _execution_result_to_payload(execution_result: ExecutionResult) -> dict[str, Any]:
    return {
        "governed_request": _governed_execution_request_to_payload(execution_result.governed_request),
        "execution_status": execution_result.execution_status,
        "output_summary": execution_result.output_summary,
        "artifact_refs": [],
        "trace_refs": [],
        "observed_side_effect_notes": list(execution_result.observed_side_effect_notes),
        "execution_errors": list(execution_result.execution_errors),
        "execution_warnings": list(execution_result.execution_warnings),
        "started_at": execution_result.started_at,
        "ended_at": execution_result.ended_at,
        "execution_family": execution_result.execution_family,
        "execution_command_id": execution_result.execution_command_id,
        "executed_command": execution_result.executed_command,
        "working_directory": execution_result.working_directory,
        "exit_code": execution_result.exit_code,
        "stdout_excerpt": execution_result.stdout_excerpt,
        "stderr_excerpt": execution_result.stderr_excerpt,
    }


def _execution_result_from_payload(payload: dict[str, Any]) -> ExecutionResult:
    return ExecutionResult(
        governed_request=_governed_execution_request_from_payload(payload["governed_request"]),
        execution_status=payload["execution_status"],
        output_summary=payload.get("output_summary"),
        observed_side_effect_notes=tuple(payload.get("observed_side_effect_notes", ())),
        execution_errors=tuple(payload.get("execution_errors", ())),
        execution_warnings=tuple(payload.get("execution_warnings", ())),
        started_at=payload.get("started_at"),
        ended_at=payload.get("ended_at"),
        execution_family=payload.get("execution_family"),
        execution_command_id=payload.get("execution_command_id"),
        executed_command=payload.get("executed_command"),
        working_directory=payload.get("working_directory"),
        exit_code=payload.get("exit_code"),
        stdout_excerpt=payload.get("stdout_excerpt"),
        stderr_excerpt=payload.get("stderr_excerpt"),
    )


def _outcome_to_payload(outcome: Outcome) -> dict[str, Any]:
    return {
        "action_id": outcome.action_id,
        "scope": _scope_to_payload(outcome.scope),
        "outcome_state": outcome.outcome_state,
        "observed_completion_posture": outcome.observed_completion_posture,
        "target_effect_posture": outcome.target_effect_posture,
        "artifact_posture": outcome.artifact_posture,
        "side_effect_posture": outcome.side_effect_posture,
        "uncertainty_markers": list(outcome.uncertainty_markers),
        "mismatch_markers": list(outcome.mismatch_markers),
        "evidence_refs": [],
    }


def _outcome_from_payload(payload: dict[str, Any]) -> Outcome:
    return Outcome(
        action_id=payload["action_id"],
        scope=_scope_from_payload(payload["scope"]),
        outcome_state=payload["outcome_state"],
        observed_completion_posture=payload["observed_completion_posture"],
        target_effect_posture=payload["target_effect_posture"],
        artifact_posture=payload["artifact_posture"],
        side_effect_posture=payload["side_effect_posture"],
        uncertainty_markers=tuple(payload.get("uncertainty_markers", ())),
        mismatch_markers=tuple(payload.get("mismatch_markers", ())),
    )


def _evaluation_result_to_payload(evaluation: EvaluationResult) -> dict[str, Any]:
    return {
        "objective_summary": evaluation.objective_summary,
        "outcome": _outcome_to_payload(evaluation.outcome),
        "evaluation_verdict": evaluation.evaluation_verdict,
        "rationale": evaluation.rationale,
        "recommended_next_step": evaluation.recommended_next_step,
        "deterministic_override_reasons": list(evaluation.deterministic_override_reasons),
    }


def _evaluation_result_from_payload(payload: dict[str, Any]) -> EvaluationResult:
    return EvaluationResult(
        objective_summary=payload["objective_summary"],
        outcome=_outcome_from_payload(payload["outcome"]),
        evaluation_verdict=payload["evaluation_verdict"],
        rationale=payload["rationale"],
        recommended_next_step=payload["recommended_next_step"],
        deterministic_override_reasons=tuple(payload.get("deterministic_override_reasons", ())),
    )


def _transition_request_to_payload(request: TransitionRequest) -> dict[str, Any]:
    return {
        "transition_id": str(request.transition_id),
        "transition_type": request.transition_type,
        "basis_state_version": request.basis_state_version,
        "scope": _scope_to_payload(request.scope),
        "payload": dict(request.payload),
    }


def _transition_result_to_payload(result: TransitionResult) -> dict[str, Any]:
    return {
        "transition_id": str(result.transition_id),
        "transition_result": result.transition_result,
        "state_before_version": result.state_before_version,
        "state_after_version": result.state_after_version,
        "changed_paths": list(result.changed_paths),
        "validation_errors": [
            {
                "code": issue.code,
                "message": issue.message,
                "field_name": issue.field_name,
            }
            for issue in result.validation_errors
        ],
    }


def _transition_result_from_payload(payload: dict[str, Any], *, state: GlobalState) -> TransitionResult:
    from jeff.core.schemas.envelopes import ValidationIssue

    return TransitionResult(
        transition_id=payload["transition_id"],
        transition_result=payload["transition_result"],
        state_before_version=payload["state_before_version"],
        state_after_version=payload["state_after_version"],
        state=state,
        changed_paths=tuple(payload.get("changed_paths", ())),
        validation_errors=tuple(
            ValidationIssue(
                code=issue["code"],
                message=issue["message"],
                field_name=issue.get("field_name"),
            )
            for issue in payload.get("validation_errors", ())
        ),
    )


def _flow_lifecycle_to_payload(lifecycle: FlowLifecycle) -> dict[str, Any]:
    return {
        "flow_id": lifecycle.flow_id,
        "flow_family": lifecycle.flow_family,
        "scope": _scope_to_payload(lifecycle.scope),
        "lifecycle_state": lifecycle.lifecycle_state,
        "current_stage": lifecycle.current_stage,
        "reason_summary": lifecycle.reason_summary,
    }


def _flow_lifecycle_from_payload(payload: dict[str, Any]) -> FlowLifecycle:
    return FlowLifecycle(
        flow_id=payload["flow_id"],
        flow_family=payload["flow_family"],
        scope=_scope_from_payload(payload["scope"]),
        lifecycle_state=payload["lifecycle_state"],
        current_stage=payload.get("current_stage"),
        reason_summary=payload.get("reason_summary"),
    )


def _event_to_payload(event: OrchestrationEvent) -> dict[str, Any]:
    return {
        "ordinal": event.ordinal,
        "flow_family": event.flow_family,
        "scope": _scope_to_payload(event.scope),
        "stage": event.stage,
        "event_type": event.event_type,
        "summary": event.summary,
        "emitted_at": event.emitted_at,
    }


def _event_from_payload(payload: dict[str, Any]) -> OrchestrationEvent:
    return OrchestrationEvent(
        ordinal=payload["ordinal"],
        flow_family=payload["flow_family"],
        scope=_scope_from_payload(payload["scope"]),
        stage=payload.get("stage"),
        event_type=payload["event_type"],
        summary=payload["summary"],
        emitted_at=payload["emitted_at"],
    )


def _routing_decision_to_payload(routing: RoutingDecision) -> dict[str, Any]:
    return {
        "route_kind": routing.route_kind,
        "routed_outcome": routing.routed_outcome,
        "scope": _scope_to_payload(routing.scope),
        "source_stage": routing.source_stage,
        "reason_summary": routing.reason_summary,
        "auto_execute": routing.auto_execute,
    }


def _routing_decision_from_payload(payload: dict[str, Any]) -> RoutingDecision:
    return RoutingDecision(
        route_kind=payload["route_kind"],
        routed_outcome=payload["routed_outcome"],
        scope=_scope_from_payload(payload["scope"]),
        source_stage=payload["source_stage"],
        reason_summary=payload["reason_summary"],
        auto_execute=payload.get("auto_execute", False),
    )


def _supported_flow_output_to_payload(name: str, value: object) -> dict[str, Any] | None:
    if isinstance(value, ProposalResult):
        return {"kind": "proposal_result", "value": _proposal_result_to_payload(value)}
    if isinstance(value, SelectionResult):
        return {"kind": "selection_result", "value": _selection_result_to_payload(value)}
    if isinstance(value, Policy):
        return {"kind": "policy", "value": _policy_to_payload(value)}
    if isinstance(value, Approval):
        return {"kind": "approval", "value": _approval_to_payload(value)}
    if isinstance(value, CurrentTruthSnapshot):
        return {"kind": "current_truth_snapshot", "value": _truth_snapshot_to_payload(value)}
    if isinstance(value, ActionEntryDecision):
        return {"kind": "action_entry_decision", "value": _action_entry_decision_to_payload(value)}
    if isinstance(value, ExecutionResult):
        return {"kind": "execution_result", "value": _execution_result_to_payload(value)}
    if isinstance(value, Outcome):
        return {"kind": "outcome", "value": _outcome_to_payload(value)}
    if isinstance(value, EvaluationResult):
        return {"kind": "evaluation_result", "value": _evaluation_result_to_payload(value)}
    if isinstance(value, TransitionResult):
        return {"kind": "transition_result", "value": _transition_result_to_payload(value)}
    del name
    return None


def _supported_flow_output_from_payload(payload: dict[str, Any], *, state: GlobalState) -> object:
    kind = payload["kind"]
    value = payload["value"]
    if kind == "proposal_result":
        return _proposal_result_from_payload(value)
    if kind == "selection_result":
        return _selection_result_from_payload(value)
    if kind == "policy":
        return _policy_from_payload(value)
    if kind == "approval":
        return _approval_from_payload(value)
    if kind == "current_truth_snapshot":
        return _truth_snapshot_from_payload(value)
    if kind == "action_entry_decision":
        return _action_entry_decision_from_payload(value)
    if kind == "execution_result":
        return _execution_result_from_payload(value)
    if kind == "outcome":
        return _outcome_from_payload(value)
    if kind == "evaluation_result":
        return _evaluation_result_from_payload(value)
    if kind == "transition_result":
        return _transition_result_from_payload(value, state=state)
    raise ValueError(f"unsupported persisted flow output kind: {kind}")


def _flow_run_to_payload(run_id: str, flow_run: FlowRunResult) -> dict[str, Any]:
    outputs: dict[str, Any] = {}
    for name, value in flow_run.outputs.items():
        encoded = _supported_flow_output_to_payload(name, value)
        if encoded is not None:
            outputs[name] = encoded

    return {
        "schema_version": _SCHEMA_VERSION,
        "record_class": "flow_run_support",
        "recorded_at": _utc_timestamp(),
        "run_id": run_id,
        "lifecycle": _flow_lifecycle_to_payload(flow_run.lifecycle),
        "outputs": outputs,
        "events": [_event_to_payload(event) for event in flow_run.events],
        "routing_decision": (
            None if flow_run.routing_decision is None else _routing_decision_to_payload(flow_run.routing_decision)
        ),
        "selection_failure": None,
        "objective_summary": flow_run.objective_summary,
        "memory_handoff_attempted": flow_run.memory_handoff_attempted,
        "memory_handoff_result": _memory_write_decision_to_payload(flow_run.memory_handoff_result),
        "memory_handoff_note": flow_run.memory_handoff_note,
    }


def _flow_run_from_payload(payload: dict[str, Any], *, state: GlobalState) -> tuple[str, FlowRunResult]:
    outputs = {
        name: _supported_flow_output_from_payload(output_payload, state=state)
        for name, output_payload in payload.get("outputs", {}).items()
    }
    flow_run = FlowRunResult(
        lifecycle=_flow_lifecycle_from_payload(payload["lifecycle"]),
        outputs=outputs,
        events=tuple(_event_from_payload(event_payload) for event_payload in payload.get("events", ())),
        routing_decision=(
            None
            if payload.get("routing_decision") is None
            else _routing_decision_from_payload(payload["routing_decision"])
        ),
        selection_failure=None,
        objective_summary=payload.get("objective_summary"),
        memory_handoff_attempted=payload.get("memory_handoff_attempted", False),
        memory_handoff_result=_memory_write_decision_from_payload(payload.get("memory_handoff_result")),
        memory_handoff_note=payload.get("memory_handoff_note"),
    )
    return payload["run_id"], flow_run


def _memory_write_decision_to_payload(memory_write: RunMemoryHandoffResultSummary | None) -> dict[str, Any] | None:
    if memory_write is None:
        return None
    return {
        "write_outcome": memory_write.write_outcome,
        "candidate_id": str(memory_write.candidate_id),
        "memory_id": None if memory_write.memory_id is None else str(memory_write.memory_id),
        "reasons": list(memory_write.reasons),
    }


def _memory_write_decision_from_payload(payload: dict[str, Any] | None) -> RunMemoryHandoffResultSummary | None:
    if payload is None:
        return None
    return RunMemoryHandoffResultSummary(
        write_outcome=payload["write_outcome"],
        candidate_id=payload["candidate_id"],
        memory_id=payload.get("memory_id"),
        reasons=tuple(payload.get("reasons", ())),
    )


def _selection_review_to_payload(run_id: str, selection_review: SelectionReviewRecord) -> dict[str, Any]:
    return {
        "schema_version": _SCHEMA_VERSION,
        "record_class": "selection_review_support",
        "recorded_at": _utc_timestamp(),
        "run_id": run_id,
        "selection_result": (
            None
            if selection_review.selection_result is None
            else _selection_result_to_payload(selection_review.selection_result)
        ),
        "operator_override": (
            None
            if selection_review.operator_override is None
            else _operator_override_to_payload(selection_review.operator_override)
        ),
        "proposal_result": (
            None
            if selection_review.proposal_result is None
            else _proposal_result_to_payload(selection_review.proposal_result)
        ),
        "action_scope": (
            None if selection_review.action_scope is None else _scope_to_payload(selection_review.action_scope)
        ),
        "basis_state_version": selection_review.basis_state_version,
        "governance_policy": (
            None
            if selection_review.governance_policy is None
            else _policy_to_payload(selection_review.governance_policy)
        ),
        "governance_approval": (
            None
            if selection_review.governance_approval is None
            else _approval_to_payload(selection_review.governance_approval)
        ),
        "governance_truth": (
            None
            if selection_review.governance_truth is None
            else _truth_snapshot_to_payload(selection_review.governance_truth)
        ),
    }


def _selection_review_from_payload(payload: dict[str, Any]) -> tuple[str, SelectionReviewRecord]:
    selection_review = SelectionReviewRecord(
        selection_result=(
            None
            if payload.get("selection_result") is None
            else _selection_result_from_payload(payload["selection_result"])
        ),
        operator_override=(
            None
            if payload.get("operator_override") is None
            else _operator_override_from_payload(payload["operator_override"])
        ),
        resolved_basis=None,
        materialized_effective_proposal=None,
        formed_action_result=None,
        governance_handoff_result=None,
        proposal_result=(
            None if payload.get("proposal_result") is None else _proposal_result_from_payload(payload["proposal_result"])
        ),
        action_scope=None if payload.get("action_scope") is None else _scope_from_payload(payload["action_scope"]),
        basis_state_version=payload.get("basis_state_version"),
        governance_policy=(
            None
            if payload.get("governance_policy") is None
            else _policy_from_payload(payload["governance_policy"])
        ),
        governance_approval=(
            None
            if payload.get("governance_approval") is None
            else _approval_from_payload(payload["governance_approval"])
        ),
        governance_truth=(
            None
            if payload.get("governance_truth") is None
            else _truth_snapshot_from_payload(payload["governance_truth"])
        ),
    )
    return payload["run_id"], selection_review


@dataclass(frozen=True, slots=True)
class JeffRuntimeHome:
    root_dir: Path

    @classmethod
    def from_base_dir(cls, base_dir: str | Path | None = None) -> "JeffRuntimeHome":
        base_path = Path.cwd() if base_dir is None else Path(base_dir)
        return cls(root_dir=base_path / ".jeff_runtime")

    @property
    def config_dir(self) -> Path:
        return self.root_dir / "config"

    @property
    def state_dir(self) -> Path:
        return self.root_dir / "state"

    @property
    def transitions_dir(self) -> Path:
        return self.state_dir / "transitions"

    @property
    def artifacts_dir(self) -> Path:
        return self.root_dir / "artifacts"

    @property
    def research_artifacts_dir(self) -> Path:
        return self.artifacts_dir / "research"

    @property
    def flows_dir(self) -> Path:
        return self.root_dir / "flows"

    @property
    def flow_runs_dir(self) -> Path:
        return self.flows_dir / "flow_runs"

    @property
    def reviews_dir(self) -> Path:
        return self.root_dir / "reviews"

    @property
    def selection_reviews_dir(self) -> Path:
        return self.reviews_dir / "selection_reviews"

    @property
    def proposal_records_dir(self) -> Path:
        return self.reviews_dir / "proposals"

    @property
    def cache_dir(self) -> Path:
        return self.root_dir / "cache"

    @property
    def proposal_artifacts_dir(self) -> Path:
        return self.artifacts_dir / "proposals"

    @property
    def logs_dir(self) -> Path:
        return self.root_dir / "logs"

    @property
    def runtime_lock_path(self) -> Path:
        return self.config_dir / "runtime.lock.json"

    @property
    def mutation_lock_path(self) -> Path:
        return self.config_dir / "runtime.mutation.lock"

    @property
    def canonical_state_path(self) -> Path:
        return self.state_dir / "canonical_state.json"

    @property
    def legacy_research_artifacts_dir(self) -> Path:
        return self.root_dir / "research_artifacts"

    def ensure_layout(self) -> None:
        for path in (
            self.config_dir,
            self.state_dir,
            self.transitions_dir,
            self.research_artifacts_dir,
            self.proposal_artifacts_dir,
            self.flow_runs_dir,
            self.selection_reviews_dir,
            self.proposal_records_dir,
            self.cache_dir,
            self.logs_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)
        if not self.runtime_lock_path.exists():
            _write_json(
                self.runtime_lock_path,
                {
                    "schema_version": _SCHEMA_VERSION,
                    "runtime_layout_version": _LAYOUT_VERSION,
                    "runtime_root": str(self.root_dir.resolve()),
                    "created_at": _utc_timestamp(),
                },
            )

    def reset(self, *, preserve_paths: tuple[Path, ...] = ()) -> None:
        if not self.root_dir.exists():
            return

        resolved_root = self.root_dir.resolve(strict=False)
        resolved_preserve_paths = tuple(path.resolve(strict=False) for path in preserve_paths)
        for preserved_path in resolved_preserve_paths:
            if not _is_relative_to(preserved_path, resolved_root):
                raise ValueError("runtime reset preserve_paths must stay inside the runtime root")

        for child in self.root_dir.iterdir():
            _clear_runtime_path(child, preserved_paths=resolved_preserve_paths)


@dataclass
class _RuntimeMutationLock:
    path: Path
    fd: int

    def release(self) -> None:
        try:
            os.close(self.fd)
        finally:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass


class PersistedRuntimeStore:
    def __init__(self, home: JeffRuntimeHome) -> None:
        self.home = home
        self.home.ensure_layout()
        self._held_mutation_lock: _RuntimeMutationLock | None = None
        self._mutation_lock_depth = 0

    @classmethod
    def from_base_dir(cls, base_dir: str | Path | None = None) -> "PersistedRuntimeStore":
        return cls(JeffRuntimeHome.from_base_dir(base_dir=base_dir))

    def canonical_state_exists(self) -> bool:
        return self.home.canonical_state_path.exists()

    def reset_runtime_home(self) -> None:
        with self.mutation_guard():
            self.home.reset(preserve_paths=(self.home.mutation_lock_path,))
            self.home.ensure_layout()

    def _read_existing_mutation_lock(self) -> dict[str, Any] | None:
        if not self.home.mutation_lock_path.exists():
            return None
        try:
            payload = _read_json(self.home.mutation_lock_path)
        except ValueError:
            return None
        return payload

    def acquire_mutation_lock(self) -> _RuntimeMutationLock:
        self.home.ensure_layout()
        path = self.home.mutation_lock_path
        payload = {
            "schema_version": _SCHEMA_VERSION,
            "record_class": "runtime_mutation_lock",
            "pid": os.getpid(),
            "created_at": _utc_timestamp(),
            "runtime_root": str(self.home.root_dir.resolve()),
        }
        encoded = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")

        while True:
            try:
                fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError as exc:
                existing = self._read_existing_mutation_lock() or {}
                existing_pid = existing.get("pid")
                if isinstance(existing_pid, int) and not _pid_is_running(existing_pid):
                    try:
                        path.unlink()
                    except FileNotFoundError:
                        pass
                    continue
                owner = f"pid={existing_pid}" if isinstance(existing_pid, int) else "unknown owner"
                created_at = existing.get("created_at") if isinstance(existing.get("created_at"), str) else "unknown time"
                raise RuntimeMutationLockError(
                    "persisted runtime mutation is already in progress by another Jeff process "
                    f"({owner}, acquired_at={created_at}). Try again after it finishes."
                ) from exc
            except OSError as exc:
                if exc.errno == errno.EEXIST:
                    continue
                raise
            try:
                os.write(fd, encoded)
                return _RuntimeMutationLock(path=path, fd=fd)
            except Exception:
                os.close(fd)
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
                raise

    @contextmanager
    def mutation_guard(self):
        if self._held_mutation_lock is None:
            lock = self.acquire_mutation_lock()
            self._held_mutation_lock = lock
        else:
            lock = self._held_mutation_lock
        self._mutation_lock_depth += 1
        try:
            yield
        finally:
            self._mutation_lock_depth -= 1
            if self._mutation_lock_depth == 0:
                lock.release()
                self._held_mutation_lock = None

    def load_canonical_state(self) -> GlobalState:
        payload = _read_json(self.home.canonical_state_path)
        return _state_from_payload(payload["state"])

    def save_canonical_state(self, state: GlobalState) -> None:
        _write_json(
            self.home.canonical_state_path,
            {
                "schema_version": _SCHEMA_VERSION,
                "record_class": "canonical_state_snapshot",
                "recorded_at": _utc_timestamp(),
                "state": _state_to_payload(state),
            },
        )

    def apply_transition(self, state: GlobalState, request: TransitionRequest) -> TransitionResult:
        with self.mutation_guard():
            result = apply_transition(state, request)
            self.save_transition_record(request=request, result=result)
            if result.transition_result == "committed":
                self.save_canonical_state(result.state)
        return result

    def save_transition_record(self, *, request: TransitionRequest, result: TransitionResult) -> Path:
        path = self.home.transitions_dir / f"{request.transition_id}.json"
        _write_json(
            path,
            {
                "schema_version": _SCHEMA_VERSION,
                "record_class": "transition_audit_support",
                "recorded_at": _utc_timestamp(),
                "request": _transition_request_to_payload(request),
                "result": _transition_result_to_payload(result),
            },
        )
        return path

    def save_flow_run(self, run_id: str, flow_run: FlowRunResult) -> Path:
        path = self.home.flow_runs_dir / f"{run_id}.json"
        with self.mutation_guard():
            _write_json(path, _flow_run_to_payload(run_id, flow_run))
        return path

    def load_flow_runs(self, *, state: GlobalState | None = None) -> dict[str, FlowRunResult]:
        resolved_state = self.load_canonical_state() if state is None else state
        records: dict[str, FlowRunResult] = {}
        for path in sorted(self.home.flow_runs_dir.glob("*.json")):
            run_id, flow_run = _flow_run_from_payload(_read_json(path), state=resolved_state)
            records[run_id] = flow_run
        return records

    def save_selection_review(self, run_id: str, selection_review: SelectionReviewRecord) -> Path:
        path = self.home.selection_reviews_dir / f"{run_id}.json"
        with self.mutation_guard():
            _write_json(path, _selection_review_to_payload(run_id, selection_review))
        return path

    def save_proposal_record(self, record: ProposalOperatorRecord) -> ProposalOperatorRecord:
        with self.mutation_guard():
            stored_record = self._record_with_artifact_refs(record)
            record_path = self.home.proposal_records_dir / f"{stored_record.proposal_id}.json"
            record_ref = str(record_path.resolve())
            stored_record = ProposalOperatorRecord(
                proposal_id=stored_record.proposal_id,
                source_proposal_id=stored_record.source_proposal_id,
                created_at=stored_record.created_at,
                objective=stored_record.objective,
                scope=stored_record.scope,
                context_package=stored_record.context_package,
                visible_constraints=stored_record.visible_constraints,
                initial_attempt=stored_record.initial_attempt,
                repair_attempt=stored_record.repair_attempt,
                status=stored_record.status,
                final_validation_outcome=stored_record.final_validation_outcome,
                final_failure_stage=stored_record.final_failure_stage,
                final_error_message=stored_record.final_error_message,
                final_proposal_result=stored_record.final_proposal_result,
                record_ref=record_ref,
            )
            _write_json(record_path, _proposal_operator_record_to_payload(stored_record))
        return stored_record

    def load_proposal_records(self) -> dict[str, ProposalOperatorRecord]:
        records: dict[str, ProposalOperatorRecord] = {}
        for path in sorted(self.home.proposal_records_dir.glob("*.json")):
            record = _proposal_operator_record_from_payload(_read_json(path))
            records[record.proposal_id] = record
        return records

    def _record_with_artifact_refs(self, record: ProposalOperatorRecord) -> ProposalOperatorRecord:
        artifact_dir = self.home.proposal_artifacts_dir / record.proposal_id
        artifact_dir.mkdir(parents=True, exist_ok=True)
        initial_attempt = self._attempt_with_artifact_refs(artifact_dir=artifact_dir, attempt=record.initial_attempt)
        repair_attempt = (
            None
            if record.repair_attempt is None
            else self._attempt_with_artifact_refs(artifact_dir=artifact_dir, attempt=record.repair_attempt)
        )
        return ProposalOperatorRecord(
            proposal_id=record.proposal_id,
            source_proposal_id=record.source_proposal_id,
            created_at=record.created_at,
            objective=record.objective,
            scope=record.scope,
            context_package=record.context_package,
            visible_constraints=record.visible_constraints,
            initial_attempt=initial_attempt,
            repair_attempt=repair_attempt,
            status=record.status,
            final_validation_outcome=record.final_validation_outcome,
            final_failure_stage=record.final_failure_stage,
            final_error_message=record.final_error_message,
            final_proposal_result=record.final_proposal_result,
            record_ref=record.record_ref,
        )

    def _attempt_with_artifact_refs(
        self,
        *,
        artifact_dir: Path,
        attempt: ProposalPersistedAttempt,
    ) -> ProposalPersistedAttempt:
        raw_ref = attempt.raw_artifact_ref
        if attempt.raw_result is not None:
            raw_path = artifact_dir / f"{attempt.attempt_kind}-raw.txt"
            raw_path.write_text(attempt.raw_result.raw_output_text, encoding="utf-8")
            raw_ref = str(raw_path.resolve())

        parsed_ref = attempt.parsed_artifact_ref
        if attempt.parsed_result is not None:
            parsed_path = artifact_dir / f"{attempt.attempt_kind}-parsed.json"
            _write_json(parsed_path, _parsed_proposal_generation_result_to_payload(attempt.parsed_result))
            parsed_ref = str(parsed_path.resolve())

        validation_ref = attempt.validation_artifact_ref
        if attempt.validation_issues:
            validation_path = artifact_dir / f"{attempt.attempt_kind}-validation.json"
            _write_json(
                validation_path,
                {
                    "issues": [
                        _proposal_validation_issue_to_payload(issue) for issue in attempt.validation_issues
                    ]
                },
            )
            validation_ref = str(validation_path.resolve())

        return ProposalPersistedAttempt(
            attempt_kind=attempt.attempt_kind,
            prompt_bundle=attempt.prompt_bundle,
            raw_result=attempt.raw_result,
            parsed_result=attempt.parsed_result,
            parse_error=attempt.parse_error,
            validation_issues=attempt.validation_issues,
            proposal_result=attempt.proposal_result,
            failure_stage=attempt.failure_stage,
            error_message=attempt.error_message,
            raw_artifact_ref=raw_ref,
            parsed_artifact_ref=parsed_ref,
            validation_artifact_ref=validation_ref,
        )

    def load_selection_reviews(self) -> dict[str, SelectionReviewRecord]:
        records: dict[str, SelectionReviewRecord] = {}
        for path in sorted(self.home.selection_reviews_dir.glob("*.json")):
            run_id, selection_review = _selection_review_from_payload(_read_json(path))
            records[run_id] = selection_review
        return records

    def research_artifact_legacy_dirs(self, *extra_dirs: Path | None) -> tuple[Path, ...]:
        directories: list[Path] = []
        for candidate in (self.home.legacy_research_artifacts_dir, *extra_dirs):
            if candidate is None:
                continue
            resolved = Path(candidate)
            if resolved == self.home.research_artifacts_dir:
                continue
            if resolved not in directories:
                directories.append(resolved)
        return tuple(directories)


__all__ = [
    "JeffRuntimeHome",
    "PersistedRuntimeStore",
    "RuntimeMutationLockError",
]
