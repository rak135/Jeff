# Purpose

This document defines Jeff's canonical truth mutation law.

It owns:
- what a transition is and is not
- the lawful transition lifecycle
- transition input discipline
- transition validation layers
- commit and reject law
- diff and audit requirements for truth mutation
- truth-mismatch handling at the mutation boundary
- referential-integrity rules for committed mutation
- the boundary between transitions and support flows such as `Change`, apply, rollback, and reconciliation

It does not own:
- state topology
- policy meaning
- module-local business logic
- interface display contracts
- telemetry schemas
- test matrices
- roadmap sequencing

This is the canonical whole-Jeff transition-model document.
It is not a vague mutation philosophy essay, not an implementation-status report, and not a rival to the state or policy docs.

# Canonical Role in Jeff

Transitions are the only lawful path from current canonical truth to new canonical truth.

Jeff cannot tolerate rival mutation paths in:
- execution side effects
- apply results
- `Change`
- memory
- event history
- interface actions
- workflow progression
- manual direct writes

If any of those can mutate truth by themselves, Jeff immediately loses auditability, scope control, and truthful state.
This document protects the rest of the canon by making one hard answer explicit:
truth changes only through validated transition commit.

# Core Principle

All canonical truth changes must be:
- explicit
- scoped
- validated
- versioned
- committed through transitions

Transition commit is fail-closed.
If validation is missing, inconclusive, or unsafe, canonical truth does not change.

Support flows may inform, justify, or trigger transitions.
They do not mutate canonical truth by themselves.

# What a Transition Is

A transition is a structured canonical mutation operation over current truth.

A lawful transition is:
- built against current committed canonical state
- scoped to explicit global, project, work-unit, run, or other canonized truth surfaces
- validated against shared schema, topology, policy, evidence, and reference rules
- applied first to a candidate state, never directly to canonical truth
- version-advancing only on commit
- auditable as a first-class truth-mutation record

Only Core constructs, validates, commits, or rejects authoritative transitions.

# What a Transition Is Not

A transition is not:
- a direct write shortcut
- an execution side effect
- an apply result
- `Change`
- approval
- readiness
- an evaluation verdict
- workflow progression
- an interface action
- a memory write
- rollback itself
- reconciliation itself
- a patch
- a diff
- a trace
- a log line

Those things may produce evidence, triggers, or support objects.
They do not become mutation authority by existing.

# Transition Lifecycle

Every lawful truth mutation follows this lifecycle:

1. Current truth read and basis fixation.
   Core reads the current canonical state, fixes the mutation scope, and binds the expected current basis, including the current global `state_version`.

2. Proposed update basis assembly.
   Jeff gathers the allowed mutation inputs for that scope, including operator decisions, relevant governance outputs, evidence-backed module outputs, verified real-state observations where applicable, and committed linkage refs.

3. Candidate construction.
   Core constructs an explicit candidate next state and an explicit intended truth delta without mutating canonical truth.

4. Transition validation.
   The candidate and its mutation basis pass through all required validation layers.

5. Candidate-state apply and coherence check.
   Core checks that the candidate state is internally coherent, referentially sound, scoped correctly, and free of illegal support-object leakage.

6. Commit or reject.
   If and only if the candidate passes the full validator stack and can be committed safely, Core commits the transition atomically enough to preserve truthful canonical state.
   Otherwise Core rejects the transition and canonical truth remains unchanged.

7. Audit emission.
   Jeff records the committed or rejected transition result with explicit lineage, reason, and mutation visibility.

No step may be skipped.
No module may mutate canonical truth before step 6.

# Transition Input Rules

The following may legitimately inform a transition:
- current canonical state
- current global `state_version` and scoped basis
- typed scope identifiers such as `project_id`, `work_unit_id`, and `run_id`
- operator decisions
- policy, approval, or readiness outputs where those are relevant gating inputs
- evidence-backed outcome and evaluation outputs
- authoritative config or direction inputs when they are part of current truth
- verified real-state observations from apply, rollback, recovery, or reconciliation support flows
- committed `memory_id` link inputs only
- canonically justified artifact or source refs where the link itself matters to truth

