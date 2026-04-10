# Purpose of This Document

This document defines the vision, intended shape, and long-term direction of Jeff.

It exists to give one clear mental model of what Jeff is, how it should function, where it is going, and how the system is organized at a high level.

This document is binding at the vision and system-shape level.

This document does not define:
- low-level schemas
- implementation status
- test plans
- handoff structures
- detailed interface contracts

Those belong in the canonical architecture, specification, governance, and process documents.

# What Jeff Is

Jeff is a personal, modular, truth-grounded assistant and work system.

Jeff is built to help one operator think, research, plan, execute, and sustain work over time without collapsing into prompt chaos, memory sludge, or opaque autonomy theater.

Jeff is:
- a general personal work system, not a single-purpose Jeff-development assistant
- a project-centered system that can support many different kinds of work
- a truth-governed system with one global canonical state and nested project isolation
- a system for bounded research, evidence gathering, synthesis, planning, execution, and review
- a persistent collaborator rather than a prompt-response toy
- a foundation for future bounded autonomy

Jeff must be able to support work such as:
- building Jeff itself
- software and product work in other projects
- internet research and evidence synthesis
- structured writing and reporting
- project planning and execution
- long-running bounded efforts that continue across time

The Jeff project is one important project inside the system. It is not the only valid use case and it must not distort the whole architecture around itself.

# What Jeff Is Not

Jeff is not:
- just a chatbot
- a multi-agent swarm
- a black-box autonomous framework
- prompt spaghetti with a nicer shell
- a memory dump
- a system where the LLM defines truth
- a platform-first product
- a generic agent framework disguised as a personal assistant
- a finished Jarvis in v1

Jeff must not become:
- a system that feels impressive but cannot be trusted
- a system that forces the operator to manually restitch context every time
- a system where proposal, decision, execution, and truth blur together
- a system where memory quietly replaces canonical state
- a system where orchestration becomes a hidden brain

# Why Jeff Exists

Most AI systems fail in one or more of these ways:
- they lose context across time
- they cannot preserve direction
- they mix suggestion, permission, action, and truth into one blob
- they cannot perform disciplined research with evidence boundaries
- they generate outputs without durable structure around the work
- they create more cognitive load than they remove

Jeff exists to solve that.

Jeff should reduce cognitive load by:
- holding stable project direction
- preserving bounded work containers
- keeping truth explicit
- remembering useful prior work without confusing memory for truth
- doing research and synthesis inside real project scope
- making bounded progress without needless interruption
- escalating only when approval, conflict, or uncertainty actually requires it

# Long-Term Vision

The long-term vision is a persistent personal system that can carry meaningful work over time with bounded autonomy and explicit control.

Jeff should eventually function as a calm, durable collaborator that can:
- understand what project it is operating in
- keep track of the current work unit and run context
- research the internet and other sources for evidence
- compare sources and preserve provenance
- generate clear outputs such as briefs, plans, specs, summaries, and recommendations
- execute bounded actions inside policy
- observe what happened
- evaluate the result against goals and constraints
- update memory conservatively
- update truth only through transitions
- continue work across many runs without becoming opaque

Long term, Jeff should support:
- sustained product and software collaboration
- non-Jeff research projects
- long-running project work over hours or days
- conditional planning for complex efforts
- bounded proactive continuation when policy permits it
- future operator experiences that feel closer to a disciplined personal operating partner than a chat session

This future direction matters, but it must be reached by strengthening structure, not by loosening it.

# v1 Vision and Practical Purpose

v1 is not a demo shell and not a fake prototype.

v1 must already contain the real architectural backbone:
- one global canonical state
- hard project isolation inside that state
- foundational `project + work_unit + run` containers
- first-class Governance with explicit policy, approval, and readiness boundaries
- proposal and selection separation
- explicit action-entry governance before execution
- execution, outcome, and evaluation separation
- disciplined memory
- transition-governed truth mutation
- a deterministic orchestrator that coordinates rather than thinks

The practical purpose of v1 is to make Jeff immediately useful for bounded real work while preserving the final architectural direction.

v1 should be able to:
- run a bounded execution flow inside a project
- perform project-scoped internet research
- gather source-aware evidence
- synthesize findings into clear outputs
- handle Jeff-project work and non-Jeff project work with the same backbone
- continue within scope without needless escalations
- stop, block, or escalate honestly when governance requires it

Planning in v1 is conditional, not universal.

The default v1 path is:

`selection -> action -> pre-execution governance -> execution`

Planning is invoked only when the work is:
- multi-step
- higher-risk
- review-heavy
- or spans time in a way that needs structured coordination

# Core Design Principles

## State Is Truth

Jeff has one global canonical state.

That state is the only authoritative representation of current system truth.

Projects live inside that global state as hard isolation boundaries.

Truth must not be reconstructed from:
- memory
- chat history
- execution artifacts
- UI views
- model output

## Transitions Are the Only Truth Mutation Path

Transitions are the only canonical mutation contract.

No module may change canonical truth through direct writes, implied updates, or side effects.

`Change` may exist as a supporting review or apply object, but it is not a rival truth mutation primitive.

## Proposal Is Not Decision

Proposal exists to produce bounded candidate options.

Proposal generation may honestly return 0 to 3 serious options.

Jeff must not generate fake alternatives to satisfy a procedural rule.

If there is no honest proposal, that must be explicit.

## Selection Is Not Execution Permission

Selection chooses a bounded option under truth, direction, and policy.

Selection does not grant execution permission by itself.

Before execution, Jeff must pass through pre-execution governance.

In v1, the minimum governance objects are:
- approval
- readiness

Selection chooses.

It does not authorize execution, and it does not become permission by itself.

## Execution Is Not Truth

Execution performs work.

Execution may succeed, degrade, fail, be interrupted, or produce inconclusive results.

Execution does not decide what became true.

Jeff only updates truth after outcome and evaluation have produced an evidence-backed basis for transition.

## Memory Is Not State

Memory stores useful, committed, retrievable knowledge.

Memory does not define current truth.

Only the Memory module creates memory candidates.

Canonical state may reference only committed memory IDs.

Jeff must never store uncommitted or failed memory links as if they were real truth.

## Orchestrator Coordinates, It Does Not Think

The orchestrator sequences modules, enforces order, validates boundaries, and routes failures.

It does not:
- invent decisions
- own policy semantics
- own transition semantics
- become a hidden planner
- absorb module-local reasoning

## Modules Must Remain Bounded

Every module must have:
- one clear role
- explicit inputs
- explicit outputs
- explicit non-responsibilities
- explicit failure behavior

Jeff must not accumulate blob modules that mix truth, research, planning, action, and interface concerns.

## Policy Must Stay Explicit

Policy defines what is allowed, blocked, approval-gated, or autonomy-gated.

Policy must be machine-checkable, auditable, and visible in the architecture.

It must not live only in prompt wording or operator habit.

## Architecture Must Stay Stronger Than the Model

The model is a capability inside the system, not the authority above it.

Jeff must rely on architecture to enforce:
- truth
- mutation control
- policy
- bounded autonomy
- memory discipline
- auditability

If the system depends on the model "knowing better," the architecture is already weak.

# Canonical v1 Backbone

The canonical v1 backbone is fixed.

Jeff v1 uses:
- one global canonical state with nested projects
- project as a hard isolation boundary inside global state
- `project + work_unit + run` as foundational containers
- no first-class workflow truth object in v1
- conditional planning rather than universal planning
- `selection -> action -> approval + readiness -> execution` as the default action path
- transitions as the only canonical truth mutation contract
- Memory as the only owner of memory candidate creation
- canonical state references only to committed memory IDs
- an expanded but bounded outcome and evaluation verdict model

The canonical v1 operational loop is:

`trigger -> state read -> context -> proposal -> selection -> action -> governance -> execution -> outcome -> evaluation -> memory -> transition -> updated state`

Conditional planning may be inserted between selection and governance when the work requires structured multi-step coordination.

# What Jeff Must Be Able to Do

Jeff must be able to:
- manage many operator projects inside one global system
- preserve hard project isolation inside global truth
- hold direction for each project over time
- operate through bounded work units and runs
- perform project-scoped internet research
- gather source-aware evidence
- synthesize findings into clear outputs
- compare alternatives with explicit assumptions and risks
- propose bounded next actions honestly
- select one option or honestly return a non-selection outcome such as reject-all, defer, or escalate
- form bounded action intent from selected or plan-refined work
- perform approval and readiness checks before execution
- execute bounded work through tools, model assistance, and external sources
- normalize observed outcome
- evaluate results with bounded verdicts that distinguish success, degradation, partial completion, inconclusive results, and recovery/revalidation needs
- update memory conservatively and link only committed memory
- update canonical truth only through transitions
- produce outputs that are useful for both Jeff-project and non-Jeff projects

