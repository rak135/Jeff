# Purpose

This document defines Jeff's canonical operator-surface and truthful-interface law.

It owns:
- the operator surface model
- CLI surface law
- API bridge surface law
- GUI surface law
- truthfulness rules for operator-facing display
- view-model constraints
- operator action semantics at the interface boundary
- interface contract boundaries
- interface invariants
- interface failure modes and semantic-flattening risks

It does not own:
- backend truth semantics
- governance semantics
- transition law
- module-local business logic
- telemetry schema design
- test matrices
- roadmap sequencing

This is the canonical interface/operator document for Jeff as a whole.
It is not an implementation-status note, not a GUI design essay, and not a place for interface convenience to redefine backend meaning.

# Canonical Role in Jeff

Interfaces expose backend truth, support artifacts, lifecycle views, and operator actions through downstream truthful surfaces.
They exist so the operator can inspect Jeff, understand Jeff, and lawfully invoke Jeff without having to reconstruct backend meaning from logs, blobs, or hidden heuristics.

Jeff cannot tolerate:
- interface-owned semantics
- shadow truth in caches, sessions, or view models
- convenience-driven flattening of approval, readiness, execution, outcome, evaluation, or transition distinctions
- operator surfaces that imply permission or completed effect before backend confirmation
- support artifacts being displayed as if they were current truth

This document protects operator trust and inspectability by keeping the interface layer downstream of the rest of the canon.
Interfaces render and invoke.
They do not decide what things mean.

# Core Principle

The binding law is:
- interfaces render or invoke; they do not redefine
- operator surfaces must remain truthful about authority, uncertainty, and state class
- derived views may compress or combine, but may not invent new truth
- interface and session state are not canonical truth
- interfaces do not grant permission
- interfaces do not mutate truth
- transitions remain the only canonical truth mutation contract

Backend law still owns meaning.
Interfaces must preserve that meaning rather than smoothing it into easier but false stories.

# Operator Surface Model

An operator surface is any human- or client-facing interface through which Jeff is inspected or invoked.
Whole-Jeff operator surfaces include:
- inspect surfaces for current truth, support artifacts, and bounded history
- action-entry surfaces for lawful operator requests
- review surfaces for proposals, plans, research artifacts, approvals, outcomes, and evaluations
- lifecycle and trace surfaces for runs, orchestration progression, and audit visibility
- approval, reject, retry, revalidate, recover, rerun, and escalation initiation surfaces where backend law allows them
- direct-output research and result surfaces
- error, degraded-state, blocked-state, and inconclusive-state surfaces

Operator surfaces are downstream of backend contracts.
They may expose canonical truth, derived views, support artifacts, and operator requests.
If plans or workflow-shaped views are exposed, they must remain clearly labeled support or coordination surfaces.
In v1 they do not become first-class canonical truth by being visible in an interface.
They must not create hidden backend semantics such as private status rules, private approval shortcuts, or interface-only truth classes.

# CLI Surface

The CLI is the v1 primary operator surface.
Its role is to provide contract-first, inspectable, automation-friendly access to Jeff without collapsing backend distinctions into terse command convenience.

The CLI must:
- expose explicit distinctions rather than smoothing them away
- keep read surfaces separate from action-request surfaces
- produce stable machine-readable output where JSON is claimed
- remain truthful about blocked, degraded, pending, inconclusive, and mismatch-affected conditions
- avoid hiding missing information behind polished summaries

The CLI must not:
- become a second control plane
- hide permission boundaries behind short verbs
- imply that selected means permitted, approved means applied, or completed execution means completed objective
- serialize support artifacts as if they were canonical truth

# API Bridge Surface

The API bridge is a downstream transport surface over backend contracts.
Its purpose is to carry Jeff semantics to clients without creating a second backend with alternate meanings.

The API bridge may:
- adapt transport shape
- normalize transport errors
- expose resource-oriented reads
- expose governed action-request entrypoints
- expose derived summaries when they remain truthful and traceable

The API bridge must not:
- invent alternate lifecycle meaning
- privately reinterpret business truth for one client
- hide domain states inside transport failures
- flatten blocked, degraded, pending, or inconclusive states into generic success or generic failure
- own policy, approval, readiness, evaluation, or transition semantics

If the bridge changes meaning for convenience, it stops being a bridge.

# GUI Surface

