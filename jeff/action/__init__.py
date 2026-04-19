"""Action-layer contracts for execution and outcome."""

from .execution import ExecutionResult, GovernedExecutionRequest, execute_governed_action
from .outcome import Outcome, normalize_outcome

__all__ = [
    "ExecutionResult",
    "GovernedExecutionRequest",
    "execute_governed_action",
    "Outcome",
    "normalize_outcome",
]
