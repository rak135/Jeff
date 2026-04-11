## 2026-04-11 10:45 - Evaluation layer alignment cleanup

- Scope: Cognitive-layer relocation of evaluation plus import, ownership, and note cleanup
- Done:
  - moved the active evaluation implementation to `jeff/cognitive/evaluation.py`
  - removed evaluation exports from `jeff.action` so Action now exposes execution and outcome only
  - updated orchestrator, bootstrap, and test imports to resolve evaluation from Cognitive
  - removed the README caveat about evaluation still living under `jeff/action/evaluation.py` and added alignment tests
- Validation: `python -m pytest -q tests/test_evaluation_rules.py tests/test_action_stage_boundaries.py tests/test_orchestrator_handoff_validation.py tests/test_orchestrator_failure_routing.py tests/test_acceptance_cli_orchestrator_alignment.py tests/test_evaluation_layer_alignment.py` passed with 23 tests; full `python -m pytest -q` passed with 132 tests
- Current state: evaluation now lives under Cognitive with unchanged semantics and no remaining active README mismatch note
- Next step: continue only with bounded follow-up work that preserves the current v1 architecture and deferral boundaries
- Files:
  - jeff/cognitive/evaluation.py
  - jeff/cognitive/__init__.py
  - jeff/action/__init__.py
  - jeff/action/types.py
  - jeff/orchestrator/runner.py
  - jeff/orchestrator/routing.py
  - jeff/orchestrator/validation.py
  - tests/test_evaluation_layer_alignment.py
