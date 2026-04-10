# Purpose

This document defines Jeff's canonical permissioning and action-entry law.

It owns:
- governance scope
- policy layers
- approval semantics
- readiness semantics
- action-entry law
- allowed, blocked, approval-gated, deferred, invalidated, and escalated governance outcomes
- autonomy boundaries
- the governance meaning of direction, scope, config, and related truth inputs
- governance outputs
- revalidation and staleness rules
- escalation rules
- governance invariants and failure modes

It does not own:
- state topology
- transition lifecycle or commit law
- module-local reasoning logic
- interface display contracts
- telemetry schemas
- test matrices
- roadmap sequencing

This is the canonical Jeff governance document for action permissioning.
It is not a governance philosophy essay, an implementation-status note, or a replacement for transition law.

# Canonical Role in Jeff

Governance determines whether a bounded action may proceed now.

Jeff cannot tolerate permission semantics hidden in:
- prompts
- selection logic
- workflow progression
- interface shortcuts
- execution adapters
- operator habit

If permission lives there, Jeff loses auditability, direction protection, and bounded autonomy discipline.

This document therefore makes one hard boundary explicit:
- selection chooses
- planning may structure
- action operationalizes intended work
- governance decides whether that action may begin now
- execution acts only if governance allows

Governance protects action discipline without stealing truth-mutation law.
Transitions still remain the only canonical mutation contract.
Governance constrains whether transition-relevant or externally consequential work may begin; it does not itself commit truth.

# Core Principle

No bounded action may begin unless governance allows it.

The governing law is:
- selection chooses but does not authorize
- planning may refine intended work but does not authorize
- approval and readiness are distinct pre-execution governance objects
- governance fails closed when the permission basis is missing, stale, contradictory, or unsafe
- execution performs action if and only if governance allows that action to proceed now

This applies equally to ordinary execution, research actions, recovery actions, apply-like real-world mutation support flows, and any other bounded action family Jeff later canonizes.

# Governance Scope

Governance owns the decision about whether a bounded action may lawfully begin under current conditions.

Governance covers:
- action entry
- policy interpretation and effective restriction application
- approval requirements
- readiness and start-time fit
- scope constraints
- direction protection
- autonomy limits
- blocker, degraded-trust, and truth-mismatch conditions that affect safe start
- freshness and revalidation where prior permission may be stale
- escalation when operator judgment is required
- the permissioning meaning of relevant current truth, config, and policy bindings

Governance does not own:
- proposal generation
- selection logic itself
- planning artifacts or workflow composition as such
- execution behavior after lawful start
- outcome normalization
- evaluation judgments
- transition construction or commit
- interface wording

Governance may block or defer action.
It does not turn that block or deferral into truth mutation by itself.
It may constrain whether transition-relevant work may be attempted, but it does not create a second mutation-permission law beside `TRANSITION_MODEL_SPEC.md`.

# Policy Layers

Jeff uses layered policy so that action permissioning is explicit, scoped, and inspectable.

The effective policy for a bounded action is the lawful combination of all applicable layers.
Defaults come from broader scope.
Tighter local constraints may narrow permission.
Conflicts or ambiguity fail closed.

## Global Policy

Global policy defines system-wide governance law.

It covers matters such as:
- forbidden behavior
- system-wide approval triggers
- global autonomy ceilings
- globally protected surfaces
- default governance posture when no narrower rule exists

Global policy is the floor for control and the ceiling for permissiveness.
Narrower scopes may tighten it.
They do not silently weaken it.

## Project Policy

Project policy defines governance constraints for one project inside the global state.

It may:
- tighten approval requirements
- narrow allowed tools, data access, or action families
- narrow autonomy for that project
- encode project-specific scope and direction protection rules
- define project-local risk tolerances within global bounds

Project policy does not create a second truth system.
It is a scoped policy layer inside the one canonical state model.

## Work-Unit Policy

Work-unit policy is allowed only as a bounded local restriction layer for one work unit or similarly narrow bounded effort.

It may:
- narrow scope further for the current effort
- require extra review or approval for a specific local surface
- freeze or constrain certain action classes while a blocker, experiment, or recovery condition is active

