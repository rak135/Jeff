## 2026-04-17 18:49 - Selection Slice 10 effective proposal materialization

- Scope: cognitive effective proposal materialization after Selection resolution
- Done:
  - added `jeff/cognitive/selection_effective_proposal.py` with bounded request, materialization, issue, error, and materializer surfaces
  - materialized a concrete `ProposalResultOption` deterministically from `ProposalResult` plus `ResolvedSelectionActionBasis`
  - preserved explicit no-proposal basis when resolved source is `none`
  - added focused unit tests for selection-source materialization, operator-override materialization, no-proposal basis, and fail-closed linkage mismatches
- Validation: `python -m pytest -q tests/unit/cognitive/test_selection_effective_proposal.py tests/unit/cognitive/test_selection_action_resolution.py tests/unit/cognitive/test_selection_api.py` passed (`21 passed`)
- Current state: downstream code can now materialize the concrete effective proposal option, if any, without creating Action contracts or mutating proposal/resolution truth
- Next step: keep later action formation separate from this materialization slice
- Files:
  - jeff/cognitive/selection_effective_proposal.py
  - tests/unit/cognitive/test_selection_effective_proposal.py
