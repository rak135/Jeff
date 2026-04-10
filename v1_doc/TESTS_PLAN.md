# Purpose

This document defines Jeff's canonical testing strategy.

It owns:
- test taxonomy
- invariant test coverage
- fixture strategy
- contract-to-test mapping
- phase and module exit gates
- failure scenario coverage
- testing anti-patterns
- v1 required test discipline

It does not own:
- architecture law
- state topology semantics
- governance semantics
- transition law itself
- interface rendering design
- telemetry schema design
- roadmap sequencing

This is the canonical Jeff testing-strategy document.
It is not an implementation-status note, not a generic software-testing essay, and not a substitute for module-local semantics.

# Canonical Role in Jeff

Jeff tests protect architecture and truth discipline, not just code correctness.

Jeff cannot tolerate a test posture where:
- happy paths are green while boundary erosion goes untested
- contracts drift while implementations still "work"
- interfaces flatten semantics while snapshot tests stay green
- execution, outcome, evaluation, memory, governance, and transition boundaries blur with no failing tests

The role of testing in Jeff is therefore structural:
- prove that critical invariants still hold
- prove that public contracts still mean what the canon says they mean
- prove that dangerous failure classes are surfaced honestly
- fail when semantic boundaries are violated, even if the system still looks useful

The same testing law protects Jeff-project work and non-Jeff project work.
The project domain may change.
The truth, scope, contract, and anti-drift obligations do not.

# Core Principle

The binding law is:
- Jeff tests must protect invariants, contracts, and honest semantics
- passing tests must mean more than "the script runs"
- anti-drift coverage is as important as feature coverage
- tests must fail when boundaries are violated, even if output still looks plausible

Jeff testing is not coverage theater.
It is the practical enforcement layer for architecture and truth discipline.

# Test Taxonomy

Jeff uses distinct test families because different risks require different protections.

## Init Tests

Purpose:
- prove the system can boot into a minimally valid testable state
- prove core registries, schema loaders, state bootstrap, and basic dependency wiring are not broken

Not for:
- deep business semantics
- full module interaction coverage

Jeff risks caught:
- broken startup contracts
- invalid base fixtures
- schema registry failure
- environment assumptions that make all later tests misleading

## Unit Tests

Purpose:
- verify one module or one bounded responsibility in isolation
- prove local invariants, validation rules, and rejection behavior

Not for:
- full stage sequencing
- cross-module truth handoffs

Jeff risks caught:
- local rule drift
- validator gaps
- naming drift
- deterministic override failures

## Integration Tests

Purpose:
- verify real handoffs between adjacent stages or closely related layers
- prove structured outputs are consumable by downstream modules without guesswork

Not for:
- full end-to-end claims
- interface rendering behavior in aggregate

Jeff risks caught:
- malformed handoffs
- contract reinterpretation
- scope mismatch
- hidden neighbor-layer ownership

## Functional Tests

Purpose:
- verify bounded user-visible or system-visible capabilities against their declared semantics
- prove a feature works as a coherent slice, not just as isolated functions

Not for:
- pretending one feature equals full end-to-end backbone coverage

Jeff risks caught:
- feature semantics lying by omission
- blocked or degraded behavior hidden inside a "working" capability
- action or request surfaces implying more authority than they actually have

## End-to-End Tests

Purpose:
- verify whole-Jeff flow shapes across the backbone
- prove major stages occur in lawful order and preserve distinctions across the full path

Not for:
- exhaustive combinatorial coverage
- replacing targeted invariant tests

Jeff risks caught:
- stage collapse
- unlawful sequencing
- hidden mutation shortcuts
- cross-layer semantic drift that only appears across a full flow

## Acceptance Tests

Purpose:
- verify that a module, phase, or major flow is safe enough to claim as done for its intended role
- prove that exit-gate obligations are actually met

Not for:
- vague demo confidence
- replacing lower-level failure coverage

Jeff risks caught:
- declaring phases done on happy-path evidence only
- downstream consumers still needing to guess semantics
- release or phase claims exceeding the real system

## Performance Tests

Purpose:
- verify bounded latency, throughput, cost, or resource expectations on important paths
- prove performance work does not silently corrupt semantics

Not for:
- brag metrics with no semantic integrity checks
- allowing performance gains to excuse truth or governance violations

