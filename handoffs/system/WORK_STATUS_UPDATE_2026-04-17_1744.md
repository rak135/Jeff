## 2026-04-17 17:44 â€” Selection Slice 1 prompt contract

- Scope: cognitive selection prompt files
- Done:
  - added file-backed Selection comparison prompt contract at `PROMPTS/selection/COMPARISON.md`
  - added Selection-local prompt loader and renderer in `jeff/cognitive/selection/prompt_files.py`
  - added focused unit tests for prompt loading, section markers, placeholder rendering, and fail-closed unresolved placeholders
- Validation: `python -m pytest -q tests/unit/cognitive/test_selection_prompt_files.py` passed (`7 passed`)
- Current state: Selection now has a file-backed comparison prompt contract and local prompt helper, with no runtime, parsing, validation, or orchestrator behavior added
- Next step: keep later Selection prompt work separate from runtime calling, parsing, and validation slices
- Files:
  - PROMPTS/selection/COMPARISON.md
  - jeff/cognitive/selection/prompt_files.py
  - tests/unit/cognitive/test_selection_prompt_files.py
