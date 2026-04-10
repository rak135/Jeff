# Purpose

This document defines Jeff's canonical sequencing-and-routing law.

It owns:
- accepted flow types
- sequencing rules
- lifecycle control at the orchestration layer
- input/output validation boundaries between stages
- failure routing
- escalation routing
- orchestration-level observability hooks
- orchestrator invariants
- explicit non-ownership boundaries
- flow examples and flow shapes
- orchestrator failure modes

It does not own:
- truth semantics
- governance semantics
- proposal logic
- selection logic
- evaluation logic
- transition law
- interface rendering contracts
- telemetry schemas
- test matrices
- roadmap sequencing

This is the canonical sequencing-and-routing document for Jeff as a whole.
It is not an implementation-status note.
It is not a vague essay about modules working together.
It is not a hidden replacement for governance, workflow truth, evaluation, memory, or transition law.

# Canonical Role in Jeff

The orchestrator coordinates bounded stage execution through public contracts.
It is the layer that makes Jeff's modules run in lawful order without turning sequencing convenience into hidden business semantics.

Jeff cannot tolerate:
- hidden orchestration logic that quietly owns policy
- routing logic that quietly owns selection or evaluation meaning
- workflow inflation that sneaks first-class workflow truth back into v1
- retry or recovery convenience that becomes hidden autonomy
- orchestration metadata that pretends to be canonical truth

This document protects modularity and inspectability by keeping one hard answer explicit:
- modules own their own semantics
- orchestrator owns sequence, handoff validation, routing, and stop or hold behavior

Jeff still operates inside:
- one global canonical state with nested projects
- project as a hard isolation boundary inside that state
- `project + work_unit + run` as the foundational containers orchestration must respect

# Core Principle

The binding law is:
- orchestrator sequences bounded public-stage flows
- orchestrator validates stage handoffs
- orchestrator routes explicit outputs
- orchestrator stops, holds, or escalates when required
- orchestrator does not think
- orchestrator does not own truth
- orchestrator does not own permission
- orchestrator does not own mutation law
- orchestrator does not invent business semantics from convenience

Modules think.
Modules judge.
Modules govern.
Modules mutate truth only through the transition law that belongs elsewhere.
The orchestrator coordinates those modules through explicit contracts and no more.

# Accepted Flow Types

Accepted flow types are coordination shapes.
They are not canonical truth objects.
They are not first-class workflow truth in v1.

The canonical whole-Jeff flow families are:

- bounded research direct-output flow
  A bounded truth-first context plus research path that ends in a research brief, comparison, memo, or other direct output without forcing proposal, selection, or execution.

- bounded research-to-decision-support flow
  A bounded truth-first context plus research path that feeds proposal or planning support rather than ending directly.

- bounded proposal-selection-action flow
  The default decision-to-action coordination shape:
  `state read -> context -> proposal -> selection -> action -> governance -> execution -> outcome -> evaluation -> memory -> transition`

- conditional planning insertion flow
  A legal variation where planning is inserted only when the selected or already-fixed bounded work requires multi-step structure, review points, or time-spanning coordination:
  `selection -> planning -> action -> governance -> execution`

- blocked or escalation flow
  A legal coordination shape in which the path stops or holds because a stage explicitly returns blocked, approval-required, deferred, invalidated, or escalated conditions.

- evaluation-driven follow-up flow
  A legal coordination shape in which evaluation recommends `retry`, `revalidate`, `recover`, `escalate`, `request_clarification`, or `terminate_and_replan`, and the orchestrator routes that recommendation into the next lawful entry path rather than auto-executing it.

- future bounded continuation flow
  A future multi-run coordination shape for bounded continuation across time, checkpoints, pauses, and resumptions under explicit scope and policy limits.

These are accepted flow families because they capture the lawful coordination shapes Jeff needs.
They do not make workflow first-class truth in v1, and they do not authorize hidden branching by themselves.

# Sequencing Rules

The orchestrator must preserve hard stage order while still allowing legitimate flow variation.