Work-unit policy exists to tighten local control, not to create freeform local governance.
It must stay narrower than project policy and must not become a rival owner of state or config semantics.

Policy bindings may be stored in canonical state or referenced from it, but policy meaning is owned here, not by the state document.

# Approval Model

Approval is the explicit permission decision for a bounded action when policy requires operator or otherwise authorized higher-governance consent.

Approval answers:
- may this action proceed if other current-time governance conditions are satisfied?

Approval is required when policy says the action crosses a protected boundary, such as:
- direction-sensitive action
- scope-widening action
- destructive or hard-to-reverse action
- policy-sensitive or operator-reserved action
- risk beyond the currently allowed autonomous boundary
- any other approval-gated action family defined by effective policy

Approval gates action entry.
It does not:
- choose the action
- prove the action is ready now
- guarantee success
- replace execution
- replace apply verification
- replace transition commit

Approval must be bound to the bounded action it governs.
Conceptually that binding includes:
- action identity
- scope
- target or protected surface
- relevant risk class
- any governing conditions that materially define what was approved

Approval must not be vague.
Blanket language such as "make it better" is not approval.

Approval may be:
- one-time
- time-limited
- condition-limited
- otherwise bounded by policy

If the action meaning, scope, target, risk posture, or governing conditions change materially, the old approval no longer authorizes start.

Approval may be granted, denied, absent, stale, mismatched, or not required.
Those are governance facts.
They are not execution facts.

# Readiness Model

Readiness is the explicit determination of whether a bounded action may begin now under current truth, current scope, current constraints, and current governance.

Readiness answers:
- is this action startable now?
- what still blocks it if not?
- what cautions remain if it is startable?

Readiness may consider:
- current canonical truth
- current blocker, degraded-trust, and truth-mismatch conditions
- current scope fit and target fit
- dependencies and required review points
- required approvals
- freshness-sensitive constraints
- start-time environment or target availability
- current assumptions that still matter
- risk-triggered rechecks

Readiness is not:
- approval
- execution
- outcome prediction
- workflow momentum
- plan existence
- selection confidence

Readiness is inherently current-time.
A prior readiness result is not evergreen permission.

Whole-Jeff readiness should preserve distinctions such as:
- `ready`
- `ready_with_cautions`
- `pending_approval`
- `pending_revalidation`
- `pending_review` when a real review dependency remains open
- `blocked`
- `invalidated`
- `escalated`

v1 does not need a bloated bureaucracy, but it must preserve those semantic distinctions where they matter for honest action entry.

# Action Entry Rules

The canonical action-entry law is:

`selection -> action -> governance -> execution`

When planning is conditionally used, the whole-Jeff law becomes:

`selection -> planning -> action -> governance -> execution`

The action boundary is explicit:
- selection may identify the chosen path
- planning may refine the work shape when needed
- action represents the bounded operational intent to be governed
- governance decides whether that action may start now
- execution may begin only after that governance pass

Governance evaluates a specific bounded action.
It does not evaluate:
- a raw proposal
- a raw plan step
- a workflow stage
- a remembered green light from earlier conditions

The following never imply lawful start by themselves:
- a selected option
- a plan
- a plan review
- a workflow next-step pointer
- a queued run
- a recovery suggestion
- an interface button
- previous momentum

Action may exist before approval and readiness pass.
That is correct.
Jeff needs a bounded thing to govern before execution starts.

Execution may start only when:
- the action being started is the action governance evaluated
- required approval is satisfied
- readiness is current
- no decisive blocker or contradiction remains

If the action changes materially between governance and execution start, Jeff must not pretend the original permission still applies.
It must re-enter governance on the materially changed action.

# Allowed / Blocked / Approval-Gated Behavior

Governance results must stay conceptually distinct.
They are not transition results, and they are not execution results.

The operative governance categories are:

- Allowed now
  Governance has determined that the action is within policy, any required approval is satisfied, and readiness is current.
  Execution may begin now, subject to any explicit cautions or bounded action-entry constraints.

