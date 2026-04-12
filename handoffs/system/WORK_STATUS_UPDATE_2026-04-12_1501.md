## 2026-04-12 15:01 â€” Fixed post-validation research source linkage

- Scope: research downstream persistence, projection, and debug checkpoints
- Done:
  - added downstream debug checkpoints for artifact record build, store save/load, projection, and render
  - fixed document and web persist flows to reuse the same evidence pack for synthesis and persistence
  - wrapped malformed persisted-record linkage failures cleanly at load time
  - added unit and integration coverage for downstream source-linkage stability and debug streaming
- Validation: targeted downstream tests passed; full `pytest -q` passed
- Current state: valid post-remap research artifacts now keep consistent real source IDs through persistence and rendering, with bounded downstream debug visibility in `/mode debug`
- Next step: use the new downstream checkpoints to diagnose any remaining live research failures without widening research semantics
- Files:
  - jeff/cognitive/research/persistence.py
  - jeff/interface/commands.py
  - tests/unit/cognitive/test_research_post_validation_linkage.py
  - tests/integration/test_cli_research_post_validation_debug.py
