"""Bounded manual proposal operator commands."""

from __future__ import annotations

from jeff.cognitive import (
    ProposalGenerationParseError,
    ProposalGenerationRequest,
    ProposalGenerationValidationError,
    ProposalOperatorRecord,
    ProposalPipelineFailure,
    build_proposal_input_bundle,
    build_proposal_record_id,
    build_operator_record_from_pipeline_result,
    parse_proposal_generation_result,
    proposal_record_created_at_now,
    resolve_committed_memory_support_records,
    run_proposal_generation_pipeline,
    run_proposal_repair_attempt,
    validate_proposal_generation_result,
)
from jeff.cognitive.types import require_text
from jeff.core.schemas import Scope

from ..json_views import proposal_raw_json, proposal_record_json, proposal_validation_json
from ..render import render_proposal_raw, render_proposal_record, render_proposal_validation
from ..session import CliSession
from .models import CommandResult, InterfaceContext
from .support.context import assemble_live_context_package, build_run_governance_inputs
from .support.scope_resolution import require_project_for_run, resolve_historical_run, resolve_run_from_tokens


def proposal_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    if len(tokens) < 2:
        raise ValueError(
            "proposal command must be 'proposal <objective>', 'proposal show [run_id or proposal_id]', 'proposal raw [run_id or proposal_id]', 'proposal validate [run_id or proposal_id]', or 'proposal repair [run_id or proposal_id]'"
        )

    if tokens[1] == "show":
        return proposal_show_command(tokens=tokens, session=session, context=context)
    if tokens[1] == "raw":
        return proposal_raw_command(tokens=tokens, session=session, context=context)
    if tokens[1] == "validate":
        return proposal_validate_command(tokens=tokens, session=session, context=context)
    if tokens[1] == "repair":
        return proposal_repair_command(tokens=tokens, session=session, context=context)
    return proposal_run_command(tokens=tokens, session=session, context=context)


def proposal_run_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    if context.infrastructure_services is None:
        raise ValueError(
            "proposal generation requires configured InfrastructureServices. Add jeff.runtime.toml in the startup directory to enable the bounded /proposal surface."
        )
    runtime_store = _require_runtime_store(context)
    objective = require_text(" ".join(tokens[1:]), field_name="objective")
    run, next_session, notice = resolve_historical_run(
        tokens=["proposal"],
        session=session,
        context=context,
        command_name="proposal",
    )
    run_scope = Scope(
        project_id=str(run.project_id),
        work_unit_id=str(run.work_unit_id),
        run_id=str(run.run_id),
    )
    governance_policy, governance_approval, governance_truth = build_run_governance_inputs(
        context=context,
        scope=run_scope,
    )
    live_context_package = assemble_live_context_package(
        context=context,
        trigger_summary=objective,
        purpose=_direct_proposal_context_purpose(objective),
        scope=run_scope,
        knowledge_topic_query=objective,
        governance_truth=governance_truth,
        governance_policy=governance_policy,
        governance_approval=governance_approval,
    )
    proposal_input_bundle = build_proposal_input_bundle(
        objective=objective,
        scope=run_scope,
        context_package=live_context_package,
        committed_memory_records=resolve_committed_memory_support_records(
            project_id=str(run_scope.project_id),
            context_package=live_context_package,
            store=context.memory_store,
        ),
    )
    request = ProposalGenerationRequest(
        objective=objective,
        scope=run_scope,
        context_package=live_context_package,
        proposal_input_bundle=proposal_input_bundle,
    )
    pipeline_result = run_proposal_generation_pipeline(
        request,
        infrastructure_services=context.infrastructure_services,
    )
    created_at = proposal_record_created_at_now()
    record = build_operator_record_from_pipeline_result(
        proposal_id=build_proposal_record_id(scope=run_scope, objective=objective, created_at=created_at),
        created_at=created_at,
        request=request,
        pipeline_result=pipeline_result,
    )
    stored_record = runtime_store.save_proposal_record(record)
    payload = proposal_record_json(record=stored_record, view="proposal_run")
    text = render_proposal_record(payload)
    if notice is not None:
        text = f"{notice}\n{text}"
    return CommandResult(context=context, session=next_session, text=text, json_payload=payload)


def proposal_show_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    if len(tokens) > 3:
        raise ValueError("proposal show must be 'proposal show [run_id or proposal_id]'")
    record, next_session, notice = _resolve_proposal_record(
        tokens=tokens,
        session=session,
        context=context,
        command_name="proposal show",
    )
    payload = proposal_record_json(record=record)
    text = render_proposal_record(payload)
    if notice is not None:
        text = f"{notice}\n{text}"
    return CommandResult(context=context, session=next_session, text=text, json_payload=payload)


def proposal_raw_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    if len(tokens) > 3:
        raise ValueError("proposal raw must be 'proposal raw [run_id or proposal_id]'")
    record, next_session, notice = _resolve_proposal_record(
        tokens=tokens,
        session=session,
        context=context,
        command_name="proposal raw",
    )
    payload = proposal_raw_json(record)
    text = render_proposal_raw(payload)
    if notice is not None:
        text = f"{notice}\n{text}"
    return CommandResult(context=context, session=next_session, text=text, json_payload=payload)


