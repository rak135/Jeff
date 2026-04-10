# Purpose

This document defines Jeff's canonical review/apply/change-control law.

It owns:
- the canonical meaning of `Change`
- the change-control lifecycle
- review, approval, apply, and reject distinctions
- the approval-to-apply boundary
- revalidation-before-apply rules
- review artifact status
- apply outcome categories
- change-control invariants
- change-control failure modes and anti-patterns

It does not own:
- truth mutation law itself
- state topology
- governance semantics in general
- execution semantics in general
- interface rendering design
- telemetry schema design
- roadmap sequencing

This is the canonical review/apply/change-control document for Jeff.
It exists to govern reviewable and applyable support objects without turning `Change` into a second transition system.

# Canonical Role in Jeff

Change control exists to manage reviewable and applyable support objects for bounded intended modification.
It keeps review, approval, apply, reject, and revalidation explicit without weakening transition supremacy.

Jeff still operates inside:
- one global canonical state with nested projects
- project as a hard isolation boundary inside that state
- `project + work_unit + run` as the foundational scope containers change control must respect

Jeff cannot tolerate:
- `Change` acting like a rival mutation primitive
- approval and apply being flattened together
- review artifacts being treated as truth or mutation authority
- apply uncertainty being smoothed into success
- rollback or reconciliation support being treated as direct truth repair

The hard boundary is:
- transitions own canonical truth mutation
- governance owns permission
- approval and readiness remain governance objects
- execution owns doing
- execution, outcome, and evaluation remain distinct
- change control owns the review/apply support path around bounded intended modification

If change-control pressure conflicts with transition law, transition law wins.

# Core Principle

The binding law is:
- `Change` is a support/review/apply object family
- `Change` does not mutate canonical truth by itself
- approval is not apply
- apply is not transition
- review artifacts are not truth
- when in doubt, change control fails closed rather than pretending effect or truth

Change control may govern how Jeff prepares, reviews, attempts, verifies, rejects, supersedes, or revalidates a bounded intended modification.
It never creates a second truth-mutation contract.

# What Change Is

`Change` is a bounded support object for reviewable and applyable intended modification.

`Change` may represent:
- a bounded intended modification to a real-world target or managed surface
- a reviewable mutation candidate that may later be approved, rejected, superseded, or applied
- a support object that preserves intended target, scope, lineage, and apply history

`Change` may legitimately carry:
- stable identity
- target and scope
- intended modification summary
- review lineage
- approval binding
- apply lineage and apply status
- verification or support refs
- supersession or invalidation lineage

`Change` may support:
- operator review
- governed self-modification flows when those are in scope
- non-Jeff project work that needs bounded modification control
- later transition work when verified effect needs canonical truth to be updated

`Change` is not current truth.
It may participate in a real-world apply path.
It may later inform a transition.
It does not become truth by existing or by being approved.

# What Change Is Not

`Change` is not:
- a truth mutation primitive
- a transition replacement
- approval itself
- readiness itself
- an evaluation verdict
- patch text as authority
- diff as truth
- applied-by-appearance semantics
- hidden workflow authority
- execution itself
- rollback or reconciliation law

Patch text, diff views, previews, and review notes may describe or support a change.
They do not become authoritative mutation law or current truth.

# Change-Control Lifecycle

The canonical whole-Jeff lifecycle is:

1. `created_for_review`
   A bounded `Change` exists as a reviewable intended modification.
2. `reviewed`
   The change has been inspected or compared, but is not yet authorized to apply.
3. `approved` or `rejected`
   Governance or operator decision has been recorded for the change-control path.
4. `revalidation_required` when needed
   Prior review or approval basis is stale, mismatched, or otherwise no longer safely current.
5. `apply_attempted`
   A bounded real-world apply path starts only after lawful basis is current.
6. apply outcome
   The change becomes one of the bounded apply outcomes defined below.
7. downstream support if needed
   Rollback, reconciliation, escalation, or follow-up review may occur as separate support flows.
8. later transition work where relevant
   If verified effect needs canonical truth to change, that still occurs through transitions only.

Lifecycle rules:
- approval may never be skipped silently
- apply may never be inferred from review or approval
- revalidation may interrupt the path before apply
- reject closes the current change-control path without claiming any effect
- supersession preserves lineage rather than pretending the old change never existed

