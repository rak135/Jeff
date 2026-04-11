"""Cognitive layer contracts for context, research, proposal, selection, planning, and evaluation."""

from .context import ContextPackage, assemble_context_package
from .evaluation import EvaluationResult, deterministic_override_reasons, evaluate_outcome
from .planning import PlanArtifact, create_plan, should_plan
from .proposal import ProposalOption, ProposalSet
from .research import ResearchRequest, ResearchResult
from .selection import SelectionResult

__all__ = [
    "ContextPackage",
    "EvaluationResult",
    "PlanArtifact",
    "ProposalOption",
    "ProposalSet",
    "ResearchRequest",
    "ResearchResult",
    "SelectionResult",
    "assemble_context_package",
    "create_plan",
    "deterministic_override_reasons",
    "evaluate_outcome",
    "should_plan",
]
