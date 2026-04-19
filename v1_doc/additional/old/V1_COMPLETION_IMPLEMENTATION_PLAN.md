# V1 Completion Implementation Plan

## 1. Executive judgment

Jeff is already a real CLI-first backbone, not a fake prototype. The strongest layers today are the truth-safe core, governance semantics, context and research support, orchestrator routing, and read-oriented operator surfaces. Current tests and recent green full-suite runs say the repo is structurally healthy. The repo is not suffering from architectural collapse. It is suffering from finish-line asymmetry: the inspection path is stronger than the doing path, the internal memory model is stronger than its runtime wiring, and the persisted runtime is stronger than the top-level docs but still weaker than v1 operator claims should allow.

Jeff is not yet a strong v1 operator tool for repeatable governed completion. The primary `/run` path is real but still fragile, request-entry governance is mostly receipt-only, persisted workspace behavior is not operator-safe enough, and action to execution to transition reality is too thin to justify broad completion claims. The single most important next strengthening step is to make the primary `/run` path repeatable and credible by hardening its runtime contract and then giving it one materially real, governed, runtime-backed execution slice.

## 2. Current-state classification

### Strong enough now

- Core truth model and transition discipline are strong enough now. `project + work_unit + run`, transition-only mutation, state persistence, and audit records should not be reworked beyond narrow additions needed for run-truth progression.
- Governance semantics are strong enough now. Approval, readiness, staleness, and fail-closed action-entry checks are already one of the cleanest layers in the repo.
- Orchestrator sequencing and routing are strong enough now. Stage ordering, fail-closed handoff validation, post-selection routing, and research follow-up reuse are already real and well covered.
- Truth-first context assembly is strong enough now. The current memory, compiled knowledge, and archive ordering discipline is meaningful and tested.
- Read-oriented operator surfaces are strong enough now. `/inspect`, `/show`, `/trace`, `/lifecycle`, `/selection show`, and JSON projections are already materially useful and should be preserved.
- Internal memory semantics are strong enough now. Candidate discipline, retrieval rules, write pipeline, and the PostgreSQL store are already stronger than the current operator/runtime footprint.

### Real but too thin

- `/run` is real but too thin. It launches a real bounded flow, but practical success still depends on brittle proposal output and placeholder-grade execution substance.
- Action, outcome, and evaluation are semantically real but operationally too thin. The execution side still does too little real work to carry v1 operator claims.
- Request-entry governance is real but too thin. `approve`, `reject`, `retry`, `revalidate`, and `recover` mostly stop at request receipts.
- Persisted runtime support is real but too thin. Snapshot persistence exists, but reset hygiene, live locking, and repeated-use ergonomics are not yet strong enough.
- Memory runtime behavior is real but too thin. The backend story exists, but default startup still wires an in-memory-only handoff path and exposes almost none of that value clearly.

### Operator-visible liabilities

- Top-level docs and some help surfaces still drift from current startup reality. `README.md` and parts of help still talk like startup is an explicit in-memory demo even though the repo now uses `.jeff_runtime` persistence.
- Session-local `use` commands look more durable than they are. This is intentional in tests, but still a liability unless made explicit everywhere the operator touches it.
- Auto-binding to the most recent run is lawful but operator-hostile once failed runs accumulate.
- One-shot `--json` and session `/json on` are both real, but their interaction is not operator-obvious enough.
- `/run` can create dead-looking runs when proposal generation fails, and current compact renderings understate that failure compared to JSON.
- Request-entry verbs overpromise relative to what they actually do.
- Persisted runtime has no strong operator reset or clean-room path.
- `runtime.lock.json` exists as metadata, not as an active concurrency guard.
- Complex PowerShell quoting remains high-friction on the most complex commands.

### Explicit deferrals to keep deferred

