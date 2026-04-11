import importlib

import pytest

from jeff.action import ExecutionResult, Outcome
from jeff.cognitive import EvaluationResult, evaluate_outcome
from jeff.interface.json_views import _module_for_stage


def test_evaluation_exports_now_resolve_from_cognitive_layer() -> None:
    assert EvaluationResult.__module__ == "jeff.cognitive.evaluation"
    assert evaluate_outcome.__module__ == "jeff.cognitive.evaluation"


def test_action_layer_retains_execution_and_outcome_only() -> None:
    action_module = importlib.import_module("jeff.action")

    assert action_module.ExecutionResult is ExecutionResult
    assert action_module.Outcome is Outcome
    assert not hasattr(action_module, "EvaluationResult")
    assert not hasattr(action_module, "evaluate_outcome")

    with pytest.raises(ImportError):
        exec("from jeff.action import EvaluationResult", {})


def test_operator_projection_keeps_evaluation_owned_by_cognitive() -> None:
    assert _module_for_stage("execution") == "action"
    assert _module_for_stage("outcome") == "action"
    assert _module_for_stage("evaluation") == "cognitive"
