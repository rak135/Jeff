# OPERATOR_REAL_WORLD_VALIDATION_REPORT

## 1. Purpose

This pass tested Jeff as a real CLI operator would use it today: startup, help, scope handling, run inspection, docs research, web research, selection review, override entry, and the operator-visible evaluation summary.

What I did not test:
- direct internal Python calls to drive unreachable layers
- any new feature implementation
- memory handoff on research
- approval/reject/retry/revalidate on a run that actually routes into those states
- a real interactive TTY shell session beyond startup attempt, because this environment did not provide a live terminal

"Operator-style" in this run meant:
- using the documented entrypoint `python -m jeff`
- using Jeff's CLI/operator surface first
- using one-shot `--command` invocations when the interactive shell was unavailable
- not stitching backend objects together behind the CLI

## 2. Environment and startup path

Startup commands used:
- `python -m jeff --help`
- `python -m jeff --version`
- `python -m jeff --bootstrap-check`
- `@'/help\n/exit\n'@ | python -m jeff`

Environment and runtime assumptions:
- working directory: `C:\DATA\PROJECTS\JEFF`
- shell: PowerShell on Windows
- Jeff version: `0.1.0`
- local runtime config loaded from `jeff.runtime.toml`
- configured research adapters pointed at local Ollama endpoints
- research artifact root: `.jeff_runtime/artifacts/research`

Local models/runtime availability:
- yes, effectively available for this run
- evidence: both `/research docs ...` and `/research web ...` completed through the CLI and persisted artifacts

Startup path result:
- `--help`, `--version`, and `--bootstrap-check` worked cleanly
- bootstrap clearly reported persisted runtime loading, runtime home, config loading, and research artifact root readiness
- starting `python -m jeff` without a real terminal did not open the interactive shell; Jeff reported `No interactive terminal detected. Use --command for one-shot mode.`
- practical consequence: in this environment the lawful operator surface was one-shot mode, not a sticky shell

## 3. Exact command log

### Startup and orientation
- `python -m jeff --help`
- `python -m jeff --version`
- `python -m jeff --bootstrap-check`
- `@'/help\n/exit\n'@ | python -m jeff`
- `python -m jeff --command "/help"`
- `python -m jeff --command "/project list"`
- `python -m jeff --command "/scope show"`
- `python -m jeff --project project-1 --command "/work list"`
- `python -m jeff --project project-1 --work wu-1 --command "/run list"`
- `python -m jeff --command "/project use project-1" --command "/scope show"`
- `python -m jeff --project project-1 --command "/work use wu-1" --command "/scope show"`
- `python -m jeff --project project-1 --work wu-1 --run run-1 --command "/run use run-1" --command "/scope show"`
- `python -m jeff --project project-1 --work wu-1 --command "/inspect" --command "/scope show"`
- `python -m jeff --project project-1 --work wu-1 --run run-1 --command "/show"`
- `python -m jeff --project project-1 --work wu-1 --run run-1 --command "/show" --json`
- `python -m jeff --project project-1 --work wu-1 --run run-1 --command "/trace"`
- `python -m jeff --project project-1 --work wu-1 --run run-1 --command "/lifecycle"`
- `python -m jeff --project project-1 --work wu-1 --run run-1 --command "/scope clear" --command "/scope show"`

### Research
- `python --% -m jeff --project project-1 --work wu-1 --run run-1 --command "/mode debug" --command "/research docs \"What does Jeff say about startup path, persisted runtime, and operator entry?\" README.md v1_doc/CLI_V1_OPERATOR_SURFACE.md"`
- `python --% -m jeff --project project-1 --work wu-1 --run run-1 --command "/research docs \"What does Jeff say about startup?\" README.md does-not-exist.md"`
- `python --% -m jeff --project project-1 --work wu-1 --run run-1 --command "/mode debug" --command "/research web \"What official OpenAI docs are relevant to the Responses API?\" \"OpenAI Responses API docs\" \"OpenAI API responses guide\""`
- `python --% -m jeff --project project-1 --work wu-1 --run run-1 --command "/research web \"What official OpenAI docs are relevant to the Responses API?\""`

### Selection / override / downstream review
- `python -m jeff --project project-1 --work wu-1 --run run-1 --command "/selection show"`
- `python --% -m jeff --project project-1 --work wu-1 --run run-1 --command "/selection override proposal-1 --why \"Operator validation: restore original bounded path\""`
- `python --% -m jeff --project project-1 --work wu-1 --run run-1 --command "/selection override proposal-2 --why \"Operator validation: switch to alternate bounded path\""`
- `python --% -m jeff --project project-1 --work wu-1 --run run-1 --command "/selection override proposal-999 --why \"Operator validation: invalid proposal\""`
- `python -m jeff --project project-1 --work wu-1 --run run-1 --command "/selection show"`
- `python -m jeff --project project-1 --work wu-1 --run run-1 --command "/show"`

