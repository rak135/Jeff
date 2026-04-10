# Purpose

This document defines Jeff's canonical project and work-unit container model.

It owns:
- the canonical meaning of `project` and `work_unit`
- container identity and container purpose
- container scope and isolation law
- conceptual lifecycle boundaries for `project` and `work_unit`
- the canonical relationship of `run` to `project` and `work_unit`
- truth-relevant linking rules at project and work-unit scope
- canonical dependency and blocking semantics where they belong to container truth
- container invariants and container failure modes
- the distinction between the whole-Jeff container model, the v1 enforced model, and deferred expansion

It does not own:
- root global state topology
- transition lifecycle and commit law
- governance semantics
- interface display contracts
- telemetry schemas
- test matrices
- roadmap sequencing
- low-level shared schema fields

This is the canonical bounded container-model document for Jeff.
It is not a vague philosophy essay, an implementation-status note, or a duplicate of the state, transition, or governance specs.

# Canonical Role in Jeff

`project` and `work_unit` are Jeff's main persistent work containers inside canonical truth.
They are how Jeff preserves direction, continuity, bounded effort, and scoped progress over time.

Jeff cannot tolerate blur between:
- `project`
- `work_unit`
- `run`
- `workflow`

If those collapse into each other:
- project isolation weakens
- work history starts impersonating current truth
- workflow structure starts masquerading as persistent container truth
- runs start redefining work units by convenience
- memory, artifacts, or traces get stuffed into the wrong level

This document protects continuity without creating rival truth stores.
It keeps the persistent container backbone hard while leaving execution, governance, memory, and workflow to their owning documents.

The same foundational container law applies to:
- Jeff-project work
- non-Jeff project work
- research work
- implementation work
- review or recovery work

Jeff is project-centered, not Jeff-project-centered.

# Core Principle

Jeff has one global canonical truth system.
Inside that system:
- `project` is the hard isolation boundary
- `work_unit` is the primary bounded effort container inside a project
- `run` is a bounded attempt inside a work unit

These containers are:
- persistent truth containers
- scope anchors
- continuity anchors

They are not:
- UI concepts
- workflow shortcuts
- history dumps
- policy engines
- memory warehouses
- trace archives

`project + work_unit + run` are foundational containers.
Workflow is not first-class canonical truth in v1.

# Project Model

## Identity

A project is a stable canonical container identified by `project_id`.

Project identity means:
- the project remains the same bounded line of work across many work units and runs
- the project is the canonical owner of its project-local truth region
- the project is not a separate canonical state store

Project identity does not mean:
- an independent per-project truth universe
- a UI workspace only
- a loose folder of related artifacts

## Purpose

The project exists to hold one bounded line of work together over time.

Project purpose is to provide:
- durable direction
- durable project-local scope boundaries
- durable project-local bindings and constraints
- durable project-local integrity and status truth
- the parent container for project work units

Project is where Jeff knows:
- what line of work this is
- what direction governs it
- what bounded truths apply across its work units
- where project-local continuity begins and ends

## Scope

Project scope is broader than any one work unit but narrower than the global system.

Project-scoped truth may include:
- project identity
- direction
- project-local constraints and bindings
- project-local integrity, blocker, or degraded-state truth
- the project's work-unit collection
- truth-relevant refs that belong at project scope

Project scope may carry thin refs to current supporting objects when the link itself is current truth.
Project scope must not absorb the local truth of every child work unit or run.

Project is the holder of direction and project-local bounded truth.
It is not a shadow root state.

## Isolation Rules

Project is a hard isolation boundary inside one global canonical state.

That means:
- every work unit belongs to exactly one project
- in v1, every run belongs to exactly one project through one work unit
- project-local truth does not leak across projects by convenience
- memory, artifacts, traces, and support objects do not become cross-project truth just because they are useful elsewhere

Cross-project freeform linkage is forbidden as canonical container truth.
If Jeff later needs cross-project truth, it must be owned by an explicit global construct, not by weakening project isolation.

