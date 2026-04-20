"""Selection review and operator override command handlers."""

from __future__ import annotations

from jeff.cognitive import SelectionResult
from jeff.cognitive.post_selection.override import (
    OperatorSelectionOverrideRequest,
    build_operator_selection_override,
)
from jeff.cognitive.post_selection.selection_review import recompute_selection_review_record
from jeff.cognitive.types import require_text

from ..json_views import selection_override_receipt_json, selection_review_json
from ..render import render_selection_override_receipt, render_selection_review
from ..session import CliSession
from .models import CommandResult, InterfaceContext
from .support.scope_resolution import require_project_for_run, resolve_historical_run
from .support.selection_review_runtime import (
    ensure_selection_review_for_run,
    materialize_selection_review_for_run,
    replace_selection_review,
)


def selection_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    if len(tokens) < 2:
        raise ValueError(
            "selection command must be 'selection show [run_id]' or "
            "'selection override <proposal_id> --why \"operator rationale\" [run_id]'"
        )

    if tokens[1] == "show":
        return selection_show_command(tokens=tokens, session=session, context=context)
    if tokens[1] == "override":
        return selection_override_command(tokens=tokens, session=session, context=context)

    raise ValueError(
        "selection command must be 'selection show [run_id]' or "
        "'selection override <proposal_id> --why \"operator rationale\" [run_id]'"
    )


def selection_show_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    if len(tokens) > 3:
        raise ValueError("selection show must be 'selection show [run_id]'")
    run, next_session, notice = resolve_historical_run(
        tokens=["selection", *tokens[2:]],
        session=session,
        context=context,
        command_name="selection show",
    )
    project = require_project_for_run(context, run.project_id)
    work_unit = project.work_units[run.work_unit_id]
    flow_run = context.flow_runs.get(str(run.run_id))
    next_context, selection_review = materialize_selection_review_for_run(
        context=context,
        run=run,
        flow_run=flow_run,
    )
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


def selection_override_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    proposal_id, operator_rationale, run_token = parse_selection_override_tokens(tokens)
    run_tokens = ["selection override"] if run_token is None else ["selection override", run_token]
    run, next_session, notice = resolve_historical_run(
        tokens=run_tokens,
        session=session,
        context=context,
        command_name="selection override",
    )
    run_id = str(run.run_id)
    flow_run = context.flow_runs.get(run_id)
    next_context, existing_review = ensure_selection_review_for_run(context=context, run=run, flow_run=flow_run)
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
    updated_review = recompute_selection_review_record(
        existing_review=existing_review,
        selection_result=selection_result,
        operator_override=operator_override,
    )
    next_context = replace_selection_review(context=next_context, run_id=run_id, selection_review=updated_review)
    payload = selection_override_receipt_json(
        run_id=run_id,
        selection_review=updated_review,
    )
    text = render_selection_override_receipt(payload)
    if notice is not None:
        text = f"{notice}\n{text}"
    return CommandResult(context=next_context, session=next_session, text=text, json_payload=payload)


def parse_selection_override_tokens(tokens: list[str]) -> tuple[str, str, str | None]:
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