Jeff risks caught:
- latency collapse on core paths
- pathological retrieval blowups
- orchestration overhead regressions
- cost increases hidden behind "still correct" claims

## Smoke Tests

Purpose:
- provide fast fail-closed checks that core surfaces still load, route, and obey basic contract shape
- catch obvious breakage before deeper suites run

Not for:
- semantic sign-off
- acceptance claims

Jeff risks caught:
- broken CLI/API entry points
- missing required commands or payload fields
- catastrophic stage-entry failure
- obvious invalid state/bootstrap conditions

# Invariant Test Coverage

Every major canonical invariant must map to explicit test obligations.
If a canonically important boundary can be violated without a targeted failing test, coverage is incomplete.

## One Global State With Nested Projects

Test obligations:
- state-model tests must prove there is one canonical root and that projects are nested inside it rather than treated as separate truth stores
- transition tests must reject writes that would create rival truth homes or illegal root shapes
- context tests must read current truth from canonical state first rather than reconstructing it from memory, artifacts, or traces

Anti-drift failures to test:
- per-project truth-store drift
- interface cache or memory being accepted as truth source
- run/history/memory reconstructing state by convenience

## Project Isolation

Test obligations:
- state, context, memory, orchestrator, and interface tests must prove project remains the hard isolation boundary
- retrieval and handoff tests must reject wrong-project reads and wrong-project linked refs
- flow tests must prove one project's work cannot silently mutate, route through, or appear inside another project's truth

Anti-drift failures to test:
- cross-project bleed
- wrong-project retrieval
- cross-scope action or transition targeting
- interface summaries merging project surfaces

## `project + work_unit + run` Foundational Containers

Test obligations:
- state and container tests must prove runs belong to one work unit and one project in v1
- integration and e2e tests must preserve scope linkage through context, execution, outcome, evaluation, memory, and transition
- fixture suites must include minimal but explicit project/work_unit/run graphs

Anti-drift failures to test:
- run/work_unit/workflow collapse
- latest-run-defines-work-unit drift
- orphaned runs
- scope omitted from downstream objects

## Transition-Only Truth Mutation

Test obligations:
- transition tests must prove canonical truth changes only through validated transition commit
- negative tests must prove execution, evaluation, interface actions, memory writes, and orchestration metadata do not mutate truth directly
- e2e tests must verify that truth changes appear only after lawful transition steps

Anti-drift failures to test:
- direct state writes
- apply-implies-truth
- execution residue becoming truth
- interface- or orchestrator-owned mutation shortcuts

## Selection Does Not Imply Permission

Test obligations:
- decision/governance handoff tests must prove selection output cannot be consumed as execution permission
- governance tests must require action plus governance pass before execution entry
- interface tests must preserve selected vs permitted distinction

Anti-drift failures to test:
- selected-as-permitted collapse
- workflow-next-step treated as start authority
- plan review or proposal confidence treated as permission

## Approval and Readiness Separation

Test obligations:
- governance tests must prove approval and readiness are distinct outputs with distinct failure modes
- action-entry tests must prove approval can be satisfied while readiness is not, and vice versa where applicable
- interface tests must preserve approved vs applied and approved vs ready distinctions

Anti-drift failures to test:
- approval equals readiness
- approval equals apply
- stale approval reused as current readiness

## Execution / Outcome / Evaluation Separation

Test obligations:
- unit and integration tests must keep `execution_status`, `outcome_state`, and `evaluation_verdict` distinct
- deterministic override tests must prove hard failures cap evaluation optimism
- e2e tests must prove execution complete does not imply objective complete

Anti-drift failures to test:
- execution claims success it cannot know
- outcome equals evaluation
- completed equals acceptable
- artifact existence equals success

## Memory Truth Separation

Test obligations:
- memory tests must prove state wins for current-truth questions
- retrieval tests must read truth first, then memory, and keep conflicting memory labeled as support only
- transition and state tests must prove only committed memory IDs may be referenced canonically

Anti-drift failures to test:
- memory-as-truth
- stale memory overriding state
- weak memory outranking better-grounded support
- memory used as hidden truth repair

## Only Memory Creates Memory Candidates

Test obligations:
- module-boundary tests must prove execution, evaluation, research, interfaces, and orchestrator cannot create memory candidates directly
- write-pipeline tests must require Memory-owned candidate creation before validation, deduplication, commit, and linking
- negative tests must reject arbitrary-module candidate injection

