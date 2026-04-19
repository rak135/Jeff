# Priority 5 Execution Checklist

## Title

Durable memory runtime wiring with minimal operator-visible value.

## Goal

Wire runtime memory against `MemoryStoreProtocol`, allow durable backend selection from runtime config, preserve truth-first retrieval, and expose minimal operator-visible memory value without creating a broad memory CLI.

## Dependency status

- Depends on: `priority_1.md` complete.
- Can proceed after: `priority_2.md` or `priority_4.md`, but does not require them to finish first.

## Ticket slices

### P5-T1. Protocol-based runtime memory wiring

- Outcome: CLI and runtime code depend on `MemoryStoreProtocol`, not `InMemoryMemoryStore` specifically.
- Done when:
- Memory injection points accept the protocol cleanly.
- In-memory and PostgreSQL stores can both satisfy the runtime path.

### P5-T2. Runtime-config backend selection

- Outcome: startup can select the durable memory backend from runtime config with truthful fallback behavior.
- Done when:
- Bootstrap check can report configured memory status clearly.
- Misconfiguration fails truthfully.

### P5-T3. Minimal operator-visible continuity value

- Outcome: research handoff and live context can expose minimal, truthful evidence of memory use without adding a large command family.
- Done when:
- `/research ... --handoff-memory` works against the configured backend.
- Read surfaces can state whether memory is configured and what happened.

## File-by-file implementation checklist

### jeff/bootstrap.py

- Replace the hard dependency on `InMemoryMemoryStore` in startup wiring.
- Add a bounded memory backend factory path.
- Keep default behavior truthful if no durable backend is configured.

### jeff/interface/command_models.py

- Replace concrete in-memory typing with `MemoryStoreProtocol` or equivalent abstract typing.

### jeff/interface/command_common.py

- Replace `require_memory_store` assumptions that force the in-memory class.
- Keep operator-visible error messages accurate under multiple backend possibilities.

### jeff/interface/command_research.py

- Keep `--handoff-memory` bounded.
- Ensure research handoff works with the selected memory backend.
- Surface write, reject, or defer truthfully in compact and JSON output.

### jeff/cognitive/context.py

- Confirm retrieval stays truth-first and project-scoped under the runtime-selected backend.
- Preserve current support ordering discipline.

### jeff/cognitive/research/memory_handoff.py

- Replace concrete store typing with `MemoryStoreProtocol`.
- Keep Memory-owned write discipline intact.

### jeff/infrastructure/config.py

- Extend runtime config to select the memory backend and any bounded connection settings needed.
- Keep the config minimal and explicit.

### New or small bootstrap helper module as needed

- Add the backend construction logic here if `bootstrap.py` would otherwise become overloaded.
- Keep backend selection and config parsing separate from memory semantics.

## Test cases to add or update

### tests/unit/cognitive/test_research_memory_handoff.py

- Update tests so handoff works through the protocol rather than the concrete in-memory class.
- Add coverage for backend-agnostic write, reject, and defer outcomes.

### tests/integration/test_research_memory_handoff_flow.py

- Add coverage for runtime-selected backend wiring.
- Ensure handoff and retrieval remain project-scoped.

### New bootstrap or config tests

- Add tests for memory backend selection, fallback, and misconfiguration.
- Add bootstrap-check coverage showing whether memory is configured and durable.

### Optional PostgreSQL integration path

- Reuse or extend the existing PostgreSQL memory integration path where DSN is available.
- Keep it optional but truthful.

## Operator validation checklist

- Start Jeff with no durable memory backend configured and confirm truthful fallback messaging.
- Start Jeff with the durable backend configured and confirm bootstrap output reflects that.
- Run `/research ... --handoff-memory` and confirm write, reject, or defer is surfaced clearly.
- Confirm live context retrieval still stays truth-first and project-scoped.

## Suggested validation commands

```text
python -m pytest -q tests/unit/cognitive/test_research_memory_handoff.py tests/integration/test_research_memory_handoff_flow.py tests/unit/memory/test_memory_v1_spec.py
python -m pytest -q
```

## Non-goals

- No broad `/memory` CLI surface.
- No memory-as-truth behavior.
- No global or cross-project memory widening.
- No memory UI or dashboard.

## Slice completion gate

- This priority is not done if runtime code still depends on `InMemoryMemoryStore` specifically.
- This priority is not done if durable backend wiring exists but the operator cannot tell whether memory is configured or what happened.
- This priority is not done if retrieval ordering or project isolation regresses.
