# Planned Step Execution Report

## Scope

This slice implements bounded active-step execution on top of Planning v1.

Jeff can now:

- persist per-step runtime posture inside the plan artifact
- identify the active planned step
- materialize one bounded action candidate from that step when lawful
- re-enter governance on that candidate with fresh current truth
- execute at most one planned step
- normalize outcome and evaluate it
- derive a deterministic checkpoint decision from evaluation
- persist the updated plan state and runtime posture
- sync run truth from the updated flow run
- resume truthfully after restart from the next active step

This remains one-step-at-a-time. No hidden loop was added.

## Design

The implementation stayed in the command layer around `/plan execute [run_id]`.

Reason:

- it reuses the existing lawful execution chain already used by `/run`
- it keeps operator control explicit
- it avoids adding a second orchestration runner or a hidden planning loop
- it avoids any new planner model call
- it keeps planning support-only and persisted on the flow run

## Product Changes

Main code changes in this slice:

- `jeff/interface/commands/plan.py`
  - added `/plan execute [run_id]`
  - made `plan checkpoint` update lifecycle, routing, persistence, and run truth consistently
  - reused fresh governance inputs, governed execution, outcome normalization, evaluation, checkpoint progression, flow persistence, and run-truth sync
- `jeff/interface/render.py`
  - added `render_plan_execute(...)`
  - exposed active/latest step runtime posture in run/plan views
  - added help text for `/plan execute`
- `jeff/interface/json_views.py`
  - exposed `/plan execute` as the next bounded operator action when routing is `planning` and the active candidate is available

Supporting model/persistence/progression/view scaffolding from the earlier in-session edits is now exercised by the real command path.

## Validation

Targeted tests run:

```text
python -m pytest -q tests/unit/cognitive/test_planning_runtime.py tests/integration/test_cli_planning_operator_surface.py
```

Observed result:

```text
6 passed in 0.55s
```

No language-service errors remained in the changed command/view files after wiring.

## Runtime Verification

I ran a bounded end-to-end probe through the real command stack in an isolated temporary runtime.

Verification setup:

- startup context and persistence used a temp runtime directory
- proposal and selection were the existing planning test doubles so the run deterministically entered the planning path
- `/plan execute` itself used the real command implementation, real governance evaluation, real execution path, real outcome normalization, real evaluation, real checkpoint progression, and real persistence/readback
- for the executable-step probe, the repo-local validation working directory was pointed at the repository root so the real smoke suite was available while keeping runtime state isolated

### Observed results

Initial planning run:

- `run_id = run-1`
- `routing_decision.routed_outcome = planning`
- `plan_status = active`
- `active_step_id = plan:run-1:proposal-2:step-1`
- `candidate_available = false`

`/plan execute` on the review-only active step:

- `executable = false`
- `executed = false`
- `reason = No action candidate formed because the active step is review-only.`
- `plan_status = active`
- `active_step_runtime_state = not_executable`

Manual checkpoint progression:

- `/plan checkpoint continue_next_step`
- latest checkpoint decision became `continue_next_step`
- active step advanced to `plan:run-1:proposal-2:step-2`

`/plan execute` on the executable validation step:

- `executable = true`
- `executed = true`
- `governance_outcome = allowed_now`
- `execution_status = completed`
- `exit_code = 0`
- `evaluation_verdict = acceptable`
- deterministic checkpoint decision = `continue_next_step`
- resulting `plan_status = active`
- next active step became `plan:run-1:proposal-2:step-3`

Restart readback:

- persisted `plan_status = active`
- persisted `active_step_id = plan:run-1:proposal-2:step-3`
- latest runtime record state = `checkpointed`
- latest runtime execution status = `completed`
- latest runtime evaluation verdict = `acceptable`
- candidate availability on restart = `false`

## Boundary Check

Boundaries preserved in the implemented slice:

- planning runtime facts stay inside `PlanArtifact.step_runtime_records`
- no new truth layer was added
- governance is re-entered fresh on execution attempts; no stale permission is reused
- only one active planned step is executed per `/plan execute`
- downstream progression is deterministic from evaluation output, not model-generated
- operator surfaces now show truthful runtime posture instead of forcing inference from old execution outputs

## Current Status

This bounded slice is implemented and validated.

Jeff now supports planned active-step execution with governance re-entry, deterministic checkpoint progression, persisted runtime posture, and restart-safe continuation, while remaining explicitly one-step-at-a-time.

## Remaining Risk

The main remaining limitation is not correctness of the one-step path. It is breadth.

This slice does not add any auto-resume loop or richer multi-step automation, by design. Further expansion should stay explicit about where operator control ends and where hidden orchestration must still fail closed.
