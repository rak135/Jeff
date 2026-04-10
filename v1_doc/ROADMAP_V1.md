# Purpose

This document defines Jeff's canonical v1 sequencing-and-delivery law.

It owns:
- the v1 strategic objective
- the v1 phase sequence
- dependency rules for build order
- entry criteria by phase
- exit criteria by phase
- v1 scope cuts
- the immediate build order
- sequencing risks and failure modes
- what is explicitly deferred beyond v1

It does not own:
- architecture law
- module semantics
- truth semantics
- handoff template bodies
- docs authority order itself
- interface design details
- roadmap fantasy beyond what the canon and real dependency logic justify

This is the canonical v1 sequencing-and-delivery document for Jeff.
It turns the already-set canon into disciplined build order.
It does not redefine Jeff meaning.
It does not act as a wishlist, status report, or rival semantic layer.

# Canonical Role in Jeff

Jeff already has its meaning defined in the canonical `v1_doc` set.
The role of the roadmap is to sequence delivery of that canon into a real v1 system without letting build convenience rewrite architecture.

Jeff cannot tolerate roadmap drift such as:
- phase order that contradicts the canonical dependency chain
- scope expansion because a later-layer feature feels attractive
- demo progress being treated as semantic readiness
- interface or orchestration richness arriving before backend meaning is stable
- roadmap language quietly reintroducing first-class workflow truth, universal planning, memory-as-truth, or hidden autonomy

This document protects build realism by making one thing explicit:
- canon defines what Jeff means
- roadmap defines the order in which v1 earns those capabilities safely

# Core Principle

The binding law is:
- the v1 roadmap is sequencing law for delivery, not a semantic authority layer
- build order must follow dependency and risk, not aesthetic preference or demo value
- a phase is not done because something demos; it is done when its semantic, contract, test, and documentation gates are met
- explicit deferral is healthier than fake inclusion

Jeff v1 must be built from truth safety outward:
- state and transition discipline before downstream convenience
- governance before governed action
- stage boundaries before orchestration richness
- truthful CLI-first surfaces before GUI or broad API ambition
- docs, handoffs, and tests strong enough to prevent parallel-authority drift while implementation grows

# v1 Strategic Objective

The v1 objective is to deliver one truthful, testable, CLI-first Jeff backbone that can:
- operate on one global canonical state with nested projects
- preserve `project + work_unit + run` as foundational containers
- assemble truth-first context
- perform bounded research, proposal, selection, and conditional planning where needed
- require governance before execution
- keep execution, outcome, and evaluation separate
- preserve memory as durable non-truth continuity
- coordinate bounded flows through a non-thinking orchestrator
- expose operator-visible truth without interface-owned semantics

This objective serves the whole-Jeff target context without pretending v1 includes every future richness.
It is the smallest complete backbone that makes Jeff architecturally real rather than merely promising.

# Phase Sequence

Jeff v1 should be delivered in the following bounded sequence.

## Phase 1 - Canonical Backbone and Truth-Safe Core

Purpose:
- establish the canonical backbone that all later phases depend on

This phase establishes:
- shared schema discipline
- one global canonical state with nested projects
- hard project isolation
- `project + work_unit + run` as foundational containers
- transition-only truth mutation
- canonical docs, handoff, and test discipline strong enough to stop early drift

This phase depends on:
- the canonical `v1_doc` set as the active authority layer

## Phase 2 - Governance and Action-Entry Safety

Purpose:
- make permission, approval, readiness, and lawful action entry real before any execution flow is allowed to matter

This phase establishes:
- governance outputs as distinct objects
- selection-not-permission discipline in implementation
- narrow `action` handling at the action-entry boundary
- revalidation and staleness discipline for governed action

This phase depends on:
- Phase 1 truth, container, and transition discipline

## Phase 3 - Context, Research, Decision, and Conditional Planning

Purpose:
- make Jeff able to assemble bounded truth-first reasoning input and produce bounded decision support without collapsing research, proposal, selection, and planning into one blob

This phase establishes:
- truth-first context assembly
- bounded research and provenance discipline
- bounded proposal generation
- bounded selection with honest `0..3` serious options
- planning only where work shape actually requires it

This phase depends on:
- Phase 1 truth and transition discipline
- Phase 2 governance and action-entry boundaries

## Phase 4 - Governed Execution, Outcome, and Evaluation

Purpose:
- make Jeff able to perform governed action and judge observed results without collapsing execution, outcome, and evaluation

This phase establishes:
- execution only after governance allows action
- normalized outcome handling
- evidence-backed evaluation
- bounded verdict families
- bounded recommended next-step outputs

This phase depends on:
- Phase 2 governance and action-entry safety
- Phase 3 upstream decision and planning outputs being contract-stable enough to form lawful action

