# Real CLI Validation Report

## Audit method
- I treated Jeff as a normal operator-facing CLI first and started from the documented entrypoint in `README.md`: `python -m jeff`.
- I used only visible surfaces for the first pass: `README.md`, `python -m jeff --help`, `python -m jeff --bootstrap-check`, `/help`, and actual one-shot CLI commands.
- I did not start by reading deep source code. I used code and tests only after the operator-first pass to explain observed behavior.
- I used the repo root runtime exactly as Jeff loaded it, including persisted `.jeff_runtime` state already present in the workspace. Because Jeff is explicitly persisted-runtime software, that existing state counts as part of operator reality.
- I then inspected startup, interface, command routing, session scope, render/json projection, research flow, selection review/override, request-entry handling, runtime persistence, orchestrator seams, and relevant smoke/integration tests.
- I also ran the documented smoke suite and targeted integration files after the diagnosis pass.

Operator-first limitations:
- The automation harness does not provide a real TTY, so `python -m jeff` refused to enter the interactive shell and printed `No interactive terminal detected. Use --command for one-shot mode.` I count that observed behavior, but I could not fully drive the live prompt loop.
- A few research commands needed careful PowerShell escaping. That is itself an operator usability finding.

## Commands and scenarios tested
- `python -m jeff --help`
  Outcome: worked; clear startup/options surface.
- `python -m jeff --bootstrap-check`
  Outcome: worked; confirmed runtime, config, research, and memory status.
- `jeff --help`
  Outcome: failed with command-not-found; the console script is declared in packaging but not installed in this repo checkout.
- `@('/help','/exit') | python -m jeff`
  Outcome: did not open the shell; printed top-level help and `No interactive terminal detected. Use --command for one-shot mode.`
- `python -m jeff --command "/help"`
  Outcome: worked; useful command map, but it advertises more surface than a normal user can reliably complete.
- `python -m jeff --command "/project list"`
  Outcome: worked.
- `python -m jeff --command "/work list"`
  Outcome: failed clearly because no project scope was selected.
- `python -m jeff --command "/run list"`
  Outcome: failed clearly because no project scope was selected.
- `python -m jeff --command "/project use project-1" --command "/work list" --command "/work use wu-1" --command "/run list" --command "/run use run-1" --command "/show"`
  Outcome: worked; repeated one-shot commands share session scope inside one process.
- `python -m jeff --project project-1 --work wu-1 --run run-1 --command "/inspect"`
  Outcome: worked.
- `python -m jeff --project project-1 --work wu-1 --run run-1 --command "/trace"`
  Outcome: worked.
- `python -m jeff --project project-1 --work wu-1 --run run-1 --command "/lifecycle"`
  Outcome: worked.
- `python -m jeff --project project-1 --work wu-1 --run run-1 --command "/show" --json`
  Outcome: worked; JSON payload was valid and useful.
- `python -m jeff --command "/project list" --json`
  Outcome: stayed in text mode; `--json` did not apply to this list command.
- `python -m jeff --project project-1 --command "/work list" --json`
  Outcome: stayed in text mode.
- `python -m jeff --project project-1 --work wu-1 --command "/run list" --json`
  Outcome: stayed in text mode.
- `python -m jeff --project project-1 --work wu-1 --run run-1 --command "/json on" --command "/show" --command "/json off" --command "/show"`
  Outcome: `/json on` acknowledged the toggle, but the next `/show` still rendered text, not JSON.
- `python -m jeff --command "hello"`
  Outcome: failed clearly and truthfully.
- `python -m jeff --command "/bogus"`
  Outcome: failed clearly and truthfully.
- `python -m jeff --project project-1 --work wu-1 --run run-1 --command "/selection show"`
  Outcome: worked, but surfaced a persisted operator override that `/show` did not surface the same way.
- `python -m jeff --command "/project use project-1" --command "/work use wu-1" --command "/run use run-2" --command "/scope show" --command "/scope clear" --command "/scope show"`
  Outcome: worked.
