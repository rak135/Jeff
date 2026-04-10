# Purpose

This document defines Jeff's canonical memory law.

It owns:
- what memory is for
- what memory is not
- the canonical memory type families
- the memory record model
- memory candidate creation rules
- write authority
- the memory write pipeline
- rejection rules
- linking rules
- retrieval rules
- conflict-with-truth rules
- scope rules
- memory invariants and failure modes

It does not own:
- current truth topology
- transition lifecycle or truth-mutation law
- proposal or selection semantics
- interface display contracts
- telemetry schemas
- test matrices
- roadmap sequencing

This is the canonical durable non-truth continuity document for Jeff as a whole.
It is not an implementation-status note.
It is not a vague essay about why memory matters.
It is not a backup truth layer, a note bucket, or a rival authority for state, transition, or governance.

# Canonical Role in Jeff

Memory preserves useful continuity across time without becoming current truth.
It exists so Jeff can reuse durable lessons, findings, rationale, and bounded prior experience without redoing the same work blindly.

Jeff still operates inside:
- one global canonical state with nested projects
- project as a hard isolation boundary inside that state
- `project + work_unit + run` as the foundational scope containers memory must respect

Jeff cannot tolerate:
- memory-as-truth collapse
- uncontrolled memory writes
- memory sludge from storing everything
- retrieval dump behavior
- weakly grounded summaries outranking better evidence
- cross-project bleed that weakens project isolation

This document protects future reuse without weakening truth discipline.
Memory is for continuity.
State is for current truth.
Transitions are for truth mutation.

# Core Principle

The binding law is:
- memory stores what is likely to matter again, not everything that happened
- memory is selective, structured, and support-oriented
- memory is not current truth
- memory does not silently repair, replace, or override truth
- only Memory creates memory candidates
- only committed memory IDs may be referenced canonically
- transitions remain the only canonical truth mutation contract

Execution, outcome, evaluation, research, planning, and operator input may all produce signals that inform memory work.
None of them create canonical memory candidates by themselves.

# What Memory Is For

Memory exists to preserve durable continuity that is likely to improve future judgment or future work quality.

Legitimate memory roles include:
- reusable findings worth carrying forward
- meaningful decisions or rationale worth preserving
- directional anchors and anti-drift lessons
- operational learning that improves future work
- important bounded episodic events that may serve as precedent later
- project continuity across time

These are support roles only.
Memory may inform later context assembly, research, proposal, planning, selection, evaluation review, or operator explanation.
It does not become truth authority for any of them.

# What Memory Is Not

Memory is not:
- current truth
- raw log storage
- raw trace archive
- chat history dump
- prompt dump
- universal note bucket
- policy authority
- hidden state repair layer
- uncontrolled "remember everything" storage
- a duplicate home for state, direction, readiness, approval, or active status

If something belongs in canonical state, policy, or another truth-owning object, memory must not impersonate it.

# Memory Types

Jeff keeps a bounded canonical memory type family:
- `episodic`
- `semantic`
- `directional`
- `operational`

Each committed memory record has one primary type.
Type is not cosmetic metadata.
Type affects write discipline, retrieval use, and review expectations.

Type meanings:
- `episodic`: a bounded remembered case or event that may matter later because that specific episode is instructive
- `semantic`: a reusable learned conclusion, pattern, or durable knowledge statement derived from grounded support
- `directional`: a durable strategic anchor, boundary, non-goal rationale, or anti-drift lesson
- `operational`: durable practical know-how, procedure, or repeated working lesson that improves future execution, review, or recovery

Anti-blur rules:
- current direction is not directional memory
- current truth is not semantic memory
- raw event history is not episodic memory
- one-off tactical clutter is not operational memory
- if one remembered thing serves two materially different roles, split it into separate memories rather than creating a muddy hybrid
- ad hoc fuzzy types such as "insight", "general", or "important" are forbidden

Jeff v1 keeps all four types.
That is bounded enough to stay useful and strong enough to prevent one-bucket sludge.

# Memory Record Model

A committed memory record must be concrete enough to stay retrievable, inspectable, and non-drifting.

At minimum, a committed memory record should carry:
- `memory_id`
- primary `memory_type`
- primary scope
- concise summary
- key remembered points or remembered claim set
- why the memory exists or why it is expected to matter again
- provenance or support linkage
- support quality or confidence
- typed links to related project, work unit, run, artifacts, source refs, and related memory where relevant

Record model rules:
- memory bodies must stay concise and structured
- memory is stored as support content, not as container truth
- the record must be understandable without reopening raw residue blindly
- the record must preserve enough linkage that its support can be inspected later
- the record must not be a raw dump of logs, traces, prompts, or research bodies

# Memory Candidate Creation Rules

Only Memory creates memory candidates.
That rule is hard.

Upstream stages may provide signals or support such as:
- research findings and recommendation context
- execution residue and outcome evidence
- evaluation verdicts and rationale
- operator-marked "this may matter later" cues
- current-truth refs that frame why something is continuity-worthy

Those inputs may inform Memory.
They do not create canonical candidates themselves.

