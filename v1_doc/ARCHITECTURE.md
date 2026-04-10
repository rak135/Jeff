# Purpose of This Document

This document defines the canonical structural architecture of Jeff.

It owns:
- the architectural backbone of Jeff as a whole
- layer boundaries
- dependency direction
- module placement by layer
- object-class placement at architecture level
- hard boundary laws
- repository architecture rules
- architectural invariants and anti-patterns
- the distinction between overall Jeff architecture, v1 enforced architecture, and deferred expansion

It does not own:
- low-level schemas
- field enums
- exact transition payload structure
- exact approval or readiness schemas
- roadmap sequencing
- implementation status
- test matrices

This is a canonical Jeff architecture document, not a v1-only snapshot.
It is the replacement-layer architecture authority for Jeff.
Where older architecture docs, module-rule docs, or interface/governance docs disagree with it, this document controls the structural law and the older material is subordinate input or archive material.

# Role of Architecture in Jeff

Architecture exists in Jeff to preserve truth discipline, modularity, auditability, and capability growth without collapse.

Its role is to make the following structurally hard to violate:
- one current truth model
- one lawful mutation path for canonical truth
- explicit governance before action
- explicit stage boundaries across cognition, action, memory, and transition
- honest degraded-state handling
- truthful interface surfaces
- growth through stronger contracts rather than looser semantics

Jeff must not become a persuasive shell whose real semantics live in prompts, interfaces, caches, or orchestration glue.
Architecture is the mechanism that prevents that collapse.

# Architectural Principles

- One authority per concern.
- No rival truth layers.
- No rival mutation primitives.
- Truth-first reads before memory or artifacts.
- No hidden control flow.
- No implicit mutation.
- No prompt-only governance.
- No interface-owned truth.
- No orchestration-owned business logic.
- No adapter-owned semantics.
- No decorative modularity.
- No plan-, workflow-, or selection-implied permission.
- Fail closed on truth mutation.
- Preserve hard scope boundaries before convenience.
- Keep architecture stronger than the model.

# Canonical Architectural Backbone

The whole-Jeff architectural backbone is:

`trigger -> state read -> context -> optional research -> proposal -> selection -> optional planning -> action -> governance -> execution -> outcome -> evaluation -> memory -> transition -> updated state -> truthful interface result`

That backbone is the Jeff architecture as a whole.
`action` is the narrow transient operational bridge between selected or planned intent and governed doing.
It allows research-heavy work, conditional planning, bounded continuation, and future richer operator surfaces without changing the core law.

The v1 first-delivered enforced path is narrower and explicit:

`state read -> context -> proposal -> selection -> action -> approval + readiness -> execution -> outcome -> evaluation -> memory -> transition`

The settled architectural decisions inside that backbone are:
- Jeff has one global canonical state with nested projects.
- Project is a hard isolation boundary inside global state.
- `project + work_unit + run` are foundational containers.
- Workflow is not first-class canonical truth in v1.
- Planning is conditional, not universal.
- Proposal may honestly return 0 to 3 serious options.
- Selection does not grant execution permission.
- `action` is a narrow transient operational object family between selection or planning and action-entry governance.
- Pre-execution governance minimally includes approval and readiness.
- Governance evaluates action for permission and start-time fit.
- Execution performs action if and only if governance allows it.
- Transitions are the only canonical truth mutation contract.
- `Change` may support review and real-world apply flows, but it is never a rival truth mutation primitive.
- Only Memory creates memory candidates.
- Canonical state may reference only committed memory IDs.
- Outcome and evaluation use an expanded but bounded verdict model.

# Top-Level Layer Model

Jeff uses nine top-level layers:

1. Core
2. Governance
3. Cognitive
4. Action
5. Memory
6. Orchestration
7. Interface
8. Infrastructure
9. Assistant

This is the final architecture model for Jeff.

