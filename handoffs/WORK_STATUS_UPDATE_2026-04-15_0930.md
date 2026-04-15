## 2026-04-15 09:30 — Infrastructure Slice 7: contract_runtime added

- Scope: jeff/infrastructure contract runtime surface
- Done:
  - added `contract_runtime.py` with `ContractCallRequest` (validated descriptor) and `ContractRuntime` (thin wrapper over InfrastructureServices)
  - `ContractRuntime.invoke` routes by purpose, maps strategy to response mode, auto-generates request_id when absent
  - `ContractRuntime.invoke_with_adapter` added for explicit adapter selection (repair/retry paths)
  - added `contract_runtime` property to `InfrastructureServices` for convenient access
  - exported `ContractCallRequest` and `ContractRuntime` from `jeff/infrastructure/__init__.py`
  - added 18 focused unit tests; 81/81 infrastructure tests pass
- Validation: full infrastructure unit test suite passed, no regressions
- Current state: Infrastructure now has a thin reusable strategy-aware/purpose-aware call entrypoint; existing research flow unchanged; no domain semantics in infrastructure
- Next step: Research or Proposal layer adopts ContractRuntime, or Slice 8 wires CapabilityProfileRegistry into routing
- Files:
  - jeff/infrastructure/contract_runtime.py (new)
  - jeff/infrastructure/runtime.py (contract_runtime property added)
  - jeff/infrastructure/__init__.py (2 exports added)
  - tests/unit/infrastructure/test_contract_runtime.py (new)
