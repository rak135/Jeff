"""Thin request-entry command handlers."""

from __future__ import annotations

from .command_common import require_flow_run, resolve_run_from_tokens
from .command_models import CommandResult, InterfaceContext
from .json_views import request_receipt_json
from .render import render_request_receipt
from .session import CliSession


def request_command(*, tokens: list[str], session: CliSession, context: InterfaceContext) -> CommandResult:
    request_type = tokens[0]
    target_run = resolve_run_from_tokens(tokens=tokens, session=session, context=context, command_name=tokens[0])
    flow_run = require_flow_run(context, str(target_run.run_id))
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