Interpretation rules:
- Core, Governance, Cognitive, Action, and Memory are the semantic owner layers.
- Orchestration coordinates semantic layers through public contracts.
- Interface presents and invokes the system through truthful surfaces.
- Infrastructure provides technical support and never defines Jeff semantics.
- Assistant is future higher-level interaction behavior above the rest of the system and remains subordinate to backend law.
- The Action layer is not the same thing as the `action` object family.
- The `action` object family is a transient operational object family between decision and action-entry, not a new top-level layer.

Governance is a distinct first-class layer.
Policy, approval, and readiness do not belong half in Core and half in Action.
Core owns truth and transition law.
Governance owns permission and action-entry law.

# Layer Responsibilities and Non-Responsibilities

## Core

Purpose:
- own canonical truth and the only lawful canonical mutation path

Owns:
- global canonical state
- project truth
- work_unit truth
- run truth
- transition construction, validation, and commit
- shared structural contracts that define truth objects and references

Does not own:
- proposal generation
- selection
- approval
- readiness
- execution
- memory candidate authorship
- interface semantics
- orchestration logic

Interaction with neighboring layers:
- exposes read-only canonical truth surfaces to Governance, Cognitive, Memory, Orchestration, and approved Interface projections
- accepts canonical mutation only through transition logic
- consumes no downstream layer as a semantic dependency

## Governance

Purpose:
- determine whether a bounded action may proceed now

Owns:
- policy
- approval
- readiness
- freshness and revalidation checks when they are required
- explicit allow, block, defer, and escalate results for action entry

Does not own:
- canonical truth
- transition commit
- proposal generation
- execution side effects
- outcome normalization
- evaluation verdicts
- memory creation

Interaction with neighboring layers:
- reads current truth from Core
- consumes bounded action objects formed from selected or plan-refined intent
- passes governed action objects and action-entry decisions to Action through Orchestration and public contracts

## Cognitive

Purpose:
- assemble bounded inputs, reason over them, generate options, choose one, plan only when needed, and judge results

Owns:
- context
- research
- proposal
- selection
- conditional planning
- evaluation

Does not own:
- canonical truth
- policy semantics
- approval
- readiness
- execution
- outcome normalization
- memory candidate creation
- transition commit

Interaction with neighboring layers:
- reads truth from Core first
- may consume Governance constraints as inputs, but does not own final permission
- hands bounded selected or plan-refined operational intent downstream as action
- does not let selection or planning imply permission by themselves
- consumes outcome from Action for evaluation
- may recommend transition-relevant updates, but does not author or commit canonical transitions

## Action

Purpose:
- perform governed action and report what happened

Owns:
- execution
- outcome
- conditional support flows for real-world mutation such as `Change`, apply, rollback, recovery, and reconciliation support

Does not own:
- action formation from selection or planning
- policy
- approval
- readiness
- the semantic authority to redefine `action` as governance, execution, or truth
- evaluation
- memory authorship
- canonical truth mutation

Interaction with neighboring layers:
- consumes governed action objects and action-entry decisions from Governance
- reads Core only through explicit read contracts needed to act within scope
- uses Infrastructure adapters to execute governed action
- passes execution traces and normalized outcomes to Cognitive evaluation
- feeds evidence to Memory and Transition through defined handoffs, never through direct truth mutation

## Memory

Purpose:
- create, store, retrieve, and link durable non-truth continuity

Owns:
- memory candidate creation
- memory write discipline
- memory storage
- memory retrieval
- memory linking

Does not own:
- canonical truth
- transition commit
- evaluation verdicts
- proposal generation
- approval
- readiness

Interaction with neighboring layers:
- reads Core truth to preserve scope and link discipline
- consumes evaluation-backed signals and other allowed inputs
- returns only committed memory IDs for any canonical linkage
- never substitutes memory for current truth

## Orchestration

Purpose:
- coordinate bounded flow sequencing across modules

Owns:
- flow sequencing
- lifecycle coordination
- boundary validation between stage outputs and next-stage inputs
- failure routing
- escalation routing

Does not own:
- truth semantics
- policy semantics
- proposal logic
- evaluation logic
- transition law
- interface semantics

Interaction with neighboring layers:
- depends only on public contracts of Core, Governance, Cognitive, Action, and Memory
- sequences calls and validates handoffs
- never becomes the hidden business-logic owner of the system