The binding sequencing rules are:
- a flow starts from a bounded trigger and an explicit scope binding
- truth-first context must be assembled before proposal or bounded research that depends on current truth
- proposal must occur before selection when decision among alternatives is required
- selection must occur before action formation
- planning may insert only after selection or another already-fixed bounded objective, never before truthful problem framing
- planning is conditional, not universal
- action must exist before governance can judge lawful start
- governance must complete before execution begins
- execution must occur before outcome
- outcome must occur before evaluation
- evaluation must occur before memory work that depends on execution judgment
- memory must occur before transition when committed memory linkage is relevant to the transition basis
- transition may occur only after lawful basis exists under the transition model

Legal shape variation does exist:
- direct research output may stop after research
- proposal may honestly return 0 to 3 serious options
- selection may honestly return `reject_all`, `defer`, or `escalate`
- blocked or escalated paths may stop before execution
- evaluation may recommend revalidation, recovery, or replanning rather than forward progress

Illegal sequencing includes:
- execution before governance
- evaluation before outcome
- transition before lawful basis
- selection treated as execution permission
- workflow progression treated as lawful sequencing authority in v1
- memory or evaluation outputs treated as truth mutation by sequencing convenience

# Lifecycle Control

Lifecycle control is the orchestrator's local control over flow progression.

At the orchestration layer, lifecycle control may include states such as:
- flow start
- active progression
- waiting
- paused
- blocked
- completed
- failed
- escalated
- invalidated
- restarted when lawful

Lifecycle control means the orchestrator may:
- start a bounded flow
- progress a flow through lawful stages
- hold a flow on missing input, escalation, or explicit wait conditions
- stop a flow on contract failure or terminal result
- mark a flow complete when its coordination obligations are finished
- invalidate and restart a flow when current basis changed enough that the existing path is no longer lawful

Lifecycle control does not mean:
- canonical truth by itself
- a replacement for run truth
- a replacement for project or work-unit truth
- hidden workflow truth in v1

If some lifecycle fact needs canonical truth status, that fact must be owned and committed elsewhere.
Orchestrator lifecycle is coordination state unless separately canonized through other owned contracts.

# Input / Output Validation Boundaries

This boundary is hard.

The orchestrator validates stage handoff contracts.
It must verify, before each downstream call, that:
- the required upstream output exists
- the output is structurally valid under shared schema law
- the scope binding is present and still lawful
- the upstream object family is the one the downstream stage is allowed to consume
- required decisive fields are present and explicit
- the handoff is not semantically impossible under public contracts

The orchestrator may reject:
- malformed input
- malformed stage output
- missing required output
- impossible stage order
- scope mismatch
- contract-type mismatch

Examples of semantically impossible handoffs the orchestrator must stop:
- execution requested without governed action
- transition requested without lawful transition basis
- memory stage treated as candidate author by a non-Memory module
- selection output treated as approval
- evaluation recommendation treated as permission
- workflow or plan artifact treated as execution authority

The orchestrator does not reinterpret domain meaning beyond public contracts.
It must not:
- decide whether a policy verdict is substantively correct
- decide whether an evaluation verdict is substantively correct
- infer missing business meaning from vague outputs
- paper over missing or invalid outputs so the next stage can continue

If the contract is missing, malformed, or impossible, the flow stops or holds.

# Failure Routing

Failure routing is contract-based, not intuition-based.

The orchestrator routes based on explicit outputs such as:
- malformed input
- contract validation failure
- stage failure
- blocked result
- degraded result
- inconclusive result
- retry recommendation
- revalidation recommendation
- recovery recommendation
- terminate-and-replan recommendation
- request-clarification recommendation

Binding failure-routing rules:
- malformed input or malformed stage output stops the current path and surfaces a validation failure
- missing required upstream output stops the current path; the orchestrator must not synthesize a placeholder result
- stage failure routes to explicit stop, hold, escalation, or other registered follow-up based on the producing stage's public contract
- blocked result holds or stops the affected path and preserves the blocking reason and scope
- degraded result remains visible and may continue only through explicit downstream law; it must not be greenwashed
- inconclusive result remains visible and may route to revalidation, clarification, escalation, or terminate-and-replan handling, not silent forward progress
- retry, revalidate, recover, and terminate-and-replan recommendations route to a new lawful entry path or operator-visible hold, not direct auto-execution

The orchestrator may route to:
- flow stop
- flow hold
- escalation surface
- new bounded follow-up flow
- operator-visible terminal result