### Conditional / evaluation-adjacent operator paths
- `python -m jeff --project project-1 --work wu-1 --command "/approve"`
- `python -m jeff --project project-1 --work wu-1 --command "/retry"`
- `python -m jeff --project project-1 --work wu-1 --command "/revalidate"`
- `python -m jeff --project project-1 --work wu-1 --run run-1 --command "/approve"`
- `python -m jeff --project project-1 --work wu-1 --run run-1 --command "/reject"`
- `python -m jeff --project project-1 --work wu-1 --run run-1 --command "/retry"`
- `python -m jeff --project project-1 --work wu-1 --run run-1 --command "/revalidate"`

## 4. Results by layer

### Research

Reachable through CLI? `yes`

What worked:
- `/research docs ...` worked with a bounded local input set and produced a readable result.
- `/research web ...` worked with bounded queries and produced a readable result.
- debug mode was useful; Jeff exposed adapter, citation remap, provenance validation, projection, and artifact-save steps.
- both research paths printed a concrete `artifact_id` and `artifact_locator`.
- artifacts were actually persisted under `.jeff_runtime/artifacts/research/`.
- invalid input handling was good:
  - docs mode correctly rejected a missing file with `error_code=missing_input_paths`
  - web mode correctly rejected a missing query list

What failed:
- nothing hard-failed in the single-operator research path

What was confusing:
- PowerShell one-shot quoting is fragile for commands with embedded quoted questions. In practice I needed `python --% -m jeff ...` to get the command through intact.
- web output quality was shallow. Jeff discovered five web sources but produced only one finding, with weak metadata on the stored artifact.
- the operator has limited source-shaping control beyond raw queries.

What is implemented in backend but not honestly operator-available yet:
- no major research backend/operator mismatch was proven in this pass

### Proposal

Reachable through CLI? `partial`

What worked:
- proposal summaries are visible inside `/show`, `/inspect`, and `/selection show`
- the existing demo run exposes two retained proposals with IDs, type, assumptions count, risk count, and summary text

What failed:
- no lawful CLI path was found that generates a fresh proposal result from operator input
- no dedicated `/proposal ...` command was exposed by `/help`

What was confusing:
- `/inspect` looks like a natural place to drive work, but in practice it auto-selected the existing demo run and showed already-computed proposal support
- the operator can see proposal summaries, but not an obvious proposal-stage object they can explicitly request, rerun, or inspect in depth

What is implemented in backend but not honestly operator-available yet:
- backend proposal implementation exists under `jeff/cognitive/proposal/`
- I did not find an honest CLI path that invokes that proposal layer to create fresh output during this run
- operator reality today is proposal visibility-through-demo-support, not proposal generation-as-a-CLI-workflow

### Selection / Override / Review chain

Reachable through CLI? `partial`

What worked:
- `/selection show` is a strong review surface
- it truthfully shows:
  - original selection disposition and selected proposal
  - retained proposal set
  - operator override as a separate object
  - resolved effective choice
  - downstream action formation
  - downstream governance handoff
- valid overrides worked when run as a single operator:
  - override to `proposal-1`
  - override to `proposal-2`
- override receipts were explicit and truthful:
  - `original_selection_unchanged=True`
  - `override_is_separate_support=True`
  - `execution_started=False`
- invalid override was fail-closed and specific:
  - `chosen_proposal_id must come from the original considered proposal set`

What failed:
- the broader `/show` run view does not surface the effective override result
- after overriding the effective proposal to `proposal-2`, `/show` still reported `selected_proposal_id=proposal-1`
- this makes the general run view less truthful than `/selection show`

What was confusing:
- the initial demo state already contained an override to `proposal-2`; that is useful for demo coverage but confusing if an operator expects a clean baseline
- Windows one-shot override entry with `--why "..."` is awkward enough that PowerShell stop-parsing (`--%`) was needed for reliable execution

What is implemented in backend but not honestly operator-available yet:
- selection review and override are operator-available
- fresh hybrid/deterministic selection generation was not lawfully triggerable from the CLI in this pass
- operator reality today is review of existing selection output plus override, not a full operator-driven selection generation flow

### Evaluation

Reachable through CLI? `partial`

What worked:
- evaluation is visible in `/inspect` and `/show`
- the operator can see:
  - `evaluation_verdict=acceptable`
  - evidence posture
  - recommended next step
  - evaluation reason summary
- `/trace` and `/lifecycle` show that the demo flow reached evaluation and completed

What failed:
- no dedicated evaluation command was exposed in `/help`
- no lawful CLI path was found to trigger or rerun evaluation directly

What was confusing:
- conditional commands exist, but on this run they were not actionable:
  - without run scope they just say scope is missing
  - with `run-1` they say the command is not currently available because `routed_outcome is none`
- that does not help the operator understand how to reach an evaluation-control path, if one exists

What is implemented in backend but not honestly operator-available yet:
- backend evaluation implementation exists at `jeff/cognitive/evaluation.py`
- operator visibility exists only as a rendered summary on the demo run
- fresh evaluation as a first-class operator workflow was not honestly reachable in this pass

## 5. Truthfulness assessment

Overall judgment: `mixed but mostly honest on the deep review surfaces`