Anti-drift failures to test:
- arbitrary modules writing memory
- auto-memory on every run end
- uncommitted candidate refs leaking into canonical state

## Orchestrator Non-Ownership

Test obligations:
- orchestration tests must prove the orchestrator sequences, validates, routes, stops, and escalates through public contracts only
- negative tests must prove orchestrator does not perform selection, policy, evaluation, memory authorship, or truth mutation
- failure-routing tests must prove malformed outputs stop the flow rather than being patched over

Anti-drift failures to test:
- god-orchestrator drift
- hidden policy in routing
- silent retries
- invented outputs or guessed handoffs

## Interface Truthfulness / No Semantic Flattening

Test obligations:
- CLI/API/GUI contract tests must preserve canonical truth vs support artifact vs derived view vs local UI state
- interface tests must explicitly preserve approved vs applied, selected vs permitted, and outcome_state vs evaluation_verdict
- view-model tests must fail on convenience fields that erase authority or lifecycle distinctions

Anti-drift failures to test:
- shadow truth
- approved equals applied flattening
- execution complete equals objective complete flattening
- support artifact shown as truth object

# Fixture Strategy

Jeff fixtures must be small, explicit, and semantically useful.
Fixture convenience must never blur canonical distinctions.

Required fixture families:
- minimal `project + work_unit + run` fixtures
  Used to prove container, scope, and linkage invariants without extra noise.
- malformed-contract fixtures
  Used to prove schema and handoff rejection behavior.
- blocked, degraded, partial, inconclusive, and mismatch fixtures
  Used to prove honest failure-state handling across outcome, evaluation, orchestration, and interface surfaces.
- approval-required fixtures
  Used to prove selection is not permission and that approval/readiness remain distinct.
- stale-basis and revalidation fixtures
  Used to prove old readiness, approval, plan, or research support does not silently remain valid.
- memory conflict fixtures
  Used to prove state-first truth reads, committed-ID rules, and stale/conflicting memory labeling.
- interface truth-label fixtures
  Used to prove display layers preserve truth class and authority class.
- multi-run continuation fixtures where relevant
  Used to prove retry, resume, or continuation behavior does not rewrite terminal truth or smuggle workflow truth into v1.
- cross-project isolation fixtures
  Used to prove scope leakage, retrieval bleed, and illegal refs are rejected.

Fixture rules:
- keep fixtures bounded to the scenario being tested
- include explicit scope IDs and typed refs
- prefer one clear degraded fixture over one giant omnibus fixture
- model negative cases directly rather than forcing tests to improvise malformed objects inline
- keep canonical truth, support artifacts, and derived views separate inside fixtures

# Contract-to-Test Mapping

Every meaningful contract family must map to one or more test families.
If a contract is strong enough to govern behavior, it is strong enough to deserve a failing test when violated.

## Schema Contracts

What to test:
- shared envelopes
- typed IDs and refs
- required fields
- enum naming and stage-specific field names
- list/detail/action response shapes where relevant

Required test mapping:
- unit tests for validators
- smoke tests for basic contract presence
- integration tests for real producer/consumer handoffs

Must-fail examples:
- missing required scope field
- illegal generic `status` where stage-specific field is required
- malformed CLI JSON envelope
- wrong typed ID family

## Stage Handoff Contracts

What to test:
- context -> proposal
- proposal -> selection
- selection or planning -> action
- action -> governance
- governance -> execution
- execution -> outcome
- outcome -> evaluation
- evaluation -> memory
- memory or other lawful basis -> transition

Required test mapping:
- integration tests for adjacent handoffs
- e2e tests for lawful stage order
- contract rejection tests for impossible or malformed handoffs

Must-fail examples:
- execution invoked without governed action
- transition requested from raw execution result
- evaluation recommendation treated as permission
- non-Memory module attempting memory-candidate handoff

## Object-Family Distinctions

What to test:
- state vs memory
- action vs plan
- execution vs outcome vs evaluation
- approval vs readiness
- support artifact vs canonical truth

Required test mapping:
- unit tests for local model validators
- functional tests for feature surfaces that display or invoke these objects
- interface tests for truthful rendering

Must-fail examples:
- plan artifact consumed as execution authority
- approval displayed as apply completion
- memory body embedded as state truth