- `python -m jeff --command "/project use general_research" --command "/work list"`
  Outcome: worked; visible ad-hoc research work units existed.
- `python -m jeff --command '/research docs ""What is the primary startup path?"" README.md'`
  Outcome: worked after PowerShell quote-escaping guesswork; produced a persisted research artifact.
- `python -m jeff --command '/research web ""What is Jeff right now?"" ""Jeff CLI runtime""'`
  Outcome: technically worked, but returned off-target internet results about unrelated "Jeff" entities.
- `python -m jeff --command "/project use project-1" --command "/work use wu-1" --command "/run validate README smoke path"`
  Outcome: created `run-4`, then stopped at a non-execution defer path.
- `python -m jeff --project project-1 --work wu-1 --run run-4 --command "/selection show" --command '/selection override proposal-1 --why ""Need to investigate first""' --command "/selection show"`
  Outcome: worked; override was recorded, but no action or governance continuation started.
- `python -m jeff --project project-1 --work wu-1 --run run-4 --command "/approve"`
  Outcome: unavailable for that run.
- `python -m jeff --project project-1 --work wu-1 --run run-4 --command "/revalidate"`
  Outcome: unavailable for that run.
- `python -m jeff --project project-1 --work wu-1 --run run-4 --command "/reject"`
  Outcome: unavailable for that run.
- `python -m jeff --project project-1 --work wu-1 --run run-4 --command "/retry"`
  Outcome: unavailable for that run.
- `python -m jeff --project project-1 --work wu-1 --run run-4 --command "/recover"`
  Outcome: unavailable for that run.
- `python -m jeff --command "/project use project-1" --command "/work use wu-1" --command "/run repo-local validation"`
  Outcome: created `run-5`, then failed in proposal generation/validation before action or execution.
- `python -m jeff --project project-1 --work wu-1 --run run-5 --command "/show"`
  Outcome: worked; surfaced the proposal validation failure truthfully.
- `python -m jeff --command '/research docs ""What is the primary startup path?"" README.md --handoff-memory'`
  Outcome: failed with a memory-candidate validation error.

Observed concurrency issue:
- Running multiple one-shot inspection commands in parallel against the same runtime produced a raw Windows lock-file error on `.jeff_runtime\config\runtime.mutation.lock` rather than a clean operator-facing conflict message.

## Operator-first findings

### What a normal user can actually do today
- Start Jeff reliably with `python -m jeff`.
- Discover the top-level CLI surface through `--help`, `--bootstrap-check`, and `/help`.
- Navigate project/work/run scope when they already understand the session model.
- Inspect persisted runs with `/show`, `/inspect`, `/trace`, and `/lifecycle`.
- Run document research with explicit paths and get a persisted artifact.
- Run web research and get a persisted artifact, though result relevance is inconsistent.
- Review a selection chain and record a manual override.

### What is strong through the CLI
- Read-oriented inspection is the most convincing surface. `/show`, `/trace`, and `/lifecycle` feel real and expose meaningful support/evidence rather than empty placeholders.
- Runtime persistence is real in operator terms. Jeff loads history, seeded runs, past research work units, and prior support records on startup.
- The CLI is usually truthful about unsupported or unavailable operations. It mostly fails honestly instead of pretending work happened.
- Docs research is a real workflow, not just a receipt. It read `README.md`, generated findings, persisted an artifact, and surfaced source paths.

### What is confusing or awkward
- Scope is strictly session-local and process-local. That is documented, but a normal user will still trip over it immediately unless they happen to chain commands in one process.
- The research command syntax is shell-fragile in PowerShell. The help text tells you the logical syntax, not the actual escaping pain.
- `--json` and `/json on` do not behave consistently across surfaces.
- The seeded/persisted demo data makes the tool feel more complete than a fresh operator-created flow really is.
- `/show` and `/selection show` can disagree in a way that feels inconsistent to an operator, especially when an old override exists.