def proposal_validate_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    if len(tokens) > 3:
        raise ValueError("proposal validate must be 'proposal validate [run_id or proposal_id]'")
    record, next_session, notice = _resolve_proposal_record(
        tokens=tokens,
        session=session,
        context=context,
        command_name="proposal validate",
    )
    final_attempt = record.final_attempt
    if final_attempt.raw_result is None:
        payload = proposal_validation_json(
            record=record,
            attempt_kind=final_attempt.attempt_kind,
            parse_error=final_attempt.error_message or "no raw output is available for validation",
            validation_issues=(),
            proposal_result=None,
        )
    else:
        parse_error = None
        validation_issues = ()
        proposal_result = None
        try:
            parsed_result = parse_proposal_generation_result(final_attempt.raw_result)
        except ProposalGenerationParseError as exc:
            parse_error = str(exc)
        else:
            try:
                proposal_result = validate_proposal_generation_result(parsed_result)
            except ProposalGenerationValidationError as exc:
                validation_issues = exc.issues
        payload = proposal_validation_json(
            record=record,
            attempt_kind=final_attempt.attempt_kind,
            parse_error=parse_error,
            validation_issues=validation_issues,
            proposal_result=proposal_result,
        )
    text = render_proposal_validation(payload)
    if notice is not None:
        text = f"{notice}\n{text}"
    return CommandResult(context=context, session=next_session, text=text, json_payload=payload)


def proposal_repair_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    if len(tokens) > 3:
        raise ValueError("proposal repair must be 'proposal repair [run_id or proposal_id]'")
    if context.infrastructure_services is None:
        raise ValueError(
            "proposal repair requires configured InfrastructureServices. Add jeff.runtime.toml in the startup directory to enable the bounded /proposal surface."
        )
    runtime_store = _require_runtime_store(context)
    record, next_session, notice = _resolve_proposal_record(
        tokens=tokens,
        session=session,
        context=context,
        command_name="proposal repair",
    )
    if record.status == "success":
        raise ValueError(f"proposal repair is not applicable for successful proposal {record.proposal_id}")
    failed_attempt = record.final_attempt
    if failed_attempt.failure_stage not in {"parse", "validation"} or failed_attempt.raw_result is None:
        raise ValueError(
            f"proposal repair is not applicable for proposal {record.proposal_id}; terminal failure stage is {record.final_failure_stage or '-'}"
        )
    request = ProposalGenerationRequest(
        objective=record.objective,
        scope=record.scope,
        context_package=record.context_package,
        visible_constraints=record.visible_constraints,
        proposal_input_bundle=record.proposal_input_bundle,
    )
    repair_failure = ProposalPipelineFailure(
        request=request,
        failure_stage=failed_attempt.failure_stage,
        error=ValueError(failed_attempt.error_message or failed_attempt.parse_error or "proposal repair failure"),
        prompt_bundle=failed_attempt.prompt_bundle,
        raw_result=failed_attempt.raw_result,
        parsed_result=failed_attempt.parsed_result,
        validation_issues=failed_attempt.validation_issues,
        status=f"{failed_attempt.failure_stage}_failure",
    )
    repair_result = run_proposal_repair_attempt(
        request,
        failure=repair_failure,
        infrastructure_services=context.infrastructure_services,
    )
    created_at = proposal_record_created_at_now()
    repair_record = build_operator_record_from_pipeline_result(
        proposal_id=build_proposal_record_id(scope=record.scope, objective=record.objective, created_at=created_at),
        created_at=created_at,
        request=request,
        pipeline_result=repair_result,
        source_proposal_id=record.proposal_id,
    )
    stored_record = runtime_store.save_proposal_record(repair_record)
    payload = proposal_record_json(record=stored_record, view="proposal_repair")
    text = render_proposal_record(payload)
    if notice is not None:
        text = f"{notice}\n{text}"
    return CommandResult(context=context, session=next_session, text=text, json_payload=payload)


def _resolve_proposal_record(
    *,
    tokens: list[str],
    session: CliSession,
    context: InterfaceContext,
    command_name: str,
) -> tuple[ProposalOperatorRecord, CliSession, str | None]:
    records = _require_runtime_store(context).load_proposal_records()
    identifier = tokens[2] if len(tokens) == 3 else None
    if identifier is None:
        run, next_session, notice = resolve_historical_run(
            tokens=[command_name],
            session=session,
            context=context,
            command_name=command_name,
        )
        return _latest_record_for_run(records, str(run.run_id)), next_session, notice
    if identifier in records:
        return records[identifier], session, None
    run = resolve_run_from_tokens(
        tokens=[command_name, identifier],
        session=session,
        context=context,
        command_name=command_name,
    )
    require_project_for_run(context, run.project_id)
    return _latest_record_for_run(records, str(run.run_id)), session, None


def _latest_record_for_run(records: dict[str, ProposalOperatorRecord], run_id: str) -> ProposalOperatorRecord:
    matches = [record for record in records.values() if str(record.scope.run_id) == run_id]
    if not matches:
        raise ValueError(f"no persisted proposal records are available for run {run_id}")
    matches.sort(key=lambda record: (record.created_at, record.proposal_id))
    return matches[-1]


def _require_runtime_store(context: InterfaceContext):
    if context.runtime_store is None:
        raise ValueError("proposal commands require the persisted Jeff runtime store")
    return context.runtime_store


def _direct_proposal_context_purpose(objective: str) -> str:
    return f"proposal support direct support action preparation {objective}"
