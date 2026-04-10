# Purpose

This document defines Jeff's canonical handoff structure law.

It owns:
- handoff hierarchy
- placement rules
- ownership rules
- required template bodies
- repo-level handoff template
- module-level handoff template
- submodule-level handoff template
- update rules
- truthfulness rules for handoffs
- handoff anti-patterns
- required module handoff section structure

It does not own:
- backend truth semantics
- architecture law
- module business logic
- transition law
- test matrices
- roadmap sequencing

This is the canonical Jeff handoff-structure document.
It defines how handoffs are written, placed, owned, and kept truthful.
It does not turn handoffs into a rival authority layer.
It does not define `project`, `work_unit`, `run`, or any other canonical Jeff semantics.

# Canonical Role in Jeff

Handoffs are practical continuation and navigation documents.
They exist so someone can continue work, debug, onboard, or transfer ownership without reconstructing reality from chat history, guesses, or stale summaries.

Jeff cannot tolerate:
- stale status fiction
- duplicated specs
- pseudo-truth prose
- repo-level summaries that pretend to know local detail
- module handoffs that erase submodule ownership

This document protects continuity without creating a second semantic system.
Canonical semantics still live in canonical specs.
Handoffs stay downstream, practical, and reality-facing.

# Core Principle

The binding law is:
- handoffs are support documents
- canonical semantics live in canonical specs, not handoffs
- handoffs must be truthful, bounded, and updateable
- handoffs must help someone continue work without rereading the whole repo
- handoffs must not become novels, changelog dumps, or fake "everything is fine" summaries

Handoffs carry practical continuation reality.
They do not create canonical truth.
They do not replace architecture, policy, transition, or module-spec ownership.

# Handoff Hierarchy

## Repo-Level Handoffs

Repo-level handoffs summarize whole-repo continuation state and navigation.

They exist to provide:
- overall continuation entry
- module map and handoff index
- cross-module risks that matter now
- cross-module next-work priorities
- links to the canonical docs and local handoffs that matter first

Repo-level handoffs are for overall system understanding only.
They must not absorb deep module internals or detailed submodule reality.

## Module-Level Handoffs

Module-level handoffs are the main practical continuation documents for individual modules.

Each module must have its own handoff section or local module handoff.
That module-level handoff owns:
- the module's practical current reality
- boundaries and non-ownership
- important invariants under risk
- active gaps and next continuation steps
- submodule map and links outward

Module-level handoffs summarize submodules at overview level.
They do not erase submodule ownership.

## Submodule-Level Handoffs

Submodule-level handoffs exist when the submodule has enough independent complexity that a parent-module summary is no longer sufficient.

A submodule handoff is justified when at least one of the following is true:
- the submodule has its own governing spec or contract
- the submodule has independent invariants or failure risks
- the submodule has independent implementation cadence or ownership pressure
- the submodule has enough active continuation work that burying it in the parent handoff would create drift

If none of those are true, the submodule stays inside the parent module handoff only.

# Placement Rules

Handoff placement must follow ownership and maintenance reality.

Binding placement rules:
- repo-level handoffs live at the repo or top planning level
- module-level handoffs live with the module they describe
- submodule-level handoffs live with the submodule they describe
- top-level Jeff handoffs are for overall navigation, not deep module internals
- handoff location should reinforce local ownership, not random convenience

Forbidden placement drift:
- one generic dump folder as the canonical home of all handoff truth
- repo-level handoffs standing in for local module handoffs
- detached handoffs that live far from the code or docs they describe for no ownership reason

# Ownership Rules

Every handoff must have a clear owner or ownership locus.
Owner here means the module, submodule, or repo-maintaining locus responsible for keeping that handoff truthful.