The GUI is a future operator convenience and view layer.
It may compose timelines, filters, panels, dashboards, and review surfaces so long as it stays subordinate to backend law.

The GUI may:
- combine related backend objects into bounded operator views
- provide list, detail, summary, timeline, and attention surfaces
- maintain local UI state such as tab selection, sorting, filters, expansion state, and panel layout
- expose operator actions that route into backend law

The GUI must not:
- invent backend truth
- flatten critical distinctions for cleanliness
- imply effect before confirmation
- present memory, review artifacts, or history as current truth
- turn local UI state into shared or canonical truth

GUI-local state is legitimate as presentation state only.
It is never canonical state.

# Truthfulness Rules

The following rules are binding:
- label canonical truth, support artifacts, derived views, and local UI state distinctly where that distinction matters
- preserve a truth or authority class in structured inspect data for significant operator-facing objects and views
- do not present derived inference as canonical truth
- do not present selected as permitted
- do not present approval as applied
- do not present execution complete as objective complete unless evaluation supports that judgment
- do not hide degraded, blocked, inconclusive, partial, or mismatch-affected conditions
- do not hide missing evidence, missing linkage, or stale basis behind clean summaries
- do not present artifact existence as success
- do not present timeline recency as current truth
- do not present memory as current truth
- do not present plan or workflow visibility as canonical status authority in v1
- do not overstate token or cost certainty; if usage or cost is estimated, partial, delayed, or unavailable, that must be explicit
- do not let color, badge shape, or summary prose outrank the underlying structured meaning

Truthfulness includes honesty about uncertainty and honesty about authority.
An interface that is visually clear but semantically false is still lying.

# View-Model Constraints

Derived views and view models may aggregate, compress, and normalize data for operator use.
They must stay traceable to authoritative backend objects and must preserve material distinctions.

View-model rules:
- preserve the source-of-truth class where relevant
- preserve important backend distinctions even when the view is compressed
- identify when a value is derived rather than authoritative
- do not merge multiple backend states into one misleading summary without explicit labeling
- keep current truth, history, memory, artifacts, and operator-local state distinct
- keep action availability derived from authoritative backend conditions, not frontend guesswork
- keep stale or delayed projections visibly stale when freshness matters

The following distinctions must remain visible when relevant:
- approved vs applied
- selected vs permitted
- pending vs blocked vs deferred vs escalated
- execution_status vs outcome_state vs evaluation_verdict
- canonical truth vs support artifact
- degraded vs failed vs inconclusive
- memory vs current truth
- history or timeline item vs current state

Projection convenience must not erase backend semantics.

# Operator Action Semantics

Interface-triggered actions are requests or invocations at the interface boundary.
They are not semantic authority by themselves.

Operator-facing action families may include:
- inspect and read requests
- review requests
- approve and reject requests
- retry, revalidate, recover, and rerun requests
- bounded continuation requests
- escalation acknowledgement or response requests where backend law supports them

Binding rules:
- an operator click or command means a request entered the system, not that the requested effect already happened
- the backend still decides through governance, orchestration, and transition law
- the interface must not imply success, permission, or mutation before backend confirmation
- action availability must reflect authoritative backend conditions, and disabled reasons must remain inspectable where relevant
- operator actions must preserve scope and target clarity
- inspect actions must remain non-mutating
- surface results should report request-local facts such as accepted, rejected, blocked, queued, created follow-up refs, or boundary-local completion, not downstream completion theater

The interface may expose that a request was accepted, blocked, rejected, queued, or completed.
It must not blur those stages into one friendly "done" story.

# Interface Contract Boundaries

Interfaces depend on public backend contracts only.
They may shape those contracts for operator usability, but that shaping must remain subordinate.

Binding contract rules:
- interface contracts must not become the source of business truth
- CLI/API/GUI convenience fields must not redefine canonical meanings
- derived summaries are allowed only with truthful labeling and traceability
- interface transport and rendering contracts must preserve typed distinctions already established by backend law
- interface-specific shaping must not introduce hidden lifecycle meanings or shadow permissions

The interface layer may expose public projections.
It may not privately repair missing backend meaning through guesswork.

# Interface Invariants

