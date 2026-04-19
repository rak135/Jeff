# Real CLI Validation Report

## Audit method
- Date of audit: 2026-04-19.
- I started as a normal operator, not a repo author: README first, then `python -m jeff --help`, then actual CLI commands.
- I did not start by reading deep implementation code. The first pass was black-box and command-driven.
- After the operator pass, I inspected startup, interface, routing, persistence, research, selection override, request-entry, orchestrator, and relevant tests to explain what I had already observed.
- I did not delete or reset `.jeff_runtime`. That means the report reflects Jeff as an operator would actually encounter it in this repo, including persisted state and state drift from prior use.
- Limitation: I could not validate the real interactive shell loop in a true TTY because this environment is non-interactive. I did validate startup behavior for `python -m jeff` in non-TTY mode and then exercised the supported one-shot surface heavily.

## Commands and scenarios tested
- `python -m jeff --help`
  Outcome: worked. Startup help is clear about `python -m jeff`, `--command`, `--bootstrap-check`, scope flags, and `--json`.
- `python -m jeff --bootstrap-check`
  Outcome: worked. Reported persisted runtime, local runtime config, research adapter, and artifact root.
- `python -m jeff`
  Outcome: did not enter shell here. Printed help plus `No interactive terminal detected. Use --command for one-shot mode.`
- `python -m jeff --command "/help"`
  Outcome: worked, but help text is stale and says startup uses an explicit in-memory demo state.
- `python -m jeff --command "/project list"`
  Outcome: worked. Projects were discoverable.
- `python -m jeff --command "/inspect"`
  Outcome: failed clearly because no project scope was set.
- `python -m jeff --command "/trace"`
  Outcome: failed clearly because no run or work scope was set.
- `python -m jeff --command "/project use project-1"`
  Outcome: reported success, but that scope did not persist into a new process.
- `python -m jeff --command "/scope show"`
  Outcome: showed empty scope in a fresh one-shot process. This makes `use` look more persistent than it is.
- `python -m jeff --command "/project use project-1" --command "/work use wu-1" --command "/scope show"`
  Outcome: worked inside one process. Repeated `--command` calls share temporary scope.
- `python -m jeff --project project-1 --work wu-1 --command "/inspect"`
  Outcome: worked. Auto-selected `run-1` initially and showed a convincing bounded demo flow with truth, derived, support, and telemetry sections.
- `python -m jeff --project project-1 --work wu-1 --command "/trace"`
  Outcome: worked. Trace surface is readable and useful.
- `python -m jeff --project project-1 --work wu-1 --command "/run list"`
  Outcome: worked. Listed runs in the selected work unit.
- `python -m jeff --project project-1 --work wu-1 --command "/show run-1"`
  Outcome: worked. Good operator summary for the demo run.
- `python -m jeff --project project-1 --work wu-1 --command "/lifecycle run-1"`
  Outcome: worked. Lifecycle projection is compact and understandable.
- `python -m jeff --project project-1 --work wu-1 --command "/show run-1" --json`
  Outcome: worked. JSON shape is strong and actually useful.
- `@('/help','/scope show','/exit') | python -m jeff`
  Outcome: did not behave as an interactive shell. Non-TTY refusal message only.
- `python -m jeff --project project-1 --work wu-1 --command "/run Check operator-created run"`
  Outcome: created a new run. Later inspection showed the run had a failed bounded proposal flow rather than a successful execution path.
- `python -m jeff --project project-1 --work wu-1 --command "/show run-2"`
  Outcome: showed a created run with no useful completed flow attached in compact mode.
- `python -m jeff --project project-1 --work wu-1 --command "/show run-2" --json`
  Outcome: revealed much more truthfully that the flow actually failed in proposal stage. JSON was more informative than compact text here.
- `python -m jeff --project project-1 --work wu-1 --command "/selection show run-3"`
  Outcome: worked. Truthful missing-chain output for a failed run.
- `python -m jeff --project project-1 --work wu-1 --command "/approve run-3"`
  Outcome: failed truthfully. Not currently available because routed outcome was `none`.
- `python -m jeff --project project-1 --work wu-1 --command "/reject run-3"`
  Outcome: same pattern as `/approve`.
- `python -m jeff --project project-1 --work wu-1 --command "/retry run-3"`
  Outcome: same pattern as `/approve`.
- `python -m jeff --project project-1 --work wu-1 --command "/revalidate run-3"`
  Outcome: same pattern as `/approve`.
- `python -m jeff --project project-1 --work wu-1 --command "/recover run-3"`
  Outcome: same pattern as `/approve`.
- `python -m jeff --project project-1 --work wu-1 --command "/run use run-1" --command "/json on" --command "/show"`
  Outcome: confusing. `/json on` reported success but `/show` still rendered human text in one-shot mode.
