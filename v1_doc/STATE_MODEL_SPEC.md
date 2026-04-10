# Purpose

This document defines Jeff's canonical truth topology.

It owns:
- where current authoritative truth lives
- the conceptual root shape of canonical state
- what belongs in canonical state
- what must stay out of canonical state
- how `project`, `work_unit`, and `run` sit inside canonical truth
- what state may reference
- the read and write discipline at the state-model level

It does not own:
- transition lifecycle details
- policy semantics
- module-local business logic
- interface display contracts
- telemetry schemas
- test matrices
- roadmap sequencing

This is the canonical state-model document for Jeff as a whole.
It is not a v1-only implementation snapshot and not an implementation-status report.

# Canonical Role in Jeff

This document fixes where current authoritative truth lives.

Jeff cannot tolerate rival truth layers in:
- memory
- traces and event history
- artifacts
- chat history
- interface caches
- workflow glue
- module-private summaries

If current truth can be reconstructed from many competing places, Jeff loses auditability, isolation, and control.
This document protects the rest of the canon by making one hard answer explicit:
current authoritative truth lives only in canonical state, and canonical state has one global topology.

# Core Principle

Canonical state is Jeff's only authoritative current-truth layer.

State must be:
- explicit
- structured
- versioned
- referentially sound
- transition-controlled

State is not:
- memory
- logs
- traces
- telemetry
- artifacts
- chat history
- interface/session state
- execution residue

# What State Owns

Canonical state owns current truth that Jeff must rely on operationally.

That includes:
- one global canonical state root
- system-scoped truth that applies across projects
- nested project truth regions
- canonical project direction
- authoritative project-scoped config or policy bindings where those bindings are part of current truth
- work-unit truth as the durable bounded effort anchor inside a project
- run truth as the bounded canonical truth of one concrete attempt or flow instance
- truth-level status, lifecycle, blocker, integrity, and degraded-state fields when they are part of current reality rather than interface convenience
- narrow canonical active-context truth when Jeff treats current operating scope as authoritative
- typed canonical references whose linkage itself is part of current truth

State owns the fact that these truths are current.
It does not own every supporting object that helped produce them.

# What State Does Not Own

Canonical state does not own support residue, historical exhaust, or presentation convenience.

State does not own:
- raw logs
- verbose traces
- event streams
- telemetry payloads
- full execution outputs
- full artifact bodies
- full chat history
- memory content bodies
- memory candidates
- speculative or inferred facts presented as truth
- uncommitted or failed memory links
- full source or evidence bodies
- interface/session-local state
- cached summaries that rival state
- `action` as a canonical truth family
- first-class workflow truth in v1
- full embedded payloads for `selection`, `approval`, `readiness`, `Change`, `outcome`, `evaluation`, or similar support/governance objects

Those objects may matter.
They do not become canonical truth merely because they exist.

# Root State Topology

Jeff has one global canonical state root.

The conceptual root shape is:

```text
global_state
- state_meta
- system
- active_context (only if canonical operating focus is committed)
- projects[project_id]
  - project truth
  - work_units[work_unit_id]
    - work-unit truth
    - runs[run_id]
```

Interpretation rules:
- `state_meta` carries global state-version and transition lineage metadata.
- `system` carries system-scoped truth, global bindings, and global integrity markers that are not owned by any single project.
- `active_context` is optional and narrow. It exists only if Jeff commits a current operating scope as truth.
- `projects` is the single project registry inside one truth system.
- each project contains its own project truth plus child `work_units`
- each work unit contains its own child `runs`

`project`, `work_unit`, and `run` are foundational containers.
They are not independent root truth stores.

Each commit advances the global canonical state version.
Project-, work-unit-, and run-level updated markers may exist, but they are subordinate to the global canonical truth version.

# Global vs Project Truth Placement

Jeff has one global canonical state.
Projects are nested truth regions inside that state.

System-level truth belongs at global scope when it is truly cross-project, such as:
- system identity and integrity markers
- global config or policy bindings where authoritative
- global current-truth metadata
- any future cross-project constructs that are explicitly canonized

Project-local truth belongs inside the owning project subtree, such as:
- direction
- project-local bindings
- project-local status and blockers
- work units
- runs

Project is a hard isolation boundary inside one truth system.
It is not a separate independent truth store.

Forbidden topologies:
- one canonical store per project
- project truth reconstructed from project memory
- project truth reconstructed from runs alone
- interface-owned project truth

# Project Placement Inside Global State

Each project lives inside `global_state.projects[project_id]`.

Project scope owns project-local truth such as:
- stable project identity
- direction and scope boundaries
- authoritative config or policy bindings, or authoritative refs to those bindings
- project status and integrity markers
- project-level blocker or degraded-state truth when current and canonical
- the collection of project work units
- project-level typed refs that current truth requires

