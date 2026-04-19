# Jeff Interface Refactor Proposal

Scope: interface/operator contract hardening only. No greenfield rewrite, no GUI/API/autonomy/provider widening, no core/governance/orchestrator redesign except minimal truth-projection adjustments.

Planning milestones for this pass:

- [x] M1 — audited black-box report and current repo interface reality
- [x] M2 — classified strong vs misleading vs weak interface surfaces
- [x] M3 — diagnosed root causes
- [x] M4 — produced milestone-based refactor plan
- [x] M5 — produced verification strategy
- [x] M6 — produced execution order

---

## 1. Executive judgment

Jeff's interface is credible as a **persisted inspection and bounded research shell**. `/show`, `/trace`, `/lifecycle`, `/research docs`, `--bootstrap-check`, and scope-aware one-shot chaining all do something real. The internal backbone (transitions, flow lifecycle, governance handoff, selection review) shows through these surfaces in a mostly truthful way.

What the interface currently overpromises is **operator-driven live action**. `/run <objective>` implies a general execution entry but is actually a single hardcoded `RepoLocalValidationPlan` in `command_scope.py`, gated upstream by proposal validation that forbids authority-language in provider output. Request-entry verbs (`approve/reject/revalidate/retry/recover`) are surfaced in `/help` but almost unreachable by a normal operator. `--json` is wired into some command families and silently ignored in others. Read commands silently persist support records. A seeded demo run is indistinguishable from fresh operator runs at inspection time.

The single most important interface hardening step is **narrowing and truthing `/run`**: rename/scope it so the operator knows the verb they typed matches the action that will run, make terminal non-execution paths render as something other than `completed`, and make failure modes legible in plain CLI text rather than stack-adjacent error strings.

---

## 2. Current interface reality classification

### Strong enough now
- `python -m jeff --help`, `--bootstrap-check`, `--reset-runtime`
- `/project list|use`, `/work list|use`, `/run list|use`, `/scope show|clear`
- `/show`, `/trace`, `/lifecycle` as historical inspection
- `/research docs` with explicit paths (produces persisted artifact)
- One-shot scope via `--project/--work/--run`
- Error messages for missing scope, unknown commands, unknown IDs
- `--json` on `/show`, `/trace`, `/lifecycle`, `/inspect`, `/selection`, `/research`, request verbs