- `python -m jeff --command "/bogus"`
  Outcome: good failure message.
- `python -m jeff --command "hello"`
  Outcome: good failure message; plain text is rejected.
- `python -m jeff --project project-1 --work wu-1 --command "/selection show run-1"`
  Outcome: worked. Review surface is one of the most convincing parts of the CLI.
- `python -m jeff --project project-1 --work wu-1 --command '/selection override proposal-1 --why ""operator rationale"" run-1'`
  Outcome: worked, but PowerShell quoting is awkward and easy to get wrong.
- `python -m jeff --command '/research docs ""What is Jeff right now?"" README.md'`
  Outcome: worked. Created `general_research`, created a research work unit, created a run, persisted an artifact, and produced a reasonable answer.
- `python -m jeff --command '/research web ""What is Jeff right now?"" ""Jeff CLI backbone""'`
  Outcome: worked mechanically, but answered about unrelated people named Jeff. This is real output, not a stub, but it is weak as an operator tool without stronger grounding.
- `python -m jeff --command '/research docs ""What is the primary startup path?"" README.md --handoff-memory'`
  Outcome: worked. Research ran, artifact persisted, and memory handoff truthfully deferred rather than pretending success.
- `python -m jeff --project general_research --command "/work list"`
  Outcome: worked. Ad-hoc research state is inspectable afterward.
- `python -m jeff --project use`
  Outcome: failed clearly with correct usage guidance.
- `python -m jeff --project project-1 --command "/work use missing-wu"`
  Outcome: failed clearly with discovery guidance.
- `python -m jeff --project project-1 --work wu-1 --command "/run use missing-run"`
  Outcome: failed clearly with discovery guidance.
- `python -m jeff --project project-1 --work wu-1 --command "/scope clear" --command "/scope show"`
  Outcome: worked. Scope clear is local and coherent.
- `python -m jeff --version`
  Outcome: worked.
- `python -m pytest -q tests/smoke/test_cli_entry_smoke.py tests/integration/test_runtime_workspace_persistence.py tests/unit/interface/test_cli_scope_and_modes.py tests/unit/interface/test_cli_run_resolution.py`
  Outcome: 24 passed, 4 failed. Failures were operator-relevant: persisted state made `/show run-1` ambiguous and made `/show` and `/inspect` auto-bind the newest failed run (`run-3`) instead of the original demo run.

## Operator-first findings

### What a normal user can actually do today
- Start Jeff from the documented entrypoint.
- Get useful startup help and bootstrap diagnostics.
- Navigate projects, work units, and runs inside one process.
- Inspect an already-materialized run through `/inspect`, `/show`, `/trace`, `/lifecycle`, and `/selection show`.
- Use `--json` to get solid machine-readable output for several read surfaces.
- Run docs or web research if runtime config is present, and get persisted research artifacts back through the CLI.
- Record a selection override as a downstream support object.

### What feels real through the CLI
- The read surfaces are the strongest part of Jeff: `/show`, `/trace`, `/lifecycle`, and `/selection show` feel like real operator tools.
- The JSON views are substantial, not decorative.
- Docs research is a real flow: it creates scope, runs backend logic, persists artifacts, and returns grounded findings.
- Failure messages are usually specific and honest.

### What is confusing or misleading
- README and `/help` still talk like startup is an explicit in-memory demo, while `--help` and bootstrap output say startup uses a persisted `.jeff_runtime` workspace.
- `/project use` and `/work use` sound like durable operator actions, but they only affect the current process. A fresh one-shot invocation loses that scope.
- `/run <objective>` sounds like end-to-end execution. In practice it can create a run and then fail during proposal validation, leaving a dead-looking run behind.
- `/approve`, `/reject`, `/retry`, `/revalidate`, and `/recover` read like control verbs, but for most observed runs they were unavailable, and even when accepted they are only request receipts.
- `/json on` looks like a session feature, but in one-shot CLI usage it did not make later commands emit JSON.
- Web research is exposed as if it is operator-meaningful, but with a broad question it happily researched the wrong Jeff.

### What required guesswork
- How much state is process-local versus persisted.
- Whether to rely on `--project/--work` flags or `/project use` and `/work use`.
- How to quote commands with nested quotes in PowerShell, especially for `/selection override` and `/research ...`.
- Whether `/show` means "show the canonical demo run" or "show the latest run in the current work unit".

### Normal-user judgment before diagnosis
- Jeff is already a real inspection CLI for a bounded runtime slice.
- Jeff is not yet a convincing general operator CLI for running work through governance and action to completion.
- The tool looks broader than it really is because the command surface is larger than the reliably useful surface.
- A normal user will get frustrated quickly by stale help text, one-shot scope surprise, quoting friction, dirty persisted state, and control commands that mostly do not lead to completed workflows.

## Layer grades (1-5)

