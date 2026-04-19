# Priority 6 Execution Checklist

## Title

Operator contract and status alignment cleanup.

## Goal

Align README, `/help`, bootstrap diagnostics, and status files with the actual persisted-runtime startup path, strengthened `/run` contract, approval workflow, JSON behavior, memory configuration, and explicit v1 deferrals.

## Dependency status

- Depends on: stabilized behavior from `priority_1.md` through `priority_5.md` as applicable.
- This is the final cleanup pass, not an enabling slice.

## Ticket slices

### P6-T1. Startup and help truth alignment

- Outcome: startup, help, and quickstart text all match real behavior.
- Done when:
- No top-level operator surface still describes default startup as explicit in-memory demo state.

### P6-T2. Primary-path honesty alignment

- Outcome: `/run` is described honestly as the primary bounded path only after the earlier priorities make that true.
- Done when:
- Docs and operator surfaces do not overclaim broader completion ability.

### P6-T3. Status and handoff truth alignment

- Outcome: status files and handoffs stop overstating unfinished surfaces and stop understating already-real ones.
- Done when:
- The next status update reads like operator-reality hardening, not phase theater.

## File-by-file implementation checklist

### README.md

- Update startup path, quickstart, reset or clean-room guidance, JSON behavior, scope-locality guidance, and memory/runtime config wording.
- Keep the README short and operator-focused.
- Do not turn it into a canonical semantics document.

### jeff/main.py

- Align `--help` descriptions and examples with stabilized runtime behavior.
- Ensure the bootstrap-check surface reflects real runtime and memory configuration truthfully.

### jeff/interface/render.py

- Align `/help` wording with stabilized command semantics.
- Ensure run, scope, JSON, approval, and memory-related messaging reflect the actual behavior that landed.

### handoffs/system/WORK_STATUS_UPDATE.md

- Update the current status summary so it reflects the strengthened runtime contract and primary-path reality.
- Remove stale wording that still underclaims persisted runtime or overclaims unfinished control workflows.

### New timestamped WORK_STATUS_UPDATE file

- Write the next update as an operator-reality hardening note.
- Include exact validation commands used.
- Call out what remains deferred explicitly.

### Module handoffs as needed

- Update any stale `HANDOFF.md` files that contradict the stabilized runtime, `/run`, approval, or memory behavior.
- Keep handoffs subordinate to `v1_doc/` and the new implementation-plan docs.

## Test cases to add or update

### tests/smoke/test_cli_entry_smoke.py

- Update help and startup expectations to match the final operator contract.

### tests/smoke/test_quickstart_paths.py

- Update quickstart expectations to match the final README path.

### tests/acceptance/test_acceptance_cli_orchestrator_alignment.py

- Add or update assertions for the final truthful operator wording where appropriate.

### Any doc-adjacent anti-drift coverage already present

- Update those tests so they protect the new truthful operator contract from drifting again.

## Operator validation checklist

- Read README first, then run `python -m jeff --help`, then run the real primary-path commands.
- Confirm that an operator can understand startup, scope, JSON mode, `/run`, approval workflow, and memory behavior without insider knowledge.
- Confirm status files do not claim more than the repo can do.

## Suggested validation commands

```text
python -m pytest -q tests/smoke/test_cli_entry_smoke.py tests/smoke/test_quickstart_paths.py tests/acceptance/test_acceptance_cli_orchestrator_alignment.py
python -m pytest -q
```

## Non-goals

- No documentation rewrite project.
- No marketing polish pass.
- No new surface-area expansion for optics.

## Slice completion gate

- This priority is not done if README, `/help`, and actual behavior still disagree.
- This priority is not done if status files still present stale phase language instead of current runtime truth.
- This priority is not done if operator understanding still depends on reading implementation code.
