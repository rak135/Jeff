# Direct Proposal Scope And Support Report

## 1. Executive summary

Direct `/proposal` is not project-only and not work-unit-only. It is a run-scoped command path that always resolves a concrete historical run before proposal generation. Once the run is resolved, it reads current canonical truth for exactly three truth families when available in scope:

- project truth
- work_unit truth
- run truth

The bounded product-code fix in this slice was to make the direct `/proposal` path request bounded direct-support context so scope-matched archive artifacts are actually retrieved when they exist. That change made live direct `/proposal` on `run-1` materially richer: it now receives archive-backed evidence support and exposes it clearly in the persisted proposal bundle and operator surfaces.

Committed memory support was also audited. In the current live workspace it still does not appear for one-shot CLI invocations, not because direct `/proposal` ignores memory support, but because startup is currently constructing an `InMemoryMemoryStore` in this environment and `memory-1` is not actually present when a new `python -m jeff` process starts. Integration tests proved that direct `/proposal` does include committed memory support when the store is genuinely populated in scope.

## 2. Exact answer: what state direct `/proposal` reads without `/run`

Direct `/proposal` does not create a new run and does not use flow-run output as truth input.

It resolves a concrete historical run first via `resolve_historical_run(...)` and then calls `assemble_live_context_package(...)` with:

- `scope = Scope(project_id=<run.project_id>, work_unit_id=<run.work_unit_id>, run_id=<run.run_id>)`
- `state = context.state`

That means the canonical state read is the persisted global state already loaded into `InterfaceContext.state`, scoped down to the resolved run.

The truth records are extracted by `assemble_context_package(...) -> _extract_truth_records(...)` from canonical state in this order:

1. project truth
2. work_unit truth
3. run truth

There is no direct `/proposal` path that reads only project truth or only work_unit truth once a run has been resolved. The proposal path always resolves to a run scope first.

## 3. Exact answer: does direct `/proposal` use project truth, work_unit truth, run truth, or some subset

When direct `/proposal` executes successfully, it uses:

- project truth: yes
- work_unit truth: yes
- run truth: yes

Black-box confirmation after the change:

- live direct `/proposal` on `run-1` returned `truth_snapshot.item_count = 3`
- the truth families were `project`, `work_unit`, and `run`

If no run can be resolved, direct `/proposal` fails closed before proposal generation instead of falling back to a project-only or work-unit-only truth snapshot.

## 4. Scope-resolution behavior

### explicit run

If `--run <run_id>` is present or the session already has `run_id`, direct `/proposal` uses that exact run.

Observed live behavior:

```text
python -m jeff --project project-1 --work wu-1 --run run-1 --command '/proposal What is Jeff architecture?' --json
```

Result:

- proposal executed successfully
- truth snapshot included project/work_unit/run
- scope frame was `project-1 / wu-1 / run-1`

### no run

If no explicit run is provided and the session has no current run:

- if the selected work unit has exactly one run, `resolve_historical_run(...)` auto-selects it
- if the selected work unit has no runs, direct `/proposal` fails closed
- if the selected work unit has multiple runs, direct `/proposal` fails closed as ambiguous

Observed live behavior in the current workspace:

```text
python -m jeff --project project-1 --work wu-1 --command '/proposal Frame bounded operator options' --json
```

Result:

```text
[error] proposal found multiple runs in work_unit wu-1. Use /run list, then /run use <run_id> or pass an explicit <run_id>.
```

Targeted integration coverage added for the single-run auto-select case and the multi-run ambiguous case.

### ambiguous run

Ambiguity is fail-closed.

- direct `/proposal` does not guess
- it does not choose the newest run
- it does not drop down to broader truth

## 5. Black-box commands executed

Live commands were run strictly one at a time.

1.

```text
python -m jeff --project project-1 --work wu-1 --command '/work list' --json
```

Observed:

- only `wu-1` exists in `project-1`

2.

```text
python -m jeff --project project-1 --work wu-1 --command '/proposal Frame bounded operator options' --json
```

Observed before and after the code change:

- fails closed because `wu-1` has multiple runs

3.

```text
python -m jeff --project project-1 --work wu-1 --run run-9 --command '/proposal What bounded rollout should execute now?' --json
```

Observed before the change:

- truth snapshot contained project/work_unit/run
- evidence support empty
- memory support empty

4.

```text
python -m jeff --project project-1 --work wu-1 --run run-1 --command '/proposal What is Jeff architecture?' --json
```

Observed before the change:

- evidence support empty even though scope-matched archive artifacts existed on `run-1`

Observed after the change:

- `evidence_support.evidence_count = 2`
- `artifact_refs = [artifact-a40760a8dd0c48d6, artifact-40af7a0f2b804520]`
- proposal output now referenced evidence bundles instead of saying only project identity was available

5.

```text
python -m jeff --project project-1 --work wu-1 --run run-1 --command '/proposal show run-1' --json
python -m jeff --project project-1 --work wu-1 --run run-1 --command '/proposal raw run-1' --json
python -m jeff --project project-1 --work wu-1 --run run-1 --command '/proposal validate run-1' --json
```