### What is misleading or thinner than it looks
- `/run <objective>` looks like a general operator entry surface, but in practice it is one narrow repo-local validation path and it is fragile under the live model configuration.
- Request-entry commands (`approve`, `reject`, `revalidate`, `retry`, `recover`) look like a meaningful control surface, but a normal operator may never naturally reach the states where they are usable.
- A run can be marked `completed` even when it actually ended in a terminal non-execution defer path. That overstates practical success.
- Existing seeded run data is useful for inspection, but it can be mistaken for proof that live end-to-end execution is already robust.

### Normal-user judgment before code diagnosis
- A normal user can inspect Jeff far better than they can operate Jeff.
- Jeff feels real as an inspection shell with persistence, traces, and research support.
- Jeff feels thin at the point where the user expects a fresh `/run` objective to turn into a dependable end-to-end action.
- The CLI feels bigger than it really is around `/run`, approval controls, and machine-readable surfaces.
- The fastest path to frustration is: try `/run` with a natural objective, then try to understand why it deferred, failed, or still shows `completed` without actually doing the thing.

## Layer grades (1-5)

### Core / state / transitions
- Grade: 3
- Why: persisted runtime state, project/work/run creation, and reload behavior are real and operator-visible, but the truth surface is not consistently trustworthy in practice.
- What works: startup seeds and reloads runtime state; scope navigation works; runs persist; new runs can be created; traces/history stay attached.
- What does not: operator-facing truth can be confusing or contradictory, such as `run-1` showing `run_lifecycle_state=created` while derived flow state is completed, and `run-4` showing `completed` even though it deferred without execution.
- What holds it back: weak operator ergonomics plus weak truth projection, not an absence of underlying state machinery.
- Main weakness type: weak durability/truth surfacing, weak operator ergonomics.

### Governance
- Grade: 2
- Why: governance metadata and routed outcomes exist, but a normal CLI user cannot benefit from them much without already knowing how to manufacture specific internal states.
- What works: governance handoff is visible in selection review; unavailable request commands fail truthfully; tests show real approval and revalidation paths exist.
- What does not: black-box operator usage did not naturally reach an approval-required run; request-entry commands were mostly unusable; the CLI does not make it obvious how to reach a governable continuation state.
- What holds it back: governance is present more as inspectable internal structure than as a usable operator control path.
- Main weakness type: missing CLI exposure, insufficient real flow completion.

### Cognitive
- Grade: 3
- Why: docs research, selection review, and explanation surfaces are materially real, but live-model proposal generation and web research quality are not reliable enough for stronger operator trust.
- What works: document research; persisted research artifacts; selection review; operator override recording; live context support packaging is visible.
- What does not: `/run` proposal generation is fragile under the real provider; web research can be badly off-target; the CLI does not help the user know what objectives are likely to succeed.
- What holds it back: a mix of live backend fragility and operator discoverability gaps.
- Main weakness type: thin backend capability in live mode, weak operator ergonomics.

### Action / outcome / evaluation
- Grade: 2
- Why: inspection of action/outcome/evaluation is decent, but fresh operator-triggered flow completion is not dependable.
- What works: existing completed runs expose execution, outcome, and evaluation clearly; the repo-local validation execution plan is real; failure reporting is usually honest.
- What does not: a normal user could not reliably create a successful new execution from `/run`; one natural objective deferred without execution, another failed before action formation.
- What holds it back: the layer is more inspectable than usable.
- Main weakness type: insufficient real flow completion.

### Memory
- Grade: 1
- Why: operator-visible memory is almost nonexistent, and the one exposed handoff path failed in real CLI use.
- What works: bootstrap reports that memory is configured; research can theoretically request handoff with `--handoff-memory`; tests show the pipeline exists internally.
- What does not: there is no meaningful `/memory` operator surface; a real docs-research handoff failed with `summary must stay concise and below 200 characters`; the user cannot inspect, repair, or reason about memory from the CLI.
- What holds it back: memory is mostly internal capability, not operator utility.
- Main weakness type: missing CLI exposure, thin operator path.

