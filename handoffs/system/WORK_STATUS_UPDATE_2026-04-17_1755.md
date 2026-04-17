## 2026-04-17 17:55 â€” Selection Slice 2 comparison bundle surface

- Scope: cognitive selection comparison entry
- Done:
  - added `jeff/cognitive/selection/comparison.py` with `SelectionComparisonRequest`, `SelectionComparisonPromptBundle`, and `build_selection_comparison_prompt_bundle(...)`
  - rendered Selection-local comparison input from `SelectionRequest`, including considered proposal ids, scarcity reason, scope, and stable option blocks
  - narrowed `PROMPTS/selection/COMPARISON.md` placeholders to the real Selection-local inputs this slice can supply
  - added focused unit tests for request construction, prompt-bundle rendering, explicit empty sentinels, and fail-closed unresolved placeholders
- Validation: `python -m pytest -q tests/unit/cognitive/test_selection_comparison.py tests/unit/cognitive/test_selection_prompt_files.py tests/unit/cognitive/test_selection_rules.py` passed (`16 passed`)
- Current state: Selection now has a bounded comparison request surface and prompt-bundle builder on top of the file-backed prompt contract, with no runtime, parsing, validation, API composition, or orchestrator behavior added
- Next step: keep later Selection slices separate by adding runtime handoff, parsing, and validation only in their own bounded modules
- Files:
  - jeff/cognitive/selection/comparison.py
  - PROMPTS/selection/COMPARISON.md
  - tests/unit/cognitive/test_selection_comparison.py
  - tests/unit/cognitive/test_selection_prompt_files.py