Observed:

- show/raw/validate all reflected the richer direct proposal bundle
- evidence support stayed separated from truth/governance/execution/memory sections

6.

```text
python -m jeff --project project-1 --work wu-1 --run run-1 --command '/run What bounded rollout should execute now?' --json
```

Observed:

- `/run` remained execution-support-driven
- live context stayed at truth families `project/work_unit/run`
- archive support count stayed `0` for that `/run` case
- current execution support and visible constraints still drove proposal richness there

## 6. Observed support availability before changes

### direct `/proposal` on `run-9`

- truth snapshot: present
- archive/evidence support: absent
- committed memory support: absent

Exact reasons:

- no scope-matched archive existed for `run-9`
- the startup context in the live one-shot CLI was using `InMemoryMemoryStore`
- `memory-1` was not actually present in that startup store when a new process started

### direct `/proposal` on `run-1`

- scope-matched archive artifacts did exist
- direct `/proposal` still produced empty evidence support before the fix

Exact reason:

- direct `/proposal` used purpose text `proposal support action preparation ...`
- that purpose turned on memory and compiled knowledge retrieval, but not archive retrieval
- archive support was therefore under-fetched even though it existed in the current run scope

## 7. Code changes made

### direct proposal support acquisition

Changed [jeff/interface/commands/proposal.py](jeff/interface/commands/proposal.py) so direct `/proposal` now uses:

```text
proposal support direct support action preparation <objective>
```

instead of:

```text
proposal support action preparation <objective>
```

That bounded change enables archive retrieval on the direct `/proposal` path because the context policy already recognizes `direct support` as an archive-support marker.

### tests

Extended [tests/integration/test_cli_proposal_operator_surface.py](tests/integration/test_cli_proposal_operator_surface.py) with:

- direct `/proposal` single-run auto-resolution coverage
- direct `/proposal` multi-run ambiguity coverage
- direct `/proposal` archive + committed-memory support coverage
- persisted readback coverage for the richer direct proposal bundle after restart

No new truth layer was introduced.
No memory-as-truth shortcut was introduced.
No proposal bundle flattening was introduced.

## 8. Tests run and results

Targeted suites:

```text
python -m pytest -q tests/integration/test_cli_proposal_operator_surface.py tests/unit/cognitive/test_proposal_generation.py tests/unit/cognitive/test_proposal_api.py
```

Result:

```text
27 passed in 0.78s
```

## 9. Live verification after changes

### direct `/proposal` without explicit run

Observed result in the current workspace:

- still ambiguous and fail-closed because `wu-1` currently has multiple runs
- this behavior did not change

### direct `/proposal` with explicit run on `run-1`

Observed result after the fix:

- truth snapshot still contained project/work_unit/run
- `evidence_support.evidence_count = 2`
- `evidence_support.artifact_refs = [artifact-a40760a8dd0c48d6, artifact-40af7a0f2b804520]`
- `governance_relevant_support.item_count = 2`
- `current_execution_support.item_count = 0`
- `memory_support.summary_count = 0`

The generated proposal changed materially:

- before the fix, it said only project identity/status were available
- after the fix, it proposed investigating the named evidence bundles in scope

### `/proposal show`

Observed:

- evidence support stayed visible and separated
- truth snapshot remained separate
- memory support remained visibly absent rather than hidden

### `/proposal raw`

Observed:

- raw output referenced `evidence_summary_1` and `evidence_summary_2`

### `/proposal validate`

Observed:

- parse success true
- validation success true

### `/run` comparison

Observed after the direct proposal fix:

- `/run` still used purpose `proposal support action preparation ...`
- `/run` remained execution-support-driven
- live context showed truth families `project/work_unit/run`
- archive support count remained `0` in the tested `/run` case

## 10. Whether direct `/proposal` now receives richer archive/evidence/memory support when available

### archive/evidence support

Yes.

Direct `/proposal` now receives richer archive/evidence support when scope-matched archive artifacts actually exist, as verified live on `run-1`.

### committed memory support

Yes in product code when the store is genuinely populated for the current scope, as verified by targeted integration tests.

No in the current live one-shot workspace process, because the current startup path is building an empty `InMemoryMemoryStore` and `memory-1` is not present when each new `python -m jeff` process starts.

## 11. Exact remaining gaps

1. Live committed memory support is still not demonstrable across one-shot CLI restarts in this workspace because the current startup path is using `InMemoryMemoryStore` rather than a persisted committed-memory backend.

2. Live archive support is still scope-sensitive by design. `run-1` archive artifacts are not visible to `run-9` direct proposals because archive retrieval correctly does not cross from one run into another run scope.

3. Direct `/proposal` archive retrieval is still bounded and scope-based rather than semantic-query-ranked. That is acceptable for this slice, but it means relevance quality still depends on lawful scope and bounded archive inventory.

## 12. Single next best step

Make committed memory support demonstrable in live direct `/proposal` across restarts by wiring startup to a persisted committed-memory backend in the local runtime configuration, or by adding persisted filesystem-backed memory for non-Postgres local runs if that is the intended product direction.