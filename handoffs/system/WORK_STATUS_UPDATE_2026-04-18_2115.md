## 2026-04-18 21:15 â€” Planning can fail-closed bridge into action

- Scope: bounded plan-to-action bridge after planning continuation
- Done:
  - added `plan_action_bridge` for deterministic fail-closed Action formation from one explicit bounded plan step
  - wired orchestrator planning continuation to use the bridge before governance and to stop truthfully at planning when no Action is formed
  - added focused unit, integration, and acceptance coverage for bridgeable and non-bridgeable planning outputs
  - updated post-selection and orchestrator handoffs to reflect optional planning-to-action bridging without permission collapse
- Validation: targeted pytest rings for new bridge tests and nearby planning/orchestrator/post-selection regressions passed
- Current state: planning can now reach governance only when the produced plan artifact exposes one explicit bounded executable step; otherwise Jeff still holds truthfully at planning
- Next step: add a later bounded slice only if Jeff needs richer plan artifact structure or explicit multi-step chooser semantics
- Files:
  - jeff/cognitive/post_selection/plan_action_bridge.py
  - jeff/orchestrator/runner.py
  - tests/unit/cognitive/post_selection/test_plan_action_bridge.py
  - tests/integration/test_orchestrator_post_selection_next_stage_routing.py
  - tests/acceptance/test_acceptance_orchestrator_post_selection_next_stage.py
  - jeff/cognitive/post_selection/HANDOFF.md
