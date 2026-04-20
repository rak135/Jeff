# Planning Slice Report

## 1. Executive summary

This slice implements Jeff's bounded Planning v1 layer as real product code.

Planning is now a deterministic, conditional, support-only layer under `jeff/cognitive/planning/`. It can form a bounded multi-step plan from a selected proposal, persist that plan durably on the flow run, expose the plan through operator surfaces, advance the plan through explicit checkpoint decisions, and materialize a single active-step action candidate when the current step lawfully permits it.

The slice does not turn planning into truth, authority, approval, readiness, hidden orchestration logic, or automatic workflow execution. Planning remains inspectable support.

## 2. Design judgment

Planning in this slice is deterministic, not model-assisted and not hybrid.

Reason:

- the selected proposal contract already carries enough bounded structure to form lawful plan steps, blockers, checkpoints, and risks
- adding a planner model path here would have expanded Jeff's behavior surface before the support-only boundary was fully hardened
- deterministic planning is easier to inspect, persist, checkpoint, and keep fail-closed

## 3. Architectural outcome

Planning now does five bounded jobs:

1. decide whether planning should exist at all
2. form a bounded plan artifact from the selected proposal
3. persist that artifact as flow-run support, not canonical truth
4. expose active-step and checkpoint state to operators
5. bridge one active executable step into an action candidate without letting orchestration guess across multiple open steps

What planning still does not do:

- mutate canonical truth
- authorize execution
- replace governance
- silently choose among multiple open steps
- behave like an unbounded workflow engine

## 4. Main implementation changes

### Planning package

Replaced the old thin planning file with a real package:

- `jeff/cognitive/planning/__init__.py`
- `jeff/cognitive/planning/models.py`
- `jeff/cognitive/planning/gating.py`
- `jeff/cognitive/planning/formation.py`
- `jeff/cognitive/planning/progression.py`
- `jeff/cognitive/planning/action_bridge.py`
- `jeff/cognitive/planning/persistence.py`
- `jeff/cognitive/planning/validation.py`
- `jeff/cognitive/planning/checkpoint.py`
- `jeff/cognitive/planning/api.py`

### Shared step model

`PlanStep` was expanded in `jeff/cognitive/types.py` into the authoritative shared step model with explicit step ids, ordering, type, objective, dependencies, assumptions, risks, checkpoint posture, candidate action summary, and step status.

### Conditional planning gate

Implemented deterministic planning gate reasoning with explicit trigger reasons including:

- operator requested
- proposal marked planning needed
- planning insertion proposal selected
- blockers present
- multi-step
- review-heavy
- high-risk
- time-spanning
- dependency-heavy
- checkpoint-heavy

### Deterministic plan formation

Implemented bounded plan formation that produces a 3-step plan:

1. review plan basis
2. execute bounded validation step
3. review outcome and checkpoint decision

### Checkpoint progression

Implemented explicit checkpoint decisions:

- `continue_next_step`
- `revalidate_plan`
- `replan_from_here`
- `escalate`
- `stop_complete`
- `stop_failed`

### Active-step action bridge

Implemented active-step action materialization. The bridge can produce a bounded `Action` candidate only when the active step is actionable. Review-only steps remain non-executable by design.

### Runtime and orchestrator wiring

Added a new flow family:

- `conditional_planning_execution`

`/run` now uses this flow family and routes into planning only when the planning gate says it should.

### Persistence

Planning artifacts now persist through flow-run support records via `jeff/runtime_persistence.py` with `kind = "plan_artifact"`.

### Operator surface

Added:

- `/plan show [run_id]`
- `/plan steps [run_id]`
- `/plan checkpoint [decision] [run_id]`

Run inspection surfaces also now include planning summary data.

## 5. Files changed

Core implementation files changed in this slice:

- `jeff/cognitive/__init__.py`
- `jeff/cognitive/post_selection/plan_action_bridge.py`
- `jeff/cognitive/types.py`
- `jeff/cognitive/planning/__init__.py`
- `jeff/cognitive/planning/action_bridge.py`
- `jeff/cognitive/planning/api.py`
- `jeff/cognitive/planning/checkpoint.py`
- `jeff/cognitive/planning/formation.py`
- `jeff/cognitive/planning/gating.py`
- `jeff/cognitive/planning/models.py`
- `jeff/cognitive/planning/persistence.py`
- `jeff/cognitive/planning/progression.py`
- `jeff/cognitive/planning/validation.py`
- `jeff/interface/commands/plan.py`
- `jeff/interface/commands/registry.py`
- `jeff/interface/commands/scope.py`
- `jeff/interface/json_views.py`
- `jeff/interface/render.py`
- `jeff/orchestrator/flows.py`
- `jeff/orchestrator/validation.py`
- `jeff/runtime_persistence.py`

