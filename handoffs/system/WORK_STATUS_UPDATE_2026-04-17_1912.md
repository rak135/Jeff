## 2026-04-17 19:12 - Selection CLI review surface

- Scope: interface read-only Selection review CLI surface
- Done:
  - added `/selection show [run_id]` as a read-only Selection review command
  - added structured Selection review JSON/read payloads that keep original selection, override, resolved choice, action formation, and governance handoff separate
  - added truthful human-readable rendering for Selection review with explicit missing-data states
  - added focused interface tests for override-aware review, structured JSON truthfulness, missing-data honesty, and no write behavior
- Validation: `python -m pytest -q tests/unit/interface/test_cli_selection_review.py tests/unit/interface/test_cli_truthfulness.py tests/unit/interface/test_cli_json_views.py` passed (`11 passed`)
- Current state: operators can now inspect the Selection review chain read-only without flattening history, authority, or execution state
- Next step: keep any future override write surface separate from this read-only review slice
- Files:
  - jeff/interface/commands.py
  - jeff/interface/json_views.py
  - jeff/interface/render.py
  - tests/unit/interface/test_cli_selection_review.py