## Verdict Naming and Status Distinctions

What to test:
- `policy_verdict`, `approval_verdict`, `readiness_state`
- `execution_status`, `outcome_state`, `evaluation_verdict`
- bounded recommendation families and failure-state names

Required test mapping:
- unit tests for allowed values and deterministic override logic
- integration tests for producer and consumer compatibility
- interface tests for preserved distinctions

Must-fail examples:
- `complete` used as evaluation verdict
- `acceptable` used as outcome state
- blocked, deferred, and escalated flattened into one ambiguous state

## Operator-Surface Truthfulness Rules

What to test:
- truth labels and authority classes
- request vs completed-effect semantics
- approved vs applied
- selected vs permitted
- derived view vs canonical truth

Required test mapping:
- functional tests for CLI/API/GUI operator surfaces
- acceptance tests for truthful display on major views
- smoke tests for core machine-facing JSON shapes

Must-fail examples:
- JSON command returns prose-only error
- GUI or CLI summary hides blocked state behind generic success
- request result shown as applied before backend confirmation

# Phase / Module Exit Gates

No module, phase, or canonical surface is ready to proceed just because code exists or a demo path works.

Minimum exit gates for a module or spec area:
- required invariant coverage exists for the module's core boundaries
- core schema and handoff contracts are covered
- meaningful failure-path coverage exists, not just success paths
- semantic flattening risks are tested where the module exposes operator-facing or machine-facing contracts
- module behavior is safe enough that downstream layers do not need to guess missing semantics

For a module to be "good enough for next phase":
- its primary role is implemented
- its dangerous invariants have explicit tests
- its key handoffs are covered by integration tests
- the most important blocked, degraded, and inconclusive cases are tested
- any remaining gaps are genuinely secondary rather than architecture-threatening

A module is still too semantically unsafe to advance if:
- a truth mutation shortcut has no explicit failing test
- scope isolation is untested
- stage boundaries are still inferred rather than enforced
- operator surfaces can lie while tests still pass
- failure paths depend on manual inspection instead of assertions

Acceptance threshold:
- green happy-path coverage is insufficient
- invariant and contract suites must pass
- representative failure scenarios must pass
- acceptance tests must show that the module's role is honest enough for downstream consumption

# Failure Scenario Coverage

Jeff must test dangerous failure classes explicitly.
The goal is not exhaustive implementation detail.
The goal is to guarantee that canonical risk classes always have coverage.

Required failure coverage includes:
- malformed or missing handoffs
  Tests must prove the flow stops or rejects instead of guessing.
- blocked results
  Tests must prove blocked remains blocked and is not greenwashed into pending or success.
- degraded results
  Tests must prove degraded remains visible and does not silently become acceptable.
- inconclusive results
  Tests must prove missing or contradictory evidence does not become pass.
- stale basis
  Tests must prove old approvals, readiness checks, plans, and research support do not silently stay current.
- truth mismatch
  Tests must prove mismatch-affected conditions remain visible and do not self-repair truth.
- scope leakage
  Tests must prove wrong scope data, refs, or mutations are rejected.
- cross-project bleed
  Tests must prove retrieval, linking, routing, and view-model aggregation respect project isolation.
- duplicate memory and stale memory
  Tests must prove deduplication, supersession, and stale-memory labeling work.
- selection-as-permission drift
  Tests must prove selection cannot directly trigger execution.
- approved-vs-applied flattening
  Tests must prove governance approval and real-world or apply effect remain distinct in backend and interfaces.
- execution-complete vs objective-complete flattening
  Tests must prove clean execution completion does not skip outcome and evaluation judgment.
- recovery or revalidation recommendation misuse
  Tests must prove recommendations do not self-authorize new action or mutation.
- shadow truth in interface surfaces
  Tests must prove derived views, caches, summaries, and local UI state do not rival canonical truth.

# Anti-Patterns in Testing

The following testing patterns are forbidden:
- happy-path-only validation
- snapshot testing of lies
- tests that verify pretty summaries but not semantic truth
- tests that overfit implementation details while missing invariants
- unbounded fixtures that hide the actual scenario
- performance-only brag metrics with no semantic integrity checks
- using manual inspection as a substitute for invariant coverage
- treating green smoke tests as acceptance evidence
- relying on prose parsing instead of structured contract assertions
- allowing a module to claim completion while downstream consumers still need to infer missing meaning

