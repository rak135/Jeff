# Black-Box Operator Validation Report

## Executive Summary

This pass validated Jeff as a real CLI operator surface, not a docs surface.

What worked cleanly:
- Startup, bootstrap, project/work discovery, and persisted runtime loading all worked in fresh processes.
- Direct `/proposal` is inspectable and materially useful when the scope already has archive-backed support.
- Direct `/proposal show`, `/proposal raw`, and `/proposal validate` all read back persisted proposal artifacts truthfully.
- A bounded direct-action `/run` completed end to end and produced coherent proposal, execution, and evaluation surfaces.
- Persisted run/proposal readback across fresh process restarts is real.

What did not hold up as strongly in live operator use:
- Windows one-shot quoting for provider-backed commands is brittle enough that `--command` frequently fails before Jeff sees the request.
- Scope resolution is confusing: bootstrap reports a runtime project scope while fresh `/scope show` reports no session scope, and a `run-1` lookup crossed project/work boundaries during proposal inspection.
- Proposal memory support is not operator-visible in the live cases tested, even when `/show` reports committed memory handoff writes on the run.
- The planning surface exists and fails closed honestly, but I could not reach a live persisted `PlanArtifact` from the current Ollama-backed `/run` path after multiple grounded attempts.
- Research command UX is weak in live use: two attempts returned explicit bounded-syntax errors, and one attempt mutated persisted runtime state with no terminal output at all.

Bottom line:
- Jeff v1 is strongest today at truthful persistence, proposal inspectability, and bounded direct `/run` execution.
- Jeff v1 is not yet strong at operator ergonomics, scope clarity, memory visibility, or live planning reachability.

## Exact Commands Executed

All provider-backed commands were run strictly one at a time.
All one-shot commands below were executed in fresh processes, which also served as restart-safe readback checks.

```text
& "c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --help
& "c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --bootstrap-check
& "c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --command "/project list"
& "c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --command "/scope show"
& "c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --project general_research --command "/work list"
& "c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --project project-1 --command "/work list"
& "c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --project general_research --work research-docs-summary-d1f80a8e --command "/run list"
& "c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --project project-1 --work wu-1 --command "/run list"
& "c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --command "/help"
& "c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --project general_research --work research-docs-summary-d1f80a8e --run run-1 --command "/show"
& "c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --project project-1 --work wu-1 --run run-10 --command "/show"
& "c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --project project-1 --work wu-1 --run run-10 --command "/proposal show"
& "c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --project general_research --work research-docs-summary-d1f80a8e --run run-1 --command "/proposal show"
& "c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --project general_research --work research-docs-summary-d1f80a8e --run run-1 --command "/trace"

cmd /c '"c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --project project-1 --work wu-1 --run run-10 --command "/proposal \"What prior bounded runtime result in this scope should influence the next bounded rollout?\""'
cmd /c '"c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --project project-1 --work wu-1 --run run-1 --command "/proposal \"What is Jeff architecture?\""'

& "c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --project project-1 --work wu-1 --run run-10 --command "/proposal show"
& "c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --project project-1 --work wu-1 --run run-10 --command "/proposal raw"
& "c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --project project-1 --work wu-1 --run run-10 --command "/proposal validate"
& "c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --project project-1 --work wu-1 --run run-1 --command "/proposal show"
& "c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --project project-1 --work wu-1 --run run-1 --command "/proposal validate"

cmd /c '"c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --command "/research docs \"Summarize Jeff README startup behavior\" README.md --handoff-memory"'
cmd /c '"c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --command "/research docs \"startup summary\" README.md --handoff-memory"'
cmd /c '"c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --command "/research docs \"summary\" README.md --handoff-memory"'

& "c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --project general_research --command "/work list"
& "c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --project general_research --work research-docs-startup-summary-43bf0309 --command "/run list"
& "c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --project general_research --work research-docs-summarize-jeff-readme-startup-behavior-501178cf --command "/run list"
& "c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --project general_research --work research-docs-startup-summary-43bf0309 --run run-1 --command "/show"
& "c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --project general_research --work research-docs-summarize-jeff-readme-startup-behavior-501178cf --run run-1 --command "/show"

cmd /c '"c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --project project-1 --work wu-1 --command "/run \"What bounded rollout should execute now?\""'
cmd /c '"c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --project project-1 --work wu-1 --command "/run \"Plan the next bounded operator validation slice and hold for review.\""'
cmd /c '"c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --project project-1 --work wu-1 --command "/run \"Investigate why the literal labels are being surfaced and propose a bounded fix.\""'

& "c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --project project-1 --work wu-1 --run run-12 --command "/plan show"
& "c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --project project-1 --work wu-1 --run run-13 --command "/plan show"
& "c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --project project-1 --work wu-1 --run run-13 --command "/selection show"
& "c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --project project-1 --work wu-1 --run run-8 --command "/proposal show"
& "c:\DATA\PROJECTS\JEFF\.venv\Scripts\python.exe" -m jeff --project project-1 --work wu-1 --run run-8 --command "/show"
```

