"""Orchestration-local planning continuation helpers."""

from __future__ import annotations

from jeff.cognitive import PlanArtifact
from jeff.cognitive.post_selection import PlanActionBridgeRequest, PlannedActionBridgeResult, bridge_plan_to_action
from jeff.core.schemas import Scope


def bridge_planned_action(
    *,
    flow_id: str,
    plan_output: object,
    scope: Scope,
    bridge_plan_to_action_fn=bridge_plan_to_action,
) -> PlannedActionBridgeResult:
    if not isinstance(plan_output, PlanArtifact):
        raise TypeError("plan action bridge requires PlanArtifact output from the planning stage")

    return bridge_plan_to_action_fn(
        PlanActionBridgeRequest(
            request_id=f"{flow_id}:plan-action-bridge",
            plan_artifact=plan_output,
            scope=scope,
        )
    )
