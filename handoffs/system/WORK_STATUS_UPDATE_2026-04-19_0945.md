## 2026-04-19 09:45 — Added proposal-output-to-selection bridge

- Scope: selection and orchestrator research-followup boundary
- Done:
  - added `proposal_output_to_selection_bridge` with typed request, result, issue, and error surfaces
  - wired research-followup orchestration to run selection after lawful preserved proposal output and hold at `selection_output_ready`
  - preserved truthful fail-closed hold at `proposal_output_ready` when selection bridge inputs are missing
  - added focused unit, integration, and acceptance coverage for success, insufficiency, bypass, and missing-input cases
  - updated selection, proposal, post-selection, and orchestrator handoff docs for the new non-authorizing boundary
- Validation: focused proposal/selection/post-selection/orchestrator unit tests plus targeted integration and acceptance suites passed
- Current state: sufficient research-followup can now preserve explicit selection output and still stops before action, governance, or execution
- Next step: any downstream continuation after selection output remains a separate explicit slice
- Files:
  - jeff/cognitive/selection/proposal_output_to_selection_bridge.py
  - jeff/orchestrator/runner.py
  - jeff/orchestrator/routing.py
  - tests/unit/cognitive/test_proposal_output_to_selection_bridge.py
  - tests/integration/test_orchestrator_post_selection_next_stage_routing.py
  - tests/acceptance/test_acceptance_orchestrator_post_selection_next_stage.py