Project isolation does not mean separate per-project state stores.
It means hard containment and hard scope discipline inside one global truth system.

## Lifecycle

The project lifecycle is conceptual, not a dump of exact status enums.

A project may:
- be created
- become active
- be paused or blocked
- be frozen or archived later if canonized

Conceptually, project lifecycle is about whether the line of work exists, remains active, is temporarily constrained, or has been intentionally closed or frozen.

Project lifecycle does not mean:
- every work unit shares the same lifecycle state
- a completed work unit closes the project
- project truth is reconstructed from run history

Project direction, status, bindings, and integrity may change over time, but only through transitions.

# Work Unit Model

## Identity

A work unit is a stable canonical container identified by `work_unit_id`.
It belongs to one and only one project for its lifetime.

Work-unit identity means:
- the bounded effort remains the same effort across multiple runs
- retries create new runs, not new meanings for the same work unit
- the work unit stays distinguishable from workflow structure and run history

## Purpose

A work unit is the durable bounded effort anchor inside a project.

Its purpose is to hold:
- one bounded objective or bounded effort
- the local scope of that effort
- the local lifecycle and progress truth of that effort
- the local blocker and dependency truth of that effort
- continuity across multiple runs

A work unit may represent:
- research
- implementation
- review
- recovery
- planning when planning is actually needed

Those categories do not change the container law.
They only describe what kind of bounded effort the work unit carries.

## Scope

A work unit must be bounded enough to be operationally meaningful.

It should be able to answer:
- what bounded effort is this
- what is in scope for this effort
- what is outside scope for this effort
- what progress or blocker truth currently applies
- what runs belong to this effort

A work unit is not:
- a workflow
- a run
- a chat thread
- a generic task label
- a bag for arbitrary support residue

Work units that are too vague become useless.
Work units that absorb everything become junk drawers.

## Lifecycle

The work-unit lifecycle is conceptual and container-oriented.

A work unit may:
- be created or opened
- become active
- become blocked or paused
- reach completion
- be abandoned, cancelled, or superseded where later canon justifies that distinction

The important law is not the exact enum set.
The important law is that work-unit lifecycle truth is explicit, persistent across runs, and not guessed from surrounding support objects.

## Progress Model

Work-unit progress must be explicit enough to describe the state of the bounded effort.

Progress truth may include:
- whether the effort has started
- whether it is actively advancing
- whether it is blocked
- whether it is complete
- whether closure is provisional, degraded, or final

Progress must not be inferred only from:
- latest run status
- artifact count
- trace volume
- memory presence

Percent-complete style signals may exist later, but they are not the core canonical law.
The core law is that progress is explicit effort truth, not history interpretation.

## Dependencies / Blocking

Dependency and blocking semantics belong at work-unit scope when they affect the bounded effort itself.

A work unit may hold explicit truth about:
- dependency on another work unit
- blocked-by relationship
- local blocker condition
- unmet review or prerequisite condition

Dependency and blocker rules:
- keep them explicit
- keep them typed
- keep them sparse
- keep them within project scope in v1

The work unit should record blocker truth, not every detail of the support object behind that blocker.

Whole-Jeff may later support richer dependency graphs.
v1 does not need a complex workflow or DAG system to have honest work-unit dependencies.

# Run Relationship

`run` is the bounded attempt or flow instance inside a work unit.

Container law at this boundary is:
- project and work unit own persistent scope truth
- run owns bounded attempt truth
- work unit persists across many runs
- run does not replace the work unit

In v1:
- every run belongs to exactly one project
- every run belongs to exactly one work unit
- runs are nested under work-unit truth

Run truth may describe:
- one attempt
- one retry
- one bounded research pass
- one bounded execution pass

Workflow is not a replacement for run or work unit in v1.
Workflow may remain supporting coordination.
It does not become the persistent container backbone unless later canon explicitly promotes it.

# Linking Rules

Container linking must stay thin, typed, and truth-relevant.