Jeff-project work is one core use case. Jeff must also support non-Jeff work such as:
- researching a topic for a personal project
- gathering market or product evidence
- comparing tools or products for a real decision
- producing a source-aware research brief
- synthesizing findings into a memo, report, or decision-ready output

# End-to-End Workflow Examples

## Basic Bounded Execution Flow

1. The operator opens a project and sets a work unit objective.
2. Jeff reads global truth, then project truth, then work-unit truth.
3. Jeff assembles bounded context.
4. Jeff generates 0 to 3 serious proposals.
5. Jeff selects one option or returns an honest non-selection outcome.
6. Jeff forms a bounded action from the selected option.
7. Jeff performs approval and readiness checks.
8. If governance passes, Jeff executes the bounded action.
9. Jeff captures outcome, evaluates it, writes any committed memory, and applies truth changes through a transition.
10. Jeff returns a clear result to the operator.

## Jeff-Project Planning and Execution Example

Project: `jeff`

Work unit: define the first canonical `ARCHITECTURE.md`

1. Jeff reads the Jeff project direction, current work-unit scope, and relevant prior memory.
2. Jeff gathers relevant architecture documents and contradictions.
3. Jeff generates serious options such as:
   - write the architecture doc directly from settled canon
   - perform a short comparison pass before writing
   - reject execution because a blocking policy or unresolved contradiction remains
4. Jeff selects one path.
5. If the work is multi-step or review-heavy, Jeff creates a bounded plan first.
6. Jeff forms a bounded action for the document-writing work.
7. Jeff performs readiness and approval checks for that action.
8. Jeff executes the writing pass.
9. Jeff observes what changed, evaluates whether the result matches the canonical decisions, and records only useful committed memory.
10. Jeff updates project truth through transitions and reports the result.

## Non-Jeff Internet Research Example

Project: `home_energy_upgrade`

Work unit: research heat-pump options and incentives

1. The operator defines the project and scope.
2. Jeff assembles current project truth, objectives, constraints, and prior memory.
3. Jeff runs project-scoped internet research.
4. Jeff gathers sources, records provenance, and distinguishes findings from inference.
5. Jeff synthesizes the evidence into a clear output such as:
   - a source-aware research brief
   - a comparison table
   - a recommendation memo with cautions
6. If action is needed, Jeff generates and selects bounded next steps.
7. Jeff escalates only if approval, missing constraints, or unresolved conflict blocks the path.

This is not Jeff working on Jeff. It is Jeff acting as a general personal research and output system inside a non-Jeff project.

## Blocked and Escalation Flow

1. Jeff selects a promising option.
2. Pre-execution governance detects one of the following:
   - approval required
   - readiness failed
   - blocker present
   - stale basis
   - unresolved conflict in direction or scope
3. Jeff does not execute.
4. Jeff returns a bounded escalation that explains:
   - what blocked the action
   - why the block is real
   - what approval or clarification is needed
   - what work can continue safely, if any
5. Jeff remains truthful about the blocked state.

## Future Long-Running Bounded-Autonomy Flow

1. The operator defines a project, work unit, and autonomy boundary.
2. Jeff receives a bounded objective such as overnight research or a multi-run implementation pass.
3. Jeff continues across many runs while staying inside:
   - project scope
   - work-unit scope
   - policy
   - approval boundaries
4. Jeff updates memory conservatively and truth only through transitions.
5. Jeff surfaces checkpoints, cautions, and escalations only when needed.
6. Jeff returns with durable outputs rather than forcing the operator to restart the work from scratch.

This is future capability. It depends on stronger runtime, policy, and oversight layers, but it grows from the same backbone rather than replacing it.

# Operator Model

The operator remains the authority above the system.

The operator is responsible for:
- strategic direction
- project creation and major scope decisions
- major approvals
- meaningful risk decisions
- conflict resolution when the system cannot decide safely

Jeff should operate without operator input when:
- the objective is already bounded
- the next step is inside policy
- approval is not required
- readiness is satisfied
- uncertainty does not block safe progress

Jeff must escalate when:
- approval is required
- readiness fails
- a blocker or contradiction prevents honest continuation
- the next action exceeds allowed risk
- strategic conflict or scope conflict appears
- a degraded or inconclusive result requires operator judgment

The future operator experience should feel like this:
- the operator sets direction and boundaries
- Jeff carries bounded work forward
- Jeff asks fewer but sharper questions
- Jeff returns with clear outputs and real state updates
- Jeff does not require constant babysitting
- Jeff does not hide what it is doing or why

