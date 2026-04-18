## 2026-04-18 21:44 - Added research output sufficiency bridge

- Scope: post-selection research boundary and orchestrator research-followup handling
- Done:
  - added `research_output_sufficiency_bridge` with typed request/result/error contracts over `ResearchArtifact`
  - wired orchestrator research-followup to evaluate research sufficiency and stop truthfully at the research boundary
  - added unit coverage for sufficient, insufficient, contradictory, and malformed research outputs
  - updated integration and acceptance routing coverage for decision-support-ready vs explicit unresolved gaps
  - updated the relevant post-selection, research, and orchestrator handoff docs
- Validation: targeted unit, integration, acceptance, research, and orchestrator pytest commands passed
- Current state: research-followup now yields an explicit non-authorizing sufficiency judgment and preserves unresolved gaps when research is still insufficient
- Next step: add any future downstream bridge only as a separate explicit slice
- Files:
  - jeff/cognitive/post_selection/research_output_sufficiency_bridge.py
  - jeff/orchestrator/runner.py
  - tests/unit/cognitive/post_selection/test_research_output_sufficiency_bridge.py
  - tests/integration/test_orchestrator_post_selection_next_stage_routing.py
  - tests/acceptance/test_acceptance_orchestrator_post_selection_next_stage.py