- Blocked
  Governance has determined that current conditions prohibit start.
  Common reasons include active blocker, policy prohibition, degraded-trust condition, contradictory constraints, target unavailability, or unresolved mismatch.

- Approval required
  The action is not forbidden in principle, but it may not begin until required approval is granted for this bounded action.

- Deferred pending revalidation or review
  The action may still be viable, but the current permission basis is not current enough to start honestly.
  Typical causes are stale basis, resumed work after pause, changed truth, or unresolved review dependency.

- Invalidated
  The action no longer honestly stands as the same lawful action candidate because scope, target, direction, or current truth changed materially.
  This is stronger than blocked.

- Escalated
  Operator judgment is required before governance can produce a lawful start decision.
  This is a governance boundary event, not a generic warning.

These categories should be derived from typed governance outputs, not collapsed into one generic `status` field.

# Autonomy Boundaries

Autonomy in Jeff is bounded permission to continue without fresh operator intervention in cases where policy already allows that continuation.

Autonomy is subordinate to governance.
It does not replace governance.

The governing rules are:
- autonomy is bounded by explicit policy
- approval-gated work remains approval-gated regardless of autonomy posture
- readiness must still pass at action entry
- risk beyond allowed autonomy requires escalation
- autonomy may never expand silently through workflow, execution convenience, or interface behavior

Whole-Jeff may later express autonomy through richer tiers or classes.
That does not change the core law:
- autonomy defines what may be attempted without fresh operator approval
- governance still decides whether the bounded action may proceed now

In v1, autonomy should remain explicit, conservative, and easy to audit.
v1 does not require a standalone autonomy-mode field to make permission lawful.
If such metadata exists, it is subordinate to explicit policy and may never grant permission by itself.
Richer autonomy tiering is future expansion, not permission to weaken the present boundary.

# Direction / Config Inputs That Affect Permissioning

Governance decisions depend on current truth inputs that affect whether an action is lawful.

Those inputs commonly include:
- project direction
- explicit non-goals and strategic constraints
- project and work-unit scope boundaries
- authoritative policy bindings
- authoritative config values or effective config relevant to the action
- active blockers, incidents, degraded-trust markers, or truth mismatches
- current project, work-unit, and run scope
- current target availability and bounded environmental facts
- currently open approvals, escalations, or review requirements when canonically material

Governance meaning of those inputs:
- direction protects against strategically off-path action
- scope boundaries protect against surface widening
- policy bindings define what requires approval, what is forbidden, and what autonomy is allowed
- config truth may change whether a boundary is sensitive, risky, or even applicable
- blocker and integrity truth may prohibit start even when the action is otherwise attractive

This document does not own where those truths live or how config resolution is computed.
It owns how those truths affect permissioning once they are current and authoritative.

# Governance Outputs

Governance outputs must be typed and semantically explicit.
They must follow the shared naming discipline in `CORE_SCHEMAS_SPEC.md`.

At the conceptual level, governance should produce:
- `policy_verdict`
  The policy-layer conclusion about whether the action is allowed, blocked, approval-gated, or requires escalation.
- `approval_verdict`
  Whether approval is not required, granted, denied, missing, stale, mismatched, or otherwise not usable for this action.
- `readiness_state`
  Whether the action is ready, ready with cautions, pending approval, pending revalidation, pending review, blocked, invalidated, or escalated.
- decisive blockers or decisive constraints
  The concrete facts that prevent start or materially bound it.
- cautions and action-entry constraints
  Non-blocking conditions that must remain visible if start is allowed.
- escalation requirement where relevant
  The fact that operator judgment is required before lawful start.

The important rule is structural:
- do not flatten governance into one generic `status`
- preserve typed permission, approval, and readiness meaning
- do not require a separate first-class `governance_pass` object when the same meaning is already carried by typed outputs

Lawful start is the composite condition expressed by those outputs:
- `policy_verdict` does not block the action
- `approval_verdict` is satisfied for the bounded action where approval is required
- `readiness_state` currently allows start
- the action identity, scope, and governing basis still match

