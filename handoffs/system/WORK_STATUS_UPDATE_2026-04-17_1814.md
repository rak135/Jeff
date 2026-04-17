## 2026-04-17 18:14 â€” Selection Slice 4 deterministic parsing

- Scope: cognitive selection parsing layer
- Done:
  - added `jeff/cognitive/selection/parsing.py` with `ParsedSelectionComparison`, `SelectionComparisonParseError`, and `parse_selection_comparison_result(...)`
  - implemented strict parsing for the bounded Selection comparison output contract with required-field, duplicate-field, and malformed-line rejection
  - preserved raw shape parsing only, including `NONE` sentinel handling and `yes`/`no` planning recommendation parsing
  - added focused unit tests proving valid parse success and fail-closed malformed-shape behavior without semantic validation
- Validation: `python -m pytest -q tests/unit/cognitive/test_selection_parsing.py tests/unit/cognitive/test_selection_comparison_runtime.py tests/unit/cognitive/test_selection_rules.py` passed (`16 passed`)
- Current state: Selection now has a deterministic parser for raw comparison output, while semantic validation, canonical `SelectionResult` conversion, API composition, and downstream wiring remain out of scope
- Next step: add the separate Selection validation slice so parsed output can be judged lawfully without collapsing parsing into semantics
- Files:
  - jeff/cognitive/selection/parsing.py
  - tests/unit/cognitive/test_selection_parsing.py