## Interface

Purpose:
- provide truthful human and client surfaces into Jeff

Owns:
- CLI
- future API bridge
- future GUI
- operator-facing projections and actions built from backend contracts

Does not own:
- canonical truth
- hidden write paths
- hidden governance shortcuts
- private lifecycle semantics

Interaction with neighboring layers:
- consumes Orchestration and approved read-only projection contracts
- presents canonical, derived, execution, memory, and review surfaces with explicit truth labels
- never mutates truth from read or inspect surfaces

## Infrastructure

Purpose:
- provide technical support without defining Jeff meaning

Owns:
- storage backends
- model adapters
- tool adapters
- observability
- configuration plumbing
- external connectors

Does not own:
- truth
- governance
- reasoning semantics
- transition semantics
- interface semantics

Interaction with neighboring layers:
- supports all layers through narrow adapters
- remains replaceable plumbing rather than semantic control

## Assistant

Purpose:
- provide future high-level personal interaction behavior on top of the system

Owns:
- conversational continuity
- higher-level interaction framing
- future initiative and scheduling behavior

Does not own:
- truth
- policy
- approval
- readiness
- transition commit
- hidden action permission

Interaction with neighboring layers:
- sits above Interface and Orchestration public surfaces
- routes operator intent and presents results
- remains subordinate to backend structural law

# Dependency Direction

## Allowed Dependency Direction

- Core may depend only on Infrastructure.
- Governance may depend on Core read surfaces and Infrastructure.
- Cognitive may depend on Core read surfaces, Governance public contracts, Memory retrieval contracts, and Infrastructure.
- Action may depend on Governance public contracts, Core read surfaces, and Infrastructure.
- Memory may depend on Core read surfaces, Cognitive handoff contracts, and Infrastructure.
- Orchestration may depend on the public contracts of Core, Governance, Cognitive, Action, Memory, and Infrastructure.
- Interface may depend on Orchestration and approved read-only projection contracts.
- Assistant may depend on Interface and Orchestration public surfaces.

Layers may depend on another layer's public contracts and read surfaces, never on its internal implementation or private representations.

## Forbidden Dependency Direction

- Core must not depend on Governance, Cognitive, Action, Memory, Orchestration, Interface, or Assistant.
- Governance must not depend on Cognitive choice logic to define permission law.
- Cognitive must not mutate Core truth directly.
- Action must not define or override Governance.
- Memory must not define or override current truth.
- Orchestration must not own domain logic that belongs to semantic layers.
- Interface must not reconstruct backend truth or permission semantics privately.
- Infrastructure must not define Jeff semantics.
- Assistant must not bypass Governance or Transition law.

## Read and Mutation Rules

- Reasoning starts from current canonical truth and current effective resolution before memory or artifacts.
- All meaningful reads of current truth use sanctioned Core read surfaces.
- Read surfaces are non-mutating.
- Only Core transition logic may mutate canonical truth.
- Transition commit is fail-closed: no canonical commit on inconclusive validation, no partial canonical commit, and no canonical commit from unverified apply results.
- Other layers may recommend updates, but only Core constructs, validates, and commits authoritative transitions.
- Real-world mutation support objects such as `Change`, apply, rollback, and recovery never mutate canonical truth by themselves.

## ASCII Dependency Diagram

```text
Assistant
   |
Interface
   |
Orchestration
   +--> Core
   +--> Governance
   +--> Cognitive
   +--> Action
   +--> Memory

Governance --> Core
Cognitive --> Core
Cognitive --> Governance
Cognitive --> Memory (retrieval only)
Action --> Governance
Action --> Core (read only)
Memory --> Core
Memory --> Cognitive (handoff input only)

Infrastructure supports every layer through adapters.
```

# Module Placement by Layer

## Core

- `state`
- `transition`
- `schemas`
- the foundational container families for `project`, `work_unit`, and `run`

## Governance

- `policy`
- `approval`
- `readiness`
- conditional freshness and revalidation checks

## Cognitive

- `context`
- `research`
- `proposal`
- `selection`
- `planning` as a conditional module
- `evaluation`