# Human View vs System View

## User-Facing View

From the operator's perspective, Jeff should feel like:
- one personal system
- organized by projects
- carrying real ongoing work rather than isolated prompts
- capable of research, synthesis, planning, and bounded execution
- able to explain current status, next action, and blockers clearly

The operator should think in terms of:
- what project is active
- what work unit is in focus
- what Jeff is doing
- what Jeff found
- what Jeff needs from the operator, if anything

## System-Facing View

From the system's perspective, Jeff is:
- one global truth system
- containing nested projects
- each project containing work units
- each work unit containing runs over time
- surrounded by bounded modules that read, decide, govern, act, observe, evaluate, remember, and transition

The system does not think in terms of chat alone.

It thinks in terms of:
- canonical state
- project isolation
- bounded work containers
- evidence-backed results
- controlled transitions

# Future Autonomy Model

Future autonomy is bounded expansion of the same architecture, not a new architecture.

Jeff should eventually be able to:
- continue bounded work across time
- run repeated research or execution passes
- manage waiting states and resumptions
- preserve continuity across many runs
- ask for approval only when required
- stop, escalate, or revalidate honestly

Future autonomy must remain bounded by:
- explicit policy
- explicit approval rules
- explicit readiness rules
- explicit state transitions
- explicit work-unit scope
- explicit operator override

Future autonomy must not be built by:
- hiding loops in orchestration
- letting planning become universal command authority
- treating memory as truth
- removing human control points

Open future edge:
- long-running autonomous continuation is a future system capability, not a v1 promise

# Top-Level Architecture

Jeff has nine top-level layers:
- Core
- Governance
- Cognitive
- Action
- Memory
- Orchestration
- Interface
- Infrastructure
- Assistant

These layers are ordered by responsibility, not style.

Core owns truth, state, transitions, and shared truth contracts.

Governance owns policy and action-entry permission law.

Cognitive owns bounded reasoning and judgment.

Action owns execution, outcome, and bounded real-world mutation support flows.

Memory owns durable non-truth continuity.

Orchestration owns sequencing.

Interface owns human and client access.

Infrastructure owns commodity technical capabilities.

Assistant owns future higher-level interaction behavior on top of the rest of the system.

# Module Placement by Layer

## Core

Core contains:
- state
- transitions
- schemas

Core owns:
- canonical truth
- truth mutation law
- shared truth contracts
- foundational `project + work_unit + run` containers

## Governance

Governance contains:
- policy
- approval
- readiness
- pre-execution permissioning and action-entry safety checks

Governance owns:
- permission law
- action-entry safety
- explicit allow/block/defer/escalate decisions

## Cognitive

Cognitive contains:
- context
- research
- proposal
- selection
- evaluation
- conditional planning

Cognitive owns:
- truth-first context assembly
- source-aware research
- bounded option generation
- controlled decision
- judgment of results
- planning only when the work shape requires it

## Action

Action contains:
- execution
- outcome
- bounded `Change` / apply / recovery support flows when required

Action owns:
- governed doing after permission
- tool and model-assisted execution
- observed-result normalization

## Memory

Memory contains:
- memory candidate creation
- memory write policy
- memory storage
- memory retrieval
- memory linking

Memory owns:
- conservative long-term storage
- retrieval for future work
- committed memory references only

## Orchestration

Orchestration contains:
- system orchestrator
- flow sequencing
- lifecycle control
- failure routing

Orchestration owns:
- order
- handoff validation
- lifecycle progression
- stop and escalation routing

## Interface

Interface contains:
- CLI
- future GUI
- future API bridge

Interface owns:
- human and client access
- truthful display of system state
- controlled action entry points

## Infrastructure

Infrastructure contains:
- storage backends
- model adapters
- tool adapters
- observability
- configuration plumbing
- external connectors

Infrastructure owns:
- technical support
- provider abstraction
- low-level system plumbing

## Assistant

Assistant contains:
- intent framing
- conversational continuity
- future scheduling and initiative behavior

Assistant owns:
- human-facing interaction behavior above the core system

Assistant does not own truth, mutation, or policy.

# Repository and Folder Architecture

The repository should be organized to make architecture visible and drift harder.