# Review / Approval / Apply / Reject Distinctions

These distinctions are hard.

Review is inspection.
It may examine:
- scope
- target
- assumptions
- risks
- previews
- diffs
- apply plan quality
- stale-basis signs

Review does not:
- grant permission
- prove readiness
- prove effect
- mutate truth

Approval is permission for the change-control path.
It answers whether this bounded change may proceed to an apply attempt if current basis still holds.

Approval does not:
- prove apply succeeded
- replace readiness or pre-apply guards
- replace transition commit
- guarantee that the real target still matches the approved basis

Apply is the bounded attempt to cause the declared external or operational effect.
Apply is an effect stage, not a permission stage.
It may:
- succeed
- fail
- be blocked
- become uncertain
- require revalidation

Reject stops the current change-control path.
Reject means:
- do not apply this change in its current form
- do not claim any effect
- do not update truth by change-control convenience

Any later canonical truth update still belongs to transitions.

# Revalidation Before Apply

Prior review or approval basis can go stale.
Change control must treat that as normal, not exceptional.

Revalidation before apply is required when any of the following is true:
- current truth changed materially
- target state changed materially
- project, work unit, or run scope changed materially
- the approved change no longer matches the current intended modification
- blockers, degraded-trust conditions, or mismatch conditions appeared
- operator or policy constraints changed materially
- meaningful time passed on a freshness-sensitive change
- the apply path resumed after pause, interruption, or recovery
- prior verification or review artifacts are no longer strong enough to trust

Revalidation rules:
- stale approval is not evergreen apply authority
- stale review is not current review
- if current basis cannot be re-established, apply must not proceed
- if current basis is uncertain, the path fails closed into `revalidation_required`, `apply_blocked`, or escalation rather than "probably still valid"

Revalidation is not transition law.
It is the change-control guard against old green lights being reused dishonestly.

# Review Artifact Status

Review artifacts are support artifacts only.

This includes:
- patch text
- diffs
- previews
- comparison artifacts
- apply plans
- review notes
- verification notes

Their lawful role is to:
- support inspection
- support operator understanding
- support approval decisions
- support apply verification
- preserve review lineage

Their forbidden role is to:
- become current truth
- become mutation law
- prove apply success by existence alone
- override current basis checks
- substitute for transitions

Artifact rules:
- patch or diff existence is not apply success
- review artifact quality is not truth authority
- support artifacts may be linked from `Change`, but the change-control path must still rely on explicit approval, explicit apply outcome, and later transitions where truth changes matter
- interface surfaces must label these objects as support, not truth

# Apply Outcome Categories

Jeff uses a bounded apply outcome family:
- `applied`
- `apply_failed`
- `apply_blocked`
- `apply_uncertain`
- `revalidation_required`
- `superseded`

Use them as follows:

`applied`
- use only when the bounded apply attempt completed and verification is strong enough to say the intended effect occurred within declared scope
- `applied` is still not the same thing as canonical truth mutation

`apply_failed`
- use when the intended effect did not occur, or did not occur sufficiently, and the resulting external state is known well enough to say the change is not applied
- a failed apply may still lead to rollback or reconciliation support

`apply_blocked`
- use when apply did not lawfully begin or could not proceed because approval, scope, target fit, guards, policy, or current conditions blocked it before real effect

`apply_uncertain`
- use when some external effect may have occurred or verification is too weak, contradictory, or incomplete to claim either clean success or clean failure
- `apply_uncertain` must remain visibly dangerous

`revalidation_required`
- use when the path reached apply time but current basis was stale, mismatched, or otherwise not safe to trust without renewed checking
- this is not clean failure and not permission to continue

`superseded`
- use when a newer or more current bounded change replaces this one, or when basis changed enough that the old change should no longer be applied

Partial external-effect handling:
- partial external effect never becomes `applied` by default
- if final target state cannot be confidently classified, partial effect maps to `apply_uncertain`
- if the target state is known and the intended effect was not actually achieved, partial effect maps to `apply_failed`
- partial, degraded, or uncertain effect must remain visible and inspectable

Rollback and reconciliation relation:
- rollback or reconciliation may be recommended or triggered downstream of `apply_failed` or `apply_uncertain`
- those flows do not themselves certify canonical truth
- later truth repair still belongs to transitions

# Change-Control Invariants