## Phase 5 - Memory and Durable Continuity Discipline

Purpose:
- preserve continuity safely after Jeff can already act and judge

This phase establishes:
- Memory as the only creator of memory candidates
- committed-memory-only canonical references
- selective write pipeline
- scoped, truth-first retrieval
- hard separation between memory and current truth

This phase depends on:
- Phase 4 outcome and evaluation being stable enough to inform memory work without candidate-authority blur

## Phase 6 - Orchestrator Integration and CLI-First Operator Surface

Purpose:
- coordinate the now-stable stage contracts into lawful flow shapes and expose them through truthful operator surfaces

This phase establishes:
- orchestrator sequencing by public contracts only
- bounded routing for blocked, escalated, retry, revalidate, recover, and terminate-and-replan paths
- CLI as the primary truthful operator surface
- thin API bridge only where needed to support the CLI-first contract model

This phase depends on:
- Phases 2 through 5 having stable stage contracts worth sequencing and exposing

## Phase 7 - Hardening, Acceptance, and Continuation Discipline

Purpose:
- prove the v1 backbone is trustworthy enough to treat as the real delivery baseline rather than an optimistic prototype

This phase establishes:
- cross-phase acceptance confidence
- anti-drift test coverage across the full backbone
- docs and handoffs aligned with implementation reality
- explicit deferral boundaries that stop v1 from quietly expanding

This phase depends on:
- the earlier phases being implemented and contract-visible end to end

# Dependency Rules

The roadmap obeys the following hard sequencing rules:

- truth safety before convenience
- one canonical state and transition-only mutation before downstream flow composition
- project isolation before cross-surface aggregation
- governance before execution
- stage boundaries before orchestration richness
- contract stability before exposing broader operator surfaces
- evaluation before memory write discipline
- memory discipline before richer retrieval behavior
- CLI-first truthfulness before GUI or broad public API ambitions
- docs governance, handoff discipline, and tests must advance with implementation rather than lag behind it
- phase advancement requires semantic readiness, not demo confidence
- if sequencing pressure conflicts with canon, canon wins

Practical dependency consequences:
- do not build interface richness to hide missing backend meaning
- do not let orchestrator convenience absorb governance, evaluation, or transition semantics
- do not broaden memory before truth separation is safe
- do not introduce workflow-shaped authority as a shortcut around v1's non-first-class workflow rule
- do not scale module count faster than docs, tests, and handoff truth can support

# Entry Criteria by Phase

Each phase has explicit entry obligations.
If they are not met, the phase may be explored, but not treated as active delivery.

## Phase 1 - Canonical Backbone and Truth-Safe Core

Entry criteria:
- the canonical `v1_doc` set exists as the active authority layer
- open semantic contradictions at the backbone level are already settled or explicitly out of scope for this phase
- docs governance and handoff discipline are active enough to prevent new parallel-authority drift during implementation

## Phase 2 - Governance and Action-Entry Safety

Entry criteria:
- Phase 1 exit criteria are met
- shared schema naming and object-family distinctions are stable enough to represent governance outputs cleanly
- state and transition surfaces are strong enough that governance is not being built on shadow truth

## Phase 3 - Context, Research, Decision, and Conditional Planning

Entry criteria:
- Phase 2 exit criteria are met
- truthful reads of canonical state are already available
- action-entry safety exists strongly enough that proposal/selection work is not implicitly drifting into execution authority

## Phase 4 - Governed Execution, Outcome, and Evaluation

Entry criteria:
- Phase 3 exit criteria are met
- governed action entry is real, not inferred
- bounded action formation is possible without collapsing plans, proposals, or selections into execution authority

## Phase 5 - Memory and Durable Continuity Discipline

Entry criteria:
- Phase 4 exit criteria are met
- outcome and evaluation outputs are stable enough to inform memory work without becoming memory candidates themselves
- truth-first reads remain stronger than any candidate retrieval behavior

## Phase 6 - Orchestrator Integration and CLI-First Operator Surface

Entry criteria:
- Phases 2 through 5 exit criteria are met
- stage handoff contracts are explicit enough that orchestration can sequence them without guessing
- truthful operator display can be built on backend meaning rather than compensating for missing semantics

## Phase 7 - Hardening, Acceptance, and Continuation Discipline

Entry criteria:
- Phase 6 exit criteria are met
- at least one bounded end-to-end Jeff backbone flow is real
- docs, handoffs, and tests are strong enough that hardening work can reveal drift instead of hiding it

# Exit Criteria by Phase

Each phase must prove semantic safety for the next phase.
Exit criteria are aligned with `TESTS_PLAN.md`, `DOCS_GOVERNANCE.md`, and the relevant canonical module specs.

## Phase 1 - Canonical Backbone and Truth-Safe Core