Governance outputs are primarily transient operational records used by orchestrator and execution entry.
Canonical state may hold only thin refs or current flags to governance objects when operational truth must expose them, such as:
- an open approval dependency
- an active blocking escalation
- current governed run lineage

Action, workflow, or interface states may reflect these governance outputs as derived projections.
They do not replace the underlying approval and readiness semantics or become permission authority themselves.

Full governance semantics stay here, not in state topology.

# Revalidation / Staleness Rules

Permission basis is time-sensitive.
Prior governance results do not silently remain valid forever.

An approval becomes stale or unusable when any of the following is true:
- the bounded action identity changed materially
- scope or target changed materially
- relevant risk posture changed materially
- governing policy or direction changed in a way that affects the approval
- a one-time approval was already consumed
- an explicit validity window expired
- a blocker, mismatch, or degraded-trust condition invalidated the original basis

A readiness determination becomes stale or unusable when any of the following is true:
- execution start was delayed materially
- current truth changed in a way that matters to the action
- scope or target changed
- blocker or degraded-trust state changed
- approval status changed
- workflow or plan resumed after a meaningful pause
- recovery or reconciliation changed the relevant operating conditions
- policy or direction changed

Start-time rechecks are mandatory whenever:
- any freshness trigger above occurred
- a previously checked action is resumed after pause or delay
- the action is approval-gated or risk-sensitive and actual start is later than the last meaningful check
- Jeff cannot prove that the earlier permission basis still matches the action about to start

Execution must rely on current readiness, not remembered readiness.

Revalidation may confirm that a prior basis still stands.
It may also produce:
- pending revalidation
- pending approval recheck
- blocked
- invalidated
- escalated

Old green lights must downgrade honestly when freshness fails.
Jeff must not smooth stale permission into "still probably fine."

Stale permission never silently remains valid.
If Jeff cannot establish current validity, it fails closed.

# Escalation Rules

Governance must escalate when operator judgment is required before a lawful start decision can be made.

Escalation is required when, for example:
- approval is required and the operator decision is still missing
- policy, scope, or direction constraints conflict materially
- an unresolved blocker or degraded-trust condition exceeds allowed autonomous handling
- risk exceeds the currently allowed autonomy boundary
- the permission basis is uncertain, contradictory, or stale enough that Jeff must not decide alone
- the action touches an operator-reserved or policy-sensitive surface
- the action has been invalidated and lawful continuation now requires strategic choice

Governance escalations should distinguish at least:
- approval escalation
- policy-boundary escalation
- risk-tradeoff escalation
- blocker or truth-mismatch escalation
- recovery or re-entry escalation when start conditions cannot be resolved autonomously

Approval and escalation must not collapse together.
An escalation requests operator judgment.
An approval records one kind of operator decision.

Blocking escalations stop affected action entry until resolved.
Advisory escalations may remain visible without authorizing start through the blocked boundary.

# Governance Invariants

The following invariants are binding:

- selection never implies permission
- planning never implies permission
- workflow progression never implies permission
- approval and readiness remain distinct
- approval never equals apply
- approval never equals transition commit
- no hidden policy in prompts, interfaces, workflow glue, or execution adapters
- no interface-owned permission path exists
- governance may block or defer action but does not mutate truth directly
- stale, contradictory, or unsafe permission basis fails closed
- execution never self-authorizes
- autonomy is bounded by policy and cannot expand silently
- blocked, approval-required, deferred, invalidated, and escalated outcomes remain distinct where they matter
- action-entry governance is required for bounded action before execution start
- recovery, rollback, reconciliation, and apply-like flows do not bypass governance

# Governance Failure Modes

Governance is failing if any of the following happens:

- selection-as-permission collapse
- approval and readiness flattened into one green light
- policy hidden in prompt wording or operator habit
- interface-owned permission shortcuts
- stale approvals treated as evergreen
- stale readiness treated as evergreen
- workflow momentum treated as authorization
- plan review treated as execution clearance
- execution self-authorizing on convenience grounds
- recovery or apply flow used as a governance bypass
- autonomy posture treated as blanket permission
- off-direction action allowed because local convenience outran explicit direction protection
- blocked, deferred, and escalated conditions flattened into one vague waiting state
- contradictory constraints tolerated instead of failing closed
- governance outputs reduced to a generic `status` blob that erases meaning

