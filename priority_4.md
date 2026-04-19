# Priority 4 Execution Checklist

## Title

Real approval-required operator workflow.

## Goal

Make `approve` and `revalidate` a genuinely useful bounded v1 workflow for approval-required runs. `reject` may become a truthful terminal operator action. `retry` and `recover` remain deferred unless the earlier slices expose a narrow, evidence-backed need.

## Dependency status

- Depends on: `priority_1.md`, `priority_2.md`, and `priority_3.md` complete.
- Must finish before: `priority_6.md`.

## Ticket slices

### P4-T1. Durable approval record

- Outcome: `approve` writes a bounded approval record tied to a specific action identity, scope, and governing basis.
- Done when:
- Approval cannot be vague or blanket.
- Approval is invalidated if the action basis changes materially.

### P4-T2. Revalidate continuation path

- Outcome: `revalidate` can continue an approval-required run lawfully or fail closed when the basis changed.
- Done when:
- Governance remains authoritative.
- The continuation path is explicit and inspectable.

### P4-T3. Truthful terminal reject path

- Outcome: `reject` stops the continuation path truthfully without implying apply or mutation.
- Done when:
- The operator can see what was rejected and why the run did not continue.

## File-by-file implementation checklist

### jeff/governance/approval.py

- Add the bounded approval record model or extension required for real operator approval.
- Bind approval to action identity, scope, and governing basis.
- Add staleness or mismatch invalidation rules where needed.

### jeff/governance/action_entry.py

- Ensure revalidation can consume a real approval record and current truth together.
- Fail closed on stale or mismatched approvals.

### jeff/orchestrator/continuations/

- Add the bounded continuation logic for approval-required runs.
- Keep continuation explicit and operator-triggered.
- Do not add autonomous background continuation.

### jeff/orchestrator/routing.py

- Preserve approval-required routing and add the bounded follow-up route shapes needed for approve and revalidate.
- Keep retry and recover out unless explicitly justified later.

### jeff/orchestrator/runner.py

- Add the continuation entrypoints or resume paths needed for revalidation.
- Preserve fail-closed routing behavior.

### jeff/interface/command_requests.py

- Upgrade `approve` from receipt-only to bounded record creation.
- Upgrade `revalidate` from receipt-only to lawful continuation entry.
- Upgrade `reject` from receipt-only to truthful terminal handling.
- Keep `retry` and `recover` visibly bounded or deferred if they remain receipts.

### jeff/runtime_persistence.py

- Persist any bounded approval or request-status support records needed for reloadable operator inspection.
- Keep these distinct from canonical truth unless a narrow canonical truth change is required through transitions.

### jeff/interface/json_views.py and jeff/interface/render.py

- Add truthful operator visibility for approval status, revalidation outcome, and rejected continuation.
- Preserve request-versus-effect distinctions clearly.

## Test cases to add or update

### New unit tests for approval binding and invalidation

- Add tests for approval bound to action identity and scope.
- Add tests for stale approval invalidation.
- Add tests for mismatch invalidation when the action basis changed.

### New integration tests for approve then revalidate

- Start from an approval-required `/run`.
- Approve it.
- Revalidate it.
- Confirm lawful continuation to execution or truthful fail-closed invalidation.

### Acceptance test for approval-required workflow

- Add one acceptance slice where an approval-required run becomes executable only after lawful operator approval.
- Add a rejection slice that remains terminal and truthful.

## Operator validation checklist

- Produce an approval-required `/run`.
- Run `/approve` and confirm it records a bounded approval, not a fake completion.
- Run `/revalidate` and confirm it either continues lawfully or explains why not.
- Run `/reject` and confirm the run stops truthfully.

## Suggested validation commands

```text
python -m pytest -q tests/unit/governance tests/unit/interface tests/integration
python -m pytest -q
```

## Non-goals

- No queueing system.
- No background resumption engine.
- No broad approval bureaucracy.
- No automatic retry or recovery workflow.

## Slice completion gate

- This priority is not done if `approve` and `revalidate` still behave like decorative receipts.
- This priority is not done if stale approvals can still start execution.
- This priority is not done if the interface blurs approved, revalidated, executing, and completed states.