Binding ownership rules:
- a repo-level handoff owns only repo-level continuation and navigation reporting
- a module-level handoff owns practical continuation for that module, not canonical semantics
- a submodule-level handoff owns practical continuation for that submodule
- repo-level handoffs must not absorb detailed module ownership
- module handoffs may summarize submodules, but must not override submodule-local reality
- if a handoff conflicts with a canonical spec on semantics, the spec wins
- if a broader handoff conflicts with a more local handoff on local implementation reality, the more local handoff wins
- if a handoff conflicts with live implementation reality, neither handoff wins by declaration; the discrepancy must be surfaced explicitly and the stale handoff must be corrected
- ownerless handoffs are forbidden

# Required Template Bodies

Every handoff should be short enough to navigate quickly and concrete enough to continue work immediately.
The templates below are minimum structures, not invitations to add filler.

## Repo-Level Template

A repo-level handoff must include at least:
- `Repo Scope / Purpose`
- `How to Start`
- `Canonical Docs to Read First`
- `Module Map / Handoff Index`
- `Current Repo-Level Reality`
- `Cross-Module Risks / Unresolved Issues`
- `Next Recommended Continuation Work`
- `Related Repo-Level Handoffs`

Repo-level bodies may summarize module reality only at navigation level.
They must link downward instead of retelling module semantics.

## Module-Level Template

A module-level handoff must include at least:
- `Module Name`
- `Module Purpose`
- `Current Role in Jeff`
- `Boundaries / Non-Ownership`
- `Owned Files / Areas`
- `Dependencies In / Out`
- `Canonical Docs to Read First`
- `Current Implementation Reality`
- `Important Invariants`
- `Active Risks / Unresolved Issues`
- `Next Continuation Steps`
- `Submodule Map`
- `Related Handoffs`

Module-level bodies should describe the module clearly enough that someone can enter the module without first reading every neighboring document.

## Submodule-Level Template

A submodule-level handoff must include at least:
- `Submodule Name`
- `Parent Module`
- `Submodule Purpose`
- `Boundaries / Non-Ownership`
- `Owned Files / Areas`
- `Canonical Docs to Read First`
- `Current Implementation Reality`
- `Local Invariants / Contract Notes`
- `Active Risks / Blockers / Unresolved Issues`
- `Next Continuation Steps`
- `Related Handoffs`

Submodule handoffs should be sharper than module handoffs, not longer by default.

# Module Handoff Sections

Each module must have its own handoff section.
That section may live in a standalone module handoff file or in an equivalent module-owned handoff surface, but the section itself is mandatory.

Every module handoff section must include:
- module name
- purpose
- boundaries / non-ownership
- canonical docs
- current implementation reality
- important invariants
- active risks / unresolved issues
- next continuation steps
- submodule map if applicable

Strongly recommended additional fields are:
- owned files / areas
- dependencies in and out
- related handoffs

Submodule decision rule:
- create a submodule handoff when the submodule has independent contract weight, invariant pressure, or active continuation complexity
- keep the submodule only inside the parent module handoff when the parent summary remains sufficient and truthful

Parent-module obligations still remain:
- every meaningful submodule must appear in the parent module's submodule map
- the parent module must state whether the submodule has its own handoff or remains parent-contained

# Update Rules

Handoffs must be updated whenever the practical continuation truth at their scope changes materially.

Required update triggers include:
- implementation reality changed materially
- boundaries or non-ownership changed materially
- active risks changed materially
- next continuation steps changed materially
- a new meaningful submodule appeared
- a submodule gained or lost the need for its own handoff
- a spec/implementation gap opened, closed, or changed meaningfully
- ownership locus changed

Update-order rule:
1. update the most local relevant handoff first
2. update the parent module handoff next if that local change affects the module view
3. update the repo-level handoff only if cross-module or repo-level continuation reality changed materially

Uncertainty rule:
- if reality is uncertain, say it is uncertain
- if a fact is suspected but not confirmed, label it as suspected or unverified
- lying by omission is worse than admitting uncertainty

