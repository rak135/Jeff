## 2026-04-11 11:51 - CLI usability cleanup for operator flow

- Scope: CLI operator usability, command guidance, and shell readability without backend semantic changes
- Done:
  - added `/run list` for truthful run discovery inside current project/work scope
  - improved missing-scope and unknown-ID guidance for `/inspect`, `/project use`, `/work use`, and `/run use`
  - clarified `/help` and shell startup text so the CLI reads as a command-driven slash-command surface
  - added bounded prompt/error readability helpers with ANSI color support and plain-text fallback
  - updated README demo commands and added targeted CLI usability tests
- Validation: `python -m pytest -q tests/unit/interface tests/smoke/test_cli_entry_smoke.py` passed with 24 tests; `python -m pytest -q tests/acceptance/test_acceptance_cli_orchestrator_alignment.py tests/acceptance/test_acceptance_truthfulness.py` passed with 4 tests; `python -m pytest -q` passed with 139 tests
- Current state: the CLI is easier to navigate and read while preserving existing backend meaning and truth labels
- Next step: keep future CLI refinements bounded to operator usability unless canon explicitly expands the interface surface
- Files:
  - jeff/interface/commands.py
  - jeff/interface/json_views.py
  - jeff/interface/render.py
  - jeff/main.py
  - tests/unit/interface/test_cli_usability.py
  - README.md