What Jeff preserves well:
- original selection vs override: preserved well in `/selection show` and override receipts
- action formed vs governance evaluated: preserved as separate lines in the selection review surface
- governance evaluated vs execution performed: preserved; override receipts explicitly state `execution_started=False`
- real failure vs missing data vs unsupported path: often good, especially in research errors and invalid override validation

Where truthfulness breaks down:
- `/show` flattens the run back to the original `selected_proposal_id` and does not expose the resolved effective proposal after override
- the initial demo run already having an override is not wrong, but it is easy to misread as the current baseline truth unless the operator explicitly opens `/selection show`
- conditional command failures are technically truthful but operationally under-explanatory

## 6. Operator-friendliness assessment

- startup: `3/5`
  - clear docs, clear bootstrap-check, clear one-shot help
  - loses points because the interactive shell is unavailable without a real TTY and one-shot scope is not sticky across invocations

- research docs: `4/5`
  - worked end-to-end, printed useful artifacts, and handled missing files well
  - loses points for Windows quoting friction

- research web: `3/5`
  - worked end-to-end and persisted an artifact
  - loses points because the result was shallow relative to the five discovered sources and metadata quality was thin

- proposal visibility: `2/5`
  - proposal summaries are visible
  - loses heavily because no honest operator path was found to generate or explicitly inspect proposal-stage output as its own workflow

- selection review: `4/5`
  - `/selection show` is the strongest operator surface in the product right now
  - loses points because `/show` is not override-aware and the baseline demo already contains an override

- override entry: `3/5`
  - the actual override workflow is truthful and fail-closed
  - loses points because one-shot quoting on PowerShell is clumsy and easy to get wrong

- overall CLI ergonomics: `3/5`
  - good slash-command discoverability, decent scope hints, useful debug traces
  - loses points because too much operator knowledge is still implicit: TTY expectation, sticky scope only within a live shell, quoting traps, and missing top-level proposal/evaluation commands

## 7. Hard failures and gaps

### True bugs

- `/show` is not truthfully downstream-aware after selection override. Effective choice can be `proposal-2` while `/show` still reports `selected_proposal_id=proposal-1`.
- Jeff is sensitive to concurrent multi-process access to the same persisted selection review on Windows. Running multiple Jeff processes against the same run produced `Errno 13` / `WinError 32` on `.jeff_runtime/reviews/selection_reviews/run-1.json.tmp`.

### Missing operator surfaces

- no honest CLI path found for fresh proposal generation
- no dedicated CLI proposal inspect surface
- no honest CLI path found for fresh evaluation execution or rerun
- no dedicated CLI evaluation inspect surface
- no obvious CLI path found for generating fresh selection behavior rather than reviewing the preloaded demo run

### Confusing UX

- one-shot quoted commands are awkward in PowerShell; `--%` was effectively required for reliable `/research ...` and `/selection override ... --why "..."` usage
- session scope does not persist across separate one-shot invocations, so operators either need a real shell or repeated `--project/--work/--run` flags
- `/inspect` sounds generative, but here it only auto-selected and displayed the existing demo run
- the demo run already containing an override muddies the baseline story unless the operator inspects carefully

### Backend-implemented but operator-inaccessible capabilities

- proposal backend exists under `jeff/cognitive/proposal/`, but proposal generation was not lawfully operator-reachable in this pass
- evaluation backend exists at `jeff/cognitive/evaluation.py`, but evaluation is operator-visible only as a summary, not a first-class executable/reviewable CLI stage

### Minimal fixes made during operator validation

- none

## 8. Recommended next fixes

Top 3 operator-facing fixes:
1. Add a lawful CLI path for fresh run/proposal generation and make it obvious from `/help`.
2. Make `/show` reflect resolved downstream truth, including override presence and effective proposal, instead of only original selection truth.
3. Reduce one-shot quoting pain on Windows:
   - document `--%` explicitly for PowerShell
   - or add a safer argument form for quoted slash commands
   - or allow non-TTY batch input without requiring nested shell quoting

Top 3 backend/flow fixes blocking operator usefulness:
1. Make persisted review writes safe under concurrent CLI access on Windows.
2. Expose fresh selection and evaluation execution through the operator surface instead of only surfacing precomputed demo outputs.
3. Improve conditional-command diagnostics so `approve/reject/retry/revalidate` explain what routed state is required and how an operator can reach it.

## 9. Final verdict

Jeff is usable today as a real operator tool for:
- startup/bootstrap verification
- workspace and run inspection
- docs research
- web research
- deep selection review
- lawful selection override recording

Jeff is not yet usable as a full real-world operator tool for:
- fresh proposal generation
- fresh selection generation
- first-class evaluation control
- clear end-to-end operator execution beyond the preloaded demo flow

The smooth parts are real: help, bootstrap, run inspection, research artifacts, and `/selection show`.

The fragile or incomplete parts are also real: Windows one-shot quoting, missing proposal/evaluation operator surfaces, `/show` not reflecting override-resolved truth, and heavy reliance on a precomputed demo run instead of a fully operator-driven flow.
