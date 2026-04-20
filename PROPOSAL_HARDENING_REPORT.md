# Proposal Hardening Report

## 1. What changed

- Rewrote Proposal Step 1 generation to follow the stronger research-style contract: exact required line structure, exact fallback markers, explicit anti-authority guidance, and built-in self-check instructions.
- Removed proposal-side semantic dependence on `NONE` and aligned parsing plus validation to the new canonical fallback markers.
- Added one bounded correction-guided repair pass for proposal generation on parse or validation failure.
- Updated targeted unit and integration fixtures to the new contract and verified the real `/run` path against the configured live runtime.

## 2. Files changed

- `PROMPTS/proposal/STEP1_GENERATION.md`
- `PROMPTS/proposal/STEP1_REPAIR.md`
- `jeff/cognitive/proposal/parsing.py`
- `jeff/cognitive/proposal/validation.py`
- `jeff/cognitive/proposal/generation.py`
- `jeff/cognitive/proposal/api.py`
- `tests/unit/cognitive/test_proposal_parsing.py`
- `tests/unit/cognitive/test_proposal_validation.py`
- `tests/unit/cognitive/test_proposal_generation.py`
- `tests/unit/cognitive/test_proposal_api.py`
- `tests/integration/test_cli_run_live_context_execution.py`

## 3. Prompt contract changes

- `STEP1_GENERATION.md` now forbids `NONE` anywhere in proposal output.
- `SCARCITY_REASON` always exists. For `PROPOSAL_COUNT` 2 or 3 the canonical fallback is:
  `No additional scarcity explanation identified from the provided support.`
- Canonical fallback markers now exist for assumptions, risks, constraints, blockers, feasibility, reversibility, and support refs.
- `direct_action` is explicitly framed as a candidate path only, never permission, readiness, approval, selection, or start authority.
- The prompt now explicitly forbids winner language, selection language, readiness/start language, and authority leakage.
- The prompt now includes an internal completeness/self-check and canonical 0-option plus 1-option examples.

## 4. Parser changes

- Proposal parsing is now strict ordered line parsing rather than loose field collection.
- The parser enforces:
  - `PROPOSAL_COUNT` first
  - `SCARCITY_REASON` second
  - exact `OPTION_n_*` order per option block
  - exact line count per proposal count
- Legacy `NONE` now fails explicitly with a parse error.
- Canonical fallback markers are parsed into internal `None` or empty tuples where appropriate.
- The parser keeps fail-closed behavior and surfaces specific errors for missing top-level fields, malformed lines, and field-order drift.

## 5. Validator changes

- Removed the prompt-vs-validator contradiction around assumptions, risks, constraints, and blockers.
- Canonical absence markers now parse cleanly and validate without being treated as missing semantic content.
- Validation remains fail-closed for:
  - invalid proposal counts
  - missing scarcity reason when proposal count is 0 or 1
  - duplicate / materially padded options
  - real authority leakage
- Authority leakage detection is narrower now. It targets approval, permission, authorization, winner/selection outcome language, and readiness/start-authority phrases rather than broad blanket matches like any use of `execution` or `governance`.

## 6. Repair-pass behavior

- Proposal generation now gets exactly one repair pass.
- Flow:
  1. primary proposal generation
  2. parse + validate
  3. if parse or validation fails, build a correction-guided repair prompt with failure stage, failure reason, validation issues, and prior output
  4. one repair generation attempt
  5. parse + validate again
  6. if repair still fails, return the final failure stage and error while preserving the initial failure details
- No hidden loops were added.
- Repair attempts are inspectable through the preserved initial failure artifacts on pipeline success or failure.

## 7. Tests run and results

Targeted proposal unit suite:

```text
pytest tests/unit/cognitive/test_proposal_parsing.py tests/unit/cognitive/test_proposal_validation.py tests/unit/cognitive/test_proposal_generation.py tests/unit/cognitive/test_proposal_api.py -q
33 passed in 0.31s
```

Wider proposal + `/run` targeted suite:

```text
pytest tests/unit/cognitive/test_proposal_parsing.py tests/unit/cognitive/test_proposal_validation.py tests/unit/cognitive/test_proposal_generation.py tests/unit/cognitive/test_proposal_api.py tests/unit/cognitive/proposal/test_proposal_generation_bridge.py tests/integration/test_cli_run_live_context_execution.py -q
51 passed in 28.16s
```

## 8. Real `/run` command(s) executed

Scope discovery commands:

```text
python -m jeff --command "/project list" --json
```

Observed result:
- `project-1` exists and is active.

```text
python -m jeff --project project-1 --command "/work list" --json
```

Observed result:
- `wu-1` exists and is open.

Live `/run` verification command:

```text
python -c "import sys; from jeff.__main__ import main; sys.argv=['jeff','--project','project-1','--work','wu-1','--command','/run validate_repo_local_path','--json']; main()"
```

Observed result:
- `/run` completed successfully.
- Flow family: `bounded_proposal_selection_execution`
- Active stage at completion: `evaluation`
- Proposal succeeded and produced one retained option.
- Selection succeeded with `selected_proposal_id=proposal-1`.
- Governance outcome: `allowed_now`
- Execution succeeded and ran the bounded smoke pytest plan.
- Execution command id: `smoke_quickstart_validation`
- Execution exit code: `0`
- Evaluation verdict: `acceptable`
- Run lifecycle state: `completed`
- Persisted run id: `run-2`

## 9. Whether proposal now works live

Yes.

Under the live configured runtime in `jeff.runtime.toml` (`proposal = "ollama_default"`), proposal generation now passes well enough for `/run` to complete end to end.

The observed live proposal summary for `run-2` was:

- serious option count: `1`
- proposal type: `direct_action`
- selected proposal id: `proposal-1`
- summary: `Perform the validation of the repository local path as specified by the trigger.`

## 10. If not, the exact remaining failure and where it occurs

Not applicable for the final live verification.

The earlier live history still contains a prior failed run (`run-1`) that died at proposal validation before this hardening slice, but the final black-box verification (`run-2`) completed successfully.

## 11. Remaining risks / next recommended step

- Live success is now proven, but the successful provider output still used zero assumptions, zero risks, zero constraints, and zero blockers after canonical fallback normalization. That is contractually aligned now, but it remains a quality risk if downstream stages need richer proposal content.
- The shell-level Windows quoting around `--command "/run ..."` was unreliable in PowerShell for this environment, so live verification used Jeff's real CLI entrypoint with explicit `sys.argv` to ensure the `/run` command string arrived intact.
- Next recommended step: add one or two acceptance-style live-provider tests that assert proposal-stage success without relying on manual runtime inspection, while keeping them optional or environment-gated.