## Startup And Scope Findings

Observed cleanly:
- `--help` and `--bootstrap-check` worked immediately.
- Bootstrap truthfully reported persisted runtime loading from `.jeff_runtime`.
- Project and work discovery worked and exposed two active projects: `general_research` and `project-1`.
- Fresh-process one-shot commands are a real persisted-runtime operator path, not a mock surface.

Observed friction:
- `--bootstrap-check` reported `runtime project scope ready: general_research`, while a fresh `/scope show` reported `project_id=- work_unit_id=- run_id=-`. That is technically explainable by runtime scope versus session scope, but operator-facing wording makes it feel contradictory.
- Multiple projects and duplicated run ids are live reality. That matters because run ids like `run-1` are not globally unique.
- A proposal readback invoked with `--project general_research --work research-docs-summary-d1f80a8e --run run-1` resolved to `project-1/wu-1/run-1`, not the requested general_research scope. That is a serious operator trust issue in historical run resolution.

Representative outputs:

```text
bootstrap checks passed
- Startup loaded persisted runtime state from C:\DATA\PROJECTS\JEFF\.jeff_runtime.
- runtime project scope ready: general_research
- runtime loaded 11 persisted run support record(s)
...

[session] scope
project_id=-
work_unit_id=-
run_id=-
...
```

## Direct Proposal Findings

### Thin Scope

Live command:

```text
/proposal "What prior bounded runtime result in this scope should influence the next bounded rollout?"
scope: project-1 / wu-1 / run-10
```

Observed behavior:
- Proposal succeeded.
- Proposal stayed honestly thin with `proposal_count=0`.
- `proposal_input_bundle` showed `evidence_items=0` and `memory_items=0`.
- `/proposal raw` and `/proposal validate` read back the same truthfully.

This is good honesty. Jeff did not invent support it did not have.

### Archive / Evidence Scope

Live command:

```text
/proposal "What is Jeff architecture?"
scope: project-1 / wu-1 / run-1
```

Observed behavior:
- Proposal succeeded.
- Proposal exposed real archive support: `evidence_items=2` and explicit `evidence_refs`.
- The resulting proposal stayed appropriately thin in content quality: it could only recommend inspecting evidence artifacts, not answer the architecture question directly.
- `/proposal validate` remained coherent and inspectable.

This is a good slice. The support is visible, bounded, and inspectable.

### Committed Memory Scope

I explicitly tested runs where `/show` reported committed memory handoff writes:
- `run-8` reported `memory_handoff outcome=write memory_id=memory-1`
- `run-10` reported `memory_handoff outcome=write memory_id=memory-1`
- `run-12` reported `memory_handoff outcome=write memory_id=memory-2`

Observed behavior:
- Direct `/proposal` on `run-10` still surfaced `memory_items=0`.
- Historical readback on `run-8` also surfaced `memory_items=0` even for an objective explicitly asking to use prior evidence and memory.
- I did not get a live operator case where direct `/proposal` exposed operator-visible `memory_support` after restart, despite using fresh processes for readback.

Conclusion:
- Persisted memory writes are real.
- Operator-visible proposal memory support is still under-verified at best and absent in the live cases I exercised.

### Proposal Inspectability Quality

Strong:
- `/proposal show` is one of the best surfaces in the runtime.
- `/proposal raw` is useful when the summary is too compressed.
- `/proposal validate` is truthful and useful for determining whether the stored record is structurally valid.