Project scope may include compact references such as:
- active or open work-unit ids
- current blocking refs
- current incident or integrity refs if those objects are canonized elsewhere
- committed memory ids when the link itself matters to current project truth

Project scope must not absorb:
- full work-unit local truth
- full run bodies or histories
- memory bodies
- artifact archives
- trace archives
- interface summaries

Cross-project linkage is not freeform.
Any cross-project truth must be explicitly promoted to a global canonical construct.

# Work Unit Placement Inside Project Truth

A work unit is a project-scoped canonical truth container.
It is the durable bounded effort anchor inside one project.

Work-unit truth belongs inside the owning project's `work_units` collection.
Work-unit truth may include:
- identity
- bounded objective
- scope and constraints local to the effort
- current lifecycle or progress truth
- explicit blocked or degraded conditions
- active-run refs or latest-run refs when those links are current truth
- current local support-object refs when those links matter to current work-unit reality
- closure metadata when the work unit is closed

Work-unit truth must stay separate from:
- project direction as a whole
- full run history
- full traces
- full artifacts
- chat/session residue
- memory content

Work-unit status must not be guessed from the latest run alone.
A new run does not retroactively redefine work-unit truth unless a lawful transition commits that change.

# Run Placement and Boundaries

`run` is retained as a canonical truth object because Jeff needs one authoritative record of the current and terminal truth of each bounded attempt.

Without canonical run truth:
- operator views reconstruct run reality from traces
- orchestrator logic leans on logs instead of truth
- approval/apply/evaluation lineage becomes ambiguous
- retry history gets rewritten by convenience

Canonical run truth is narrow.
It may include:
- run identity
- owning `project_id`
- owning `work_unit_id`
- mode or flow identity
- creation source and timestamps
- current lifecycle state
- current bounded operational refs that matter now
- compact terminal outcome summary once terminal
- retry lineage
- local flags or markers when they have stable canonical meaning
- last-transition and update metadata

Canonical run truth does not include:
- full trace bodies
- telemetry streams
- event histories
- full execution outputs
- full evidence bundles
- full approval/readiness/evaluation payloads
- full `Change` payloads
- full artifact bodies
- memory content

Runs live in the owning work unit's `runs` collection, not as independent global roots.
In v1, every canonical run belongs to exactly one project and exactly one work unit.
Any later system-scoped exception would need explicit canonization and is not part of the enforced v1 model.

Run truth is the current bounded truth of one attempt.
Trace, event, artifact, and telemetry layers remain separate historical or support layers that a run may reference.

# Active Context Rules

Jeff may carry a narrow canonical active-context object when current operating focus is itself current truth.

Canonical active context is limited to durable operating scope such as:
- active `project_id`
- active `work_unit_id` when Jeff is currently anchored to one work unit
- active `run_id` when one run is the currently authoritative operating path

Canonical active context may also carry minimal metadata such as:
- why the focus is current
- when it was last updated

Canonical active context must not include:
- freeform "current focus" prose as a substitute for structured truth
- UI tab state
- selected list row
- filter state
- scroll position
- draft text
- per-session view choices
- "last thing the operator looked at" convenience state

Rule:
- operating focus that changes orchestration, context assembly, or lawful next-step scope may be canonical
- interface or session attention that exists only to support one client surface is not canonical

Jeff must not let GUI, CLI, or API sessions create rival focus truth.

# Canonical References Inside State

State may reference other objects only when the link itself is part of current truth.

Reference rules:
- typed ids are the default reference form
- direct ids are preferred over rich embedded objects
- structured refs are allowed only when identity alone is insufficient
- locator data does not replace identity

Canonical state may reference:
- other canonical containers by typed id
- transition ids
- committed `memory_id` values only
- artifact ids or thin artifact refs where the artifact link itself matters to current truth
- governance/support-object ids when current operational truth must point to them
- source/evidence refs only when the support basis is itself current truth and must remain inspectable

Canonical state may not reference:
- uncommitted memory candidates
- failed or pending memory writes
- dangling artifact links
- session-local objects
- freeform file paths as substitute identity

State should not over-embed support structures.
Most support objects should stay outside canonical state and be linked by typed refs only when operationally necessary.

# What May Be Stored in State

The following truth classes may be stored in canonical state:
- authoritative identity and scope fields
- current lifecycle and status truth
- current blocker, integrity, and degraded-state truth
- direction and scope-boundary truth
- authoritative config or policy bindings when they are part of current truth
- bounded work-unit objective and scope truth
- bounded run lifecycle and terminal summary truth
- explicit current refs to relevant runs, work units, transitions, artifacts, governance objects, or support objects when those refs matter to current reality
- committed `memory_id` links when the memory relationship itself is canonical
- versioning and audit linkage metadata
- narrow canonical active context

