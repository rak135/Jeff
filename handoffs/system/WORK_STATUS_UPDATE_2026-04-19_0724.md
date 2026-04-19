## 2026-04-19 07:24 - Added research decision-support handoff bridge

- Scope: post-selection research-followup boundary and decision-support handoff preservation
- Done:
  - added `research_to_decision_support_bridge` with typed request, handoff, and fail-closed validation
  - wired orchestrator research-followup to preserve sufficiency results and build a decision-support handoff only on the sufficient branch
  - added focused unit coverage for the new bridge and updated orchestrator/post-selection routing coverage
  - updated integration and acceptance tests for explicit handoff-ready vs unresolved-gap outcomes
  - updated the relevant post-selection, research, and orchestrator handoff docs
- Validation: targeted unit, integration, acceptance, research, and orchestrator pytest commands passed
- Current state: sufficient research-followup output now yields an explicit non-authorizing decision-support handoff while insufficient research still stops with explicit unresolved items
- Next step: add any future research-to-proposal or research-to-selection consumer only as a separate explicit slice
- Files:
  - jeff/cognitive/post_selection/research_to_decision_support_bridge.py
  - jeff/orchestrator/runner.py
  - tests/unit/cognitive/post_selection/test_research_to_decision_support_bridge.py
  - tests/integration/test_orchestrator_post_selection_next_stage_routing.py
  - tests/acceptance/test_acceptance_orchestrator_post_selection_next_stage.py