The following may not serve as authoritative mutation input by themselves:
- raw execution output
- apply success claims without verification
- `Change`
- approval or readiness alone
- evaluation verdict alone
- workflow progression
- interface cache or session state
- memory bodies
- uncommitted memory candidates
- failed or pending memory writes
- patches, diffs, traces, or event-log entries
- support-object payloads embedded as substitute truth

Input rule:
support information may justify or constrain a transition, but it never becomes truth without transition discipline.

# Transition Validation Layers

Transition commit requires a layered fail-closed validator stack.
At minimum, the following layers are binding:

1. Shared schema validity.
   The transition request, scope, typed IDs, and shared machine-facing fields must satisfy `CORE_SCHEMAS_SPEC.md`.

2. Basis and version validity.
   The transition must be evaluated against the current committed state and current global `state_version`.
   Stale-basis mutation is illegal.

3. Scope validity.
   Targets must exist in the declared scope and may not drift outside that scope during commit.

4. State-topology validity.
   The candidate post-state must preserve one global canonical state with nested projects, project-local work units, and work-unit-local runs.
   v1 may not smuggle workflow or `action` back in as canonical truth.

5. Transition-type legality.
   The requested mutation must be legal for the affected truth object family and any declared lifecycle or binding transition.

6. Referential integrity.
   All canonical refs must resolve, parent-child ownership must remain sound, and no dangling or contradictory refs may remain after commit.

7. Policy and permission validation.
   The mutation must respect applicable policy, approval, readiness, blocker, and governance constraints.
   Selection, planning, or workflow momentum never substitutes for permission.

8. Evidence alignment.
   The truth change must be supported by evidence-backed findings or verified observed results.
   Unverified side effects, inference blur, or support-object presence are insufficient.

9. Support-object containment validation.
   The candidate state may not embed `selection`, `approval`, `readiness`, `Change`, `outcome`, `evaluation`, or other support payloads as if they were canonical truth.
   Thin refs are allowed only when the link itself is current truth.

10. Memory-link validation.
   Canonical state may reference only committed `memory_id` values.
   Only Memory creates memory candidates, and no pending or failed memory write may be committed into truth.

11. Project-boundary validation.
   Project is a hard isolation boundary inside global state.
   No transition may cross project boundaries except through an explicitly canonized global construct.

12. Candidate-state coherence validation.
   The full candidate must remain structurally complete, internally consistent, and commit-safe.
   No partial canonical commit may be required to make the candidate make sense.

Any failed or inconclusive layer requires reject, not best effort.

# Commit / Reject Rules

Commit is allowed only when all of the following are true:
- the transition is well-typed and valid under shared schema law
- the current basis is still current
- the scope and target set are lawful
- the candidate post-state preserves topology and referential integrity
- applicable policy, approval, and readiness conditions are satisfied
- the truth change is sufficiently evidenced
- any memory links are committed `memory_id` links
- commit can complete without leaving canonical truth in a partial state

Reject is mandatory when any of the following occurs:
- validation fails
- validation is inconclusive
- basis or version mismatch is detected
- required permission or approval is absent
- evidence is insufficient or contradictory for the claimed truth update
- referential integrity would break
- project boundary would be violated
- uncommitted memory would be referenced
- support-object payload would become truth by embed
- storage or commit safety is uncertain

Commit rules:
- no partial canonical commit
- no best-effort truth write
- no optimistic success marking
- no commit on inconclusive validation
- global `state_version` advances only on commit
- rejected transitions leave canonical truth and global `state_version` unchanged

Additional project-, work-unit-, or run-level revision markers may exist, but they are subordinate to the global canonical version lineage.

# Diff and Audit Requirements

Every transition attempt must produce an auditable record.

For committed transitions, the audit record must preserve:
- `transition_id`
- transition type
- scope
- mutation cause or basis refs
- prior global `state_version`
- new global `state_version`
- explicit canonical truth diff or equivalent changed-field summary
- relevant approval, evidence, artifact, or committed memory linkage refs
- result classification
- timestamp

For rejected transitions, the audit record must preserve:
- `transition_id`
- attempted scope and target summary
- failed validation layer or decisive reject reason
- whether canonical truth changed, which must be `no`
- whether mismatch, degraded state, reconciliation, or escalation follow-up is required