# v1 Required Test Discipline

v1 must enforce enough testing discipline to keep Jeff honest before richer future coverage exists.

Non-negotiable v1 requirements:
- smoke tests for core entry surfaces and machine-facing contracts
- unit tests for local validators, invariants, and deterministic override rules
- integration tests for every major adjacent stage boundary in the canonical backbone
- end-to-end and acceptance tests for the core v1 flow families:
  - standard bounded action flow
  - direct research or other direct-output flow
  - conditional planning insertion flow where planning is actually needed
  - blocked or escalated stop flow
  - evaluation-driven revalidation or recovery follow-up flow
  - committed-memory transition-sensitive flow where memory linkage matters to lawful continuation or truth update
- explicit invariant tests for:
  - one global state with nested projects
  - project isolation
  - transition-only truth mutation
  - selection not implying permission
  - approval/readiness separation
  - execution/outcome/evaluation separation
  - memory non-truth behavior
  - only Memory creating memory candidates
  - orchestrator non-ownership
  - interface truthfulness and anti-flattening
- failure coverage for blocked, degraded, inconclusive, stale, mismatch, and scope-leak scenarios
- acceptance gates strong enough to block phase advancement when semantic safety is still weak

v1 does not require:
- exhaustive combinatorial flow enumeration
- giant benchmark farms
- heavy property-based or fuzz infrastructure on day one
- full cross-interface parity matrices before richer API and GUI surfaces exist

v1 does require that architecture-threatening drift be test-visible.

# Deferred / Future Expansion

Deferred expansion may later add:
- richer property-based and fuzz testing for contracts and transitions
- stronger multi-run continuation and pause-resume testing
- richer cross-interface parity tests across CLI, API bridge, and GUI
- stronger performance and load testing
- deeper audit and replay validation
- richer historical comparison tests for evaluation and memory behavior

Deferred expansion does not weaken current law.
Future coverage may expand.
Invariant, contract, and anti-drift coverage remain the backbone.

# Questions

No unresolved testing-strategy questions were found in this pass.

# Relationship to Other Canonical Docs

- `ARCHITECTURE.md` defines the backbone and boundary law that tests must protect.
- `STATE_MODEL_SPEC.md` defines current-truth topology and the one-global-state model that invariant tests must enforce.
- `TRANSITION_MODEL_SPEC.md` defines the only lawful truth mutation contract that tests must guard.
- `POLICY_AND_APPROVAL_SPEC.md` defines permission, approval, and readiness semantics that tests must keep distinct.
- `CORE_SCHEMAS_SPEC.md` defines shared naming, envelope, ID, and schema discipline that contract tests must enforce.
- `CONTEXT_SPEC.md` defines truth-first context assembly and memory-use constraints that context and retrieval tests must protect.
- `PROPOSAL_AND_SELECTION_SPEC.md` defines bounded proposal/selection law, cardinality, and non-permission boundaries that tests must cover.
- `PLANNING_AND_RESEARCH_SPEC.md` defines bounded research, conditional planning, provenance, and support-artifact rules that testing must keep from drifting.
- `EXECUTION_OUTCOME_EVALUATION_SPEC.md` defines execution/outcome/evaluation separation, verdict models, and recommendation boundaries that tests must preserve.
- `MEMORY_SPEC.md` defines memory write authority, pipeline, scope, retrieval, and truth-separation rules that tests must enforce.
- `ORCHESTRATOR_SPEC.md` defines sequencing, handoff validation, routing, and non-ownership boundaries that tests must keep hard.
- `INTERFACE_OPERATOR_SPEC.md` defines truthful downstream surfaces and anti-flattening rules that interface tests must protect.
- `PROJECT_AND_WORK_UNIT_MODEL_SPEC.md` defines the foundational container model whose scope and linkage tests must remain explicit.
- `GLOSSARY.md` fixes the meanings of the distinctions this document requires tests to preserve.

# Final Statement

Jeff testing is successful only when it makes architectural drift, truth drift, and semantic flattening expensive to introduce and easy to detect.

That requires a test strategy built around invariants, contracts, bounded fixtures, failure classes, and hard exit gates.
It is not enough for Jeff to look useful.
The test plan must make it difficult for Jeff to lie about truth, permission, progress, completion, or authority while still passing green.
