# PROPOSAL_BLACK_BOX_AND_TUNING_REPORT.md

## 1. Executive summary

Proposal was already real and persisted, but the black-box pass found two operator-visible weaknesses:

- single-option outputs often leaned on generic scarcity/fallback phrasing even when the objective and scope supported more specific content
- `/run` used proposal internally but did not persist an operator-inspectable proposal record, so `/proposal show <run_id>` failed after `/run`

I implemented two bounded proposal-local improvements plus one `/run`-surface proposal input fix:

- tightened the proposal prompt/repair prompt to prefer objective- and scope-grounded detail over generic fallback text
- added shared proposal-record identity helpers and persisted proposal operator records for `/run` proposal attempts
- passed explicit `/run`-family bounded-validation constraints into proposal generation so generic `/run` wording still has a lawful candidate path

After re-test, direct `/proposal` quality improved, `/proposal show run-<id>` works after `/run`, and both specific and generic `/run` objectives completed again. One honest live initial validation failure occurred during `/run` re-test and was recovered by the built-in single repair pass.

## 2. Runtime constraint handling

- Confirmed: all live Ollama-backed `/proposal` and `/run` commands were executed strictly one at a time.
- No overlapping live provider traffic was launched.
- Parallel shell use was limited to non-live discovery, file reads, and local test runs.

## 3. Black-box commands executed

### Discovery and scope sanity

- `python -m jeff --bootstrap-check`
- `python -m jeff --command "/help"`
- `python -m jeff --command "/scope show"`
- `python -m jeff --command "/project list"`
- `python -m jeff --project general_research --command "/work list"`
- `python -m jeff --project project-1 --command "/work list"`
- `python -m jeff --project project-1 --work wu-1 --command "/run list"`

### Phase 1 live proposal and `/run` pass

| Exact command | Live Ollama | Succeeded | proposal_count | Selected option type(s) | Repair used | Quality / failure |
|---|---:|---:|---:|---|---:|---|
| `python -m jeff --project project-1 --work wu-1 --command "/proposal Review README quickstart wording and propose one bounded improvement step." --json` | no | no | - | - | no | preflight failure: `proposal found multiple runs in work_unit wu-1. Use /run list, then /run use <run_id> or pass an explicit <run_id>.` |
| `python -m jeff --project project-1 --work wu-1 --run run-2 --command "/proposal Review README quickstart wording and propose one bounded improvement step." --json` | yes | yes | 1 | `investigate` | no | acceptable but fallback-heavy; generic scarcity and sparse fields |
| `python -m jeff --project project-1 --work wu-1 --run run-2 --command "/proposal show proposal-record-run-2-20260420T162821.831608+0000-review-readme-quickstart-wording" --json` | no | yes | 1 | `investigate` | no | persisted inspection worked |
| `python -m jeff --project project-1 --work wu-1 --run run-2 --command "/proposal raw proposal-record-run-2-20260420T162821.831608+0000-review-readme-quickstart-wording"` | no | yes | 1 | `investigate` | no | raw output showed heavy fallback markers |
| `python -m jeff --project project-1 --work wu-1 --run run-2 --command "/proposal validate proposal-record-run-2-20260420T162821.831608+0000-review-readme-quickstart-wording" --json` | no | yes | 1 | `investigate` | no | parse/validation passed |
| `python -m jeff --project project-1 --work wu-1 --run run-2 --command "/proposal Update README.md quickstart to add one sentence clarifying that /project use, /work use, and /run use are process-local." --json` | yes | yes | 1 | `direct_action` | no | acceptable but scarcity-generic |
| `python -m jeff --project project-1 --work wu-1 --run run-2 --command "/proposal Investigate why direct proposal use in wu-1 required explicit run scope before it could resolve." --json` | yes | yes | 1 | `investigate` | no | content-rich relative to other runs |
| `python -m jeff --project project-1 --work wu-1 --run run-2 --command "/proposal Help me with Jeff." --json` | yes | yes | 0 | none | no | honest zero-option scarcity |
| `python -m jeff --project project-1 --work wu-1 --run run-2 --command "/proposal Improve the proposal system, but I have not decided whether the priority is prompt quality, parsing, or validation." --json` | yes | yes | 1 | `clarify` | no | acceptable |
| `python -m jeff --project project-1 --work wu-1 --command "/run Run the bounded validation path and surface failures truthfully." --json` | yes | yes | 1 internal | `direct_action` selected | no | healthy `/run` completion |
| `python -m jeff --project project-1 --work wu-1 --run run-3 --command "/proposal show run-3" --json` | no | no | - | - | no | operator inconsistency: `no persisted proposal records are available for run run-3` |
| `python -m jeff --project project-1 --work wu-1 --run run-2 --command "/proposal Investigate why the literal labels PROPOSAL_COUNT, OPTION_1_TYPE, and SCARCITY_REASON appear in proposal diagnostics and propose one bounded fix." --json` | yes | yes | 1 | `investigate` | no | parse-stress attempt still succeeded; slow but valid |
| `python -m jeff --bootstrap-check` then `python -m jeff --project project-1 --work wu-1 --run run-2 --command "/proposal show proposal-record-run-2-20260420T162901.698877+0000-update-readme-md-quickstart-to-a" --json` | no | yes | 1 | `direct_action` | no | persisted readback across fresh processes succeeded |

