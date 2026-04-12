## 2026-04-12 14:11 â€” Added bounded research malformed-output repair pass

- Scope: research synthesis malformed-output recovery
- Done:
  - added one bounded repair attempt for research synthesis when the primary adapter call fails with `malformed_output`
  - kept the repair prompt formatting-only and limited it to malformed content, exact schema, and allowed citation keys
  - preserved Slice A citation-key remap and fail-closed provenance validation after successful repair
  - added unit and integration coverage for successful repair, failed repair, one-attempt behavior, and non-malformed no-repair paths
  - refined malformed adapter errors to carry bounded raw output needed for repair input
- Validation: targeted repair-path pytest files passed; full `pytest -q` passed with 322 passed
- Current state: research synthesis can recover from one formatting-only malformed-output failure without changing successful artifact semantics
- Next step: later slices can build on this without adding retry loops or changing research semantics
- Files:
  - jeff/cognitive/research/synthesis.py
  - jeff/infrastructure/model_adapters/errors.py
  - jeff/infrastructure/model_adapters/providers/ollama.py
  - tests/unit/cognitive/test_research_synthesis_repair_pass.py
  - tests/integration/test_research_synthesis_repair_flow.py
