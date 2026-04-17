## 2026-04-17 18:56 - Selection Slice 11 action formation

- Scope: cognitive Action formation after effective proposal materialization
- Done:
  - added `jeff/cognitive/action_formation.py` with bounded request, result, issue, error, and action-formation surfaces
  - reused the existing repo `Action` contract and formed Action deterministically only for directly actionable `direct_action` proposals
  - returned explicit no-Action results for `none` source and non-directly-actionable proposal types like `planning_insertion`
  - added focused unit tests for direct Action formation, no-Action paths, fail-closed actionable-data gaps, and upstream object immutability
- Validation: `python -m pytest -q tests/unit/cognitive/test_action_formation.py tests/unit/cognitive/test_selection_effective_proposal.py tests/unit/cognitive/test_selection_action_resolution.py` passed (`20 passed`)
- Current state: downstream code can now form the existing bounded `Action` contract from a materialized effective proposal without starting governance or execution
- Next step: keep later governance or orchestration integration in separate slices
- Files:
  - jeff/cognitive/action_formation.py
  - tests/unit/cognitive/test_action_formation.py