## 4. Observed live proposal behaviors

- `direct_action`: reachable for concrete edit-shaped objectives, but early outputs were still terse and generic.
- `investigate`: common fallback for bounded objectives lacking explicit current-state detail.
- `clarify`: worked correctly for intentionally unresolved priority wording.
- zero-option scarcity: honest and available for vague objectives.
- content richness was inconsistent. The best output in Phase 1 was the explicit run-scope investigation. The weakest passed output was the first README-review proposal, which leaned on generic scarcity and empty assumptions/risks/constraints.

## 5. Observed live `/run` behaviors

- `/run "Run the bounded validation path and surface failures truthfully."` completed successfully before tuning and again after tuning.
- before the fix, `/run` proposal output was visible only in the run summary; `/proposal show <run_id>` could not inspect it because no operator record was persisted.
- after the persistence fix, `/proposal show run-5` and `/proposal show run-7` both worked and exposed the persisted proposal attempts and artifacts.

## 6. Honest failures encountered

- honest operator preflight failure:
  - `/proposal ...` without explicit `--run` inside `project-1/wu-1` failed before model invocation because multiple runs existed
- honest black-box inconsistency:
  - `/proposal show run-3` failed because `/run` had not persisted a proposal operator record
- honest live initial validation failure after tuning:
  - `/run "What bounded rollout should execute now?"` on `run-7` recorded an initial proposal validation failure: `option 1: why_now contains forbidden authority language: start_authority`
  - the built-in single repair pass corrected it and the run completed successfully

## 7. Whether `/proposal repair` was live-tested

No.

- During Phase 1, no honest terminal live failed proposal record existed, so `/proposal repair` could not be exercised honestly.
- During post-change re-test, `run-7` did hit an honest initial validation failure, but it was repaired automatically inside the existing single repair pass and did not leave a terminal failed record for the manual `/proposal repair` CLI.
- I did not fabricate a provider failure or force a fake failed record just to claim `/proposal repair` live coverage.

## 8. Proposal quality diagnosis

### Top weaknesses

1. Acceptable but fallback-heavy
- single-option outputs frequently used generic scarcity wording and empty fallback fields even when the objective/scope justified more specific statements

2. `/run` proposal inspectability gap
- `/run` relied on proposal but did not persist proposal operator records, breaking `/proposal show <run_id>` after real `/run` execution

3. Generic `/run` wording was prompt-sensitive
- after the prompt tune, `/run "What bounded rollout should execute now?"` briefly regressed to zero options until the bounded validation family was injected as explicit proposal input

### Classification of observed outputs

- content-rich: explicit run-scope investigation proposal; post-change direct `/proposal` README review; post-change generic `/run` after final fix
- acceptable but fallback-heavy: initial README review proposal; early single-option direct-action outputs
- too generic: initial scarcity reasoning for single-option proposals
- scarcity-overused: yes, before tuning
- authority-risky: yes, once, in the initial `run-7` proposal `WHY_NOW`
- parser/validator brittle: no hard brittleness observed live; parser-stress attempt stayed valid

