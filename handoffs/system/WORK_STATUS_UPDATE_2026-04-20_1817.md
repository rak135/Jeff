## 2026-04-20 18:17 — Added bounded proposal operator CLI surface

- Scope: manual proposal operator commands, durable proposal persistence, and live CLI verification
- Done:
  - added `/proposal`, `/proposal show`, `/proposal raw`, `/proposal validate`, and `/proposal repair`
  - added durable proposal operator records and persisted proposal artifact storage under `.jeff_runtime`
  - reused the existing proposal generation, parsing, validation, and single repair-pass pipeline for the operator surface
  - added JSON and text render surfaces plus targeted integration, unit, and smoke coverage
  - verified live direct `/proposal`, persisted restart inspection, and JSON output against the configured Ollama runtime
- Validation: targeted proposal/operator suites passed with 73 total tests; live `/proposal` worked against `ollama_default` on `gemma4:31b-cloud`; no honest live failure existed to exercise `/proposal repair`
- Current state: the bounded proposal operator surface is implemented, restart-safe, and live-verified for direct generation and inspection
- Next step: add optional environment-gated live coverage if a stable real-provider failure case is needed for `/proposal repair`
- Files:
  - jeff/cognitive/proposal/operator_records.py
  - jeff/cognitive/proposal/api.py
  - jeff/runtime_persistence.py
  - jeff/interface/commands/proposal.py
  - tests/integration/test_cli_proposal_operator_surface.py