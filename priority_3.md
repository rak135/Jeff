# Priority 3 Execution Checklist

## Title

Transition-backed run truth progression.

## Goal

Extend canonical truth minimally so runs can progress through truthful lifecycle and result states via transitions only, without collapsing support artifacts into state.

## Dependency status

- Depends on: `priority_1.md` and `priority_2.md` complete.
- Must finish before: `priority_4.md` and `priority_6.md`.

## Ticket slices

### P3-T1. Define narrow run-progression truth vocabulary

- Outcome: canonical run truth can represent truthful progression states required by the strengthened `/run` path.
- Done when:
- The added truth vocabulary is minimal and scoped to runs.
- It does not create workflow truth or support-artifact mirrors.

### P3-T2. Add transition path for run progression

- Outcome: run truth changes only through explicit transitions.
- Done when:
- `/run` and related continuation paths can commit lawful run-truth updates.
- Failure, blocked, approval-required, and completed states are represented truthfully.

### P3-T3. Align inspect and lifecycle views to canonical run truth

- Outcome: fresh startup and fresh-process inspection read the same run-truth story.
- Done when:
- Read surfaces no longer depend on interface-owned patching to explain run state.

## File-by-file implementation checklist

### jeff/core/containers/models.py

- Add the minimum run-truth fields needed for truthful progression.
- Keep the model narrow. Good candidates are bounded lifecycle and last-known result posture, not full execution residue.
- Do not store support blobs in canonical run state.

### jeff/core/transition/apply.py

- Add narrow transition types for run progression.
- Validate legal state changes and fail closed on impossible transitions.
- Preserve the existing transition discipline and state version rules.

### jeff/core/transition public surface as needed

- Add any request-shape or export updates needed for new run-progression transitions.
- Keep the new transition family bounded to runs.

### jeff/interface/command_common.py

- Update run creation and flow replacement paths so strengthened `/run` can commit run-truth progression lawfully.
- Keep support-record persistence separate from canonical run mutation.

### jeff/interface/command_inspect.py

- Read and render canonical run truth first.
- Keep support artifacts as supporting explanation, not truth authority.

### jeff/interface/json_views.py

- Expose canonical run-truth progression distinctly from support artifacts.
- Ensure `truth`, `derived`, and `support` remain separated.

### jeff/runtime_persistence.py

- Persist and reload the extended canonical run truth through the existing snapshot path.
- Keep flow-run and selection-review support records separate from canonical state.

## Test cases to add or update

### New unit tests for run-progression transitions

- Add positive tests for lawful run-progression commits.
- Add negative tests for impossible state changes.
- Add tests ensuring support artifacts cannot mutate run truth directly.

### tests/integration/test_runtime_workspace_persistence.py

- Add coverage proving run-progression truth survives reload cleanly.
- Add coverage proving support records remain outside canonical state.

### tests/unit/interface or integration tests for inspect alignment

- Add tests that `/show`, `/inspect`, and `/lifecycle` tell the same story from canonical run truth after reload.

### Acceptance alignment coverage

- Update acceptance CLI alignment tests so a strengthened `/run` and reload path remain consistent.

## Operator validation checklist

- Launch a bounded `/run`, then inspect the same run in a fresh process.
- Confirm canonical run state reflects blocked, failed, approval-required, or completed posture truthfully.
- Confirm support surfaces still add detail without becoming the source of truth.

## Suggested validation commands

```text
python -m pytest -q tests/integration/test_runtime_workspace_persistence.py tests/acceptance/test_acceptance_cli_orchestrator_alignment.py
python -m pytest -q
```

## Non-goals

- No workflow truth.
- No broad canonical mirrors of execution, evaluation, or support objects.
- No large state-model expansion beyond run progression.

## Slice completion gate

- This priority is not done if fresh-process inspection still needs interface-side guesswork to explain run state.
- This priority is not done if support artifacts are copied wholesale into canonical state.
- This priority is not done if run truth can still change outside the transition path.