# v1 Enforced Governance Model

v1 enforces the following governance model:

- one explicit governance layer between action and execution
- explicit policy layering across global, project, and bounded work-unit scope, with stricter local constraints allowed but silent loosening forbidden
- an explicit action boundary even when the action object remains thin and transient
- the default path `selection -> action -> governance -> execution`
- conditional planning only where the work shape requires it, never as automatic permission
- distinct `approval_verdict` and `readiness_state`
- approval-gated actions do not start without recorded approval
- readiness checks at least current-truth fit, scope fit, blocker or degraded-state fit, approval presence when required, freshness, and relevant target availability
- distinct governance outcomes for allowed, blocked, approval-required, deferred pending revalidation, invalidated, and escalated behavior
- fail-closed action entry when the permission basis is missing, stale, contradictory, or unsafe
- no workflow-implied, interface-implied, or execution-implied start authority
- no rich workflow truth requirement for governance in v1
- no requirement for a heavy durable action bureaucracy in v1
- thin governance refs in state or run truth only when current operational truth genuinely needs them

This is sufficient to prevent the main governance drift:
- selection acting like permission
- approval being treated as readiness
- stale basis being reused as current permission
- execution convenience bypassing explicit governance

# Deferred / Future Expansion

Deferred expansion may add:
- richer risk models and autonomy tiering
- stronger multi-session freshness and permission-expiration logic
- more expressive approval binding schemes for complex multi-step or multi-target actions
- more explicit override classes and escalation classes
- richer persistent governance lineage where runtime pressure justifies it
- stronger policy tooling around long-running bounded continuation

Deferred expansion does not weaken the core law.
Future governance may become richer.
It does not become optional.

# Questions

No unresolved governance questions were found in this pass.

# Relationship to Other Canonical Docs

- `ARCHITECTURE.md` owns the structural placement of Governance as a distinct layer and the hard separation between action, execution, and transitions.
- `GLOSSARY.md` owns the meanings of `policy`, `approval`, `readiness`, `action`, `selection`, `execution`, `revalidation`, and `escalation`.
- `CORE_SCHEMAS_SPEC.md` owns shared naming law such as `policy_verdict`, `approval_verdict`, `readiness_state`, and typed linkage ids.
- `STATE_MODEL_SPEC.md` owns where policy bindings, direction truth, blockers, and thin governance refs may live in canonical state.
- `TRANSITION_MODEL_SPEC.md` owns mutation validation and commit law; this document only determines whether bounded action may lawfully begin.
- `PROJECT_AND_WORK_UNIT_MODEL_SPEC.md` owns project and work-unit container semantics and local bounded constraints.
- `PROPOSAL_AND_SELECTION_SPEC.md` owns proposal and selection; this document makes explicit that neither grants permission.
- `PLANNING_AND_RESEARCH_SPEC.md` owns planning and research artifacts; this document governs whether plan-refined action may actually begin.
- `EXECUTION_OUTCOME_EVALUATION_SPEC.md` owns execution, outcome, and evaluation after lawful action entry.
- `MEMORY_SPEC.md` owns memory; memory may inform later work but does not authorize action.
- `ORCHESTRATOR_SPEC.md` owns sequencing; orchestrator invokes governance but does not define its semantics.
- `INTERFACE_OPERATOR_SPEC.md` owns downstream operator surfaces; interfaces may surface governance but may not invent or flatten it.

# Final Statement

Jeff has one hard action-entry law:

- selection may choose
- planning may structure
- action may exist as bounded intended work
- governance decides whether that action may proceed now
- execution acts only after governance allows it

Approval and readiness remain distinct.
Selection never implies permission.
Stale or contradictory basis fails closed.
Autonomy remains bounded by explicit policy.

If these laws stay hard, Jeff can expand in capability without losing control.
If they soften, Jeff collapses into workflow momentum, hidden permission, and unsafe action.
