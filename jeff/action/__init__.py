"""Action-layer contracts for execution and outcome."""

from .execution import ExecutionResult, GovernedExecutionRequest
from .outcome import Outcome, normalize_outcome

__all__ = [
    "ExecutionResult",
    "GovernedExecutionRequest",
    "Outcome",
    "normalize_outcome",
]
