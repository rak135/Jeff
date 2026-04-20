# Memory Runtime Persistence Report

## 1. Executive summary

This slice made committed memory real across normal one-shot local Jeff restarts.

Before the change, the live local startup path used an in-process `InMemoryMemoryStore`, so committed memory written during one `python -m jeff` process was gone when a fresh process started. After the change, normal local runtime now defaults to a persisted `LocalFileMemoryStore` under `.jeff_runtime/memory`, and committed memory survives restart as support-only state.

The live proof required by the slice is now satisfied:

- startup uses `LocalFileMemoryStore`
- a real `/run` wrote `memory-1`
- a fresh process reloaded that memory
- direct `/proposal` on the matching run showed non-empty `memory_support`
- `truth_snapshot` remained limited to `project`, `work_unit`, and `run`

## 2. Root cause before the fix

The product behavior gap was not in proposal bundling or retrieval semantics. The gap was startup backend selection.

What existed before:

- `InMemoryMemoryStore`
- `PostgresMemoryStore`

What local one-shot startup actually used before this slice:

- `InMemoryMemoryStore`

Why committed memory did not survive restart:

- memory writes completed inside one process
- the next `python -m jeff` process created a new empty in-memory store
- retrieval and direct `/proposal` then had nothing durable to read

## 3. Bounded product change

Implemented a new persisted local backend:

- `LocalFileMemoryStore`

Behavior:

- persists committed records
- persists embeddings
- persists links
- persists write and retrieval audit events
- persists maintenance jobs
- persists the memory id counter
- supports restart-safe retrieval for normal local usage
- keeps memory support-only and out of truth

Local persistence location:

- `.jeff_runtime/memory/memory_store.json`

Runtime selection change:

- local runtime default backend changed from `in_memory` to `local_file`
- explicit backends remain available: `in_memory`, `local_file`, `postgres`

## 4. Files changed

- `jeff/memory/local_file_store.py`
- `jeff/memory/__init__.py`
- `jeff/bootstrap.py`
- `jeff/infrastructure/config.py`
- `jeff.runtime.toml`
- `tests/unit/memory/test_local_file_store.py`
- `tests/unit/infrastructure/test_runtime_config.py`
- `tests/integration/test_bootstrap_runtime_config.py`
- `tests/integration/test_cli_proposal_operator_surface.py`

## 5. Implementation details

### New backend

Added `LocalFileMemoryStore` as a filesystem-backed implementation of the memory store protocol.

Key properties:

- workspace-local durability
- atomic snapshot/restore behavior inside `atomic()`
- lexical and semantic retrieval support
- counter persistence so ids continue as `memory-1`, `memory-2`, and so on across reloads

### Startup wiring

Updated bootstrap so memory store construction now receives the runtime root and uses:

- `LocalFileMemoryStore(runtime_root / "memory")` when backend is `local_file`

### Runtime config

Updated config defaults and validation so:

- `research.memory.backend` defaults to `local_file`
- `local_file` is a first-class accepted backend

### Live workspace config

Updated local runtime config to explicitly set:

```toml
[research.memory]
backend = "local_file"
```

## 6. Tests run

Focused suite:

```text
python -m pytest -q tests/unit/memory/test_local_file_store.py tests/unit/infrastructure/test_runtime_config.py tests/integration/test_bootstrap_runtime_config.py tests/integration/test_cli_proposal_operator_surface.py
```

Result:

```text
29 passed in 1.10s
```

Broader runtime regression suite:

```text
python -m pytest -q tests/integration/test_cli_research_runtime_config.py tests/integration/test_runtime_workspace_persistence.py
```

Result:

```text
26 passed in 1.47s
```

## 7. Live verification

All live Ollama-backed commands were run strictly one at a time.

### 7.1 Fresh-process backend inspection before the live `/run`

Observed fresh-process output:

```text
memory_store_type = LocalFileMemoryStore
memory_store_root = C:\DATA\PROJECTS\JEFF\.jeff_runtime\memory
memory_record_count = 0
```

This proved the live workspace startup was no longer using `InMemoryMemoryStore`.

### 7.2 Real live `/run`

Objective used:

```text
What bounded rollout should execute now for memory persistence verification 2026-04-20-1?
```

Observed result:

- `run_id = run-11`
- execution completed successfully
- `memory_handoff_attempted = true`
- `memory_handoff_note = automatic run memory handoff completed with outcome write`
- `memory_handoff_result.memory_id = memory-1`

The execution summary included repo-local smoke validation with:

```text
22 passed in 5.57s
```

### 7.3 Fresh-process retrieval after restart

Observed fresh-process output:

```text
memory_store_type = LocalFileMemoryStore
memory_record_count = 1
memory_1_exists = True
retrieved_memory_ids = ['memory-1']
```

This proved restart persistence and scope-matched retrievability.

### 7.4 Live direct `/proposal` after restart

Direct `/proposal` was then run against `run-11` after explicit run selection.

Observed result:

- `memory_support.memory_ids = ['memory-1']`
- `memory_support.summary_count = 1`
- `memory_support.memory_summaries[0].source_id = 'memory-1'`
- `truth_snapshot.item_count = 3`
- truth families were exactly `project`, `work_unit`, `run`

This is the required proof that direct `/proposal` now sees real committed memory support after restart.

### 7.5 Persisted proposal readback

`/proposal show run-11` preserved the same support separation:

- `memory_support.summary_count = 1`
- `memory_ids = ['memory-1']`
- `truth_snapshot` still only contained `project`, `work_unit`, `run`

## 8. Truth separation

Memory remains support-only.

Observed live behavior after the fix:

- committed memory is exposed through `memory_support`
- committed memory does not enter `truth_snapshot`
- canonical truth remains limited to the expected state-backed families

This slice did not add a new truth layer and did not weaken truth-first behavior.

## 9. Problems encountered during implementation

Issues hit during the slice:

- exporting the new store surfaced a circular import in `jeff.memory.__init__.py`
- one proposal integration helper still fell back to `InMemoryMemoryStore`
- one honest handoff test assumed a hard-coded run number

Fixes applied:

- reordered memory package imports
- changed the integration helper fallback to `LocalFileMemoryStore`
- updated the test to use explicit run selection and relaxed the fixed run-id assumption

## 10. Exact outcome

The bounded goal is complete.

Normal local Jeff startup now uses a persisted local memory backend by default, committed memory survives one-shot process restart, and direct `/proposal` shows real non-empty `memory_support` when scope matches that persisted memory.

## 11. Remaining gaps

Remaining limitations are narrower than before:

1. This slice covers normal local durability through `local_file`; it does not replace or remove the optional `postgres` backend.
2. Memory remains support-only by design; that is intentional, not a gap.
3. Retrieval quality is still bounded by the existing retrieval heuristics and current support inventory.

## 12. Next best slice

The next best bounded slice is not more memory persistence work. The persistence/runtime gap is closed.

The highest-value next slice is the weakest remaining orchestration layer identified in the post-memory audit: deterministic planning and checkpointed plan-step execution.