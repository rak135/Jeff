"""Accepted orchestration flow families and explicit stage orders."""

from __future__ import annotations

from typing import Literal

FlowFamily = Literal[
    "bounded_research_direct_output",
    "bounded_research_to_decision_support",
    "bounded_proposal_selection_action",
    "conditional_planning_insertion",
    "blocked_or_escalation",
    "evaluation_driven_followup",
]

StageName = Literal[
    "context",
    "research",
    "proposal",
    "selection",
    "planning",
    "action",
    "governance",
    "execution",
    "outcome",
    "evaluation",
    "memory",
    "transition",
]

FLOW_STAGE_ORDERS: dict[FlowFamily, tuple[StageName, ...]] = {
    "bounded_research_direct_output": ("context", "research"),
    "bounded_research_to_decision_support": ("context", "research", "proposal", "selection"),
    "bounded_proposal_selection_action": (
        "context",
        "proposal",
        "selection",
        "action",
        "governance",
        "execution",
        "outcome",
        "evaluation",
        "memory",
        "transition",
    ),
    "conditional_planning_insertion": (
        "context",
        "proposal",
        "selection",
        "planning",
        "action",
        "governance",
        "execution",
        "outcome",
        "evaluation",
        "memory",
        "transition",
    ),
    "blocked_or_escalation": ("context", "proposal", "selection", "action", "governance"),
    "evaluation_driven_followup": ("evaluation",),
}


def stage_order_for_flow(flow_family: FlowFamily) -> tuple[StageName, ...]:
    return FLOW_STAGE_ORDERS[flow_family]