### Orchestrator
- Grade: 3
- Why: the orchestrator is real enough to expose traces, lifecycle, routing decisions, and persisted flow support, but its operator semantics are sometimes misleading.
- What works: `/trace`, `/lifecycle`, routed outcomes, event history, persisted flow records.
- What does not: terminal non-execution defer can still surface as `completed`; orchestrator strength is visible mostly through inspection, not through reliable end-to-end control.
- What holds it back: the operator sees routing and lifecycle output, but not always with semantics that match plain-language expectations.
- Main weakness type: weak operator ergonomics, insufficient real flow completion.

### Interface / CLI
- Grade: 3
- Why: the CLI is usable for bounded discovery and inspection, but not polished or coherent enough to deserve a stronger operator grade.
- What works: startup, help, scope commands, list/show/trace/lifecycle, readable error messages, one-shot chaining.
- What does not: `jeff` script was not available by default in this checkout; interactive mode is TTY-dependent; research quoting is awkward; `/json on` in repeated one-shot mode does not work as advertised; `--json` coverage is partial.
- What holds it back: too many small operator traps for a tool that is claiming a CLI-first surface.
- Main weakness type: weak operator ergonomics.

### Infrastructure / runtime / providers
- Grade: 2
- Why: runtime loading and config detection are real, but live-provider behavior is not robust enough for confident operator use.
- What works: startup loads config; bootstrap reports provider state; docs research worked with the configured local provider; runtime persistence itself is solid.
- What does not: the live `/run` path failed on proposal validation under the real model setup; web research was technically live but low-relevance; concurrent CLI invocations exposed lock fragility.
- What holds it back: too much depends on provider outputs staying inside narrow internal validation boundaries.
- Main weakness type: thin backend reliability, weak durability under concurrent use.

### Overall operator usefulness
- Grade: 2
- Why: Jeff is already a real CLI for inspection and bounded research, but it is not yet a convincing real operator tool for dependable end-to-end run control.
- What works: inspection, persistence, traceability, some research.
- What does not: dependable fresh `/run` completion, coherent request-entry control, memory utility, consistent machine-readable behavior.
- What holds it back: the tool currently feels stronger in internal architecture and tests than in black-box operator reality.

## What works well
- The documented startup path is clear and works.
- `--bootstrap-check` is a good operator-facing truth surface.
- `/help` is readable and mostly honest about what Jeff is and is not.
- `/show`, `/trace`, and `/lifecycle` are the strongest CLI surfaces today.
- Runtime persistence is genuinely load-bearing and visible.
- Docs research is a real CLI workflow with artifact persistence and source transparency.
- Error messages for missing scope and bad IDs are good.

## Where the gaps are
- `/run` is not operator-trustworthy enough yet.
- JSON mode is inconsistent across commands and modes.
- Request-entry controls are exposed more broadly than they are practically reachable.
- Web research needs better operator guidance or better repo-aware querying to avoid irrelevant results.
- Persisted demo/support data can make the product look more complete than live operator flows really are.
- Some "read" commands are not truly read-only because they materialize and persist support records, which contributes to lock contention.

## What does not really work yet
- A dependable fresh `/run <objective>` flow for a normal operator.
- A coherent, discoverable approval/revalidate control loop in live operator use.
- Memory as an operator-visible feature.
- Fully trustworthy machine-readable CLI output across the command set.
- Clean concurrent CLI use against the same runtime workspace.

## What must be done before v1
- Make `/run` reliably succeed or fail for normal objectives under the real provider configuration, not only under fake adapters and test monkeypatches.
- Narrow or reword the `/run` promise so the operator knows exactly what kind of objective is expected and what Jeff will actually do.
- Fix JSON behavior so `--json` and `/json on` are consistent across one-shot and repeated-command sessions.
- Decide whether terminal non-execution defer/reject paths should really look `completed` to operators. Right now that is too misleading.
- Make the request-entry surface reachable and understandable from black-box usage, or de-emphasize it until it is.
- Make memory handoff robust enough not to fail on ordinary research summaries, or stop advertising it as an operator path.
- Reduce seeded-demo confusion. If Jeff boots with demo runs, it should make that explicit in the CLI so a user does not mistake seeded history for fresh live capability.