### Real but misleading / thin
- `/run <objective>`: works only as repo-local pytest-smoke validation, labelled like a general operator entry (`render_help` even hints as much, but the CLI ergonomics don't make it obvious)
- `/selection show` vs `/show`: both real, but disagree on effective vs original selection in the presence of an override
- `run_lifecycle_state = completed` for terminal non-execution defer paths (see `_canonical_run_lifecycle_state` in `command_common.py:438` — only `approval_required` is mapped away from the raw flow state)
- Seeded demo run (`_initialize_persisted_runtime_state` in `bootstrap.py:65`) looks like a live-operator-produced run to `/show`
- `/research web` completes but result relevance is poor on repo-adjacent queries
- `/help` advertises `retry` / `recover` as "Conditional requests" without making clear they are receipt-only

### Operator-visible liabilities
- `--json` is **silently non-uniform**: `project_command`, `work_command`, `run_command` (list/use branches) in `command_scope.py` return a `json_payload` but are **not** wrapped by `_apply_json_mode` in `commands.py:38-44`. So `--json` does nothing on `/project list`, `/work list`, `/run list`.
- `/json on` is neutralized in repeated one-shot mode because `main.py:103` passes `json_output=args.json` (default `False`) into every command; `_apply_json_mode` in `commands.py:140` treats `False` as "force text", which overrides session `/json on`.
- Read commands mutate: `inspect_command` and `show_command` call `ensure_selection_review_for_run`, which calls `replace_selection_review` → `runtime_store.save_selection_review` (`command_common.py:344`). So a pure "show" takes the mutation lock and writes files.
- `jeff` console-script missing from this checkout (packaging declares it but editable install is optional).
- Non-TTY interactive refusal prints "No interactive terminal detected" without suggesting the idiomatic `--command` pattern inline.
- Windows lock error (`.jeff_runtime/config/runtime.mutation.lock`) is surfaced as a raw OSError/`RuntimeMutationLockError` rather than a polite "another jeff is busy" message.
- Request-entry surface (`approve/reject/revalidate/retry/recover`) listed in `/help` but unreachable because `allowed_outcomes` in `command_requests.py:40` requires specific `routed_outcome` states that the normal `/run` live path never produces.
- `--handoff-memory` fails on ordinary research summaries because `require_concise_text(..., max_length=240)` in `memory/types.py:137` rejects real summary text.
- Research command PowerShell quoting is undocumented; nested `""..""` escaping is trial-and-error.

### Explicit deferrals to keep deferred
- Broad `/memory` command family
- GUI / TUI / web surface
- Autonomous continuation, background daemon
- Additional action families beyond repo-local validation
- Cross-provider adapter widening
- Non-local runtime/workspace sharing

---

## 3. Root-cause diagnosis

### 3.1 `/run` promise vs reality
- **Operator sees:** `/run <objective>` implies a general action shell; in practice the objective string is passed to proposal generation, then selection, then a fixed `RepoLocalValidationPlan` (`command_scope.py:186-204`) that always runs the smoke pytest suite.
- **Cause:** one hardcoded execution plan, and upstream proposal validation (`cognitive/proposal/validation.py:12-21`) forbids authority-language tokens (`execution`, `ready`, `allow`, `approve`, `select`, `govern`, …) which real provider output regularly contains.
- **Fix domain:** interface wording + small projection adjustment. The backend plan is intentionally narrow; the interface must reflect that.
- **Do not overcorrect:** do not loosen proposal validation to make text look successful; do not add new execution plans just to broaden the verb.

### 3.2 JSON contract inconsistency
- **Operator sees:** `--json` works on some commands, silently drops to text on list commands, and `/json on` is invisible in `--command` repetition.
- **Cause (a):** `project_command`/`work_command`/`run_command` (list/use branches) are not wrapped by `_apply_json_mode` in `commands.py`. **Cause (b):** `argparse` default `--json=False` is indistinguishable from "not set", and `main.py` passes that `False` into `_apply_json_mode`, which treats it as a hard negative rather than "defer to session."
- **Fix domain:** interface routing/projection. Promote `--json` to tri-state (`None` when absent); wrap all list commands through `_apply_json_mode`.
- **Do not overcorrect:** do not force JSON on commands that have no meaningful JSON payload (`/scope show` is already fine; `/help` should stay text-only and the help view should say so).

### 3.3 Read-only purity and hidden mutations
- **Operator sees:** running two inspects in parallel collides on `runtime.mutation.lock`; `/inspect` after `/show` can change persisted support files on disk.
- **Cause:** `ensure_selection_review_for_run` materializes missing `SelectionReviewRecord` data from `FlowRunResult` and calls `replace_selection_review` which persists. Invoked from `inspect_command`, `show_command`, `selection_command`, every request verb, and `assemble_live_context_package`.
- **Fix domain:** interface routing + small backend-support adjustment — split materialization (in-memory) from persistence (opt-in or deferred). Read surfaces must never write support files.
- **Do not overcorrect:** do not delete materialization entirely; the derived review is load-bearing for `/selection show` and `/approve` semantics.

### 3.4 Scope / session / runtime clarity
- **Operator sees:** `/project use` behaves like it persists but does not; each `python -m jeff` is a fresh session; auto-binding to the most recent run is implicit.
- **Cause:** `CliSession.scope` is in-process only; one-shot `--project/--work/--run` wires it per invocation; `resolve_or_create_active_run` chooses an implicit run when none is scoped.
- **Fix domain:** interface wording. `/scope show` already nudges correctly; `use` commands must say "session-local" in their confirmation line, and `/help` must place the session-only rule above the conditional verbs.
- **Do not overcorrect:** do not introduce a persisted "default scope" file — that is a whole new runtime concept that would widen the contract.

### 3.5 Approval / request-entry usability
- **Operator sees:** `/help` lists 5 request verbs; 5 of 5 are `unavailable for that run` in normal live use.
- **Cause:** request verbs gate on specific `routed_outcome` states (`command_requests.py:40-47`). The default `build_run_governance_inputs` seeds `Approval.not_required()` (`command_common.py:99`), so nothing routes to `approval_required`. No natural CLI verb creates an approval-required state.
- **Fix domain:** interface wording (hide verbs unless applicable) + surface guidance. Keep the underlying governance machinery untouched.
- **Do not overcorrect:** do not expose a new "force approval" mode just to make the verbs reachable.

### 3.6 Memory as an operator surface
- **Operator sees:** bootstrap says memory is configured; `--handoff-memory` on a real docs-research call fails with `summary must stay concise and below 240 characters`.
- **Cause:** `require_concise_text(max_length=240)` in `memory/types.py:137` is tighter than real docs-research summary output.
- **Fix domain:** narrow interface promise. Either the handoff flag is reliable on real output, or it is not advertised. The internals of `MemoryStoreProtocol` should not widen for v1.
- **Do not overcorrect:** do not ship a `/memory` verb family to cover this gap.

### 3.7 Seeded / demo disclosure
- **Operator sees:** `project-1/wu-1/run-1` looks like a real completed run on a clean workspace.
- **Cause:** `_initialize_persisted_runtime_state` + `build_demo_selection_review` + `build_demo_flow_run` seed a fully-formed flow on first boot (`bootstrap.py`). Startup summary says "initializing" but `/show run-1` exposes it as if it were live.
- **Fix domain:** interface wording + a small marker on seeded records. No semantic change to the state machine.
- **Do not overcorrect:** do not remove seeding entirely; it is useful as a first-boot walk-through.

### 3.8 Shell / operator ergonomics
- **Operator sees:** PowerShell requires `""..""` nested escaping for research queries; research help text gives logical syntax only.
- **Cause:** `shlex.split` vs PowerShell argument parsing. No platform-aware help.
- **Fix domain:** interface wording/examples only.
- **Do not overcorrect:** do not write a new shell layer.

---

## 4. Refactor principles

1. **Truth over smoothness.** Never make a verb sound broader than the code actually does. `/run` must not imply arbitrary execution if the execution plan is fixed.
2. **Read is read.** A command whose help line says "show", "inspect", "trace", or "lifecycle" must take no mutation lock and must write no support file.
3. **Terminal states are honest.** If a flow ended without execution, `run_lifecycle_state` in the operator view must not be `completed`.
4. **JSON is contractual or absent.** `--json` and `/json on` either apply uniformly to a command family, or the help text explicitly says the command is text-only.
5. **One-shot and session are visibly different.** Session `/json on` must work in repeated `--command`; scope confirmations must say "session-local" in their reply.
6. **Surfaces are gated by reachability.** If a verb cannot be reached from a normal operator path, it is either hidden, contextually emitted, or marked receipt-only.
7. **Demo is labelled.** Seeded records are identifiable in `/show` output; the operator never confuses them with fresh live flows.
8. **Operator trust beats feature breadth.** Any proposal that widens the CLI surface area before these invariants hold is rejected.
9. **Help is platform-aware.** Windows/PowerShell examples appear for quote-sensitive commands.
10. **Failure legibility matters.** Raw lock errors, concurrency errors, and proposal-validation errors must be translated to operator-facing sentences before they hit stderr.

---

## 5. Refactor milestones

### M-RUN — `/run` contract hardening
- **Why now:** this is the single largest overpromise.
- **Goal:** make the verb, the help, and the terminal state match what actually happened.
- **Main areas:** `jeff/interface/command_scope.py` (_run_objective_command, help lines), `jeff/interface/render.py` (render_help), `jeff/interface/command_common.py` (_canonical_run_lifecycle_state), `README.md` operator rules block.
- **Exact problem it fixes:** `/run` looks general; terminal defer still prints `completed`; proposal-validation failures emerge as raw `ValueError`.
- **Scope of change:**
  - Rename operator-facing help to `/run <repo-local-validation-objective>` or add an `[repo-local-validation]` subtitle. Verb stays for compat; help text narrows.
  - Map non-execution terminal paths (flow ended before `execution` stage, or routing decision is a terminal defer) to `run_lifecycle_state ∈ {deferred, failed_before_execution}` instead of `completed` in `_canonical_run_lifecycle_state`.
  - Catch `ProposalGenerationValidationError` in `_run_objective_command` and render it as a single operator line: "proposal validation rejected live provider output (forbidden authority tokens). /run cannot proceed; try /research docs for inspection instead."
  - Update `/help` to state: "`/run` runs one bounded repo-local pytest validation plan under the current model configuration. It is not a general command runner."
- **Acceptance criteria:**
  - `/run foo` on a defer path → `/show` displays `run_lifecycle_state=deferred` (not `completed`).
  - `/run foo` on a proposal-validation failure → single-line operator message; exit code 0; `/show <new_run_id>` shows a truthful defer/failed state.
  - `/help` and README `/run` description match the actual RepoLocalValidationPlan scope.
- **Verification:** new unit tests in `tests/unit/interface/test_cli_run_resolution.py`; new acceptance test `test_acceptance_run_terminal_state_truthfulness.py`; black-box `python -m jeff --project project-1 --work wu-1 --command "/run validate README smoke path" --command "/show"`.
- **Dependencies:** none.
- **Do NOT widen:** do not add execution plans, do not relax proposal validation, do not invent new run lifecycle states beyond `deferred` / `failed_before_execution`.
- **Risk:** medium — touches the truth-projection helper that every inspection command depends on.

### M-JSON — JSON contract unification
- **Why now:** silent dropping of `--json` is a dignity-of-interface problem; tooling cannot depend on it.
- **Goal:** every command that carries a `json_payload` renders JSON under `--json` or session `/json on`; every command that does not, says so in help.
- **Main areas:** `jeff/main.py` (args.json as tri-state), `jeff/interface/commands.py` (_apply_json_mode wrapping for list commands), `jeff/interface/cli.py` (run_one_shot), `jeff/interface/command_scope.py` (ensure project/work/run list/use produce payloads eligible for JSON), `jeff/interface/render.py` (help lines).
- **Exact problem it fixes:** `--json` silently drops on `/project list`, `/work list`, `/run list`; `/json on` neutralized in repeated `--command`.
- **Scope of change:**
  - Change argparse wiring so "user did not pass `--json`" is `None` (use a sentinel or `action="store_const", const=True, default=None`).
  - Propagate tri-state through `run_one_shot` → `execute_command` → `_apply_json_mode`. `None` defers to session; `True` forces JSON; `False` forces text.
  - Wrap `project_command`, `work_command`, `run_command` (list/use branches) in `_apply_json_mode`.
  - Define a small "JSON-eligible" marker in help output for commands with `json_payload`.
- **Acceptance criteria:**
  - `python -m jeff --command "/project list" --json` emits a JSON line.
  - `python -m jeff --command "/json on" --command "/show"` (with scope) emits JSON on the second command.
  - `/help` notes which commands are text-only.
- **Verification:** extend `tests/unit/interface/test_cli_json_views.py` to cover list commands; add session-JSON repeated-command test; black-box verification via the commands above.
- **Dependencies:** none.
- **Do NOT widen:** do not invent new JSON shapes; reuse existing `*_json` view functions.
- **Risk:** low.

### M-READ — read-only purity
- **Why now:** fixes lock contention and restores trust in "show" verbs.
- **Goal:** `/show`, `/trace`, `/lifecycle`, `/inspect`, `/selection show` take no mutation lock and persist nothing.
- **Main areas:** `jeff/interface/command_common.py` (split `ensure_selection_review_for_run` into `materialize_selection_review_in_memory` and `persist_selection_review_if_changed`), `jeff/interface/command_inspect.py`, `jeff/interface/command_selection.py`, `jeff/runtime_persistence.py` (shared read lock vs mutation lock semantics).
- **Exact problem it fixes:** concurrent reads collide on the mutation lock; "read" commands write support files.
- **Scope of change:**
  - Introduce `materialize_selection_review_view` that returns the derived record without calling `runtime_store.save_*`.
  - Restrict the persisting variant to command paths that explicitly mutate (`request_command`, `selection_command override`, `_run_objective_command`).
  - Skip `mutation_guard` on read paths.
  - Surface any concurrent-lock contention as a polite one-liner rather than a raw stack.
- **Acceptance criteria:**
  - Running two `/show` invocations in parallel against the same runtime does not raise `RuntimeMutationLockError`.
  - After `/show run-1`, on-disk `selection_reviews/run-1.json` mtime is unchanged.
  - `/inspect` still produces the same JSON payload as before.
- **Verification:** new integration test that diffs mtimes before/after read commands; parallel-read smoke test; black-box `Start-Process` of two `python -m jeff --command "/show"` calls.
- **Dependencies:** M-RUN clarifies where writes are legitimate, but M-READ can proceed independently.
- **Do NOT widen:** do not introduce a new read-lock mechanism that affects non-CLI callers; keep the split inside the interface layer.
- **Risk:** medium — materialization is load-bearing for `/selection show` equivalence.

### M-SCOPE — scope / session / runtime truthfulness
- **Why now:** scope mental model is the most common first-five-minutes trap.
- **Goal:** every scope-changing command makes the session-only nature visible; `/help` places the session-vs-persistence distinction above conditional verbs.
- **Main areas:** `jeff/interface/command_scope.py` (confirmation strings for `/project use`, `/work use`, `/run use`, `/scope clear`), `jeff/interface/render.py` (render_help ordering), `jeff/main.py` (non-TTY hint), `README.md`.
- **Exact problem it fixes:** `use` commands can read as persistent; non-TTY message is terse.
- **Scope of change:**
  - Change `/project use` reply from `session scope updated: project_id=...` to `session scope updated (process-local only): project_id=...`.
  - Extend non-TTY print: include an inline example `python -m jeff --command "/help"`.
  - Reorder `/help` to place session-only rules first.
  - Make `/scope show` mention one-shot alternatives (`--project/--work/--run`).
- **Acceptance criteria:**
  - All `use` confirmations include the words "process-local" or "session-local".
  - Non-TTY path prints one example line.
  - `/help` first non-title line mentions session scope.
- **Verification:** update `tests/unit/interface/test_cli_scope_and_modes.py`, `test_cli_usability.py`; black-box `python -m jeff` in non-TTY.
- **Dependencies:** none.
- **Do NOT widen:** no persistent default-scope file.
- **Risk:** low.

### M-REQ — request-entry surface tightening
- **Why now:** 5 advertised verbs all unreachable in normal use is the clearest "bigger than it is" symptom.
- **Goal:** request-entry verbs surface only where a run is actually in a matching `routed_outcome`; `/help` distinguishes "active" from "receipt-only".
- **Main areas:** `jeff/interface/command_requests.py`, `jeff/interface/command_inspect.py` (hints block in `/show` when routed_outcome permits approve/reject/etc.), `jeff/interface/render.py` (help).
- **Exact problem it fixes:** approval/revalidate/reject/retry/recover appear broadly in help and fail on every normal run.
- **Scope of change:**
  - In `/help`, mark `retry`/`recover` as "bounded receipt-only" explicitly; mark `approve/reject/revalidate` as "only available when a run routes to approval_required or revalidate".
  - In `/show` text render, when the run's `routed_outcome` matches an enabling state, append a "[next] /approve | /reject | /revalidate <run_id>" hint.
  - Improve the "unavailable for that run" message to name the required `routed_outcome`.
- **Acceptance criteria:**
  - On a run with routed_outcome=None, `/show` output has no approve/reject/revalidate next-hint.
  - On a synthetic approval_required run (test fixture), `/show` hint line appears.
  - `/help` disambiguates active vs receipt-only verbs.
- **Verification:** new unit tests in `test_cli_live_run_view.py`; black-box on the demo seed.
- **Dependencies:** none; complementary to M-SCOPE.
- **Do NOT widen:** do not add a new verb; do not add an "ops mode" that force-routes approval.
- **Risk:** low.

### M-MEM — memory handoff honesty
- **Why now:** `--handoff-memory` is documented but fails on real docs-research summaries.
- **Goal:** either the flag reliably works on ordinary summaries, or it is not a documented operator-facing flag in v1.
- **Main areas:** `jeff/interface/command_research.py` (flag surfacing), `jeff/cognitive/research/memory_handoff.py` (pre-handoff summary shaping), `jeff/memory/types.py` (constraint is not changed without evidence).
- **Exact problem it fixes:** `--handoff-memory` failing on docs summaries; operator sees internal validation error.
- **Scope of change (pick one, not both):**
  - Option A — reliable: add a pre-handoff summary trimmer (first sentence + ≤240 chars, deterministic) so handoff succeeds on normal output; surface a one-line notice when trimming occurred.
  - Option B — honest: remove `--handoff-memory` from `/help`, mark it experimental in README, make `handoff_persisted_research_record_to_memory` emit `ResearchOperatorSurfaceError` with a user-level message when validation would fail.
- **Acceptance criteria (A):** `/research docs ... --handoff-memory` on a default config succeeds on a real README query; the trimmed summary appears in the JSON payload.
- **Acceptance criteria (B):** `--handoff-memory` no longer listed in `/help`; README explicitly says handoff is experimental; failure mode is operator-legible.
- **Verification:** `tests/integration/test_research_memory_handoff_flow.py` runs against a real `InMemoryMemoryStore` without monkeypatching; black-box research docs command with the flag.
- **Dependencies:** none.
- **Do NOT widen:** no `/memory` verb family; no new memory CLI.
- **Risk:** medium (A) / low (B). Recommendation: B first, A only if a simple trimmer is clearly reliable.

### M-SEED — seeded/demo disclosure
- **Why now:** seeded state inflates perceived robustness.
- **Goal:** operator can always tell a seeded record from a live-operator record.
- **Main areas:** `jeff/bootstrap.py` (mark seeded selection_review + flow_run with a `provenance="seeded_demo"` tag), `jeff/interface/json_views.py` (surface `provenance`), `jeff/interface/render.py` (render `[seeded-demo]` badge in `/show`, `/run list`), README "Start" section.
- **Exact problem it fixes:** `run-1` looks live; operator mistakes bootstrap for capability.
- **Scope of change:**
  - Add a provenance field (or reuse an existing free-form tag) on the demo `FlowRunResult` and `SelectionReviewRecord`.
  - Render the tag in `/show`, `/run list`, and the text output of `--bootstrap-check`.
  - Update README "Start" to say: "first boot seeds `run-1` as a demo; subsequent operator-created runs are live."
- **Acceptance criteria:**
  - Fresh workspace → `/run list` shows `run-1 lifecycle=completed [seeded-demo]`.
  - A real `/run` afterwards shows without the tag.
  - `--bootstrap-check` mentions seeded state during first-boot initialization.
- **Verification:** `tests/smoke/test_bootstrap_smoke.py` asserts tag presence; `tests/integration/test_runtime_workspace_persistence.py` asserts fresh-run tag absence.
- **Dependencies:** M-JSON for the JSON-view surfacing of the tag.
- **Do NOT widen:** do not remove or reshape seeded data; do not add an `--no-seed` flag yet.
- **Risk:** low.

### M-SHELL — operator wording, help, README cleanup (final pass)
- **Why now:** after the other milestones, help/README must stop drifting from behavior.
- **Goal:** `/help`, `--help`, README, and `--bootstrap-check` lines are internally consistent and match observed CLI behavior on Windows and Unix.
- **Main areas:** `jeff/main.py` epilog, `jeff/interface/render.py::render_help`, `jeff/interface/command_research.py` examples, `README.md`, `jeff.runtime.toml` scaffold text if any.
- **Exact problem it fixes:** PowerShell quoting surprise; console-script advertised but not installed; terse non-TTY message; stale help lines after earlier milestones.
- **Scope of change:**
  - Add a "PowerShell quoting" example to research help and README.
  - Note that the `jeff` console script requires `pip install -e .`.
  - After M-RUN / M-JSON / M-REQ land, rewrite `render_help` in one pass so ordering and phrasing match.
  - Add a short "What `/run` does" paragraph to README.
- **Acceptance criteria:**
  - `python -m jeff --help` shows the PowerShell note.
  - README and `/help` agree on every verb surface.
  - `--bootstrap-check` lines are verified in tests to match README.
- **Verification:** README anti-drift test in `tests/antidrift/`; manual pass on Windows PowerShell and Git Bash.
- **Dependencies:** all earlier milestones.
- **Do NOT widen:** no new content families (no memory section, no GUI section, no autonomous section).
- **Risk:** low.

---

## 6. Verification strategy

For every milestone, "done" requires all four of:

1. **Black-box operator commands** (`python -m jeff --command ...`) reproduce the acceptance criteria on a clean runtime and on a seeded runtime.
2. **Targeted unit tests** under `tests/unit/interface/` cover the helper or dispatcher change.
3. **Integration tests** under `tests/integration/` exercise the full CLI-to-persistence path without monkeypatching provider behavior for the truthfulness claim.
4. **Full-suite policy**: `python -m pytest -q` must pass; plus documented smoke trio:
   `python -m pytest -q tests/smoke/test_bootstrap_smoke.py tests/smoke/test_cli_entry_smoke.py tests/smoke/test_quickstart_paths.py`.

A milestone is **not** done when:
- The acceptance criteria pass only under monkeypatched provider adapters.
- Text output is correct but JSON output diverges (or vice versa).
- Help text matches but the underlying command does something else.
- A previously read-only command becomes read-only only on success paths (lock-taken on failure is still a failure).
- An "unavailable for that run" message changed, but no test pins it.

### Per-class verification

- **M-RUN:** unit: `_canonical_run_lifecycle_state` branches; integration: `/run` with a forced-validation-failure provider (use the existing failure-injection seam in `test_cli_research_failure_surface.py` as template, but for proposal validation); black-box: `/run foo` on a workspace with a minimal model adapter config → `/show` reports defer, not complete.
- **M-JSON:** unit: every `*_json` view has an `_apply_json_mode` path; integration: `--json` on each list command; black-box: `/json on` in repeated `--command` mode emits JSON for the second command.
- **M-READ:** unit: `materialize_selection_review_view` produces the same payload shape as the persisting variant; integration: mtime-diff test on read paths; black-box: two parallel `python -m jeff --command "/show"` invocations complete without lock error.
- **M-SCOPE:** unit: confirmation strings; black-box: non-TTY output inspection.
- **M-REQ:** unit: `/show` renders the hint block only when routed_outcome allows; integration: approve on a fixture run routed to approval_required; black-box: confirm `/help` text diff.
- **M-MEM:** integration (real store, no monkeypatch): `/research docs ... --handoff-memory` on the README produces either a success record or a legible `ResearchOperatorSurfaceError`; black-box: the same.
- **M-SEED:** smoke: fresh workspace → tag present; after `/run` → tag absent on new run.
- **M-SHELL:** anti-drift test compares `/help` against `README.md` operator rules block.

Example black-box verification commands:

```
python -m jeff --reset-runtime --bootstrap-check
python -m jeff --command "/project list" --json
python -m jeff --project project-1 --work wu-1 --command "/json on" --command "/show"
python -m jeff --command "/project use project-1" --command "/work use wu-1" --command "/run README smoke path" --command "/show"
python -m jeff --project project-1 --work wu-1 --run run-1 --command "/show"
```

---

## 7. Recommended execution order

1. **M-RUN** — first, because terminal-state truthfulness underlies every other inspection surface. If this does not land first, subsequent milestones ship on top of misleading lifecycle states.
2. **M-READ** — second, in parallel with M-JSON. Both are interface-routing changes with no semantic overlap. M-READ removes the lock-contention class of bugs, which unblocks parallel black-box verification of everything later.
3. **M-JSON** — parallel with M-READ. Pure routing/projection change.
4. **M-SCOPE** and **M-REQ** — after M-RUN. M-REQ depends on M-RUN's terminal-state truth; M-SCOPE is a wording pass that benefits from stable help text.
5. **M-SEED** — after M-JSON (so the provenance tag can be surfaced in JSON views uniformly) and after M-RUN (so the demo run's lifecycle state is truthful before we label it).
6. **M-MEM** — can proceed after M-JSON. Option B (remove `--handoff-memory` from help) can land at any time; Option A depends on nothing.
7. **M-SHELL** — last. Consolidates help/README/examples after every other milestone has settled.

Parallel-safe: {M-READ, M-JSON, M-MEM-B}. Strictly sequential: M-RUN → M-SEED → M-SHELL. M-REQ after M-RUN.

---

## 8. Temptations to avoid

- Adding new verbs (`/memory`, `/status`, `/plan`) to mask reachability gaps. The fix is to hide or gate existing verbs, not add more.
- Making `/run` succeed by relaxing proposal validation so provider text passes. That turns a truthful failure into a false success.
- Making `--json` "best effort" (opportunistically JSON where possible). Either it is contractual per command or it is not advertised on that command.
- Treating seeded demo state as just another normal run. It is not, and pretending otherwise is how "completed" count metrics lie.
- Introducing a `/memory` command family to compensate for the broken `--handoff-memory` flag.
- Inventing a persistent-scope file to fix `/project use` UX. Process-local session scope is a real design choice; the fix is wording, not a new runtime concept.
- Writing a custom shell parser for PowerShell quoting. Document the quoting instead.
- Hiding concurrency failures under retry logic. Fix the read/write split first.
- Amending `/help` to be shorter without also fixing the verbs it describes. Shortening misleading help is still misleading.
- Shipping any milestone whose acceptance criteria pass only under monkeypatched tests.

---

## Recommended first milestone

**Execute M-RUN first.**

Why it goes first:
- It is the single most operator-visible overpromise in the current CLI, and the validation report singles it out.
- Every other milestone (M-READ, M-SEED, M-REQ, M-SHELL) ultimately renders or references `run_lifecycle_state`, routed_outcome, or `/run` help text. Fixing those downstream surfaces on top of an untruthful `_canonical_run_lifecycle_state` just propagates the lie.
- It is the smallest self-contained slice whose success is independently verifiable by black-box operator commands.

What a better operator experience looks like immediately after just M-RUN:
- A normal user types `/run foo`, sees a defer or a clean failure line, and `/show <new_run_id>` reports `run_lifecycle_state=deferred` (or `failed_before_execution`) — never `completed` when execution did not happen.
- `/help` and README agree that `/run` is a bounded repo-local pytest validation entry, not a general command runner.
- Proposal-validation failures (the main live-provider failure mode) emerge as one operator-facing sentence, not as a raw exception bubbling through the dispatcher.
- The request-entry verbs and the `/selection show` chain no longer sit on top of a misleading `completed` state.
