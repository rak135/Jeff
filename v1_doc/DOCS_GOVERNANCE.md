# Purpose

This document defines Jeff's canonical documentation-governance law.

It owns:
- document classes
- documentation authority order
- the design-vs-reality split
- canonical-vs-archived document treatment
- documentation update triggers
- stale-doc rules
- deprecation and archive rules
- doc-level done criteria
- documentation conflict resolution rules
- documentation failure modes

It does not own:
- backend semantics themselves
- architecture law itself
- handoff template bodies themselves
- roadmap sequencing
- module-local business logic

This is the canonical documentation-governance document for Jeff.
It exists to keep Jeff's written canon from turning back into overlapping, co-equal, stale documentation sludge.

# Canonical Role in Jeff

Docs governance prevents documentation from becoming a second chaotic system beside the architecture and code.

Jeff cannot tolerate:
- parallel authority layers
- stale rival specs that still look current
- archive docs that speak in present-authority voice
- handoffs, plans, notes, and specs blurring together
- top-level summaries quietly overriding local reality
- a return to 120-document chaos where multiple files appear to own the same topic

This document keeps documentation usable by making authority, staleness, and replacement obvious.
Without that discipline, the docs stop guiding Jeff and start competing with it.

# Core Principle

The binding law is:
- canonical docs define canonical Jeff meaning
- handoffs support continuation but do not define semantics
- archived docs may inform but do not rule
- temporary notes may help current work but do not become authority
- documentation must make authority and staleness obvious
- one topic area must not have multiple co-equal canonical owners

The canonical `v1_doc` set is the active replacement layer for the old sprawl.
It is not just another parallel layer.

# Document Classes

## Canonical Docs

Canonical docs are the active authority documents for Jeff semantics and governance.

They:
- live in the canonical `v1_doc` set
- own one explicit topic area each
- define Jeff meaning, boundaries, or governance for that owned area
- must stay aligned with the rest of the canonical set

They must never claim topics owned by another canonical document.

## Handoffs

Handoffs are continuation and navigation documents.

They:
- report practical implementation reality
- record gaps, risks, and next work
- help debugging, onboarding, transfer, and continuation

They must never:
- define canonical semantics
- override canonical docs on meaning
- act like archive replacement or pseudo-specs

`HANDOFF_STRUCTURE.md` owns handoff structure.
This document governs handoff authority and subordination.

## Archived / Reference Docs

Archived or reference docs remain only for history, mining, or background context.

They:
- may preserve useful prior reasoning
- may help explain how the canon evolved
- may support comparison or recovery of lost context

They must never:
- appear co-equal with the canonical set
- speak as active authority once replaced
- remain unlabeled if they are no longer current

## Roadmap / Process Docs

Roadmap and process docs govern sequencing, build discipline, testing discipline, handoff discipline, or docs discipline where Jeff explicitly canonizes those process areas.

They may define:
- sequencing
- process obligations
- exit-gate expectations
- documentation hygiene rules

They must never:
- override canonical semantic ownership
- redefine module meaning because sequencing convenience changed

## Temporary Working Docs

Temporary working docs are short-lived drafting, merge, audit, or investigation materials.

They may:
- support an active rewrite
- capture unresolved local working context
- hold bounded temporary analysis

They must never:
- become shadow canon by inertia
- outlive their working purpose without reclassification
- speak more strongly than the canonical docs they are helping to produce

# Authority Order

Documentation authority is not one flat stack.
Authority depends on what kind of question is being asked.

## Semantics Authority

For Jeff meaning, boundaries, and owned topic law:
1. canonical docs in `v1_doc`
2. nothing else

Rules:
- if a doc conflicts with canonical docs on semantics, the canonical docs win
- handoffs, chats, roadmap notes, and legacy docs do not define Jeff meaning
- archived legacy docs may inform interpretation only when they do not conflict with canon

## Implementation-Reality Reporting

For what is actually implemented now:
1. live implementation reality
2. the most local relevant handoff
3. broader handoffs or summary docs
4. archived/reference docs

Rules:
- live implementation reality does not silently rewrite canonical semantics
- if a handoff conflicts with live implementation reality, the mismatch must be surfaced, not hidden
- repo-level docs do not override module-local reality

## Navigation / Continuation Support

