## 2026-04-12 14:20 â€” Added separate research repair adapter override

- Scope: infrastructure runtime/config wiring for research repair adapter selection
- Done:
  - added optional `purpose_overrides.research_repair` parsing and typed config support
  - extended runtime adapter lookup so `research_repair` can resolve separately and still fall back cleanly
  - wired research malformed-output repair to use a separate repair adapter when configured and the primary adapter otherwise
  - added unit and integration coverage for repair override resolution, fallback behavior, and unchanged artifact semantics
  - updated the example `jeff.runtime.toml` and infrastructure handoff to show the new optional override
- Validation: targeted runtime/repair pytest files passed; full `pytest -q` passed with 328 passed
- Current state: research synthesis repair can use a separately configured formatter/repair adapter without changing default behavior
- Next step: later slices can build on this narrow split without adding broader capability routing
- Files:
  - jeff/infrastructure/config.py
  - jeff/infrastructure/runtime.py
  - jeff/cognitive/research/synthesis.py
  - tests/unit/infrastructure/test_runtime_purpose_overrides.py
  - tests/integration/test_research_synthesis_repair_flow.py