General linking law:
- use thin refs over embedded bodies
- only link what matters to current container truth
- keep query-derived support linkage outside canonical container truth unless the link itself is truth
- do not embed history dumps into containers
- do not let support objects rival container truth
- only the Memory module creates memory candidates

## Memory Links

Project and work unit may link to memory only when the link itself is current truth.

Rules:
- only Memory creates memory candidates
- canonical container truth may reference only committed `memory_id` values
- only committed outputs of the Memory module may become canonical memory links
- memory candidates never appear as container truth
- memory bodies do not live inside project or work-unit truth
- memory linkage is selective, not automatic

Project-level memory links are appropriate when memory is current and materially relevant to the project as a whole.
Work-unit-level memory links are appropriate when memory is current and materially relevant to that bounded effort.

## Artifact Links

Project and work unit may link to artifacts only when the artifact link itself matters to current truth.

Rules:
- use thin artifact ids or thin artifact refs
- keep full artifact bodies outside canonical containers
- do not turn artifact lineage into container truth by default

Examples of justified artifact links include:
- authoritative deliverable refs
- bounded closure outputs
- current supporting outputs whose linkage matters to the container's current reality

## Run Links

Run linkage must preserve the distinction between persistent effort truth and attempt truth.

Rules:
- a work unit may hold current run refs such as active run, latest relevant run, or closure-relevant run when that linkage is truthful
- a project may hold project-level run refs only when operational truth genuinely requires them
- project and work unit must not become run-history archives

Run history lives in run objects and transition lineage, not as embedded container history blobs.

## Dependency / Blocking Links

Work units may link to other work units for explicit structural relations such as:
- depends_on
- blocked_by
- supersedes
- split_from
- continues_from

Rules:
- links must be typed
- links must be explicit
- links must stay within the same project in v1 unless an explicit global construct later owns otherwise
- vague `related_work_unit` linkage is not enough

Project may hold project-level blocker refs where project truth needs to show an active bounded blocking condition.

## Other Truth-Relevant Refs

Project and work unit may hold other thin refs only when the link itself is canonical truth.

Allowed examples may include refs to:
- current governance objects
- current integrity or incident objects
- current transition lineage

This does not allow support-object sprawl.
If the container can stay truthful without the link, the link should usually stay outside container truth.

# What These Containers Own

## Project Owns

Project owns:
- stable project identity
- durable project direction
- project-local constraints and bindings that are part of current truth
- project-local integrity, blocker, and status truth
- the bounded collection of project work units
- project-level closure, freeze, or archive truth if canonized
- project-level truth-relevant refs

## Work Unit Owns

Work unit owns:
- stable work-unit identity
- one bounded objective or bounded effort anchor
- local scope and local constraints for that effort
- local lifecycle truth
- local progress truth
- local blocker and dependency truth
- truth-relevant current run refs
- work-unit closure or completion truth
- work-unit-level truth-relevant refs

# What They Do Not Own

Project and work unit do not own:
- the global root state topology
- transition lifecycle internals
- governance semantics
- execution permission
- full memory bodies
- full artifact bodies
- trace archives
- full execution history blobs
- full run bodies
- UI or session state
- workflow truth in v1
- full selection, approval, readiness, outcome, or evaluation payloads
- support payload sprawl
- cross-project freeform linkage
- inference presented as container truth

Additionally:
- project does not own run-local attempt truth
- work unit does not own project direction as a whole
- neither container becomes a shadow policy engine
- neither container becomes a rival memory store

# Invariants

The following invariants are binding:

- Jeff has one global canonical state with nested projects.
- Project is the hard isolation boundary inside that state.
- `project + work_unit + run` are foundational containers.
- Every work unit belongs to one project.
- In v1, every run belongs to one work unit and one project.
- Project, work unit, and run remain distinct.
- Workflow is not first-class canonical truth in v1.
- Planning is conditional, not universal.
- Selection is not execution permission.
- Approval and readiness are governance objects, not container truth.
- `action` is a narrow transient operational object family, not a container.
- `Change` is at most a support/apply/review object, never a rival mutation primitive.
- Only Memory creates memory candidates.
- Transitions are the only canonical truth mutation contract.
- Only committed-memory links may appear in canonical container truth.
- Only truth-relevant links belong in container truth.
- No container becomes a history dump.
- No container becomes a shadow policy engine.
- No container mutates outside transitions.
- Jeff-project work and non-Jeff project work use the same foundational container model.