Tests changed or added:

- `tests/unit/cognitive/test_conditional_planning.py`
- `tests/unit/cognitive/test_planning_runtime.py`
- `tests/unit/cognitive/post_selection/test_plan_action_bridge.py`
- `tests/integration/test_cli_run_live_context_execution.py`
- `tests/integration/test_cli_planning_operator_surface.py`

## 6. Important implementation detail

An import cycle appeared during the refactor when `PlanStep` was moved behind the new planning package.

Root cause:

- shared cognitive code depended on planning package exports
- planning package internals depended back on shared cognitive types

Fix:

- restored `PlanStep` as the shared authoritative type in `jeff/cognitive/types.py`
- changed planning models to import `PlanStep` from the shared type layer instead of re-exporting it as the source of truth

This kept planning below orchestration/package-level import pressure and removed the cycle cleanly.

## 7. Tests run

Targeted planning suite:

```text
python -m pytest -q tests/unit/cognitive/test_conditional_planning.py tests/unit/cognitive/test_planning_runtime.py tests/unit/cognitive/post_selection/test_plan_action_bridge.py tests/integration/test_cli_run_live_context_execution.py tests/integration/test_cli_planning_operator_surface.py
```

Result:

```text
30 passed in 25.20s
```

## 8. Live runtime verification

All live runtime checks were run serially, one command flow at a time.

### Non-planning trigger path

Verified with a bounded fake-proposal runtime path where the selected option stayed direct action.

Observed:

- flow family: `conditional_planning_execution`
- `planning_summary.available = false`
- no planning stage entered
- selected proposal remained executable without planning

The downstream execution failed truthfully because the temporary runtime directory did not contain the referenced smoke test files. That failure was acceptable for this verification because the planning question was whether planning incorrectly triggered. It did not.

### Planning trigger path

Verified with a bounded fake-proposal runtime path where selection chose a `planning_insertion` proposal.

Observed on `/run "Plan the bounded validation path before execution."`:

- `routing_decision.routed_outcome = planning`
- `active_stage = planning`
- `run_lifecycle_state = blocked`
- `orchestrator_lifecycle_state = waiting`
- `plan_status = active`
- active step was `plan:run-1:proposal-2:step-1`
- active step title was `Review plan basis`
- candidate action unavailable because the active step was review-only

This confirmed that planning stayed support-only and did not collapse into action permission or execution.

### Plan inspection and checkpoint progression

Observed on `/plan show`:

- plan id `plan:run-1:proposal-2`
- selected proposal id `proposal-2`
- step count `3`
- active step type `review`

Observed on `/plan checkpoint continue_next_step`:

- latest checkpoint decision `continue_next_step`
- active step advanced to `plan:run-1:proposal-2:step-2`
- plan stayed `active`
- resume posture became `resume_allowed`

### Restart and readback verification

After restart and `/run use run-1`, observed on `/plan show`:

- persisted active step still `plan:run-1:proposal-2:step-2`
- active step type `validation`
- candidate action available
- candidate action id `action:planned:proposal-2:plan:run-1:proposal-2:step-2`
- candidate intent summary `Prepare the bounded repo-local validation path`

This verified durable persistence and truthful readback of checkpoint progression.

## 9. Operator surface summary

The planning surface is now operator-visible in both direct plan commands and run inspection.

Operators can now see:

- whether planning exists for a run
- plan status
- active step id and type
- step-by-step plan structure
- checkpoint history
- whether the current active step can form a lawful action candidate
- why no action candidate exists when the step is review-only or orchestration must fail closed

## 10. Boundary check

This slice preserves the required architectural boundaries.

Planning is:

- conditional
- support-only
- deterministic
- persisted for inspectability
- not canonical truth

Planning is not:

- selection
- permission
- readiness
- governance
- execution authority
- hidden orchestration policy

The plan-to-action bridge remains fail-closed when multiple open steps exist. Orchestration does not guess.

## 11. Exact status

Completed in this slice:

- planning package refactor
- richer plan and step model
- conditional planning gate
- deterministic bounded plan formation
- plan persistence and readback
- active-step action bridge
- deterministic checkpoint progression
- operator inspection surfaces
- targeted tests
- live serial runtime verification

## 12. Remaining gap

The slice is complete for bounded Planning v1, but the next natural extension is not more basic planning formation. The next useful improvement would be deeper integration between planned active-step execution, governance re-entry, and downstream outcome/evaluation loops once the user wants Jeff to use this planning layer for richer resumed execution flows.

## 13. Final judgment

Planning is now a real Jeff runtime layer rather than a thin placeholder.

It is deterministic, bounded, inspectable, restart-safe, and still architecturally subordinate to truth, governance, and execution. That is the correct v1 outcome for this slice.