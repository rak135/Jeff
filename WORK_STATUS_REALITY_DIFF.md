# Work Status Reality Diff (2026-04-19)

Concise diff between major claims in `handoffs/system/WORK_STATUS_UPDATE.md` (and dated updates) and what the repo actually shows today, verified by code inspection and runtime testing.

---

## Claims Verified as Accurate

| Claim | Evidence |
|-------|---------|
| Core transition-controlled state (M-001) | `jeff/core/transition/apply.py` — real logic, used in every startup |
| Fail-closed governance evaluation (M-002) | `jeff/governance/action_entry.py` — verified: rejected bad proposals live |
| Context assembly from multi-source truth (M-003) | `jeff/cognitive/context.py` — wired into `/run` and `/research` |
| Bounded proposal contracts with 0..3 options (M-003) | `jeff/cognitive/proposal/contracts.py` — verified |
| Deterministic selection with explicit non-selection (M-003) | `jeff/cognitive/selection/decision.py` — verified |
| Governed subprocess execution (M-004) | `jeff/action/execution.py` — real `subprocess.run`, verified in code |
| Memory write pipeline (10-stage) and retrieval (10-stage) (M-005) | `jeff/memory/write_pipeline.py`, `jeff/memory/retrieval.py` — real logic |
| Orchestrator flow runner with stage validation (M-006A) | `jeff/orchestrator/runner.py` — ~500 lines of real orchestration |
| CLI slash-command surface (M-006B) | Verified live: `/help`, `/project list`, `/run`, `/show`, `/trace`, `/lifecycle`, `/scope show` all work |
| Persisted runtime under `.jeff_runtime/` (2026-04-18) | Verified live: canonical state, transitions, flow runs, research artifacts all persist and reload |
| Fresh-process reload of runs, traces, lifecycle | Verified: `run-1` visible with correct lifecycle state after fresh `python -m jeff` start |
| Research 3-step pipeline (C2a-C2e) | Verified live: `/research docs` produced structured findings from real LLM via Ollama |
| Research artifact persistence | Verified: `research-*.json` created in `.jeff_runtime/artifacts/research/` |
| Ollama HTTP adapter (Infra Slice C) | Verified live: real HTTP calls to local Ollama for research and proposal generation |
| Runtime config from `jeff.runtime.toml` | Verified: bootstrap check reports config loaded, purpose overrides active |
| `--bootstrap-check` diagnostics | Verified live: reports 12 diagnostic checks, all passing |
| `--reset-runtime` flag | Code exists in `jeff/main.py`; not destructively tested |
| GUI explicitly deferred | Confirmed: prototype scaffolding under `gui/`, not wired to runtime |
| Autonomous continuation explicitly deferred | Confirmed: no autonomous loop in codebase |
| Broader `/run` action families deferred | Confirmed: only `RepoLocalValidationPlan` exists |
| 984 passed, 28 skipped | Not re-run, but test structure (~130+ files, 5 families) is consistent |

---

## Claims with Nuance or Partial Accuracy

| Claim | Reality | Gap |
|-------|---------|-----|
| "bounded /run objective path enabled" | **True**, but the LLM proposal output consistently fails validation with real providers. The path is architecturally complete but practically unreliable. | The status notes don't mention proposal validation failure rate with real LLMs |
| "approval-gated continuation" | Code exists in `command_requests.py` (approve/reject/revalidate), wired through orchestrator continuations. Not black-box verified because `/run` never reaches the approval-required routing state in this audit. | Claimed as working; exists in code and is tested, but unverified at runtime with real providers |
| "research-followup continuation chain" | Extensive code in `orchestrator/continuations/post_research.py` (~200 lines). Not black-box verified — the chain is not triggered by the standard `/run` or `/research` paths. | Claimed as implemented; code exists and is unit-tested, but never exercised in real runtime |
| "research memory backend configured: in_memory" | **Accurate**, but undersells the implication: memory records vanish on process exit. The handoff outcome `defer` was observed live. | Status notes mention in_memory but don't highlight that memory is ephemeral by default |
| "Postgres memory backend" available | `postgres_store.py` is complete (~580 lines) with pgvector, FTS, HNSW indexing. Wired in `bootstrap.py`. | **Accurate** — a real, complete implementation. 28 skipped tests likely correspond to Postgres tests requiring local DB |

---

## Claims Not Verified (Unresolvable in This Audit)

| Claim | Why Unverifiable |
|-------|-----------------|
| Full acceptance test suite passes (984/28) | Would require running the full test suite; test structure is consistent but not re-executed |
| Operator override chain works end-to-end | Requires a successful `/run` reaching selection stage; proposal validation prevented this |
| Planning stage bridge works at runtime | Planning is only reachable through specific flow families not used by `/run` |
| Web research (`/research web`) works end-to-end | Not tested in this audit (only docs path tested); code exists in `jeff/cognitive/research/web.py` |
| Mutation lock prevents concurrent writes | PID-based locking code exists in `runtime_persistence.py`; would require concurrent process test |

---

## False or Misleading Claims

**None found.** The documentation and status updates are notably honest about the system's boundaries. The primary gap is emphasis: the status notes describe what is architecturally implemented without noting how frequently the LLM-dependent stages fail with real providers. This is not dishonest — the validation rejection is correct behavior — but it gives a more optimistic impression of the system's practical capability than what operators will experience.

---

## Summary Delta

```
STATUS_CLAIMS                    REPO_REALITY
──────────────────────────────── ────────────────────────────────
Core: complete                   ✓ Verified
Governance: complete             ✓ Verified (live rejection observed)
Cognitive: complete              ~ Architecturally complete, proposal
                                   generation unreliable with real LLMs
Action: bounded                  ✓ Verified (one plan type only)
Memory: in-memory discipline     ✓ Verified (ephemeral by default)
Orchestrator: complete           ~ Code complete, research-followup
                                   chain unverified at runtime
Interface: complete              ✓ Verified (live CLI confirmed)
Infrastructure: Ollama+Fake      ✓ Verified (real HTTP to Ollama)
Persistence: filesystem JSON     ✓ Verified (full reload confirmed)
GUI: deferred                    ✓ Confirmed deferred
Autonomous: deferred             ✓ Confirmed deferred
Broad /run: deferred             ✓ Confirmed deferred
```