The following invariants are binding:
- Jeff has one global canonical state with nested projects
- project is the hard isolation boundary change control must respect
- `Change` is not transition
- approval is not apply
- apply is not truth mutation
- review artifacts are support only
- stale basis requires revalidation
- apply uncertainty stays visible
- rejected does not imply effect
- applied does not by itself imply canonical truth change
- project, work unit, and run scope must remain explicit where relevant
- transitions remain the only canonical truth mutation contract
- interfaces remain downstream truthful surfaces
- orchestrator may route change-control stages but does not think and does not own their semantics
- workflow is not first-class canonical truth in v1
- planning is conditional and does not authorize apply

# Failure Modes / Anti-Patterns

The change-control layer is failing if any of the following happens:
- `Change` becomes rival mutation law
- approval equals applied
- diff or patch equals truth
- apply certainty is faked after ambiguous effect
- stale approved change is applied without revalidation
- review artifact is shown as authoritative reality
- operator surface claims completion before backend confirmation
- change-control path silently bypasses transition law
- giant patch-driven control blob replaces structured change discipline
- rollback success is treated as automatic truth repair
- reconciliation support is treated as direct mutation authority
- partial external effect is greenwashed into success
- blocked or revalidation-required paths are collapsed into vague waiting

# v1 Enforced Change-Control Model

v1 enforces a conservative change-control model.

v1 enforces:
- hard separation between review, approval, apply, reject, and transition
- `Change` as a bounded support/review/apply object only
- support-artifact-only status for diffs, patches, previews, and review notes
- fail-closed revalidation-before-apply discipline
- explicit bounded apply outcome categories
- visible handling for uncertain or partial external effect
- no truth mutation by change-control convenience
- no approval-implies-applied flattening in backend or interface surfaces
- no patch execution or diff execution as mutation authority

v1 does not require:
- a giant self-modification framework
- a heavy universal change taxonomy
- detailed backup, rollback, or reconciliation submodels in this document
- broad autonomous apply loops

Where v1 uses change control at all, it must stay explicit and honest.

# Deferred / Future Expansion

Deferred expansion may later add:
- richer merge and supersession handling
- stronger external-effect verification families
- richer apply lineage and verification artifacts
- more expressive review artifact families
- stronger operator tooling around change control
- more explicit rollback, reconciliation, and recovery integrations if later promoted canonically

Deferred expansion does not weaken the current law.
Future change-control richness still remains subordinate to governance, execution, and transition law.

# Questions

No unresolved change-control questions were found in this pass.

# Relationship to Other Canonical Docs

- `TRANSITION_MODEL_SPEC.md` owns the only canonical truth mutation contract; this document subordinates `Change` under that law.
- `STATE_MODEL_SPEC.md` owns truth placement and keeps support objects from becoming canonical truth.
- `POLICY_AND_APPROVAL_SPEC.md` owns approval and readiness semantics in general; this document defines how approval relates to the change-control path without redefining governance.
- `ARCHITECTURE.md` owns the layer boundaries that keep change control from becoming hidden transition law, hidden governance, or hidden orchestration semantics.
- `GLOSSARY.md` owns the meanings of `Change`, `transition`, `approval`, `readiness`, `rollback`, and `reconciliation`.
- `CORE_SCHEMAS_SPEC.md` owns shared naming and object-family rules that this document must respect.
- `EXECUTION_OUTCOME_EVALUATION_SPEC.md` owns general execution, outcome, and evaluation law; this document specializes the review/apply support path without replacing that stage chain.
- `INTERFACE_OPERATOR_SPEC.md` owns truthful operator surfaces that may show review, approval, apply, and reject states without flattening them.
- `ORCHESTRATOR_SPEC.md` owns sequencing and routing; it may coordinate change-control stages through public contracts only.
- `ROADMAP_V1.md` defines when and how much of this change-control model v1 actually delivers.

# Final Statement

Jeff change control is a support path for reviewable and applyable intended modification.

`Change` may be reviewed, approved, rejected, revalidated, applied, blocked, superseded, or found uncertain.
None of that makes it mutation law.
Truth still changes only through transitions.

If this boundary stays hard, Jeff can support bounded real-world modification control without creating a second truth system.
If it softens, `Change` will become a rival mutation primitive, approval will drift into fake success, and the system will start lying about what actually happened.