## Action

- `execution`
- `outcome`
- conditional `change_control` support for real-world mutation intent and apply/recovery support flows

## Memory

- `memory_candidate_creation`
- `memory_write_discipline`
- `memory_storage`
- `memory_retrieval`
- `memory_linking`

## Orchestration

- `flow_registry`
- `flow_runner`
- `lifecycle_control`
- `failure_routing`
- `escalation_routing`

## Interface

- `cli`
- future `api_bridge`
- future `gui`

## Infrastructure

- `storage_backends`
- `model_adapters`
- `tool_adapters`
- `observability`
- `config_plumbing`
- `external_connectors`

## Assistant

- `conversation`
- future `initiative`
- future `scheduling`
- future `priority_management`

Placement consequences:
- `action` is a canonical transient operational object family, not a new top-level layer.
- Workflow is not a first-class canonical module family in v1.
- Planning exists architecturally, but only as a conditional cognitive module.
- v1 does not require a giant standalone action framework as long as the action boundary stays explicit.
- Richer workflow coordination, typed recovery systems, and expanded operator surfaces are future or conditional expansions and do not alter the backbone.

# High-Level Object Model

## Canonical Truth Objects

- `global state`: canonical truth object
- `project`: canonical truth object
- `work_unit`: canonical truth object
- `run`: canonical truth object
- `transition`: canonical truth object

These are owned by Core.
Direction, config, and similar canonical substructures live inside global or project truth; they are not separate peer truth centers at the architecture level.

## Governance Objects

- `policy`: governance object
- `approval`: governance object
- `readiness`: governance object

These are owned by Governance.

## Transient Processing Objects

- `context`: transient processing object
- `proposal`: transient processing object
- `selection result`: transient processing object
- `action`: transient operational object family
- `execution result`: transient processing object
- `outcome`: transient processing object
- `evaluation result`: transient processing object

These are stage-bounded working objects.
They may be durable as records or artifacts, but they are not current canonical truth.
`action` is the narrow operational subtype that bridges decision structure and execution entry.

## Support/Review Objects

- `memory entry`: support/review object
- `Change`: support/review object

`Change` is the authoritative intent/apply object for bounded real-world mutation support when that flow exists.
It is never the canonical truth mutation primitive.

# Core Boundary Laws

- Canonical truth exists only in Core.
- Jeff has one global canonical state with nested projects.
- Project is the hard isolation boundary inside global truth.
- `project + work_unit + run` are the foundational bounded work containers.
- Reasoning begins from current canonical truth and current effective resolution before memory or artifacts.
- Context is the canonical truth-first assembly path for reasoning inputs.
- Transitions are the only canonical truth mutation contract.
- Only Core constructs, validates, and commits authoritative transitions.
- Transition commit is fail-closed.
- No partial canonical commit is allowed.
- `Change`, apply, rollback, recovery, workflow progression, interface actions, and execution side effects are never canonical truth mutation by themselves.
- Governance alone owns permission and action-entry law.
- Selection may choose a bounded option, but it never grants execution permission.
- `action` is the bounded operational object family between selection or planning and governance or execution entry.
- `action` is not canonical truth, not governance, not execution, not planning, and not transition law.
- Plan existence, plan review, workflow progression, and selection never imply approval, readiness, or execution permission, and they do not silently materialize governed action.
- Selection may produce or refine action intent, but governance decides whether action may start and execution performs the action.
- Approval and readiness are the minimum pre-execution governance gates in v1.
- Execution start must re-check current truth, scope, blockers, freshness, and exact approval binding at start time.
- Cognitive modules may reason, compare, and judge, but they do not mutate truth.
- Action may do work, but it does not define truth.
- Outcome is not evaluation.
- Evaluation is not transition.
- Only Memory creates memory candidates.
- Memory is durable support knowledge, not current truth.
- Canonical state may reference only committed memory IDs.
- Unresolved high-risk truth mismatch blocks further mutation in affected scope.
- Interface surfaces must label authority and truth class explicitly.
- Read and inspect surfaces must not mutate.
- Orchestration coordinates; it does not become the business-logic owner.
- Interfaces, caches, workflow state, assistant state, event history, and memory must not become rival truth centers.