The following invariants are binding:
- interfaces are downstream truthful surfaces
- interface and session state are not canonical truth
- interfaces do not mutate truth directly
- interfaces do not grant permission directly
- interfaces do not flatten critical distinctions away
- operator surfaces preserve uncertainty, degradation, and boundary conditions honestly
- `project + work_unit + run` scope remains explicit where relevant
- project remains the hard isolation boundary inside global state
- selection is not execution permission
- approval and readiness remain governance objects
- execution, outcome, and evaluation remain distinct
- transitions remain the only canonical truth mutation contract
- canonical state may reference only committed memory IDs
- orchestrator coordinates but does not think, and interfaces must not quietly absorb that missing semantics

# Failure Modes / Semantic Flattening Risks

The interface layer is failing if any of the following happens:
- shadow truth appears in GUI, API cache, or CLI-side summaries
- CLI pretty output lies by omission
- approved equals applied flattening
- selected equals permitted flattening
- execution complete equals objective complete flattening
- support artifact is shown as truth object
- derived health or status scores hide blocked, degraded, or inconclusive reality
- interface-triggered action is shown as completed before backend confirmation
- token or cost certainty is overstated
- local UI state is mistaken for shared backend state
- timeline or recent event is shown as current truth
- memory is shown as if it were canonical state
- transport failures and domain states are collapsed together
- view-model convenience becomes a private semantic layer

# v1 Scope (CLI-first)

v1 enforces enough interface/operator law to keep the operator surface truthful before richer GUI and API layers exist.

v1 enforces:
- CLI as the primary operator surface
- downstream truthfulness rather than interface-owned semantics
- explicit distinction between canonical truth, support artifacts, derived views, and interface-local state
- explicit preservation of selected vs permitted, approved vs applied, and outcome_state vs evaluation_verdict where those distinctions are surfaced
- action requests represented as requests rather than implied completed effects
- truthful blocked, degraded, pending, inconclusive, and mismatch-affected display
- no shadow-truth authority in interface state
- no hidden workflow truth introduced through interface convenience

v1 does not require:
- a fully realized GUI
- a broad public API surface
- rich dashboarding
- elaborate transport-specific schemas in this document
- complex token or cost accounting models beyond honesty about measured, estimated, partial, or unavailable data

CLI-first means truth-first, not CLI-only forever.

# Deferred / Future Expansion

Deferred expansion may later add:
- richer API bridge contracts
- richer GUI dashboards, timelines, and filters
- stronger truth-labeling affordances in operator surfaces
- better provenance and source-link display patterns
- stronger view-model lineage and traceability support
- future blended assistant/operator surfaces only if explicitly canonized later

Deferred expansion does not weaken current law.
Future interface richness must remain subordinate to backend truth, governance, and transition discipline.

# Questions

No unresolved interface/operator questions were found in this pass.

# Relationship to Other Canonical Docs

- `ARCHITECTURE.md` defines Interface as a downstream layer and forbids interface-owned truth.
- `STATE_MODEL_SPEC.md` owns canonical truth placement and the rule that interface state is not canonical state.
- `TRANSITION_MODEL_SPEC.md` owns the only canonical truth mutation contract.
- `POLICY_AND_APPROVAL_SPEC.md` owns approval, readiness, and permission semantics that interfaces must not flatten.
- `ORCHESTRATOR_SPEC.md` owns sequencing and routing; interfaces may expose those results but do not own them.
- `CORE_SCHEMAS_SPEC.md` owns shared machine-facing naming discipline that interface surfaces must preserve rather than blur.
- `GLOSSARY.md` owns the meanings of interface, derived view, memory, outcome, evaluation, approval, readiness, and related terms used here.
- `EXECUTION_OUTCOME_EVALUATION_SPEC.md` owns the post-governance action and judgment distinctions that interfaces must preserve.
- `MEMORY_SPEC.md` owns memory semantics and keeps memory subordinate to current truth.
- `PLANNING_AND_RESEARCH_SPEC.md` owns research and plan artifacts that interfaces may show only as support objects unless later canonized otherwise.

# Final Statement

Jeff interfaces are truthful downstream surfaces.
They expose what the backend means, they let the operator invoke lawful requests, and they keep canonical truth, support artifacts, derived views, and interface-local state from collapsing into one blob.

If this law stays hard, Jeff can gain richer CLI, API, and GUI surfaces without losing operator trust.
If it softens, Jeff will start lying through convenience, and the interface layer will become a rival truth system instead of a faithful one.