- GUI expansion should stay deferred. Current weakness is not lack of a front end.
- Broad API expansion should stay deferred. The CLI contract is not yet settled enough to deserve a larger public transport surface.
- Background autonomy and continuation should stay deferred. The current repo is not missing hidden autonomy; it is missing stronger bounded operator completion.
- Provider sprawl should stay deferred. The repo should not add more providers to hide weak runtime reliability.
- Workflow inflation should stay deferred. The orchestrator is already good enough without reintroducing first-class workflow truth.
- Broad memory UX should stay deferred. v1 needs runtime wiring and a minimal visible continuity loop, not a large memory command surface.
- Broad web-research ambition should stay deferred. Docs research is the more credible current operator path; web research should stay bounded and honestly framed.

## 3. Top-priority v1 gaps

1. `/run` is not yet credible as the primary operator path. It is implemented, but it still fails too easily on proposal generation and does not yet drive one materially useful governed execution path to a trustworthy finish.
2. The persisted runtime contract is not strong enough for repeated real use. Locking is not live, stale runs accumulate, reset hygiene is missing, and session-local scope is easy to misread as persisted state.
3. The weakest real link in the backbone is action to execution to transition reality. Governance is strong; execution substance and post-execution truth progression are not.
4. Governance request-entry is mostly surface area without workflow. Approval-required runs do not yet turn into a real operator continuation path.
5. Run truth progression is too narrow. The repo persists support records, but canonical run truth does not progress enough to keep the primary path honest across processes.
6. Memory is under-integrated at runtime. Durable memory exists in code and tests, but startup wiring and operator visibility still underuse it.
7. Operator contract drift is still too high. README, `/help`, bootstrap wording, JSON mode semantics, and run-binding behavior still require insider knowledge.

## 4. Real implementation plan

### Priority 1. Repeatable runtime contract for the primary path

- Why now: Jeff cannot honestly claim a primary operator flow while repeated use remains vulnerable to stale runtime state, misleading scope expectations, and concurrent-write collisions.
- Exact goal: make persisted runtime use repeatable and operator-safe by adding real single-writer mutation protection, one explicit clean-room/reset path, deterministic run-binding rules, and explicit session-local scope messaging.
- Main code areas likely touched: `jeff/runtime_persistence.py`, `jeff/bootstrap.py`, `jeff/main.py`, `jeff/interface/command_common.py`, `jeff/interface/command_scope.py`, `jeff/interface/render.py`, `README.md`.
- Main tests to add/update: `tests/integration/test_runtime_workspace_persistence.py`, `tests/unit/interface/test_cli_scope_and_modes.py`, `tests/unit/interface/test_cli_run_resolution.py`, smoke quickstart/help tests.
- Acceptance criteria:
- Mutating startup and mutating CLI operations either acquire a real lock or fail fast with a truthful operator-visible message.
- There is one explicit operator path to start from a clean runtime workspace or reset the bounded local runtime safely.
- Session-local scope behavior is preserved but clearly labeled in help, bootstrap diagnostics, and read surfaces.
- Historical auto-binding rules become deterministic and truthful enough that `/show` and `/inspect` do not silently drift into misleading latest-run behavior.
- One-shot JSON behavior and session JSON behavior are both explicit and non-surprising.
- Dependencies: none.
- What not to widen: no daemon, no multi-user runtime service, no broad workspace-management surface, no hidden background process.
- Estimated implementation risk: medium.

### Priority 2. Credible `/run` bounded governed execution slice

- Why now: `/run` is the largest remaining credibility gap between Jeff's current surface and Jeff's actual operator usefulness.
- Exact goal: make `/run` reliably drive one bounded, materially useful, runtime-backed action family end to end. The recommended v1 slice is a governed repo-local validation action family with a whitelist-backed runtime adapter, captured evidence, truthful failure states, and bounded evaluation.
- Main code areas likely touched: `jeff/interface/command_scope.py`, `jeff/cognitive/proposal/`, `jeff/cognitive/selection/`, `jeff/cognitive/post_selection/`, `jeff/action/execution.py`, `jeff/action/outcome.py`, `jeff/cognitive/evaluation.py`, `jeff/infrastructure/runtime.py`, `jeff/infrastructure/contract_runtime.py`, `jeff/infrastructure/output_strategies.py`, JSON/render surfaces for run output.
- Main tests to add/update: `tests/integration/test_cli_run_live_context_execution.py`, new integration coverage for malformed provider output, successful bounded validation execution, and truthful operator output under failure; one acceptance slice for `/run` from objective to completed governed execution.
- Acceptance criteria:
- With configured runtime services, `/run` can complete one bounded repo-local validation action family without placeholder-only execution behavior.
- Proposal/selection failures remain truthful and typed, and do not masquerade as launched work.
- Successful execution records actual runtime evidence such as exit status, bounded stdout/stderr summary, and evaluation input.
- Fresh-process inspection after `/run` shows a coherent bounded result rather than a dead-looking shell of a run.
- The operator can distinguish blocked, invalidated, failed, and completed runs without reading raw internals.
- Dependencies: Priority 1.
- What not to widen: no arbitrary shell-execution surface, no autonomous task planner, no broad write-capable action families, no general agent loop.
- Estimated implementation risk: high.