For where to start, what to read next, and what is currently blocked:
1. the most relevant handoff at the right scope
2. related canonical docs
3. archived/reference docs only as labeled background

## Historical / Reference Value

For historical context only:
1. archived/reference docs
2. temporary working notes if still explicitly active and labeled

Historical value is not authority.

# Design vs Reality Split

Jeff documentation must preserve a hard split between:
- canonical design
- current implementation reality
- known gaps between them

Canonical docs may describe the target whole-Jeff law even when implementation is behind.
Handoffs may describe current implementation reality even when it is weaker than the target law.
Neither may lie about the gap.

Binding rules:
- a canonical doc does not prove implementation exists
- a handoff does not weaken canonical design by reporting weaker implementation
- implementation drift must be named explicitly, not silently harmonized
- if a summary doc smooths away a design/reality gap, that summary is defective

Correct pattern:
- canonical doc states the law
- handoff states current reality
- the gap is explicit

# Canonical vs Archived Docs

A doc is canonical only if it is part of the active `v1_doc` canonical set and owns an active Jeff topic area.

A doc is archived/reference only if any of the following is true:
- its content was merged into a canonical replacement
- it is retained only for history or mining
- it covers a superseded model
- it is useful background but no longer active authority

Archived/reference treatment rules:
- archived docs must be visibly labeled
- archived docs must point to the active canonical replacement when one exists
- archived docs must not keep current-authority framing after replacement
- old docs may remain searchable, but not co-equal

The canonical `v1_doc` set is not optional alongside the old corpus.
It replaces the old authority layer.

# Update Triggers

Documentation review or update is mandatory when any of the following occurs:
- canonical semantics changed materially
- a new canonical decision settled an open question
- a boundary or ownership rule changed
- a canonical field, object, or status name changed materially
- a module or submodule gained real independent weight
- a module or submodule lost independent weight
- live implementation drifted materially from canonical design
- a handoff's reported reality, risks, or next steps changed materially
- a document was merged, replaced, deprecated, or archived
- a summary doc started conflicting with a more local handoff
- a legacy doc remained active-looking after replacement

Class-specific trigger rules:
- canonical docs update on meaning, boundary, naming, or ownership changes
- handoffs update on material implementation-reality changes
- archive labels update when replacement, merge, or supersession becomes true
- temporary working docs must be closed, promoted, archived, or deleted when their active purpose ends

# Stale-Doc Rules

A doc is stale when it no longer truthfully reflects its declared role while still appearing current.

Strong stale conditions include:
- a higher-authority canonical doc changed and this doc did not
- implementation reality changed and the relevant handoff did not
- a legacy doc still reads like active authority after replacement
- a summary doc no longer matches more local reality
- a doc still speaks in present-tense certainty about past or superseded behavior
- freshness is unknown but the doc still appears active without qualification

Stale-doc handling law:
- stale docs must be corrected, marked stale, deprecated, or archived
- stale docs must not quietly remain active-looking
- if freshness is uncertain, that uncertainty must be explicit
- "probably still right" is not an acceptable stale-doc state

# Deprecation / Archive Rules

A doc should be deprecated or archived when:
- a canonical replacement now owns its topic
- its content was merged into a stronger canonical doc
- its model was superseded
- its only remaining value is historical or reference value
- keeping it active-looking would create soft duplication

Deprecation/archive requirements:
- visible label near the top
- clear replacement or successor doc when one exists
- short reason for deprecation or archive status
- no present-authority voice after deprecation

Merge/replace/archive rules:
- merge when multiple docs are really one topic with one owner
- replace when an old authority surface is intentionally superseded
- archive when historical value remains but active authority must end
- do not let soft duplicates survive forever just because they are "still useful"

# Doc-Level Done Criteria

A canonical doc is done enough to count as authoritative only when:
- its owner topic is clear
- its scope boundary is clear
- what it does not own is explicit
- its relation to neighboring docs is explicit
- it is precise enough to govern decisions in its owned area
- it does not contain major unresolved contradictions
- it has a real `# Questions` section outcome, either explicit questions or an explicit no-open-questions statement
- it does not duplicate another canonical owner's job

A handoff is done enough only when:
- its scope and ownership locus are clear
- current implementation reality is explicit
- known gaps and risks are explicit
- next continuation work is concrete
- it does not claim semantic authority