# Failure Modes

The container model is failing if any of the following happens:

- per-project truth-store drift returns
- project isolation weakens into cross-project leakage
- work unit, run, and workflow collapse into one concept
- work units become too vague to anchor real work
- work units become overloaded with traces, history, or support residue
- project scope loses direction authority
- broad memory spiderweb linking turns containers into support-graph sludge
- artifact or run linkage turns containers into archive blobs
- duplicated truth appears across project and work unit with no clear owner
- latest-run convenience starts redefining work-unit truth
- project or work unit becomes a UI/session concept instead of durable truth
- workflow pressure re-enters v1 as rival persistent container truth
- governance, transition, or memory semantics leak into containers as if containers owned them

# v1 Enforced Model

v1 enforces the following container model:

- one global canonical state with nested projects
- project as a hard isolation boundary inside that state
- foundational `project + work_unit + run`
- one-project ownership for every work unit
- one-project and one-work-unit ownership for every run
- run nested under work-unit truth
- workflow not first-class canonical truth
- planning conditional rather than universal
- project truth limited to direction, project-local bounded truth, work-unit collection, and truth-relevant thin refs
- work-unit truth limited to bounded effort truth, local lifecycle/progress/blocker truth, current run refs where truthful, and truth-relevant thin refs
- memory links only as committed `memory_id` values when the link itself is current truth
- artifact and support-object links only as thin refs when canonically justified
- no freeform cross-project dependency or linkage model
- no container history dumps
- transition-only mutation of container truth
- the same foundational container law for Jeff-project and non-Jeff project work

This is enough to prevent the main legacy drift:
- project-as-separate-state
- work-unit-as-history-bag
- run/workflow collapse
- support-residue sprawl inside persistent containers

# Deferred / Future Expansion

Deferred expansion may add:
- richer work-unit dependency and continuation models
- richer work-unit split, merge, and supersession lineage
- richer project archival, freeze, and restoration semantics
- richer long-running continuation metadata across many runs
- more explicit project-level or work-unit-level integrity constructs
- possible future workflow canonization only if workflow is later promoted explicitly
- more sophisticated cross-project global constructs only if later canonized at global scope

Deferred expansion does not weaken the current backbone.
Future richness must build on `project + work_unit + run`, not replace it casually.

# Questions

No unresolved project/work-unit-model questions were found in this pass.

# Relationship to Other Canonical Docs

- `ARCHITECTURE.md` owns the structural backbone that places `project`, `work_unit`, and `run` in Jeff.
- `GLOSSARY.md` owns the canonical meanings of `project`, `work_unit`, `run`, `workflow`, `action`, and related terms used here.
- `STATE_MODEL_SPEC.md` owns root state topology and truth placement; this document owns only the meaning of the containers inside that topology.
- `TRANSITION_MODEL_SPEC.md` owns mutation law; this document only states that container truth changes through transitions.
- `POLICY_AND_APPROVAL_SPEC.md` owns governance semantics; this document only keeps governance from being absorbed into containers.
- `CORE_SCHEMAS_SPEC.md` owns typed ids and reference primitives used by these containers.
- future memory, execution, planning, and orchestrator docs own their respective support or flow semantics; this document keeps those semantics from replacing container law.

# Final Statement

Jeff's persistent work backbone is:
- project as hard isolation boundary
- work unit as bounded durable effort
- run as bounded attempt inside that effort

Those containers are how Jeff preserves scope, continuity, and truthful work ownership across time.

If they stay hard, Jeff can support Jeff work and non-Jeff work with the same backbone without collapsing into workflow fog, memory sludge, or history-as-truth.
If they soften, the system loses its container law and starts lying about what the work actually is.
