## 2026-04-18 20:56 â€” Research follow-up enters real research stage

- Scope: orchestrator research-followup continuation after post-selection routing
- Done:
  - added a bounded `conditional_research_followup` flow shape so post-selection research routes can enter the existing research stage
  - updated runner and handoff validation so `selection -> research` is lawful only for the bounded research follow-up path and direct-action branches can still bypass research
  - added truthful hold behavior after a produced `ResearchArtifact` because no repo-local downstream bridge exists after research yet
  - added focused integration, acceptance, and orchestrator unit coverage for research entry, direct-action bypass, unchanged planning/non-research paths, and fail-closed malformed research output
- Validation: targeted pytest runs passed, including the new integration/acceptance files and nearby orchestrator/research/post-selection suites
- Current state: research-followup-routed selections now produce a real research-stage result and stop truthfully at the research boundary unless a later lawful bridge is added
- Next step: add a separate bounded slice only if Jeff gains an explicit repo-owned bridge from post-selection research output into later downstream stages
- Files:
  - jeff/orchestrator/flows.py
  - jeff/orchestrator/runner.py
  - jeff/orchestrator/validation.py
  - tests/integration/test_orchestrator_post_selection_next_stage_routing.py
  - tests/acceptance/test_acceptance_orchestrator_post_selection_next_stage.py
  - jeff/cognitive/research/HANDOFF.md
