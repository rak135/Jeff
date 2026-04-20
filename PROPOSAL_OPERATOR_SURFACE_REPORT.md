# Proposal Operator Surface Report

## 1. Scope

This slice added a bounded manual Proposal operator surface to the Jeff CLI without creating a second control plane and without weakening Jeff's existing truth, governance, or fail-closed rules.

Implemented commands:

- `/proposal "<objective>"`
- `/proposal show [run_id or proposal_id]`
- `/proposal raw [run_id or proposal_id]`
- `/proposal validate [run_id or proposal_id]`
- `/proposal repair [run_id or proposal_id]`

The implemented surface is inspect/debug only. It does not select, approve, authorize, mark ready, execute, or mutate truth.

## 2. What Changed

- Added a durable proposal operator record model that preserves initial attempt state, optional repair attempt state, final status, final failure details, and final proposal result when available.
- Extended persisted runtime storage so proposal records survive restart and proposal artifacts remain inspectable from disk.
- Reused the existing proposal generation, parsing, validation, and single repair-pass pipeline rather than introducing separate proposal logic for the CLI.
- Added explicit JSON and text render surfaces for proposal record, raw output, and validation replay.
- Added command routing and resolution logic for current-run and historical proposal inspection.
- Kept proposal repair append-only by creating a new linked record with `source_proposal_id` instead of mutating the original failed record.

## 3. Persistence Model

Proposal operator persistence now uses:

- record files under `.jeff_runtime/reviews/proposals/`
- artifacts under `.jeff_runtime/artifacts/proposals/<proposal_id>/`

Persisted operator data keeps these distinctions separate:

- raw provider output
- parsed intermediate output
- validation issues
- final proposal result
- terminal failure stage and error
- initial attempt versus repair attempt

This allows restart-safe inspection without turning proposal artifacts into truth.

## 4. Main Files

Most relevant implementation files:

- `jeff/cognitive/proposal/operator_records.py`
- `jeff/cognitive/proposal/api.py`
- `jeff/runtime_persistence.py`
- `jeff/interface/commands/proposal.py`
- `jeff/interface/commands/registry.py`
- `jeff/interface/json_views.py`
- `jeff/interface/render.py`
- `tests/integration/test_cli_proposal_operator_surface.py`
- `tests/unit/interface/test_cli_usability.py`
- `tests/smoke/test_cli_entry_smoke.py`

## 5. JSON / Operator Contract

The proposal CLI now exposes truthful separation between:

- truth: proposal id, scope, objective, created_at, optional source proposal linkage
- derived status: success or failure, repair attempted, repair used, validation outcome, terminal failure stage
- proposal summary: proposal count, retained options, scarcity reason, summary source
- attempts: initial and optional repair attempt metadata and artifact refs
- artifacts: persisted record ref plus raw/parsed refs

`/proposal validate` replays parse and validation over the persisted final raw attempt rather than trusting previously rendered summaries.

## 6. Test Validation

Targeted automated validation completed.

- Proposal operator surface tests: 33 passed
- Broader persistence and adjacent CLI tests: 40 passed
- Total validated in this slice: 73 passed

Coverage included:

- direct proposal success
- parse failure persistence
- validation failure persistence
- repair success
- repair failure
- restart inspection
- missing scope handling
- ambiguous run-id handling
- help surface updates

## 7. Live Black-Box Validation

Runtime used for live verification:

- config: `jeff.runtime.toml`
- proposal adapter: `ollama_default`
- model: `gemma4:31b-cloud`
- base URL: `http://127.0.0.1:11434`

Successful live command sequence:

```text
python -m jeff --project project-1 --work wu-1 --run run-2 --command '/proposal Generate bounded operator options for validating the new proposal inspection surface.' --command '/proposal show' --command '/proposal raw' --command '/proposal validate'
```

Observed live result:

- a persisted proposal record was created successfully
- proposal status was `success`
- final validation outcome was `passed`
- repair was not used
- the live provider returned a lawful zero-option proposal with a scarcity reason
- raw output, parsed output, and record metadata were persisted under `.jeff_runtime`

Fresh-process restart verification also succeeded:

```text
python -m jeff --project project-1 --work wu-1 --run run-2 --command '/proposal show <proposal_id>' --command '/proposal raw <proposal_id>' --command '/proposal validate <proposal_id>'
```

Machine-readable live verification also succeeded:

```text
python -m jeff --project project-1 --work wu-1 --run run-2 --command '/proposal show <proposal_id>' --json
```

## 8. Direct Answer

Does live direct `/proposal` work?

Yes.

It worked against the configured live Ollama runtime and produced a truthful persisted proposal record that remained inspectable after restart.

Did live `/proposal repair` get black-box verified against a real failed provider output?

No.

The live provider did not honestly produce a parse or validation failure during black-box verification. Even provocative objectives still returned lawful zero-option scarcity outputs, so there was no real failed live proposal record to repair without fabricating a failure.

## 9. Remaining Gap

The remaining verification gap is narrow and explicit:

- automated repair behavior is covered by tests
- persisted repair readback is covered by tests
- live direct `/proposal` is verified
- live restart inspection is verified
- live JSON inspection is verified
- live `/proposal repair` on an honest real-provider failed proposal was not verified because no such live failure occurred

## 10. Outcome

The bounded manual Proposal CLI/operator surface is now implemented as real product code, persisted durably, covered by targeted tests, and verified live for direct proposal generation plus restart-safe inspection.