Thin or awkward:
- The proposal bundle often exposes only support metadata rather than descriptive substance. That is truthful, but it can feel unsatisfying to an operator expecting evidence-backed help.
- Windows quoting makes provider-backed one-shot proposal execution awkward enough that an operator may think Jeff is broken before the command reaches Jeff at all.

## `/run` Findings

### Bounded Direct-Action Style `/run`

Live command:

```text
/run "What bounded rollout should execute now?"
```

Observed behavior:
- Created `run-12`.
- Completed successfully.
- Executed the fixed repo-local validation plan and passed smoke pytest.
- Evaluation completed with `acceptable` and evidence `strong`.
- Proposal, execution, and evaluation surfaces were coherent.

Observed wrinkle:
- The run reported `flow_family=conditional_planning_execution`, but had no planning artifact and no planning summary. That naming is technically possible, but operator-facing it feels mislabeled for a straight-through direct action run.

### Planning-Oriented `/run`

Live command:

```text
/run "Plan the next bounded operator validation slice and hold for review."
```

Observed behavior:
- Created `run-13`.
- Proposal came back with `planning_needed=true` on `proposal-1`.
- Selection did not route into planning.
- Selection escalated with rationale that the proposal framed an operator judgment boundary more honestly than forcing a bounded autonomous choice.
- `/plan show run-13` failed cleanly with `no planning artifact is available for run run-13`.

### Investigative `/run`

Live command:

```text
/run "Investigate why the literal labels are being surfaced and propose a bounded fix."
```

Observed behavior:
- Created `run-14`.
- Proposal surfaced a bounded `investigate` option.
- Selection deferred terminally.
- No planning artifact was produced.

Conclusion:
- `/run` is usable for the bounded validation path.
- `/run` does not currently make planning feel reachable or reliable from an operator perspective, even when proposal output carries planning intent.

## Planning Findings

What I could verify live:
- `/plan show` fails closed honestly when no plan artifact exists.
- `/selection show run-13` explains the planning miss coherently: proposal had `planning_needed=true`, but selection escalated instead of selecting it.
- The planning CLI is implemented and expects a real persisted `PlanArtifact`; it is not a fake placeholder surface.

What I could not verify live:
- A planning-held run with a real persisted `PlanArtifact`.
- Review-only active-step behavior under `/plan execute`.
- One-step executable planned-step execution.
- Checkpoint progression after a live planned step.
- Restart-safe readback of real plan progression.

Why this matters:
- This is not just a missing test I forgot to run. I made multiple grounded live attempts to reach planning through the current operator path, including a run where the proposal explicitly persisted `planning_needed=true`.
- In live use, planning appears implemented but practically unreachable or at least under-signaled.

## Research And Memory Findings

Research command attempts:

```text
/research docs "Summarize Jeff README startup behavior" README.md --handoff-memory
/research docs "startup summary" README.md --handoff-memory
/research docs "summary" README.md --handoff-memory
```

Observed behavior:
- Two attempts returned `[error] summary must stay concise and below 200 characters`.
- The one-word `summary` attempt returned no terminal output at all.
- Despite the missing output, persisted runtime state showed new `general_research` work units had been created.
- Readback of those new runs showed failed proposal-stage runs with deferred memory handoff, not a clear research summary surface.

Operator conclusion:
- The research path is not currently trustworthy enough as an operator surface.
- Silent mutation with no terminal output is worse than an explicit failure.

## Persistence And Restart Findings

Verified:
- Proposal records persist and read back in fresh processes.
- Run history persists and read back in fresh processes.
- Memory handoff receipts persist and read back in fresh processes through `/show`.
- Failure surfaces also persist truthfully: missing plan artifacts stay missing across restarts.

Not verified positively:
- A persisted plan artifact with restart-safe readback, because I could not produce one live.
- Operator-visible proposal memory support after restart, despite persisted memory writes.

Truth/support separation quality:
- Generally good on the proposal and run surfaces.
- Jeff usually labels truth, derived, and support distinctly.
- The weak point is not truth-labeling discipline. The weak point is support reachability and operator clarity.

## Focused Code Inspection Findings

I inspected code only after the black-box pass to explain observed behavior.