Admission rule:
a value belongs in state only if Jeff must be able to answer a current-truth question from it directly and reliably.

# What Must Not Be Stored in State

The following must not be stored in canonical state:
- raw logs
- trace bodies
- event payload streams
- telemetry dumps
- full execution outputs
- full artifact bodies
- full source or evidence bundles
- full memory bodies
- memory candidates
- retrieval caches
- prompt history
- chat transcripts
- speculative conclusions
- inferred facts not committed through truth mutation
- full `selection`, `approval`, `readiness`, `Change`, `outcome`, or `evaluation` payloads
- workflow objects in v1
- unbounded arrays of historical support residue
- UI/session-local state
- shadow copies of authoritative config or policy truth
- uncommitted references of any kind
- `action` objects treated as canonical truth

If the value exists mainly for review, explanation, debugging, history, or presentation, it probably does not belong in canonical state.

# State Invariants

The following invariants are binding.

- There is exactly one canonical current-truth layer.
- Jeff has one global canonical state with nested projects.
- Project is the hard isolation boundary inside that state.
- `project`, `work_unit`, and `run` are foundational canonical containers.
- In v1, every canonical run belongs to exactly one project and one work unit.
- Canonical truth mutates only through transitions.
- No direct writes to canonical state are allowed.
- No memory leakage into truth is allowed.
- No execution side effect becomes truth automatically.
- No selection, approval, readiness, evaluation, or `Change` object mutates truth by itself.
- Canonical state may reference only committed memory ids.
- Referential integrity must hold for all canonical references.
- No rival truth layers may emerge in memory, traces, artifacts, workflows, interfaces, or caches.
- Workflow is not first-class canonical truth in v1.
- `action` is not a canonical truth object family.
- Current-truth reads must prefer state before memory, traces, or artifacts.

# Read Rules

Canonical state is readable across Jeff through sanctioned read surfaces.

Read discipline:
- read current truth from state first
- read by scope: global, then project, then work unit, then run
- use memory, artifacts, traces, and evidence only as secondary support layers after truth reads
- keep project reads inside project isolation boundaries unless an explicit global surface authorizes cross-project access
- do not mutate through read surfaces, projections, or caches
- when a current-state question is answered by state and by memory or artifact history differently, state wins until a lawful transition changes truth

Interfaces and modules may consume derived projections, but those projections remain downstream of canonical state.

# Write Rules

State changes only through transitions.

Write discipline:
- no direct mutation
- no partial direct mutation
- no best-effort truth write
- no interface/session-layer write into state
- no memory-only write into state
- no execution-result-only write into state
- no evaluation-result-only write into state
- no approval-only or readiness-only write into state
- no selection-only write into state
- no transient `action`-only write into state
- no `Change`-only write into state
- no orphan side-effect write into project, work-unit, or run truth

Every canonical write must be:
- typed
- scoped
- validated
- referentially checked
- versioned
- committed atomically

If transition validation fails, policy blocks the change, scope is invalid, or supporting truth is insufficient, canonical state does not change.

# Relationship to Memory

Memory is durable support knowledge.
State is current truth.

Rules:
- only Memory creates memory candidates
- canonical state may reference committed memory ids only
- memory does not override current truth
- memory may support context, explanation, and future reasoning
- memory may not silently repair or replace state

If memory and state disagree about a current fact, state wins until a lawful transition resolves the mismatch.

# Relationship to Governance

Governance reads canonical truth and constrains action.

Approval and readiness are governance objects, not truth objects.
Selection is not execution permission.

State may hold thin refs to governance objects when those refs are part of current operational truth, especially at run scope.
That does not make governance semantics part of state ownership.

Authoritative config or policy bindings may live in state, or be referenced from state, when they are part of current truth.
Governance decisions do not mutate canonical truth unless a lawful transition commits resulting truth changes.

# Relationship to Interfaces

Interfaces consume truth through sanctioned projections, view models, and action entry points.

Interface rules:
- interface state is not canonical state
- interfaces may shape truth for display, but may not invent or flatten semantics
- no GUI, CLI, or API layer may maintain shadow truth that rivals canonical state
- pending, approved, applied, blocked, degraded, and failed must remain distinct
- interface actions must enter the system through governed paths and, where truth changes, through transitions

Canonical state exists to keep interfaces honest, not to carry interface convenience state.

# Failure Modes / State Corruption Risks

The state model is failing if any of the following happens:

- memory-as-truth collapse
- per-project truth-store drift
- run/history/trace confusion
- direct mutation shortcuts
- unbounded support-object accumulation inside state
- interface-owned shadow state
- uncommitted memory refs in state
- execution residue treated as truth
- latest-run-defines-work-unit collapse
- duplicate config or policy truth in multiple authoritative homes
- workflow inflation back into canonical truth without explicit canonization
- support objects embedded so deeply that state becomes a junk drawer