Diff rules:
- the diff must describe canonical truth change, not raw support residue
- full artifact bodies, traces, patches, and logs stay outside canonical state and outside the core mutation diff
- if a richer diff artifact exists, the transition record links to it rather than absorbing it

Audit rules:
- transition history is not the same thing as event log
- transition history is not the same thing as decision trace
- transition history must be queryable enough to reconstruct mutation lineage

# Truth-Mismatch Handling

Truth mismatch does not weaken transition law.
It makes fail-closed mutation more important.

When support evidence conflicts with current truth:
- Jeff must not force the disputed target update into truth
- Jeff may reject the intended mutation
- Jeff may escalate or route to reconciliation support flow

When apply result is uncertain:
- Jeff must not commit claimed applied truth
- Jeff may commit only the degraded-trust or blocked condition that is actually supported

When side effects may have happened but truth cannot be safely established:
- Jeff does not guess
- the affected scope may be marked degraded, blocked, or mismatch-affected through a lawful transition if that condition itself is supported
- the disputed target truth remains uncommitted until verified

When references, authority sources, or object graph relations do not line up:
- the intended mutation is rejected
- risky further mutation in the affected scope may be blocked until repair or explicit override lawfully occurs

When degraded-trust conditions appear:
- Jeff may commit integrity, degraded-state, or mismatch truth that is actually evidenced
- Jeff may not use degraded conditions as excuse for direct repair writes

# Transition Types

Transition types should stay typed and bounded, not collapse into a generic patch blob.

Whole-Jeff transition families include:
- system or global truth updates
- project truth changes
- work-unit lifecycle and scope changes
- run lifecycle and bounded terminal-summary changes
- authoritative direction or config/binding updates
- committed memory-link changes
- integrity, blocker, degraded-state, or truth-mismatch marker updates
- explicit reconciliation repair transitions where truth repair is lawful and evidenced

These families are examples of mutation shape, not a giant enum dump.
What matters is that each committed transition names a lawful truth mutation class and stays inside it.

# Referential Integrity Rules

Committed mutation must preserve canonical reference integrity.

Binding rules:
- every canonical `project_id`, `work_unit_id`, and `run_id` reference must resolve
- in v1, every canonical run belongs to exactly one project and exactly one work unit
- no transition may leave dangling refs
- no transition may leave contradictory ownership chains
- no transition may cross a project boundary unless an explicit global construct owns that relationship
- canonical state may reference only committed `memory_id` values
- artifact or source refs may appear only when the link itself is canonically justified
- transition lineage and version linkage must remain intact after mutation

Multi-object mutation is allowed only when those rules still hold at commit time.

# Failure Handling

If a transition is rejected or fails before commit:
- canonical state remains unchanged
- global `state_version` remains unchanged
- the failure remains visible in transition audit
- support flows may continue outside truth mutation, but canonical truth stays protected

If support work changed real-world state but commit cannot safely claim new truth:
- Jeff does not backfill truth optimistically
- the result stays visible as failed, uncertain, degraded, or mismatch-affected according to the evidence

If commit persistence itself is uncertain:
- Jeff does not report successful mutation
- the affected scope must be treated as degraded until the truth situation is resolved lawfully

# Rollback / Reconciliation Boundaries

Rollback is not canonical truth mutation law.
Rollback is a support flow for real-world restoration.
If rollback succeeds and that restored reality is verified, a later transition may record restored canonical truth.

Reconciliation is not canonical truth mutation law either.
Reconciliation is the support flow for investigating and repairing truth mismatch.
If reconciliation reaches a lawful, evidenced repair basis, the actual truth repair still commits through explicit transition(s).

Apply, rollback, recovery, revalidation, and reconciliation support flows may:
- gather evidence
- classify degraded conditions
- propose repair paths
- require later transition work

They may not:
- bypass transition validation
- directly rewrite canonical truth
- become rival mutation systems

# Transition Invariants

The following invariants are binding:

- canonical truth mutates only through transitions
- Jeff has one global canonical truth system
- no direct writes to canonical state are allowed
- no partial canonical commit is allowed
- no rival mutation primitive is allowed
- no uncommitted memory refs may appear in truth
- no support object becomes mutation law
- no project-boundary violation is allowed
- global version integrity is preserved
- auditable mutation lineage is preserved
- execution side effects do not become truth automatically
- outcome and evaluation may inform mutation but do not mutate truth
- approval and readiness constrain mutation where relevant but do not replace it
- workflow progression is not mutation authority
- truth mismatch strengthens fail-closed behavior rather than weakening it

# Forbidden Mutation Anti-Patterns

The following are forbidden:

- direct state mutation
- `Change` as rival mutation law
- apply-implies-truth
- execution-implies-truth
- approval-implies-apply
- evaluation-implies-truth
- workflow progression as mutation authority
- interface-owned writes
- partial canonical commit
- silent mutation on repair or reconciliation
- memory-as-truth-repair
- truth update from unverified side effects
- patch-as-transition
- diff-as-transition
- event-log-as-truth
- trace-as-truth
- degraded-state greenwashing

# v1 Enforced Transition Model

v1 enforces the following transition model:

- one Core-owned transition system for one global canonical state with nested projects
- typed, scoped transitions over canonical global, project, work-unit, and run truth
- current-state basis fixation against the current global `state_version`
- candidate-state construction before commit
- layered validation covering schema, scope, topology, references, policy, evidence, memory-link legality, and support-object containment
- fail-closed commit or reject only
- no partial canonical commit
- no best-effort truth write
- global `state_version` advancement only on commit
- auditable commit and rejection records
- `Change` retained only as support or apply intent, never as a truth-mutation primitive
- outcome, evaluation, approval, readiness, execution, and memory outputs allowed as inputs or refs, not as mutation authority
- only committed `memory_id` values allowed in canonical truth
- workflow not treated as first-class canonical truth mutation authority

This is enough to stop the main legacy drift:
direct-write shortcuts, `Change` supremacy, apply-implies-truth, and hidden repair writes.

# Deferred / Future Expansion

Deferred expansion may add:
- richer rollback tooling and restoration guarantees
- richer reconciliation support and repair orchestration
- stronger typed degraded-state and truth-mismatch objects
- finer conflict-resolution and stale-basis handling for more advanced concurrency
- richer replay, audit, and mutation-inspection tooling

Deferred expansion does not relax the core law.
Future Jeff may gain better mutation tooling, but not a second mutation contract.

# Questions

No unresolved transition-model questions were found in this pass.

# Relationship to Other Canonical Docs

- `ARCHITECTURE.md` owns the structural law that makes transitions the only truth-mutation path.
- `GLOSSARY.md` owns the meanings of `transition`, `Change`, `approval`, `readiness`, `outcome`, `evaluation`, `rollback`, and `reconciliation`.
- `CORE_SCHEMAS_SPEC.md` owns shared IDs, reference primitives, envelope rules, and schema-version law used by transition I/O.
- `STATE_MODEL_SPEC.md` owns canonical state topology and what may live in canonical truth.
- `POLICY_AND_APPROVAL_SPEC.md` owns permissioning semantics that transitions must respect where relevant.
- `PROJECT_AND_WORK_UNIT_MODEL_SPEC.md` owns project, work-unit, and run container semantics and lifecycle detail.
- `EXECUTION_OUTCOME_EVALUATION_SPEC.md` owns execution, outcome, and evaluation semantics that may inform transitions but do not replace them.
- `MEMORY_SPEC.md` owns memory creation, write discipline, and retrieval rules; this document only constrains how committed memory links may enter truth.
- `ORCHESTRATOR_SPEC.md` owns sequencing; it may trigger transition flow but does not own mutation law.
- `CHANGE_CONTROL_SPEC.md` owns `Change`, apply, rollback, revalidation, recovery, and reconciliation support-flow semantics under this document's mutation law.

# Final Statement

Jeff has one lawful truth-mutation contract.

That contract is transition commit:
explicit, scoped, validated, candidate-based, fail-closed, versioned, and auditable.

`Change`, apply, rollback, reconciliation, outcome, evaluation, memory, workflow, and interface actions may all matter.
None of them become truth mutation law.

If this boundary stays hard, Jeff can evolve without lying about what is true.
If it softens, Jeff collapses into side effects, guessed state, and rival mutation stories.