Relevant findings:
- The planning CLI is real and expects `flow_run.outputs["planning"]`; if that output is missing, `/plan show` and `/plan execute` fail closed. That matches the live behavior.
- The planning gate in `jeff/cognitive/planning/gating.py` is simple: planning requires either `planning_needed`, `planning_insertion`, or other explicit gate reasons.
- `run-13` persisted `planning_needed=true`, but selection still produced `non_selection_outcome=escalate`, so the orchestrator never entered planning. That matches the live behavior exactly.
- `selection override` only persists a review override receipt. It does not continue the flow into planning. So it cannot rescue the live planning milestone from the operator surface.

This code inspection supports, rather than replaces, the black-box conclusion: the live planning path is implemented structurally but not practically reachable in the operator behaviors I tested.

## What Feels Strong

- Persisted runtime startup is real and stable.
- `/proposal show`, `/proposal raw`, and `/proposal validate` are strong operator tools.
- Archive/evidence-backed proposal inspectability is genuinely useful.
- Bounded direct `/run` execution is coherent and honest.
- Failure states are usually labeled honestly rather than disguised as success.

## What Still Feels Weak

- Windows command quoting for live provider-backed one-shot usage.
- Scope clarity across bootstrap scope, session scope, and historical run lookup.
- Operator-visible memory support in direct proposal.
- Research command usability and output consistency.
- Planning reachability from real live `/run` objectives.

## What Felt Confusing

- Bootstrap claiming a runtime project scope while `/scope show` says no scope is active.
- `run-1` proposal lookup crossing into the wrong project/work scope.
- A completed direct-action run labeled `conditional_planning_execution` with no plan artifact.
- A research command mutating runtime state while printing nothing.

## What Felt Too Thin

- Proposal support often stops at metadata-level evidence provenance rather than surfacing descriptive payload value.
- Memory support is claimed by run memory handoff receipts, but not delivered in live proposal input bundles.
- Planning exists as a visible command family but not as a reachable operator experience in the live path tested.

## What Looked Brittle

- PowerShell quoting around `--command` for quoted objectives.
- Historical run resolution when ids collide across projects/work units.
- Research entry behavior under docs mode.
- Planning reliance on upstream selection behavior that the operator cannot easily inspect or correct into continuation.

## Concrete Improvement Notes

1. Fix one-shot command quoting on Windows for quoted objectives.
Jeff should accept common PowerShell forms for `/proposal`, `/run`, and `/research` without forcing operators into `cmd /c` escape gymnastics.

2. Make run resolution scope-safe when run ids collide.
If `--project` and `--work` are provided, readback commands must not silently resolve a different run in another scope.

3. Expose why memory retrieval did not contribute to proposal input.
If a run has persisted memory handoff but `memory_items=0`, show a bounded reason like `no scope-matched memory summaries found` or `retrieval returned no above-threshold matches`.

4. Tighten research command operator feedback.
Every research command should end with either a receipt, a failed receipt, or a bounded error. Silent state mutation is not acceptable operator UX.

5. Make planning reachability inspectable before it is strong.
If proposal sets `planning_needed=true` but selection escalates or defers, surface that conflict explicitly in `/show` and `/selection show` as a first-class planning miss, not just a generic non-selection outcome.

## Top 5 Bounded Improvements

1. Repair historical run resolution so explicit project/work scope cannot drift to the wrong run id.
2. Add bounded memory retrieval diagnostics to `/proposal show` when memory handoff exists but memory support is empty.
3. Normalize Windows quoting support for quoted slash commands in `--command` one-shot mode.
4. Guarantee explicit terminal receipts for `/research` success, validation failure, and runtime failure.
5. Surface a `planning_not_entered_reason` when `planning_needed=true` but selection prevents planning.

## What Should Not Be Broadened Yet

- Do not broaden `/run` beyond the fixed bounded validation surface yet.
- Do not add more planning automation or hidden multi-step continuation while the first planning entry is not reliably reachable and inspectable.
- Do not market memory as a strong operator feature until proposal-time memory visibility is proven live.

## Single Next Best Slice

Make planning misses first-class and diagnosable in the live operator path.

Concrete bounded slice:
- When proposal output contains `planning_needed=true` or `proposal_type=planning_insertion` but selection yields `defer` or `escalate`, persist and render a dedicated support record that says planning was requested, why it was not entered, and what operator-visible command or condition would be needed next.

Why this is the next best slice:
- It does not broaden autonomy.
- It directly addresses the largest gap between the implemented planning surface and the live operator experience.
- It makes the current system easier to trust before adding any new breadth.