```text
Jeff/
|
+-- jeff_planning_docs/
|   +-- v1_doc/
|   |   +-- VISION.md
|   |   +-- ARCHITECTURE.md
|   |   +-- GLOSSARY.md
|   |   +-- CORE_SCHEMAS_SPEC.md
|   |   +-- STATE_MODEL_SPEC.md
|   |   +-- TRANSITION_MODEL_SPEC.md
|   |   +-- POLICY_AND_APPROVAL_SPEC.md
|   |   +-- PROJECT_AND_WORK_UNIT_MODEL_SPEC.md
|   |   +-- CONTEXT_SPEC.md
|   |   +-- PROPOSAL_AND_SELECTION_SPEC.md
|   |   +-- EXECUTION_OUTCOME_EVALUATION_SPEC.md
|   |   +-- MEMORY_SPEC.md
|   |   +-- ORCHESTRATOR_SPEC.md
|   |   +-- PLANNING_AND_RESEARCH_SPEC.md
|   |   +-- CHANGE_CONTROL_SPEC.md
|   |   +-- INTERFACE_OPERATOR_SPEC.md
|   |   +-- TESTS_PLAN.md
|   |   +-- HANDOFF_STRUCTURE.md
|   |   +-- ROADMAP_V1.md
|   |   `-- DOCS_GOVERNANCE.md
|   `-- legacy_archive/
|
+-- src/
|   `-- jeff/
|       +-- core/
|       |   +-- state/
|       |   +-- transitions/
|       |   `-- schemas/
|       +-- governance/
|       |   +-- policy/
|       |   +-- approval/
|       |   `-- readiness/
|       +-- cognitive/
|       |   +-- context/
|       |   +-- research/
|       |   +-- proposal/
|       |   +-- selection/
|       |   +-- evaluation/
|       |   `-- planning/
|       +-- action/
|       |   +-- execution/
|       |   `-- outcome/
|       +-- memory/
|       +-- orchestrator/
|       +-- interface/
|       +-- infra/
|       `-- assistant/
|
+-- governance/
|   +-- docs/
|   `-- repo_rules/
|
+-- handoffs/
|   +-- system/
|   `-- projects/
|
+-- tests/
|   +-- unit/
|   +-- integration/
|   +-- functional/
|   +-- e2e/
|   +-- acceptance/
|   +-- smoke/
|   `-- performance/
|
`-- projects/
    `-- <project_id>/
        +-- artifacts/
        +-- research/
        +-- outputs/
        +-- memory/
        `-- working_data/
```

Rules implied by this structure:
- canonical source-of-truth docs live in `jeff_planning_docs/v1_doc/`
- legacy docs do not remain equal authorities
- implementation modules live under `src/jeff/`
- root-level handoff areas support overall system understanding
- module and submodule handoffs also live with their owning code and modules
- project data remains project-scoped rather than mixed into one global artifact dump

# System Map

```text
Operator
   |
   v
Interface / Assistant
   |
   v
Orchestrator
   |
   +--> Read Global Canonical State
   |        |
   |        +--> Project
   |        |      |
   |        |      +--> Work Unit
   |        |             |
   |        |             `--> Run
   |        |
   |        `--> System-wide truth context
   |
   v
Context
   |
   +--> Truth-first state read
   +--> Relevant committed memory retrieval
   +--> Evidence and source inputs
   |
   v
Proposal (0 to 3 serious options)
   |
   v
Selection
   |
   +--> select one
   +--> reject-all / defer / escalate
   |
   +--> optional conditional planning for multi-step/high-risk work
   |
   v
Action
   |
   +--> bounded intended work
   +--> not permission by itself
   |
   v
Governance
   |
   +--> policy / approval / readiness
   |
   +--> blocked / escalate / revalidate
   +--> execution ready
   |
   v
Execution
   |
   +--> tools
   +--> internet research
   +--> model-assisted work
   |
   v
Outcome
   |
   v
Evaluation
   |
   +--> success / cautions / partial / degraded
   +--> recovery / revalidation / escalate / terminate-and-replan
   |
   v
Memory
   |
   +--> create memory candidates
   +--> commit accepted memory entries only after successful memory write pipeline
   |
   v
Transition
   |
   v
Updated Canonical State
   |
   v
Clear Output Back to Operator
```

# Mental Map

The simplest correct mental model of Jeff is this:

1. Jeff is one global truth system.
2. Inside that system, projects are hard isolation boundaries.
3. Inside each project, work happens through work units.
4. A run is one bounded attempt inside a work unit.
5. Around those containers, modules perform different jobs:
   - context sees what matters
   - proposal suggests possibilities
   - selection chooses
   - action operationalizes intended work
   - governance decides whether action may start
   - execution acts
   - outcome records what happened
   - evaluation judges the result
   - memory stores what matters later
   - transitions update truth