# Handoff Laws Between Major Stages

## Context -> Proposal

What passes:
- bounded truth-first context
- scoped project, work_unit, and run situation
- relevant memory references
- relevant evidence inputs

What authority does not pass:
- decision authority
- execution permission
- truth mutation authority

## Research -> Proposal or Direct Output

What passes:
- gathered evidence
- source distinctions
- uncertainty and gap markers
- bounded synthesis

What authority does not pass:
- decision authority
- governance authority
- truth mutation authority

Research may feed proposal generation or produce a truthful direct output.
Research never silently chooses or authorizes action.

## Proposal -> Selection

What passes:
- 0 to 3 serious options
- explicit assumptions
- explicit risks
- bounded rationale

What authority does not pass:
- approval
- readiness
- execution permission
- truth mutation authority

## Selection -> Action

What passes:
- one selected option or an explicit reject, defer, or escalate result
- bounded chosen intent
- rationale and assumptions that still matter

What authority does not pass:
- execution permission
- freshness guarantee
- approval
- readiness
- truth mutation authority

Selection chooses.
It does not authorize execution and it does not become action by itself.

## Conditional Planning -> Action

What passes:
- structured work shape
- ordered intended steps
- explicit dependencies, review points, and assumptions

What authority does not pass:
- approval
- readiness
- execution permission
- truth mutation authority

Planning structures work.
It may refine action shape.
It does not authorize work.

## Action -> Governance

What passes:
- bounded operational intent
- action identity and scope
- target and preconditions
- assumptions, risks, and relevant lineage

What authority does not pass:
- approval
- readiness
- execution permission
- truth mutation authority

Action operationalizes intended work.
Governance decides whether that action may start now.

## Governance -> Execution

What passes:
- bounded governed action
- explicit permission state
- readiness state
- scope lock
- exact approval binding when approval is required
- cautions and decisive constraints

What authority does not pass:
- evaluation authority
- truth mutation authority

Execution performs action if and only if governance allows it.

Execution performs the governed action if and only if those governance results allow start.

## Execution -> Outcome

What passes:
- traces
- artifacts
- observed effects

What authority does not pass:
- success judgment
- truth claims
- memory authority

## Outcome -> Evaluation

What passes:
- normalized observed result
- evidence bundle
- artifacts and traces

What authority does not pass:
- execution permission
- memory authorship
- truth mutation authority

## Evaluation -> Memory

What passes:
- evidence-backed signals
- value judgments
- bounded memory-worthiness signals

What authority does not pass:
- direct memory entry authorship outside Memory
- truth mutation authority

## Memory -> Transition

What passes:
- committed memory IDs only
- linkable references
- explicit write success information

What authority does not pass:
- uncommitted memory references
- memory-authored truth changes

Memory may feed transition linkage.
It does not define canonical truth.

## Evaluation / Memory -> Transition Construction

What passes:
- proposed updates
- evidence-backed recommendations
- committed linkage inputs

What authority does not pass:
- authoritative transition authorship
- commit permission

Only Core transition logic constructs, validates, rejects, or commits the authoritative transition record.

# Flow Shapes

## Standard Bounded Action Flow

```text
trigger
  ->
state read
  ->
context
  ->
proposal
  ->
selection
  ->
action
  ->
approval/readiness
  ->
execution
  ->
outcome
  ->
evaluation
  ->
memory
  ->
transition
  ->
updated state
```

## Research Flow

```text
trigger
  ->
state read
  ->
context
  ->
research
  ->
direct output
  or
  ->
proposal
  ->
selection
  ->
action
  ->
governance
  ->
execution
```

Research may end in a truthful output without forcing an execution path.

## Blocked/Escalation Flow

```text
trigger
  ->
context
  ->
proposal
  ->
selection
  ->
action
  ->
governance
  ->
blocked or escalated
  ->
no execution
  ->
truthful operator-visible result
```

## Conditional Planning Insertion

