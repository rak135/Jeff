## 2026-04-15 10:10 — Research ContractRuntime adoption: Step 1 and formatter bridge route through InfrastructureServices.contract_runtime

- Scope: jeff/cognitive/research/synthesis.py + jeff/infrastructure/contract_runtime.py
- Done:
  - added `ContractRuntime.invoke_with_request(request, adapter_id)` — dispatches a pre-built ModelRequest through the registry; supports both TEXT and JSON mode
  - added optional `contract_runtime` param to `synthesize_research`, `_invoke_step1_bounded_text_and_transform`, and `_attempt_formatter_fallback`
  - `synthesize_research_with_runtime` now passes `infrastructure_services.contract_runtime` so both Step 1 and formatter bridge calls route through ContractRuntime
  - direct adapter path (`synthesize_research(adapter=...)`) unchanged — all existing tests pass with no modification
  - added 6 focused adoption tests covering `invoke_with_request`, runtime path, formatter fallback, and backward compat
- Validation: 378 unit+integration tests pass; 10 pre-existing failures confirmed unchanged from baseline
- Current state: runtime research path dispatches through ContractRuntime; direct adapter path intact; formatter JSON mode supported via invoke_with_request passthrough
- Next step: consider migrating ContractCallRequest to support reasoning_effort so Step 1 can use invoke() instead of invoke_with_request, or proceed to Proposal/Evaluation adoption
- Files:
  - jeff/infrastructure/contract_runtime.py (invoke_with_request added)
  - jeff/cognitive/research/synthesis.py (contract_runtime threaded through runtime path)
  - tests/unit/cognitive/test_research_contract_runtime_adoption.py (new, 6 tests)