These failure modes are not cosmetic.
They are structural corruption risks.

# v1 Enforced State Model

v1 enforces the following state model:

- one global canonical state root
- nested projects inside that root
- project as the hard isolation boundary
- project-local `work_units` collection
- work-unit-local `runs` collection
- canonical project direction
- authoritative project bindings and status/integrity truth where required
- work-unit truth limited to bounded objective, scope, status, blockers, closure, and necessary refs
- run truth limited to identity, scope, mode/flow, lifecycle, bounded terminal summary, necessary refs, and retry lineage
- narrow canonical active context only when Jeff commits current operating scope as truth
- workflow not first-class canonical truth
- selection not execution permission
- `action` not canonical truth
- `Change` never a rival mutation primitive
- only committed `memory_id` links in state
- references rather than embedded support payloads
- exclusion of logs, traces, event payloads, memory bodies, chat history, and artifact bodies from state
- transition-only truth mutation

This is enough to prevent the main legacy drift:
per-project truth stores, state-as-history, state-as-memory, and state-as-interface-cache.

# Deferred / Future State Expansion

The following areas may expand later if later canon justifies them:

- richer run checkpoint, resumption, and long-running continuation truth
- stronger cross-project or system-global constructs beyond the minimal root/system layer
- richer integrity, degraded-state, and truth-mismatch objects
- a more sophisticated canonical active-focus model for multi-session or queued-autonomy operation
- richer source/evidence linkage inside state only where some truth object genuinely requires it
- first-class workflow truth only if workflow is later canonized explicitly and without weakening current state law

Deferred expansion does not relax the core rule:
there is still one global canonical current-truth layer, and support layers still do not become rival truth.

# Questions

- `SM-001`
- Topic: Canonical memory-link granularity
- Why it is unresolved: `questions_answered.md` settles that canonical state may reference only committed memory ids, but it does not fully settle which scopes must carry direct memory links versus leaving those links query-derived.
- What docs or assumptions are in tension: `questions_answered.md` rejects uncommitted memory refs, while older project/work-unit docs tend to over-link memory broadly and the anti-sprawl state discipline argues for only truth-relevant links.
- Clear question for the human: In v1, which canonical scopes must guarantee first-class `memory_id` links when truth-relevant: project only, work unit only, run only, or any of the three when the link itself is current truth?

## Answers

- `SM-001`
**Answer:**  
In v1, **any of the three scopes may carry direct committed `memory_id` links, but only when the link itself is current truth**.

That means:
- **project** may carry committed memory links when the memory is directionally or operationally current for the whole project
- **work_unit** may carry committed memory links when the memory is current and materially relevant to that bounded effort
- **run** may carry committed memory links when the memory link is part of the current bounded truth of that run
- none of those scopes should carry memory links by default just because related memory exists

So the canonical rule is:

> **not project-only, not work-unit-only, not run-only — but selective linking at any of the three scopes when and only when the link itself is truth-relevant now**

# Relationship to Other Canonical Docs

- `ARCHITECTURE.md` defines the structural law that this topology must obey.
- `GLOSSARY.md` fixes the meaning of `state`, `project`, `work_unit`, `run`, `transition`, `action`, `memory`, and related terms used here.
- `CORE_SCHEMAS_SPEC.md` owns shared id, reference, envelope, and versioning primitives used by this state model.
- `TRANSITION_MODEL_SPEC.md` owns the mutation contract, validation layers, and commit law. This document only says that transitions are the sole mutation path.
- `PROJECT_AND_WORK_UNIT_MODEL_SPEC.md` owns project/work-unit semantics and lifecycle detail. This document owns only their placement inside canonical truth.
- `POLICY_AND_APPROVAL_SPEC.md` owns governance semantics. This document only states how state relates to authoritative bindings and governance refs.
- `MEMORY_SPEC.md` owns memory creation, storage, retrieval, and write discipline. This document only fixes the state boundary against memory.
- `CONTEXT_SPEC.md` owns truth-first context assembly. This document fixes where that truth comes from.
- `EXECUTION_OUTCOME_EVALUATION_SPEC.md` owns execution, outcome, and evaluation semantics. This document prevents those outputs from silently becoming truth.
- `ORCHESTRATOR_SPEC.md` owns sequencing. It does not own truth placement.
- `INTERFACE_OPERATOR_SPEC.md` owns downstream presentation and operator-surface contracts. It does not own canonical state.

# Final Statement

Jeff has one canonical current-truth system.

That system is one global state with nested projects.
Inside each project, work units hold bounded effort truth and runs hold bounded attempt truth.
Everything else that is useful but non-authoritative stays outside canonical state unless linked by narrow typed references.

If this topology stays hard, Jeff can grow without losing truth.
If it softens, Jeff will drift back into memory-as-truth, history-as-truth, and interface-as-truth failure.