The orchestrator must not:
- decide that degraded really means acceptable
- decide that blocked really means retry
- decide that recovery is optional if progress feels likely
- silently retry because the failure "looks transient"

# Escalation Routing

Escalation routing is the orchestrator's responsibility for surfacing and preserving explicit escalation outputs.

The orchestrator must:
- surface escalation when a stage explicitly returns escalation
- preserve the escalation source stage
- preserve the escalation reason
- preserve the affected scope
- preserve whether the current path is stopped, held, or awaiting operator input

Escalation routing is not the same thing as:
- approval semantics
- readiness semantics
- governance judgment
- operator decision content

The orchestrator may:
- stop the current path
- hold the current path
- await operator input
- route to a bounded clarification or review path if that route is explicitly lawful

The orchestrator may not:
- decide the substantive escalated issue itself
- silently downgrade escalation into caution
- treat pending approval as if approval already happened

# Observability Hooks

The orchestrator should expose orchestration-level traceability without becoming a semantic owner.

Conceptual observability hooks include:
- flow start
- scope binding
- selected flow type
- stage entry
- stage exit
- handoff validation pass or failure
- routing decision based on explicit output
- escalation point
- stop reason
- hold reason
- invalidation or restart event
- flow completion

Observability rules:
- observability hooks are traceability, not truth
- observability hooks do not replace module semantics
- observability hooks must not reinterpret module meaning
- observability hooks may record that the orchestrator routed on an explicit verdict or recommendation, but must not rewrite that verdict or recommendation

This document owns the existence of orchestration-level observability hooks.
It does not own telemetry schemas or trace storage design.

# Orchestrator Invariants

The following invariants are binding:
- orchestrator coordinates but does not think
- orchestrator does not mutate truth
- orchestrator does not create memory candidates
- orchestrator does not grant permission
- orchestrator does not perform hidden selection, evaluation, or policy work
- orchestrator uses public contracts only
- orchestrator stops on missing required handoff conditions rather than guessing
- orchestrator respects `project + work_unit + run` scope boundaries
- project remains the hard isolation boundary the orchestrator must respect
- workflow is not first-class canonical truth in v1
- selection is not execution permission
- approval and readiness remain governance objects
- outcome and evaluation remain distinct
- transitions remain the only canonical truth mutation contract
- retry, revalidation, recovery, and continuation never become silent loop behavior

# What Orchestrator Must Not Own

The orchestrator must not own:
- current truth
- policy semantics
- approval semantics
- readiness semantics
- proposal logic
- selection logic
- evaluation logic
- memory write decisions
- memory candidate creation
- transition law
- hidden workflow truth in v1
- hidden planning authority
- interface truth flattening
- substantive retry judgment
- substantive revalidation judgment
- substantive recovery judgment

If the orchestrator starts owning any of those, modularity is fake and the canon is already eroding.

# Flow Examples / Shapes

## Standard bounded action flow

`trigger -> state read -> context -> proposal -> selection -> action -> governance -> execution -> outcome -> evaluation -> memory -> transition -> result`

## Direct research output flow

`trigger -> state read -> context -> research -> direct output -> result`

## Blocked or escalated flow

`trigger -> state read -> context -> proposal or action-entry -> blocked or escalated -> hold or stop -> result`

## Conditional planning flow

`trigger -> state read -> context -> proposal -> selection -> planning -> action -> governance -> execution -> outcome -> evaluation -> memory -> transition`

## Evaluation-driven revalidation recommendation flow

`trigger -> ... -> execution -> outcome -> evaluation -> recommended_next_step = revalidate -> hold current path or enter bounded revalidation path -> governance or other lawful re-entry before new execution`

## Future multi-run bounded continuation flow

`bounded objective -> repeated run-scoped flows inside one work_unit -> explicit checkpoint -> continue, pause, stop, or escalate -> fresh governance before each new action entry`

These are orchestration shapes, not user stories and not truth objects.

# Failure Modes / Boundary Erosion Risks

