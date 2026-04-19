# Priority 1 Execution Checklist

## Title

Repeatable runtime contract for the primary path.

## Goal

Make persisted runtime use repeatable and operator-safe by adding real single-writer mutation protection, one explicit clean-room or reset path, deterministic run-binding rules, and explicit session-local scope messaging.

## Dependency status

- Depends on: none.
- Must finish before: `priority_2.md`, `priority_3.md`, `priority_4.md`, `priority_5.md`, `priority_6.md`.

## Ticket slices

### P1-T1. Real runtime mutation lock

- Outcome: mutating startup and mutating CLI operations use a real single-writer lock or fail fast with a truthful message.
- Risk: medium.
- Done when:
- Startup initialization and runtime mutation paths cannot race silently.
- Lock acquisition failure produces a stable operator-visible error.
- Read-only startup and read-only commands remain usable when safe.

### P1-T2. Clean-room and reset path

- Outcome: one explicit operator path exists to start from a fresh bounded runtime workspace.
- Risk: medium.
- Done when:
- There is exactly one documented and tested clean-room or reset path.
- The path is explicit and bounded to `.jeff_runtime`.
- It does not mutate canonical truth accidentally during dry startup or read-only usage.

### P1-T3. Deterministic run binding and scope truthfulness

- Outcome: `/inspect`, `/show`, and related run-binding behavior are understandable, deterministic, and no longer drift into misleading latest-run behavior.
- Risk: medium.
- Done when:
- Auto-binding rules are stable and documented.
- Session-local scope remains session-local and is clearly labeled everywhere relevant.
- Failure or stale-run accumulation does not create misleading default behavior.

### P1-T4. JSON and help contract cleanup for runtime usage

- Outcome: one-shot `--json`, session `/json on`, bootstrap output, and help text all describe current behavior truthfully.
- Risk: low.
- Done when:
- JSON-mode behavior is explicit and unsurprising in both one-shot and interactive contexts.
- Help and startup language match persisted-runtime reality.

## File-by-file implementation checklist

### jeff/runtime_persistence.py

- Add a real lock primitive for runtime mutation, not just a metadata file.
- Decide and implement the bounded locking model:
- Prefer process-level exclusive lock around canonical-state writes, transition writes, flow-run writes, and selection-review writes.
- Keep lock scope narrow so read-only operations do not block unnecessarily.
- Add explicit helpers for `acquire`, `release`, and guarded mutation blocks.
- Fail with a precise error that can be shown at the CLI boundary when a second mutating process collides.
- Keep `runtime.lock.json` as metadata only if it still adds value; do not pretend it is the live lock if it is not.
- Add one bounded runtime-home helper for clean-room reset or runtime reset support.
- Ensure reset behavior cannot partially delete a runtime home and leave a malformed workspace.

### jeff/bootstrap.py

- Route mutating startup initialization through the real lock path.
- Decide whether ordinary persisted-state load is read-only or lock-protected; document the choice in code comments only if the behavior is non-obvious.
- Add bounded clean-room startup support if the reset path belongs in startup orchestration.
- Keep existing persisted-state behavior for normal startup intact.

### jeff/main.py

- Add the operator entrypoint for clean-room or reset behavior.
- Keep it explicit and bounded. Suitable shapes are a new startup flag or a bootstrap-only maintenance flag.
- Do not add broad workspace-management verbs.
- Ensure startup error messaging for lock conflicts is user-readable and does not dump internals.
- Clarify `--json` help text so one-shot behavior is obvious.

### jeff/interface/command_common.py

- Replace latest-run auto-binding logic if needed with deterministic run resolution rules that remain truthful under failed-run accumulation.
- Separate “active run”, “historical run”, and “auto-selected run” semantics more explicitly.
- Ensure any auto-selection message explains why that run was chosen.
- Preserve the lawful separation between session scope and canonical truth.

### jeff/interface/command_scope.py

- If runtime reset or clean-room support belongs in the slash-command surface, keep it tightly bounded and clearly labeled.
- Otherwise, update scope and JSON-mode feedback text so it accurately reflects process-local behavior.
- Make sure `/json on` messaging makes clear whether it affects only the current session.

### jeff/interface/render.py

- Update `/help`, scope hints, and operator-facing text to describe persisted runtime, session-local scope, deterministic run-binding rules, and JSON behavior truthfully.
- Remove or replace wording that still implies an in-memory-only startup story.
- Ensure compact-mode text does not hide runtime-contract boundaries.

### README.md

- Update quickstart and startup caveats to reflect the real persisted-runtime contract.
- Add the clean-room or reset path once implemented.
- Clarify that `use` commands are session-local in one-shot mode.
- Clarify one-shot `--json` versus interactive `/json on`.

## Test cases to add or update

### tests/integration/test_runtime_workspace_persistence.py

- Add a test that concurrent mutating operations fail fast with a truthful runtime-lock error.
- Add a test that read-only reload works after a locked mutation finishes.
- Add a test for the explicit clean-room or reset path.
- Add a test that reset recreates a valid runtime home rather than a partial workspace.

### tests/unit/interface/test_cli_scope_and_modes.py

- Add or update tests proving session-local scope remains non-persistent and is clearly surfaced as such.
- Add or update tests for `--json` versus `/json on` semantics.
- Add coverage for any new startup or scope guidance text introduced by this slice.

### tests/unit/interface/test_cli_run_resolution.py

- Add tests for deterministic run-binding after multiple runs exist, including failed runs.
- Add tests that `/show` and `/inspect` do not silently drift into misleading latest-run behavior.
- Add tests for explicit operator messages when auto-selection happens.

### tests/smoke/test_cli_entry_smoke.py

- Update startup-help and bootstrap-check expectations to match persisted-runtime and reset behavior.
- Add a smoke check for the clean-room or reset flag if it lives in the CLI entrypoint.

### tests/smoke/test_quickstart_paths.py

- Update quickstart expectations to match the new runtime contract.
- Add a bounded quickstart path that starts from a fresh runtime workspace explicitly.

## Operator validation checklist

- Run from a fresh workspace with no `.jeff_runtime` present.
- Run from an existing workspace with prior runs present.
- Trigger two mutating Jeff processes and confirm one fails fast truthfully.
- Confirm `python -m jeff --help` matches actual startup behavior.
- Confirm one-shot `--json` and session `/json on` each behave exactly as described.
- Confirm `/project use`, `/work use`, and `/run use` remain session-local and that the operator can tell that from the surface.

## Suggested validation commands

```text
python -m pytest -q tests/integration/test_runtime_workspace_persistence.py tests/unit/interface/test_cli_scope_and_modes.py tests/unit/interface/test_cli_run_resolution.py tests/smoke/test_cli_entry_smoke.py tests/smoke/test_quickstart_paths.py
python -m pytest -q
```

## Non-goals

- No daemon or background service.
- No multi-user runtime coordination system.
- No broad runtime-management control plane.
- No new workflow or state model.

## Slice completion gate

- This priority is not done if locking is still advisory only.
- This priority is not done if the operator still cannot tell what is persisted versus session-local.
- This priority is not done if run auto-binding still changes meaning unpredictably after failed or newer runs accumulate.