### Priority 3. Transition-backed run truth progression

- Why now: even a stronger execution slice will still feel fake if run truth remains mostly stuck at creation while real support records accumulate off to the side.
- Exact goal: extend canonical truth minimally so runs can progress through truthful lifecycle/result states via transitions only, without turning support artifacts into truth blobs.
- Main code areas likely touched: `jeff/core/containers/models.py`, `jeff/core/transition/apply.py`, any transition request/types surface needed for run progression, `jeff/interface/command_common.py`, `jeff/interface/command_inspect.py`, `jeff/interface/json_views.py`, `jeff/runtime_persistence.py`.
- Main tests to add/update: new unit tests for run-progression transitions, integration tests for persisted run truth after `/run`, acceptance alignment tests for `/show`, `/inspect`, `/lifecycle`, and fresh-start reload.
- Acceptance criteria:
- Run lifecycle truth changes only through new narrow transitions.
- `/run` updates canonical run truth to reflect states such as launched, blocked, failed, approval-required, or completed.
- Support records remain support records; they are referenced or summarized lawfully rather than copied wholesale into state.
- Fresh startup and one-shot inspection reflect the same run truth without interface-owned patching.
- Dependencies: Priorities 1 and 2.
- What not to widen: no first-class workflow truth, no broad new state graph, no replacement of support artifacts with canonical mirrors.
- Estimated implementation risk: medium.

### Priority 4. Real approval-required operator workflow

- Why now: governance semantics are already strong enough that the thin request-entry surface now stands out as a trust problem rather than a missing foundation.
- Exact goal: make `approve` and `revalidate` a real bounded v1 workflow for approval-required runs. `reject` may become a truthful terminal operator action. `retry` and `recover` should remain deferred unless the earlier slices expose a narrow, evidence-backed use case.
- Main code areas likely touched: `jeff/governance/approval.py`, `jeff/governance/action_entry.py`, `jeff/orchestrator/continuations/`, `jeff/orchestrator/routing.py`, `jeff/orchestrator/runner.py`, `jeff/interface/command_requests.py`, persisted support-record storage under `.jeff_runtime`, and read surfaces for request status.
- Main tests to add/update: unit tests for approval binding, staleness, and mismatch invalidation; integration tests for approve-then-revalidate continuation; acceptance test for an approval-required `/run` that becomes executable only after lawful operator approval.
- Acceptance criteria:
- `approve` creates a bounded approval record tied to the actual action identity, scope, and governing basis.
- `revalidate` consumes that record and either continues lawfully to execution or fails closed when the action or truth basis changed.
- `reject` truthfully ends the continuation path without implying mutation or execution.
- Request-entry commands stop reading like decorative receipts once this slice lands.
- Dependencies: Priorities 1 through 3.
- What not to widen: no queueing system, no asynchronous background continuation, no approval bureaucracy beyond per-run bounded records, no automatic retries.
- Estimated implementation risk: medium-high.

### Priority 5. Durable memory runtime wiring with minimal operator-visible value