```text
selection
  ->
if work is multi-step, high-risk, review-heavy, or time-spanning
  ->
planning
  ->
action
  ->
governance
  ->
execution
```

Planning is inserted only when the work shape requires it.

## Future Long-Running Bounded Continuation Flow

```text
bounded objective
  ->
repeated runs inside one work_unit
  ->
action at each bounded continuation boundary
  ->
governance at each action boundary
  ->
execution / outcome / evaluation / memory / transition loop
  ->
checkpoint, continue, block, or escalate
```

This is future architecture built from the same backbone, not a replacement architecture.

# Repository Architecture Rules

- Canonical topic ownership must live in one canonical document family only.
- Legacy docs may inform rewrites, but they are not equal authorities once a canonical replacement exists.
- Repository structure should mirror the layer model and foundational container model.
- Core, Governance, Cognitive, Action, Memory, Orchestration, Interface, Infrastructure, and Assistant code should remain separable by ownership.
- Architecture-relevant modules must state their layer, ownership sentence, public inputs/outputs or enforced invariant, governing spec references, and local handoff truth.
- New modules or submodules must earn admission through distinct responsibility, nameable boundaries, and non-duplication.
- Utility folders, helper buckets, and speculative abstractions must not be promoted into architecture modules.
- Project data, artifacts, and memory must remain project-scoped unless an explicit cross-project authority exists.
- Interface contracts and view models must preserve backend semantics rather than inventing new ones.
- Documentation must preserve the design-vs-current-reality split.
- Documentation misalignment is a governance defect, not "just docs."
- Architecture audit, docs governance, and local handoffs are part of architecture enforcement, not optional commentary.
- Temporary exceptions must be explicit, bounded, and treated as debt, not quiet replacement law.

# Reuse and Build-from-Scratch Rules

## Safe Reuse

Jeff may reuse infrastructure-level systems such as:
- storage engines
- vector or retrieval infrastructure
- observability tooling
- model provider SDKs
- tool execution wrappers
- serialization and validation libraries
- transport and CLI utilities

These are safe only when they are wrapped behind Jeff-owned contracts and do not define system meaning.

## Must Stay Internal

Jeff must define internally:
- canonical truth topology
- transition law
- action semantics at the decision-to-execution boundary
- governance semantics
- project, work_unit, and run semantics
- proposal and selection discipline
- evaluation semantics
- memory write discipline
- orchestrator boundaries
- interface truthfulness rules

These are architecture-defining concerns.

## Forbidden Backbone Outsourcing

Jeff must not outsource its backbone to:
- agent frameworks
- orchestration frameworks
- planner frameworks
- black-box memory systems
- black-box autonomy systems
- hidden workflow engines

Such tools may be wrapped as bounded infrastructure or action tools.
They may not become Jeff's architecture.

# Architectural Invariants

- There is exactly one canonical truth layer.
- There is exactly one canonical truth mutation path: transitions.
- Global state contains nested projects.
- Project is the hard isolation boundary inside global truth.
- `project + work_unit + run` remain foundational.
- Proposal may return 0 to 3 serious options.
- Selection never implies permission.
- `action` remains a narrow transient operational object family between selection or planning and governance or execution entry.
- Approval and readiness remain explicit pre-execution gates.
- `action` does not replace governance, execution, workflow, or transition law.
- Selection, workflow progression, and plan existence do not silently become action-entry permission.
- Planning remains conditional.
- Workflow is not first-class canonical truth in v1.
- Only Memory creates memory candidates.
- Canonical state references only committed memory IDs.
- Execution side effects do not become truth automatically.
- Outcome and evaluation remain separate.
- Memory remains support knowledge rather than truth.
- Orchestration remains coordination rather than hidden business logic.
- Interface surfaces remain downstream of backend semantics and preserve truth labels.
- Infrastructure remains subordinate to Jeff semantics.

# Architectural Anti-Patterns