The orchestration layer is failing if any of the following happens:
- god orchestrator drift
- hidden policy in routing logic
- hidden selection in routing logic
- hidden evaluation in routing logic
- silent retries without lawful basis
- silent revalidation without explicit trigger
- silent recovery loops
- routing convenience overriding scope or truth discipline
- orchestration metadata treated as canonical truth
- workflow inflation back through orchestration
- planning quietly treated as universal stage
- selection quietly treated as permission
- malformed stage outputs masked instead of stopped
- missing outputs guessed into existence
- continuation turning into hidden autonomy engine

# v1 Enforced Orchestration Model

v1 enforces enough orchestration law to prevent hidden-semantics collapse without overbuilding a workflow engine.

v1 enforces:
- one deterministic orchestrator that sequences public contracts
- accepted flow families sufficient for:
  - bounded research direct output
  - bounded proposal-selection-action flow
  - conditional planning insertion
  - blocked or escalation handling
  - evaluation-driven follow-up routing
- hard stage order where stages are present
- explicit handoff validation before each downstream call
- explicit stop or hold behavior on malformed or missing outputs
- escalation routing that preserves source stage, reason, and scope
- orchestration-local lifecycle control without turning lifecycle into rival truth
- orchestration-level observability hooks
- workflow remaining non-first-class canonical truth in v1
- planning remaining conditional rather than universal
- retry, revalidation, recovery, and continuation remaining contract-driven and non-self-authorizing

v1 does not require:
- first-class workflow truth
- planner-generated flow graphs
- giant dynamic flow registries
- autonomous retry loops
- hidden composition in interface or assistant layers
- orchestration-owned business semantics

# Deferred / Future Expansion

Deferred expansion may later add:
- richer bounded continuation across multiple runs
- more explicit multi-run coordination
- stronger orchestration observability
- richer retry and recovery routing support
- future workflow support only if workflow is explicitly canonized later

Deferred expansion does not weaken current law.
Future orchestration may become richer, but it still may not become the hidden owner of policy, decision, memory, or truth.

# Questions

No unresolved orchestrator questions were found in this pass.

# Relationship to Other Canonical Docs

- `ARCHITECTURE.md` owns the layer model and the hard law that orchestrator coordinates but does not think.
- `TRANSITION_MODEL_SPEC.md` owns truth mutation law; the orchestrator may route to transitions but does not own mutation semantics.
- `POLICY_AND_APPROVAL_SPEC.md` owns approval, readiness, and permission semantics; the orchestrator invokes governance through public contracts only.
- `STATE_MODEL_SPEC.md` owns truth placement; orchestration lifecycle and metadata do not replace canonical truth.
- `GLOSSARY.md` owns the meanings of orchestrator, workflow, action, approval, readiness, outcome, evaluation, escalation, and revalidation.
- `CONTEXT_SPEC.md` owns truth-first context assembly; the orchestrator only sequences it.
- `PROPOSAL_AND_SELECTION_SPEC.md` owns proposal and selection semantics; the orchestrator must not absorb them.
- `PLANNING_AND_RESEARCH_SPEC.md` owns research and planning semantics; the orchestrator only coordinates lawful insertion and routing.
- `EXECUTION_OUTCOME_EVALUATION_SPEC.md` owns execution, outcome, evaluation, verdicts, and recommended next-step outputs; the orchestrator routes those outputs but does not reinterpret them.
- `MEMORY_SPEC.md` owns memory candidate creation, write discipline, and retrieval; the orchestrator neither creates nor judges memory writes.
- `CORE_SCHEMAS_SPEC.md` owns shared machine-facing envelope and naming law that handoff validation depends on.
- `PROJECT_AND_WORK_UNIT_MODEL_SPEC.md` owns the container semantics and scope boundaries the orchestrator must respect.
- `VISION.md` owns the product-level requirement that Jeff remain inspectable, bounded, and non-monolithic.

# Final Statement

Jeff's orchestrator is the sequencing layer and nothing else.

It sequences bounded public-stage flows, validates handoffs, routes explicit outputs, and stops, holds, or escalates when required.
It does not think.
It does not authorize.
It does not mutate truth.
It does not own workflow truth in v1.

If these boundaries stay hard, Jeff can coordinate complex work without turning routing glue into a hidden brain.
If they soften, the orchestrator will absorb business logic, hide control decisions, and rot the rest of the architecture from the middle.