## 9. Code areas inspected

- `PROMPTS/proposal/STEP1_GENERATION.md`
- `PROMPTS/proposal/STEP1_REPAIR.md`
- `jeff/cognitive/proposal/api.py`
- `jeff/cognitive/proposal/generation.py`
- `jeff/cognitive/proposal/parsing.py`
- `jeff/cognitive/proposal/validation.py`
- `jeff/cognitive/proposal/operator_records.py`
- `jeff/interface/commands/proposal.py`
- `jeff/interface/commands/scope.py`
- `jeff/interface/json_views.py`
- `jeff/runtime_persistence.py`

## 10. Changes implemented, if any

- prompt tuning:
  - generation and repair prompts now explicitly tell the model to ground single-option scarcity and option detail in the objective, scope, truth snapshot, and constraints before falling back to generic placeholders
  - direct-action wording guidance now asks for a concrete bounded target instead of vague next-step phrasing
- proposal record identity helpers:
  - added shared helpers for proposal record timestamps and ids in `jeff.cognitive.proposal.operator_records`
- `/run` proposal persistence:
  - `/run` now saves proposal operator records for its proposal attempts, including preserved attempt artifacts
- `/run` proposal constraints:
  - `/run` now passes explicit bounded-validation-family constraints into proposal generation so generic rollout wording still has the lawful candidate path surfaced
- tests:
  - added prompt-contract assertions
  - added integration coverage proving `/run` now leaves an inspectable proposal record

## 11. Tests run and results

- `python -m pytest -q tests/unit/cognitive/test_proposal_prompt_files.py tests/unit/cognitive/test_proposal_generation.py tests/integration/test_cli_proposal_operator_surface.py tests/integration/test_cli_run_live_context_execution.py`
  - result: `29 passed`

## 12. Re-test results after changes

### Direct `/proposal`

- command:
  - `python -m jeff --project project-1 --work wu-1 --run run-2 --command "/proposal Review README quickstart wording and propose one bounded improvement step." --json`
- result:
  - success
  - `proposal_count=1`
  - type moved from `investigate` to `direct_action`
  - assumptions and support refs became more grounded
  - scarcity reason became specific: lack of a known target area in README, rather than generic one-path phrasing

### `/run` specific objective

- command:
  - `python -m jeff --project project-1 --work wu-1 --command "/run Run the bounded validation path and surface failures truthfully." --json`
- result:
  - success
  - `run_id=run-5`
  - internal proposal remained `direct_action`
  - `/proposal show run-5` succeeded and showed the persisted operator record

### `/run` generic objective

- intermediate result after first tune:
  - `run-4` and `run-6` failed before execution with `proposal_count=0`
  - that exposed the need to inject explicit `/run`-family constraint support
- final result after `/run` constraint fix:
  - command:
    - `python -m jeff --project project-1 --work wu-1 --command "/run What bounded rollout should execute now?" --json`
  - result:
    - success on `run-7`
    - internal `proposal_count=1`
    - selected type `direct_action`
    - `repair_used=true`
    - initial failure stage was honest validation failure for forbidden authority language in `WHY_NOW`
    - repaired output passed and `/proposal show run-7` exposed both attempts and persisted artifacts

## 13. Final judgment

Proposal is robust enough for bounded operator use now, with two important caveats:

- it is materially healthier after tuning and now supports real operator inspection after `/run`
- it is still prompt-sensitive around generic objectives, especially for how assumptions, risks, blockers, and constraints are filled in when support is thin

What is still weak:

- some successful single-option outputs still leave risks/blockers/constraints empty when a stronger bounded statement would be possible
- generic `/run` wording now works again, but it needed explicit command-family constraints and still triggered one live repair-worthy authority leak before settling
- manual `/proposal repair` still has no honest live CLI proof because no terminal live failed proposal record was naturally produced

Single next best proposal improvement:

- feed proposal generation a small structured support item describing the active bounded action family and current executable plan, rather than relying on prompt text and constraint prose alone to carry that context.