Candidate creation rules:
- candidate creation must be selective, not automatic
- no candidate is created merely because a run ended, an artifact exists, or a conversation happened
- a candidate must be grounded in support strong enough to justify future reuse
- a candidate must be framed as durable continuity, not copied current truth
- a candidate remains a pre-commit Memory-owned object until the write pipeline completes successfully

# Write Authority

Memory owns memory writing end to end.

Memory is the only layer allowed to:
- create memory candidates
- validate candidates
- accept, reject, or defer candidates
- assign type and scope
- deduplicate or supersede memory
- commit memory records
- issue committed memory IDs
- index memory
- link memory

Other modules may:
- provide support inputs
- request retrieval
- reference committed memory IDs where canonically allowed

Other modules may not:
- create canonical memory candidates
- commit memory directly
- issue memory IDs
- bypass rejection or validation rules
- write freeform memory into canonical storage

Operator influence may shape priority or request review, but it does not bypass Memory discipline.

# Write Pipeline

Every committed memory write must pass through a bounded pipeline.

The canonical pipeline is:
1. candidate creation by Memory
2. candidate validation
3. deduplication and incremental-value check
4. type assignment
5. scope assignment
6. compression into concise retrievable form
7. accept / reject / defer decision
8. commit and storage
9. indexing
10. linking

Pipeline rules:
- no step may be skipped silently
- no committed memory ID exists before successful commit
- a deferred or rejected candidate does not become canonically referenceable
- indexing and required linking are part of a successful write, not optional cleanup
- memory writes are structured writes, not freeform dumps
- if the pipeline cannot complete honestly, the candidate must be rejected or deferred rather than partially committed

Write outcomes are bounded:
- `write`
- `reject`
- `defer`
- `supersede_existing` where a better memory replaces an older one
- `merge_into_existing` only if merge discipline is explicit and preserves inspectability

# Rejection Rules

A memory candidate must be rejected when any of the following is true:
- it is unsupported by evidence or provenance
- it is a duplicate or near-duplicate with no meaningful addition
- it is too vague to retrieve usefully
- it is too verbose, too raw, or too residue-heavy
- it is low-value and unlikely to matter again
- it merely restates current truth with no continuity value
- it conflicts with truth without proper contradiction handling
- it has the wrong scope
- it is a weakly grounded guess presented as durable memory
- it relies on broken or missing required links

Defer is valid when:
- the idea may matter later
- support is not yet strong enough
- repetition, confirmation, or cleaner framing is still needed

Jeff should prefer false negatives over polluted memory.

# Linking Rules

Memory links exist to keep memory grounded and navigable without turning it into a spiderweb truth layer.

Memory may link to:
- `project`
- `work_unit`
- `run`
- artifacts
- source refs or evidence-bearing objects
- related committed memory

Linking rules:
- links must be thin and typed
- every committed memory must carry a primary scope link
- every committed memory should carry support linkage strong enough to inspect origin
- related-memory links must be selective and meaningful, not generic "related" sprawl
- lineage links such as supersession should remain explicit when memory is replaced or merged
- memory bodies do not become container truth just because they link to containers
- canonical state may reference only committed memory IDs
- uncommitted candidates must not appear in canonical truth through links

Linking exists to preserve provenance and reuse quality.
It does not transfer authority from truth-owning objects into memory.

# Retrieval Rules

Memory retrieval is support retrieval, not truth retrieval.

Retrieval law:
- read current truth first
- retrieve memory second
- keep retrieval scoped and selective
- prefer local scope before wider scope
- deduplicate retrieved memory
- enforce retrieval budgets
- prefer stronger, better-linked memory over weak or weakly grounded memory
- return a bounded support set, not a dump

Primary retrieval discipline:
- local scope first: same run where relevant, then same work unit, then same project
- project scope remains the primary durable write scope in v1, while run and work-unit locality sharpen retrieval through typed links and local filters
- cross-project retrieval is conservative in v1 and excluded by default unless explicitly justified later
- source-grounded memory outranks weakly grounded memory
- active, unsuperseded memory outranks stale or contradicted memory for normal reuse

Forbidden retrieval behavior:
- "dump top-k and pray"
- retrieving memory before reading truth
- treating remembered summaries as proof of current reality
- allowing weak memory to outrank better-grounded support just because it sounds cleaner

`CONTEXT_SPEC.md` owns full context assembly.
This document owns the memory-side retrieval discipline that context and other consumers must respect.

# Conflict-With-Truth Rules

State wins for current-truth questions.
That rule is absolute.

If memory conflicts with current truth:
- memory does not override truth
- conflicting memory must stay labeled as support, contradiction, stale memory, or uncertainty support
- memory may justify later review, reconciliation, or transition work
- memory conflict does not authorize truth mutation

If a candidate tries to encode current-truth claims that belong in state:
- reject it
- or rewrite it as continuity value such as rationale, lesson, precedent, or uncertainty support if that is honest

Memory may preserve why something mattered, how a conflict emerged, or what was learned from it.
Memory may not silently repair truth by itself.

# Scope Rules

Scope discipline applies to both writing and retrieval.

