"""Public Selection surface."""

from .contracts import SelectionDisposition, SelectionRequest, SelectionResult
from .decision import run_selection
from .proposal_output_to_selection_bridge import (
    SelectionBridgeError,
    SelectionBridgeIssue,
    SelectionBridgeRequest,
    SelectionBridgeResult,
    build_and_run_selection,
)

__all__ = [
    "SelectionBridgeError",
    "SelectionBridgeIssue",
    "SelectionBridgeRequest",
    "SelectionBridgeResult",
    "SelectionDisposition",
    "SelectionRequest",
    "SelectionResult",
    "build_and_run_selection",
    "run_selection",
]