### Core / state / transitions
- Grade: 3
- Why: There is real state, real persisted transitions, real project/work/run creation, and real scope navigation. The operator can benefit from this today.
- What works: persisted `.jeff_runtime`, project/work/run discovery, auto-created research scope, transition-backed run creation, reloadable state.
- What does not: no obvious reset/clean-slate path, latest-run auto-selection can become misleading, state drift quickly changes CLI behavior, concurrent mutation is fragile.
- What holds it back: weak operator ergonomics and weak durability under repeated or concurrent use.
- Main weakness type: weak durability and weak operator ergonomics.

### Governance
- Grade: 2
- Why: governance is inspectable, but normal-user control is thin.
- What works: governance outcomes are visible in `/show`, `/selection show`, and JSON; approval-required states are modeled truthfully.
- What does not: request-entry verbs were mostly unavailable in real use, and even accepted requests are explicitly only receipts.
- What holds it back: the CLI exposes governance inspection better than governance action.
- Main weakness type: insufficient real flow completion and missing real control exposure.

### Cognitive
- Grade: 3
- Why: proposal/selection/evaluation visibility is real, docs research is real, and failure surfaces are not fake. But it remains bounded and fragile.
- What works: demo proposal/selection/evaluation inspection, selection review chain, docs research artifact generation, some meaningful JSON projections.
- What does not: `/run` failed on actual proposal generation; web research can be context-poor and misleading; a lot of the strongest cognitive behavior still depends on the canned demo run.
- What holds it back: thin backend reliability for open-ended operator use.
- Main weakness type: thin backend capability.

### Action / outcome / evaluation
- Grade: 2
- Why: demo action/outcome/evaluation is visible, but actual operator action completion is not strong.
- What works: demo run shows a coherent action-to-evaluation story; selection override recomputes downstream action and governance surfaces.
- What does not: selection override does not execute; `/run` did not reliably reach execution in actual use; request-entry verbs do not carry work forward.
- What holds it back: the CLI mostly inspects completed or failed artifacts instead of driving end-to-end action.
- Main weakness type: insufficient real flow completion.

### Memory
- Grade: 1
- Why: memory exists mostly as a side-effect of research handoff, not as a usable operator layer.
- What works: `--handoff-memory` is exposed and truthful about defer/reject/write outcomes.
- What does not: there is no meaningful operator memory workflow through the CLI beyond asking research to try a handoff.
- What holds it back: almost all memory value is backend- or test-visible, not operator-usable.
- Main weakness type: missing CLI exposure.

### Orchestrator
- Grade: 3
- Why: trace, lifecycle, routing, and failed-stage visibility are real and valuable.
- What works: `/trace`, `/lifecycle`, routed outcomes in JSON, persisted flow runs, failed proposal-stage runs that still surface useful history.
- What does not: the main operator path to drive the orchestrator is thin, and failed runs pile up in a way that later hurts discoverability.
- What holds it back: strong inspection, weak completion and weak operator recovery.
- Main weakness type: insufficient real flow completion.

### Interface / CLI
- Grade: 3
- Why: the CLI is real, command coverage is broad, and read surfaces are useful, but ergonomics are rough enough that a normal operator will hit friction quickly.
- What works: documented startup path, one-shot mode, helpful discovery errors, JSON mode via `--json`, coherent read commands.
- What does not: stale `/help`, shell quoting friction, non-durable `use` commands across processes, `/json on` not helping one-shot usage, no clean reset path, interactive shell unverified here because non-TTY.
- What holds it back: the operator contract is not as clear as the command list suggests.
- Main weakness type: weak operator ergonomics.

### Infrastructure / runtime / providers
- Grade: 2
- Why: runtime config and provider wiring are real, but day-to-day operator reliability is not yet strong.
- What works: bootstrap reports runtime config; docs research and web research can run against configured infrastructure; artifacts persist.
- What does not: proposal generation for `/run` failed under actual provider output; concurrent runtime writes collided on Windows; persisted runtime state bleeds into later behavior and test expectations.
- What holds it back: provider-dependent behavior is too fragile for confident normal use.
- Main weakness type: thin backend capability and weak durability.

### Overall operator usefulness
- Grade: 2
- Why: Jeff is already a real bounded inspection and research CLI, but it is not yet a strong end-to-end operator tool.
- What works: inspection, traceability, JSON read views, bounded docs research, truthful failure.
- What does not: robust run execution, meaningful governance control, usable memory, stable repeated-session behavior.
- What holds it back: the tool presents more surface area than it can currently turn into reliable completed operator workflows.

## Operator-observed behavior vs implementation diagnosis

### Operator-observed behavior
- Startup help and bootstrap check are usable.
- The best operator experience is inspection of already-existing runs.
- Docs research feels real. Web research feels real mechanically but weak semantically.
- `/run` is the biggest mismatch between what a normal user would expect and what I could reliably accomplish.
- Request-entry verbs look bigger than they are.
- Dirty persisted state changes what `/show`, `/inspect`, and even smoke tests do.