Whole-Jeff scope law:
- every committed memory must belong to an explicit primary scope
- scope must never weaken project isolation
- Jeff-project work and non-Jeff project work use the same memory law

v1 scope law:
- project scope is primary
- `project + work_unit + run` remain the foundational containers memory must respect
- work-unit and run locality are expressed mainly through typed links and retrieval filters inside the project boundary rather than by weakening project isolation
- future global or system memory is conditional and must be explicitly canonized later before use
- cross-project writing and retrieval remain conservative

Scope rules:
- do not over-promote local memory into broad scope
- do not let project memory drift into global memory by convenience
- do not use cross-project memory to bypass project isolation
- scope errors are retrieval quality errors as well as write-quality errors

# Memory Invariants

The following invariants are binding:
- memory is durable non-truth continuity
- only Memory creates memory candidates
- only committed memory IDs may be referenced canonically
- memory does not define current truth
- memory does not override truth
- memory writes are selective
- memory writes are structured
- memory retrieval is scoped and bounded
- memory is not a raw archive
- memory does not mutate truth
- transitions remain the only canonical truth mutation contract
- project remains the hard isolation boundary memory must respect
- each committed memory has one primary canonical type
- Jeff-project and non-Jeff project work use the same memory law

# Memory Failure Modes

The memory layer is failing if any of the following happens:
- memory-as-truth collapse
- remember-everything sludge
- uncontrolled candidate creation by arbitrary modules
- duplicate memory buildup
- low-signal clutter
- stale memory treated as current truth
- weakly grounded memory outranking better-grounded support
- uncontrolled cross-project bleed
- retrieval dump behavior
- hidden memory repair of truth
- type blur that collapses episodic, semantic, directional, and operational memory into one blob
- lineage or supersession drift that leaves conflicting old memory active by default

# v1 Enforced Memory Model

v1 enforces enough of the whole-Jeff memory model to prevent sludge, truth drift, and write-authority erosion.

v1 enforces:
- memory as durable non-truth continuity
- only Memory creates memory candidates
- only committed memory IDs may be referenced canonically
- project-scoped committed memory as the primary scope model
- four fixed memory type families with one primary type per memory
- a conservative write pipeline with validation, deduplication, type/scope assignment, compression, commit, indexing, and linking
- explicit reject or defer outcomes instead of "store now, clean later"
- typed support links and primary scope links
- truth-first, scoped, bounded retrieval
- local-first retrieval inside project boundaries
- state-winning conflict handling
- no raw dump memory writes
- no arbitrary module memory commits

v1 does not require:
- rich global memory
- giant memory graphs
- aggressive auto-merging
- heavy autonomous memory review bureaucracy
- retrieval systems that weaken scope or truth discipline for recall volume

# Deferred / Future Expansion

Deferred expansion may later add:
- richer global memory only if explicitly canonized without weakening project isolation
- stronger deduplication and merge strategies
- richer memory-quality grading and review
- stronger lineage, supersession, and deprecation handling
- richer retrieval strategies and ranking
- more expressive but still typed memory-link families

Deferred expansion does not weaken current law.
Future memory richness must remain selective, scoped, provenance-preserving, and truth-subordinate.

# Questions

No unresolved memory-model questions were found in this pass.

# Relationship to Other Canonical Docs

- `GLOSSARY.md` owns the canonical meanings of `memory`, `memory candidate`, `memory entry`, and `committed memory ID`.
- `STATE_MODEL_SPEC.md` owns truth placement and the rule that canonical state may reference only committed memory IDs.
- `TRANSITION_MODEL_SPEC.md` owns truth mutation law and keeps memory non-mutating.
- `CONTEXT_SPEC.md` owns truth-first context assembly; this document supplies the memory retrieval discipline that context must respect.
- `EXECUTION_OUTCOME_EVALUATION_SPEC.md` owns execution, outcome, and evaluation; those layers may inform memory work but do not create memory candidates.
- `CORE_SCHEMAS_SPEC.md` owns shared schema naming and machine-facing field discipline; this document does not redefine low-level schema contracts.
- `ARCHITECTURE.md` places Memory as its own layer with its own ownership boundary and keeps memory from collapsing into state or orchestrator logic.
- `PROJECT_AND_WORK_UNIT_MODEL_SPEC.md` owns project, work unit, and run container law that memory must respect through scope and typed links.
- `PLANNING_AND_RESEARCH_SPEC.md` owns research and planning artifacts that memory may later preserve selectively as durable continuity.
- `VISION.md` owns the product-level requirement that memory provide continuity without becoming fake truth.

# Final Statement

Jeff memory is durable continuity, not current truth.
It remembers what is likely to matter again, in a selective, structured, inspectable form.

Only Memory creates memory candidates.
Only committed memory IDs may enter canonical reference surfaces.
Truth still lives in state.
Truth still changes only through transitions.

If these laws stay hard, Jeff can preserve continuity for both Jeff-project and non-Jeff project work without turning memory into sludge or fake truth.
If they soften, memory will become a second state layer, retrieval quality will collapse, and future judgment will degrade with it.