6. Planning is conditional support for structured work, not the universal path.
7. Workflow is not a first-class truth object in v1.
8. The operator sets direction and boundaries; Jeff carries bounded work forward inside them.

If someone cannot explain Jeff in those terms, they are probably describing either a chatbot, an agent framework, or a workflow engine, not Jeff.

# Success Criteria

## Product Success

Jeff succeeds as a product if it:
- reduces cognitive load
- supports real project work across time
- performs useful project-scoped research
- gathers evidence and produces clear outputs
- helps the operator make and execute decisions with less fragmentation
- works for Jeff and non-Jeff projects alike

## Architectural Success

Jeff succeeds architecturally if:
- one global canonical state remains the only truth
- project isolation remains hard inside that state
- transitions remain the only truth mutation path
- selection remains distinct from execution permission
- Governance remains a distinct first-class layer
- approval and readiness remain real governance gates
- execution remains distinct from truth
- memory remains bounded and secondary to truth
- modules stay bounded
- orchestrator remains a coordinator
- future autonomy grows from stronger structure rather than weaker boundaries

## v1 Practical Success

Jeff v1 succeeds practically if it:
- supports bounded project work through `project + work_unit + run`
- performs useful project-scoped internet research
- produces source-aware outputs
- runs the default `selection -> action -> governance -> execution` path cleanly
- invokes planning only when the work shape genuinely needs it
- handles blocked, degraded, inconclusive, and escalation paths honestly
- feels simpler and more useful than manually restitching the same work in raw chat sessions

# Failure Modes

## Architectural Failure Modes

Jeff is architecturally failing if:
- memory starts acting like truth
- transitions are bypassed
- `Change` becomes a rival truth mutation path
- selection is treated as execution permission
- workflow becomes a first-class hidden brain before it is earned
- orchestrator absorbs reasoning and policy
- modules start mixing many roles
- project and work-unit scope stop anchoring the system

## Product Failure Modes

Jeff is failing as a product if:
- it only works well on Jeff and not on general personal projects
- internet research remains shallow or source-blind
- outputs are verbose but not decision-useful
- the operator has to babysit every step
- the system asks too many low-value questions
- the system creates more complexity than it removes
- the system feels like a prompt wrapper with extra folders

## Documentation Failure Modes

Jeff documentation is failing if:
- vision, architecture, and specs drift apart
- canonical docs lose authority to legacy documents
- future capability language is mistaken for v1 commitment
- repository structure in docs becomes decorative rather than directive
- high-level docs start carrying low-level contract detail they do not own

# Non-Goals

Jeff v1 does not aim to be:
- a finished Jarvis
- an always-on autonomous runtime
- a multi-agent framework
- a platform-first product
- a workflow object empire
- a GUI-first system
- a broad integration marketplace
- a memory-maximization system
- a fully general planning engine where every task becomes a plan

Jeff in any version does not aim to be:
- a system where model output silently becomes truth
- a system where research, proposal, selection, execution, and evaluation collapse together
- a system where the operator loses meaningful control

# Boundary of This Document

This document defines:
- what Jeff is
- what Jeff is for
- the canonical v1 backbone
- the top-level architectural shape
- the intended operator model
- the repository and system mental model

This document does not define:
- low-level schema fields
- exact verdict enumerations
- exact transition object structure
- exact approval object structure
- detailed research contracts
- test requirements
- implementation status
- handoff templates

Open future edges are marked explicitly where they belong, especially around long-running autonomy and richer assistant behavior.

# Questions

No unresolved vision-level questions were found in this pass.

# Final Statement

Jeff is a personal, modular, truth-grounded work system built to reduce cognitive load without surrendering control.

It is designed to support real projects, real research, real outputs, and real bounded execution across time.

Its v1 backbone is clear:
- one global canonical state
- hard project isolation
- `project + work_unit + run` as the work containers
- proposal separated from selection
- selection separated from execution permission
- action before governance
- approval and readiness before execution
- execution separated from truth
- memory separated from state
- transitions as the only truth mutation path

If that backbone remains intact, Jeff can grow into a powerful bounded-autonomy system without becoming chaos.

If that backbone is weakened, Jeff will collapse into another smart-looking but unreliable AI shell.