### Implementation diagnosis
- `jeff/main.py` now clearly boots a persisted workspace under `.jeff_runtime`.
- `jeff/interface/render.py` still renders `/help` text that says startup uses explicit in-memory demo state. That matches the operator-visible mismatch.
- `jeff/interface/session.py` keeps scope local to the CLI session only. `tests/integration/test_runtime_workspace_persistence.py` explicitly locks that in, so one-shot non-persistence is intentional, not accidental.
- `jeff/interface/command_scope.py` makes `/run <objective>` a real bounded backend flow when infrastructure is configured. It is not fake wiring. My failed runs were real failures, not absent implementation.
- `jeff/interface/command_requests.py` confirms that approve/reject/retry/revalidate/recover are intentionally request-entry only. Even success is only a receipt, not a state-changing workflow.
- `jeff/interface/command_research.py` explains why research without project scope creates `general_research`, derived work units, and runs. That behavior is intentional and tested.
- `jeff/interface/command_common.py` auto-selects the highest run ID in a work unit. That explains why repeated usage drifted `/show` and `/inspect` toward failed `run-3`.
- `jeff/runtime_persistence.py` writes JSON via `temp_path.replace(path)` but does not actually use the recorded `runtime.lock.json` as a live lock. That explains the Windows file-lock collision I hit by running two mutating Jeff processes in parallel.
- `jeff/main.py` passes `json_output=args.json` into every one-shot command. Because that is always an explicit boolean, `/json on` inside one-shot mode does not influence later commands in the same outer process. That matches the confusing observed behavior exactly.

### Inferred gaps before v1
- Jeff is stronger internally than the CLI sometimes makes it look, especially in selection review, routing, and persisted projections.
- Jeff is also weaker in operator reality than the surface area suggests, especially around actual control, action completion, memory, and repeated real-world use.
- Some failures are truthful and intentional deferrals, but they still count against v1 operator usefulness.

## What works well
- Startup and bootstrap diagnostics.
- Read-oriented run inspection.
- Trace and lifecycle projections.
- JSON read surfaces.
- Docs research with artifact persistence.
- Selection review as an inspection surface.
- Clear invalid-command and invalid-scope guidance.

## Where the gaps are
- Startup/help messaging is inconsistent.
- One-shot scope is easy to misunderstand.
- `/run` is exposed as a primary flow but is not yet robust in real usage.
- Request-entry verbs are too thin to count as strong operator capability.
- Persisted state has no obvious clean reset path and degrades later usability.
- Web research needs stronger grounding to the current project/tool context.
- PowerShell quoting friction hurts actual usability for the most complex commands.

## What does not really work yet
- A convincing operator path from new request to completed governed execution through the CLI.
- Meaningful governance control from the operator surface.
- Memory as a user-usable CLI feature.
- Stable repeated-session behavior without drift from prior runs.
- Multi-process safety for a persisted shared runtime.

## What must be done before v1
- Make the startup story truthful and consistent everywhere: README, `--help`, `/help`, bootstrap language, and operator expectations.
- Decide and document the scope contract clearly: process-local scope versus persisted runtime state, and make the UX make that obvious.
- Make `/run <objective>` reliably usable with configured providers, or stop presenting it as part of the normal primary flow.
- Add a clean operator reset or clean-room mode for `.jeff_runtime`, or at minimum a documented way to start from a known state.
- Fix one-shot mode semantics for `/json on`, or document that only outer `--json` matters in one-shot usage.
- Reduce ambiguity caused by latest-run auto-selection and duplicated `run-1` IDs across projects/work units.
- Turn at least one governance request-entry path into a real operator workflow, not just a receipt surface.
- Add real runtime write locking or another concurrency-safe persistence strategy.

## What should not be done before v1
- Do not add more command families that expand surface area without completing the real operator path.
- Do not spend pre-v1 effort on GUI polish, broad API expansion, or richer demo language while the CLI contract is still this easy to misread.
- Do not over-invest in more inspection views until the main action/governance path is materially more usable.

## Bottom line
- Is Jeff already a real CLI operator tool?
  No, not in the strong sense. It is a real bounded inspection and research CLI with honest surfaces, but it is not yet a strong end-to-end operator tool.
- What is it genuinely good at today?
  Inspecting persisted state, showing traces and lifecycle, exposing truthful JSON projections, and running bounded docs research with artifact persistence.
- What is still too thin?
  Actual operator control, reliable run execution, memory as a usable feature, and repeated-session durability.
- What is the single most important thing to fix next?
  Make the primary operator path honest and reliable: a clean, repeatable `/run` workflow from scope selection to a materially useful completed outcome, with state handling and help text that match what the CLI really does.