- Why now: the repo already paid for a serious memory model and PostgreSQL backend, but v1 still defaults to a much thinner continuity story than the code actually supports.
- Exact goal: wire runtime memory against `MemoryStoreProtocol`, allow durable backend selection from runtime config, preserve truth-first retrieval, and expose minimal operator-visible evidence of memory write/retrieval outcomes without inventing a large memory CLI.
- Main code areas likely touched: `jeff/bootstrap.py`, `jeff/interface/command_models.py`, `jeff/interface/command_common.py`, `jeff/interface/command_research.py`, `jeff/cognitive/context.py`, `jeff/cognitive/research/memory_handoff.py`, `jeff/infrastructure/config.py`, memory backend bootstrap helpers.
- Main tests to add/update: `tests/unit/cognitive/test_research_memory_handoff.py`, `tests/integration/test_research_memory_handoff_flow.py`, memory backend selection tests, bootstrap-check tests, optional PostgreSQL integration path where DSN is available.
- Acceptance criteria:
- CLI/runtime code depends on the memory store protocol rather than `InMemoryMemoryStore` specifically.
- Runtime config can select a durable backend cleanly, with truthful fallback behavior.
- `/research ... --handoff-memory` works against the selected backend and reports write, reject, or defer truthfully.
- Live context retrieval continues to prioritize truth first and remains project-scoped.
- Existing read surfaces can tell the operator whether memory is configured and what happened, without adding a broad command family.
- Dependencies: Priority 1.
- What not to widen: no memory-as-truth, no global memory, no broad `/memory` command suite, no memory UI.
- Estimated implementation risk: medium.

### Priority 6. Operator contract and status alignment cleanup

- Why now: once the earlier behavior slices land, the repo must stop carrying stale wording and misleading status language.
- Exact goal: align README, `/help`, bootstrap diagnostics, and status files with the actual persisted-runtime startup path, primary `/run` contract, approval workflow, JSON behavior, memory configuration, and explicit v1 deferrals.
- Main code areas likely touched: `README.md`, `jeff/main.py`, `jeff/interface/render.py`, `handoffs/system/WORK_STATUS_UPDATE.md`, the next timestamped work-status file, and any stale module handoffs that contradict current behavior.
- Main tests to add/update: smoke help/quickstart tests, acceptance CLI-alignment tests, and any doc-adjacent anti-drift checks already present.
- Acceptance criteria:
- No top-level operator surface claims explicit in-memory startup as default when persisted startup is the real path.
- README and `/help` present `/run` honestly as the primary bounded path only after Priorities 1 through 4 make that true.
- Session-local scope, JSON mode behavior, auto-binding behavior, and memory/runtime config are described truthfully.
- Status files stop overstating unfinished surfaces and stop understating already-real ones.
- Dependencies: Priorities 1 through 5, or at minimum the relevant stabilized subset.
- What not to widen: no documentation rewrite project, no marketing polish pass, no new operator surfaces added for optics.
- Estimated implementation risk: low.

## 5. Recommended sequence

### Immediately

- Priority 1 first. Jeff needs a repeatable runtime contract before stronger operator claims are safe.
- Priority 2 second. Once the runtime contract is stable, Jeff should earn one credible `/run` slice with real bounded execution.

### Soon after

- Priority 3 next. A stronger execution slice should immediately feed truthful run progression through transitions.
- Priority 4 after that. Approval-required flows become worth making real only after `/run` and run truth are credible.
- Priority 5 in parallel with late Priority 4 work if capacity allows. It is mostly orthogonal once the runtime contract is cleaned up.

### Only after earlier slices stabilize

- Priority 6 last. Documentation and status alignment should codify stabilized behavior, not chase moving targets.

## 6. Validation strategy

### Targeted tests

- Every slice should land with focused unit coverage for its exact contract changes before broader integration work.
- Runtime-contract work is not done without targeted tests for lock behavior, reset/clean-room behavior, scope non-persistence, and deterministic run resolution.
- `/run` work is not done without targeted tests for malformed proposal output, governed blocked paths, successful bounded execution, and truthful failure rendering.
- Approval workflow work is not done without tests for approval binding, stale approval invalidation, and revalidate gating.
- Memory runtime work is not done without backend-selection tests and end-to-end handoff/retrieval coverage.

### Integration tests