Exit criteria:
- one global canonical state with nested projects is implemented and test-protected
- project isolation is implemented and test-protected
- `project + work_unit + run` exist as real foundational containers, not placeholders
- transitions are the only canonical truth mutation contract in implementation and tests
- core schema, state, transition, and container handoffs have contract coverage
- docs governance and handoff discipline are active enough that local implementation truth can be reported without semantic drift

## Phase 2 - Governance and Action-Entry Safety

Exit criteria:
- approval and readiness are distinct in contracts, implementation, and tests
- selection does not imply permission anywhere in the active flow surface
- action entry requires governance and rejects stale or incomplete basis
- governance outputs are explicit enough that downstream stages do not infer missing meaning
- negative tests exist for selection-as-permission and approval/readiness flattening

## Phase 3 - Context, Research, Decision, and Conditional Planning

Exit criteria:
- context is truth-first and scoped, with memory and evidence remaining subordinate and distinct
- research is bounded, provenance-preserving, and distinguishes findings, inference, and recommendation
- proposal may honestly return `0..3` serious options and does not fabricate option abundance
- selection remains distinct from proposal and from permission
- planning is demonstrably conditional rather than universal
- failure coverage exists for weak evidence, contradiction, reject-all, defer, escalate, and unnecessary-plan scenarios

## Phase 4 - Governed Execution, Outcome, and Evaluation

Exit criteria:
- execution begins only after governance allows action
- execution, outcome, and evaluation are contractually and behaviorally distinct
- outcome and evaluation use bounded verdict families rather than coarse success/fail theater
- deterministic hard failures cap optimistic evaluation where required
- evaluation recommendations remain recommendations and do not self-authorize follow-up action
- tests cover blocked, degraded, inconclusive, mismatch-affected, and execution-complete-versus-objective-complete distinctions

## Phase 5 - Memory and Durable Continuity Discipline

Exit criteria:
- only Memory creates memory candidates in implementation and tests
- canonical state references only committed memory IDs where memory linkage exists
- memory write pipeline is selective and bounded, with reject and defer paths real
- truth-first retrieval is enforced and memory does not override current truth
- failure coverage exists for duplicate memory, stale memory, weakly grounded memory, and cross-project bleed

## Phase 6 - Orchestrator Integration and CLI-First Operator Surface

Exit criteria:
- orchestrator sequences public stage contracts without absorbing business logic
- malformed or impossible handoffs stop or hold rather than getting patched over
- blocked, escalated, retry, revalidate, recover, and terminate-and-replan routing preserve explicit reasons and scope
- CLI truthfully preserves key distinctions including:
  - selected vs permitted
  - approved vs applied
  - outcome state vs evaluation verdict
  - canonical truth vs support artifact
- interface/session state does not become shadow truth
- smoke, integration, and functional coverage exist for the CLI-first surface and orchestration boundaries

## Phase 7 - Hardening, Acceptance, and Continuation Discipline

Exit criteria:
- the core v1 end-to-end flow families required by `TESTS_PLAN.md` pass
- phase-to-phase invariants remain green under failure-path coverage, not just happy paths
- docs, handoffs, and canonical references are current enough that continuation does not depend on chat reconstruction
- no major known semantic flattening, shadow-truth, or hidden-authority drift remains untracked
- explicit beyond-v1 deferrals are documented and not being silently built under v1 language

# v1 Scope Cuts

The roadmap must be explicit about what v1 includes, what is conditional, and what is out of scope.

## Definitely In v1

- the canonical `v1_doc` set as the active authority layer
- one global canonical state with nested projects
- hard project isolation
- `project + work_unit + run` as foundational containers
- transition-only truth mutation
- governance with distinct approval and readiness
- truth-first context
- bounded research, proposal, and selection
- conditional planning only where work shape requires it
- governed execution, normalized outcome, and evidence-backed evaluation
- memory as durable non-truth continuity
- a non-thinking orchestrator over public contracts
- truthful CLI-first operator surfaces
- tests, docs governance, and handoff discipline strong enough to prevent drift during delivery

## Conditional In v1

- direct research-output flows where they are genuinely bounded and useful
- planning insertion after selection only where the selected work actually needs multi-step structure
- thin API bridge support where it serves the CLI-first contract model rather than expanding public product surface
- bounded recovery, revalidation, or retry routing where explicit recommendations already exist
- submodule handoffs where local complexity justifies them

## Out of Scope for v1

- first-class workflow truth
- hidden autonomy engine or silent self-propelling loops
- universal planning bureaucracy
- memory-as-truth shortcuts
- rich global memory that weakens project isolation
- heavy autonomous retry or recovery systems
- rich GUI ambition before CLI-first truthfulness is solid
- broad public API ambition before backend semantics and CLI contracts are proven
- scope expansion driven by roadmap optimism rather than canonical dependency