## What should not be done before v1
- Do not add a broad `/memory` command family before the existing handoff path is reliable and understandable.
- Do not expand into more action families before the current bounded repo-local validation path is dependable.
- Do not spend v1 effort on GUI or broad API surface; the CLI still needs coherence first.
- Do not inflate the request-entry surface with more verbs while `approve/revalidate/reject/retry/recover` are still mostly unreachable or receipt-only.

## Bottom line
- Is Jeff already a real CLI operator tool?
  Not yet in the stronger sense. It is a real persisted inspection and research CLI, but it is not yet a convincing real operator tool for dependable end-to-end run execution.
- What is it genuinely good at today?
  Truthful inspection of persisted runs, trace/lifecycle visibility, and bounded docs research with saved artifacts.
- What is still too thin?
  Fresh `/run` execution, approval/revalidation as a practical operator loop, memory, and machine-readable consistency.
- What is the single most important thing to fix next?
  Make the primary `/run <objective>` path reliably complete a real bounded flow under the live provider setup, and make the operator-facing semantics match what actually happened.

## Diagnosis pass summary

### Why some operator behavior looked stronger than it really was
- Startup seeds a demo run and persists its flow/support records. That is why `run-1` already looks rich on first inspection. This comes from the bootstrap path in `jeff/bootstrap.py`, not from a fresh operator-created run.
- The tests are materially stronger than the live operator experience because many key `/run` and research integration tests use fake adapters or monkeypatched search/execution plans rather than the real configured provider path.

### Why `/run` was fragile in live use
- The live `/run` path is a single repo-local validation plan wired in `jeff/interface/command_scope.py`.
- Successful `/run` depends on proposal generation producing a valid proposal that survives semantic validation in `jeff/cognitive/proposal/validation.py`.
- That validation forbids authority-like words including `execution`, `ready`, `allow`, `approve`, and similar terms inside proposal fields.
- In real CLI use, the configured live model produced text that violated those rules, so the flow failed before action formation or execution.
- In contrast, passing tests often inject carefully crafted fake proposal text that already respects those validation rules.

### Why `/show` and `/selection show` felt inconsistent
- `/show` derives `selected_proposal_id` from the original flow selection output.
- `/selection show` also includes resolved override state and effective downstream choice.
- That means a persisted operator override can appear in `/selection show` while `/show` still looks like the original selection won. This is internally explainable, but operator-confusing.

### Why JSON mode was inconsistent
- Some command families produce JSON payloads but are never passed through the JSON projection helper in the main dispatcher, so `--json` does nothing for them.
- Repeated-command one-shot mode also passes the top-level `args.json` boolean into every command. When `--json` is not set, that explicit `False` blocks session-level `/json on` from taking effect.

### Why concurrent "read" commands collided
- Several inspect/show paths materialize and persist selection-review support on demand.
- That means commands that look read-only can still take the runtime mutation lock and write support files.
- In practice this makes parallel CLI invocations against the same runtime more fragile than an operator would expect.

### Test execution after diagnosis
- Documented smoke suite run:
  `python -m pytest -q tests/smoke/test_bootstrap_smoke.py tests/smoke/test_cli_entry_smoke.py tests/smoke/test_quickstart_paths.py`
  Result: `18 passed`
- Targeted integration run:
  `python -m pytest -q tests/integration/test_cli_run_live_context_execution.py tests/integration/test_cli_research_flow.py tests/integration/test_runtime_workspace_persistence.py`
  Result: `31 passed`
- Interpretation: the internals are materially more capable than the black-box live-provider operator pass suggests, but much of that strength currently depends on controlled fake/monkeypatched test conditions or on seeded persisted demo state.
