## 2026-04-19 09:15 â€” Added proposal generation bridge after proposal input

- Scope: proposal and orchestrator research-followup boundary
- Done:
  - added `jeff.cognitive.proposal.proposal_generation_bridge` with typed request/result/error surfaces and fail-closed validation
  - wired research-followup orchestration to build a lawful `ProposalGenerationRequest`, run proposal generation, preserve proposal output, and otherwise hold at a truthful `proposal_input_boundary`
  - added focused unit, integration, and acceptance coverage for success, missing runtime inputs, malformed proposal input, and non-authorizing proposal-output behavior
  - updated proposal, post-selection, research, and orchestrator handoffs for the new proposal-output boundary
- Validation: targeted proposal/post-selection/orchestrator unit tests plus the focused integration and acceptance suites passed
- Current state: sufficient research-followup can now preserve proposal output without auto-continuing into selection, action, governance, or execution
- Next step: add a later explicit downstream bridge only if repo-local selection continuation is separately authorized
- Files:
  - jeff/cognitive/proposal/proposal_generation_bridge.py
  - jeff/orchestrator/runner.py
  - jeff/orchestrator/routing.py
  - tests/integration/test_orchestrator_post_selection_next_stage_routing.py
  - tests/acceptance/test_acceptance_orchestrator_post_selection_next_stage.py