Handoffs should be incrementally updateable.
They should not require full rewrites after every small change.

# Truthfulness Rules

Handoffs must distinguish clearly between:
- canonical spec
- implementation reality
- known gaps
- next work

Binding truthfulness rules:
- do not present planned work as implemented reality
- do not present guesses as confirmed facts
- do not flatten blocked, degraded, partial, or uncertain reality into "done"
- do not overstate stability, completeness, or test confidence
- do not paraphrase canonical semantics badly when a direct link is better
- do not let prose polish outrank truthful status and boundary reporting
- if implementation differs from canonical design, name the gap explicitly
- if handoff text differs from observed repo reality, mark the mismatch explicitly instead of smoothing it away
- if a more local handoff exists, link to it rather than pretending summary is enough

Handoffs are truthful support surfaces.
They are not semantic authority.

# Forbidden Handoff Anti-Patterns

The following are forbidden:
- handoff as duplicated spec
- handoff as stale project diary
- handoff as changelog dump
- handoff as vague motivational summary
- handoff hiding unresolved issues
- handoff pretending planned work is already real
- repo-level handoff swallowing module detail
- module handoff swallowing submodule ownership
- no-owner handoffs
- giant handoff walls of text with no navigation value
- handoff as fake source of truth for backend semantics
- root summary overriding more local implementation reality
- continuation notes that depend on chat memory instead of written repo truth

# v1 Required Discipline

v1 enforces enough handoff law to stop documentation chaos and stale-summary drift without building a heavy bureaucracy.

v1 requires:
- one consistent repo-level handoff model
- each module has its own handoff section
- submodule handoffs only where justified
- standard minimum fields for repo, module, and submodule handoffs
- module handoffs that summarize submodules without replacing them
- honest update discipline with local-first updates
- explicit link-back to canonical docs
- explicit distinction between canonical spec, implementation reality, known gaps, and next work
- repo-level handoffs that stay navigation-oriented rather than detail-heavy

v1 does not require:
- handoffs for trivial utility folders
- a giant central handoff dump
- narrative status essays
- handoffs that restate full module semantics

# Deferred / Future Expansion

Deferred expansion may later add:
- handoff linting or review automation
- stale-field detection and freshness tooling
- richer cross-linking between handoffs and canonical docs
- stronger repo-generated handoff indexes
- explicit operator-debug handoff variants if later justified

Deferred expansion does not weaken current law.
Future tooling may make handoffs easier to maintain.
It must not turn them into a second authority system.

# Questions

No unresolved handoff-structure questions were found in this pass.

# Relationship to Other Canonical Docs

- `ARCHITECTURE.md` owns the structural backbone, repository architecture rules, and module-admission law that handoff placement must respect.
- `GLOSSARY.md` owns the meanings of module, submodule, canonical, support, truth, and related terms used here.
- canonical module specs own semantics for their domains; this document only governs how handoffs point to them and report current reality around them.
- `ORCHESTRATOR_SPEC.md` owns runtime handoff validation between stages; this document owns documentation handoff structure, not runtime routing.
- `INTERFACE_OPERATOR_SPEC.md` owns truthful downstream surfaces; handoffs may be rendered through those surfaces but do not gain new authority there.
- `TESTS_PLAN.md` owns the test discipline that should catch handoff drift, truthfulness failures, and missing contract coverage.
- `VISION.md` owns the high-level repo shape and continuity goals that make truthful handoffs necessary.

# Final Statement

Jeff handoffs are practical continuation structure, not canonical semantics.

Repo-level handoffs orient.
Module-level handoffs carry the main local continuation load.
Submodule-level handoffs exist only where complexity justifies them.
All of them must stay truthful, bounded, locally owned, and easy to update.

If this law stays hard, Jeff can support continuation, debugging, onboarding, and transfer from written reality instead of reconstruction.
If it softens, handoffs will drift into stale status fiction, duplicated specs, and documentation chaos.