- Add or expand integration tests around persisted runtime reload, fresh-process operator inspection after `/run`, and approve-plus-revalidate continuation.
- Preserve existing integration coverage for research follow-up, post-selection routing, and truth-first context ordering; those are already strong and should act as regression tripwires.
- Any richer runtime-backed execution slice should have at least one integration path using the fake adapter and one optional real-provider path when local infrastructure is available.

### Full-suite policy

- Continue the current discipline of running targeted suites first and the full suite before calling a slice done.
- A slice is not done if it only passes its narrow file set but regresses anti-drift, acceptance, or smoke surfaces.
- For high-risk slices, require at least one clean full-suite pass from a non-dirty runtime workspace after the slice lands.

### Operator validation

- After each of Priorities 1 through 4, run a black-box operator pass from README/help/bootstrap to one-shot commands.
- Validate from a fresh runtime workspace and from a previously used runtime workspace.
- Validate one-shot usage specifically, because that is where scope confusion, JSON confusion, and stale persisted-state drift currently show up most clearly.
- Treat operator confusion as a real failure, not a documentation-only issue, when the confusion comes from misleading command semantics.

### When a slice is not allowed to be called done

- When the main happy path works but blocked, stale, malformed, or approval-gated paths still lie or flatten distinctions.
- When fresh-process behavior differs materially from in-process behavior without being clearly surfaced.
- When compact text still tells a cleaner story than JSON in ways that hide failure reality.
- When the new behavior depends on README explanations to stay safe because the CLI itself is still misleading.
- When docs/status files still overclaim or underclaim the relevant surface after behavior stabilized.

## 7. Status-file recommendation

The next `WORK_STATUS_UPDATE` after Priorities 1 and 2 land should not read like another phase-complete note. It should read like an operator-reality hardening update.

Recommended content:

- State that Jeff's persisted runtime contract is now explicit and operator-safe enough for repeatable local use.
- State exactly how locking now behaves and how clean-room/reset startup is performed.
- State that `/run` now executes one bounded repo-local governed action family with real runtime evidence rather than placeholder-only execution.
- State what remains intentionally deferred: broader action families, broad retry/recover workflowing, GUI/API growth, autonomy, provider expansion.
- State which earlier liabilities are now closed and which still remain, especially around approval workflow and durable memory wiring if those are not yet landed.
- Include the exact targeted, integration, and full-suite validation commands used for the slice.

Suggested status-update wording focus:

- “primary operator path strengthened” rather than “new capability added”
- “runtime contract clarified and hardened” rather than “persistence improved”
- “bounded governed execution slice is now real” rather than “execution support added”

Planning-pass milestones:

- M1 — audited current reports/docs/code reality: complete.
- M2 — identified strongest vs weakest real layers: complete.
- M3 — extracted the real v1-critical gaps: complete.
- M4 — produced prioritized implementation slices: complete.
- M5 — produced validation strategy: complete.
- M6 — produced status-update recommendation: complete.

## 8. Optional appendix

### Temptations to avoid

- Do not add a GUI to hide that `/run` and request-entry workflows are still the weak spots.
- Do not add more providers to claim flexibility while the primary bounded path is still fragile.
- Do not build a broad API while the CLI contract still needs cleanup and narrowing.
- Do not expand retry, recover, or autonomous continuation before `approve` plus `revalidate` becomes genuinely useful.
- Do not invent workflow-heavy state or planner-heavy abstractions to compensate for thin execution reality.
- Do not build a large memory command surface before durable runtime wiring and minimal operator-visible continuity are in place.
- Do not widen web research just to look more capable; docs research and repo-local bounded execution are the more honest v1 strengths.

## Recommended first slice

- Exact first slice to execute: Priority 1, Repeatable runtime contract for the primary path.
- Why it is first: Jeff cannot make stronger `/run` claims until repeated local use is safe, deterministic, and honest about what is session-local versus persisted.
- What success would look like after just that slice: operators can start Jeff in a clean or existing runtime workspace predictably, concurrent mutation fails closed instead of colliding, run binding is understandable, and the CLI/help/startup surfaces stop implying persistence or auto-selection semantics they do not actually provide.