- God orchestrator.
- Action catch-all inflation.
- Action-as-governance.
- Action-as-execution.
- Action-as-hidden-truth.
- Action-as-workflow-bureaucracy.
- Actionless execution semantics.
- Workflow inflation.
- Rival truth layers.
- Rival mutation primitives.
- Interface-owned backend logic.
- Universal planning bureaucracy.
- Memory sludge.
- Prompt-defined policy.
- Hidden execution permission.
- Decorative modularity with real coupling.
- Adapter-owned semantics.
- Bridge or view-model semantic flattening.
- Approval-implied apply.
- Plan-implied permission.
- Workflow-implied permission.
- Patch or diff as mutation authority.
- Memory-as-truth repair.
- Silent recovery or mismatch greenwashing.
- Generic `status` flattening across distinct lifecycle meanings.

# v1 Architectural Scope

## Whole-Jeff Architecture

Jeff as a whole is defined by the backbone in this document.
That whole architecture includes bounded research, conditional planning, future richer operator surfaces, future bounded continuation, and stricter integrity and recovery systems without changing the central law of truth, governance, action, memory, and transition.

## In v1

- one global canonical state with nested projects
- hard project isolation inside that state
- foundational `project + work_unit + run`
- Core truth and transition law
- first-class Governance with policy, approval, and readiness
- Cognitive context, research, proposal, selection, and evaluation
- narrow canonical `action` object family between selection or planning and approval/readiness
- Action execution and outcome
- Memory candidate creation, storage, retrieval, and linking
- deterministic orchestration
- CLI-first truthful interface surface
- transition-only canonical mutation

## Conditional in v1

- lightweight action materialization is acceptable in v1 as long as the `selection -> action -> governance -> execution` boundary stays explicit
- planning for work that is multi-step, high-risk, review-heavy, or time-spanning
- real-world mutation support through `Change` and apply/recovery support flows when needed
- freshness and revalidation checks beyond the minimum approval/readiness gate
- richer interface surfaces that still preserve backend truth labels

## Deferred Beyond v1

- first-class workflow truth objects
- universal planning as a mandatory stage
- multi-work-unit workflow systems as core architecture
- always-on long-running autonomy
- GUI as an architectural driver
- API bridge as an architectural driver
- assistant initiative and scheduling as central behavior
- broad self-modification frameworks as default backbone

# Relationship to Other Canonical Documents

- `VISION` owns system identity, purpose, long-term direction, and human mental model.
- `GLOSSARY` owns terminology.
- `CORE_SCHEMAS_SPEC` owns shared machine-facing schema primitives.
- `STATE_MODEL_SPEC` owns state topology and truth placement.
- `TRANSITION_MODEL_SPEC` owns transition structure, validation, and commit details.
- `POLICY_AND_APPROVAL_SPEC` owns governance contracts.
- `PROJECT_AND_WORK_UNIT_MODEL_SPEC` owns container semantics and lifecycle.
- `CONTEXT_SPEC` owns context assembly contracts.
- `PROPOSAL_AND_SELECTION_SPEC` owns proposal and selection contracts.
- `EXECUTION_OUTCOME_EVALUATION_SPEC` owns the action-result-judgment chain.
- `MEMORY_SPEC` owns memory model, write discipline, and retrieval.
- `ORCHESTRATOR_SPEC` owns sequencing contracts.
- `TESTS_PLAN` owns verification strategy.
- `HANDOFF_STRUCTURE` owns handoff writing rules and placement.
- `ROADMAP_V1` owns sequencing and build order.
- `DOCS_GOVERNANCE` owns document authority, staleness rules, and conflict resolution.

This document does not duplicate those documents.
It defines the structural law that makes their ownership boundaries coherent.
If any other document uses older high-level architectural shorthand, this document wins on architectural structure and boundary law.

# Questions

No unresolved architecture questions were found in this pass.

# Final Statement

Jeff has one architecture.

That architecture is built around:
- one global canonical truth model
- hard project isolation inside that truth
- foundational `project + work_unit + run` containers
- narrow `action` objects between decision and action-entry governance
- governance before action
- bounded cognition
- bounded action
- disciplined memory
- transition-only canonical mutation
- truthful downstream interfaces

If those laws stay hard, Jeff can grow in capability without losing meaning.
If those laws soften, Jeff collapses into another smart-looking but unreliable AI system.
