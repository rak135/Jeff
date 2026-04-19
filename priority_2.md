# Priority 2 Execution Checklist

## Title

Credible `/run` bounded governed execution slice.

## Goal

Make `/run` reliably drive one bounded, materially useful, runtime-backed action family end to end. The recommended v1 slice is a governed repo-local validation action family with whitelist-backed runtime execution, captured evidence, truthful failure states, and bounded evaluation.

## Dependency status

- Depends on: `priority_1.md` complete.
- Must finish before: `priority_3.md` and `priority_4.md`.

## Ticket slices

### P2-T1. Bounded action family definition

- Outcome: Jeff has one concrete v1 execution family that is materially useful and tightly bounded.
- Suggested scope: repo-local validation commands such as test or lint execution behind an allowlist and scope checks.
- Done when:
- The allowed action family is explicit in code and config.
- The family is narrow enough that it does not become arbitrary shell execution.

### P2-T2. Runtime-backed governed execution path

- Outcome: `/run` can move from proposal through governance into real execution for the bounded action family.
- Done when:
- Governance can still block truthfully.
- Successful runs record real runtime evidence.
- Failed runs remain truthful and non-decorative.

### P2-T3. Honest failure and result surfacing

- Outcome: proposal, selection, execution, and evaluation failures remain typed and operator-visible.
- Done when:
- Compact and JSON views both tell the truth.
- Failed `/run` results no longer look like dead-looking empty shells.

## File-by-file implementation checklist

### jeff/interface/command_scope.py

- Keep `/run` as the primary bounded path.
- Replace placeholder execution assumptions with the new bounded action-family path.
- Ensure proposal-stage failures, governance blocks, execution failures, and successful completion are all surfaced as distinct outcomes.
- Preserve live-context assembly and the current bounded flow structure unless a narrow change is required.

### jeff/cognitive/proposal/

- Tighten proposal generation expectations for the bounded action family so valid output is easier to obtain and validate.
- Add any bounded proposal-shaping support needed for the execution family, without widening proposal semantics globally.
- Keep proposal honesty intact: no padding, no fake alternatives.

### jeff/cognitive/selection/

- Ensure selection output for the bounded action family remains deterministic or truthfully hybrid where needed.
- Preserve the selected-versus-permitted boundary.

### jeff/cognitive/post_selection/

- Tighten the post-selection chain so the bounded action family produces a complete actionable basis.
- Ensure action formation, effective proposal materialization, and governance handoff all preserve the bounded runtime action shape.

### jeff/action/execution.py

- Add real execution support for the bounded action family.
- Capture runtime evidence such as command identity, exit status, bounded output summaries, and any execution-local failure markers.
- Keep execution semantics separate from outcome and evaluation.

### jeff/action/outcome.py

- Normalize real execution residue into truthful outcomes for the bounded action family.
- Reflect partial, failed, blocked, degraded, or inconclusive postures honestly.

### jeff/cognitive/evaluation.py

- Evaluate the bounded action-family outcome using the captured evidence rather than placeholder success assumptions.
- Preserve deterministic overrides for weak or missing evidence.

### jeff/infrastructure/runtime.py

- Implement the bounded execution adapter surface.
- Enforce the whitelist and repo-local scope protections.
- Refuse any command or target outside the approved v1 slice.

### jeff/infrastructure/contract_runtime.py

- Add the runtime contract types needed to carry bounded execution requests and results.
- Keep adapter-owned semantics out of this layer.

### jeff/infrastructure/output_strategies.py

- Add any bounded output truncation or summarization needed so evidence remains useful without dumping raw output blindly.

### jeff/interface/json_views.py

- Expose real execution evidence, outcome posture, and evaluation verdict truthfully.
- Keep support artifacts labeled as support.
- Ensure JSON does not overstate completion.

### jeff/interface/render.py

- Update compact output so failed or blocked `/run` results are still informative.
- Do not let compact output tell a cleaner story than JSON.

## Test cases to add or update

### tests/integration/test_cli_run_live_context_execution.py

- Add a success case for the new bounded validation action family.
- Add a governance-blocked case that never executes.
- Add an execution-failure case with truthful evidence and verdict surfacing.
- Add a malformed proposal or malformed runtime-output case that fails closed.

### New integration test file for bounded runtime execution

- Add focused integration coverage for the whitelist-backed runtime adapter.
- Verify non-whitelisted or out-of-scope actions are rejected.
- Verify bounded output capture and truncation behavior.

### New acceptance test for `/run`

- Add one acceptance slice from objective to completed governed execution using the new bounded action family.
- Confirm fresh-process inspection still shows a coherent result afterward.

### Update CLI alignment tests

- Ensure operator-facing `/run` surfaces remain truthful in both compact and JSON modes.

## Operator validation checklist

- Run `/run` with configured fake runtime and confirm a completed bounded execution path.
- Run `/run` into an approval-required or blocked path and confirm execution does not happen.
- Inspect the same run from a fresh process and confirm the result is still coherent.
- Compare compact output to JSON and verify compact output is not hiding failure reality.

## Suggested validation commands

```text
python -m pytest -q tests/integration/test_cli_run_live_context_execution.py tests/acceptance/test_acceptance_backbone_flow.py
python -m pytest -q
```

## Non-goals

- No arbitrary shell execution.
- No broad action-family expansion.
- No background autonomy or task-loop behavior.
- No provider-sprawl work.

## Slice completion gate

- This priority is not done if `/run` still mostly produces empty-looking failed runs.
- This priority is not done if successful execution still relies on placeholder-only execution semantics.
- This priority is not done if the bounded action family can widen into arbitrary repo commands.