# Immediate Build Order

The practical near-term build order implied by this roadmap is:

1. Lock the canonical docs set, docs-governance rules, and handoff discipline as the active authority baseline.
2. Build shared schema discipline, root state topology, project/work_unit/run containers, and transition-only mutation with invariant tests.
3. Build governance, approval/readiness separation, and action-entry safety with negative tests for selection-as-permission drift.
4. Build truth-first context, bounded research, proposal, selection, and conditional planning without execution authority shortcuts.
5. Build execution, outcome, and evaluation with explicit verdict separation and failure-path coverage.
6. Build Memory's selective write pipeline and truth-first retrieval discipline.
7. Build orchestrator sequencing over those public contracts, then expose truthful CLI-first operator surfaces.
8. Harden the end-to-end backbone with acceptance gates, handoff cleanup, and explicit beyond-v1 deferrals.

This is a build order, not a daily task list.
It is the shortest sequence that keeps Jeff architecturally honest while still producing a real v1 backbone.

# Risks / Failure Modes in Sequencing

The roadmap is failing if sequencing drifts into any of the following:

- building interface richness before backend semantic stability
- allowing orchestrator convenience to absorb governance, evaluation, or transition meaning
- broadening memory before truth separation is safe
- adding workflow abstractions too early and effectively smuggling workflow truth into v1
- advancing phases on demo confidence instead of exit-gate evidence
- parallel implementation causing canon drift across modules
- letting roadmap optimism reintroduce scope sprawl
- treating tests as late hardening instead of phase-exit evidence
- letting docs and handoffs lag until implementation reality becomes hard to report truthfully
- allowing proposal, planning, action, governance, execution, outcome, and evaluation to collapse under delivery pressure

These are not project-management concerns only.
They are architectural failure modes.

# What Is Explicitly Deferred Beyond v1

The following are deliberately beyond v1 unless later canon says otherwise:

- first-class workflow truth
- richer global memory beyond the conservative v1 project-primary model
- advanced GUI dashboards and broad GUI surface richness
- broad public API expansion beyond thin support for the truthful CLI-first model
- strong multi-run continuation engines
- heavy autonomous retry, recovery, or revalidation systems
- hidden assistant-style autonomy layers that sit above orchestration
- rich workflow composition engines, branching systems, or DAG-style orchestration
- broader automation around docs, handoffs, or governance beyond what v1 needs to stay disciplined
- roadmap expansion that adds whole new semantic layers not already owned by the canon

Deferral here is intentional.
These items are not "almost in v1."
They are outside the v1 delivery promise because the backbone must be earned before richer behavior is allowed.

# Questions

No unresolved roadmap questions were found in this pass.

# Relationship to Other Canonical Docs

- The canonical `v1_doc` set owns Jeff meaning; this document only sequences delivery of that canon.
- `ARCHITECTURE.md` defines the backbone and dependency direction that this roadmap must respect.
- `STATE_MODEL_SPEC.md`, `TRANSITION_MODEL_SPEC.md`, and `PROJECT_AND_WORK_UNIT_MODEL_SPEC.md` define the truth-safe core that must be built first.
- `POLICY_AND_APPROVAL_SPEC.md` defines why governance and action-entry safety must precede execution.
- `CONTEXT_SPEC.md`, `PROPOSAL_AND_SELECTION_SPEC.md`, and `PLANNING_AND_RESEARCH_SPEC.md` define the bounded cognition and conditional-planning work that should be built before richer orchestration and interfaces.
- `EXECUTION_OUTCOME_EVALUATION_SPEC.md` and `MEMORY_SPEC.md` define the post-governance action and continuity layers that v1 must implement before claiming real Jeff backbone behavior.
- `ORCHESTRATOR_SPEC.md` and `INTERFACE_OPERATOR_SPEC.md` define the downstream coordination and operator-surface laws that should only be built once earlier contracts are stable.
- `TESTS_PLAN.md` defines the invariant, contract, failure-path, and acceptance evidence that this roadmap uses as phase gates.
- `HANDOFF_STRUCTURE.md` and `DOCS_GOVERNANCE.md` define the documentation discipline that must advance with implementation so v1 does not recreate parallel-authority chaos.

# Final Statement

Jeff v1 should be delivered as one disciplined backbone:
truth-safe core first, governance next, bounded cognition after that, then governed action and judgment, then memory, then orchestration and truthful operator access, and only then hardening and acceptance.

This roadmap is successful only if it makes semantic drift, authority blur, and scope sprawl harder at each phase.
If it stays hard, v1 becomes a real Jeff baseline.
If it softens, implementation order will quietly rewrite the canon and the roadmap will have failed its only job.