A deprecated/archive doc is done enough only when:
- its non-canonical status is obvious
- its replacement or archival role is obvious
- it cannot reasonably be mistaken for current canon

# Conflict Resolution Rules

When docs conflict, resolve them by conflict type first, then by authority.

## Canonical Doc vs Canonical Doc

If two canonical docs appear to own the same semantic topic:
- that is a documentation defect
- the more explicitly owning canonical doc wins temporarily
- the overlap must be corrected
- if ownership is genuinely unresolved, raise a real question rather than letting both stand

## Handoff vs Canonical Spec

If a handoff conflicts with a canonical doc on semantics:
- the canonical doc wins on meaning
- the handoff must state the implementation gap explicitly
- the handoff must not rewrite the law by implication

## Doc vs Live Implementation Reality

If documentation conflicts with live implementation reality:
- reality wins for the question "what is implemented now"
- the mismatch must be surfaced explicitly
- the relevant handoff must be updated
- canonical docs change only if the intended law actually changed

## Archived Legacy Doc vs Canonical Doc

If an archived or legacy doc conflicts with canon:
- canon wins
- the archived doc must not remain active-looking
- if the archive label is missing or weak, fix that label

## Summary Doc vs Local Module Doc

If a summary or repo-level doc conflicts with a more local handoff on local reality:
- the more local handoff wins for local reporting
- the summary doc is stale and must be corrected

Ignoring a conflict is not resolution.

# Documentation Failure Modes

Documentation governance is failing if any of the following happens:
- duplicate semantic authority
- stale docs that still look current
- archive docs treated as active canon
- handoff/spec blur
- design/reality gaps hidden by polished prose
- module-local reality overridden by top-level summary
- endless document sprawl
- temporary docs becoming permanent shadow authority
- answered questions, roadmap notes, or chats being treated like active semantics owners
- unlabeled legacy docs continuing to steer decisions
- the `v1_doc` set becoming just another layer instead of the replacement layer

# v1 Governance Discipline

v1 enforces enough documentation law to stop chaos and parallel authority from returning.

v1 requires:
- the canonical `v1_doc` set as the active authority layer
- clear archive/reference-only treatment of old docs
- explicit update discipline for canonical docs, handoffs, and archive labels
- no new semantic-authority docs created casually outside the canonical set
- handoffs staying subordinate to canon
- explicit design-vs-reality gap reporting instead of silent smoothing
- stale docs being corrected, marked, or archived instead of left active-looking
- conservative doc creation to prevent new sprawl

v1 does not allow:
- legacy docs remaining co-equal with canon
- temporary working docs surviving indefinitely as shadow authority
- summary docs overriding local handoff reality
- handoffs or roadmap docs quietly redefining semantics

# Deferred / Future Expansion

Deferred expansion may later add:
- doc linting and review automation
- stronger stale-doc detection
- generated indexes or authority maps
- richer traceability between docs and implementation
- stricter automated archive labeling if later justified

Deferred expansion does not weaken current law.
Future tooling may make governance easier to enforce, but it must not create new parallel authority layers.

# Questions

No unresolved docs-governance questions were found in this pass.

# Relationship to Other Canonical Docs

- `ARCHITECTURE.md` owns Jeff's structure and boundary law; this document governs documentation authority around that law.
- canonical topic docs in `v1_doc` own their domain semantics; this document keeps those ownership lines singular and explicit.
- `HANDOFF_STRUCTURE.md` owns handoff hierarchy and template discipline; this document keeps handoffs subordinate to canon and properly classified.
- `TESTS_PLAN.md` owns test strategy; this document defines when documentation drift itself becomes a governance defect.
- `VISION.md` owns the high-level shape and long-range clarity Jeff is trying to preserve.

# Final Statement

Jeff documentation is only trustworthy if authority, staleness, and replacement are obvious.

The canonical `v1_doc` set defines Jeff meaning.
Handoffs support continuation.
Archived docs may inform history.
Temporary notes may help current work.
None of those layers may remain co-equal.

If this law stays hard, Jeff can keep one readable canon instead of growing a new pile of competing markdown authority.
If it softens, the repository will drift back into parallel truths, stale confidence, and documentation chaos.
