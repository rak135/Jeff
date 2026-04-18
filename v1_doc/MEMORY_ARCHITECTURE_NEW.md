# MEMORY_ARCHITECTURE.md

Status: implementation architecture proposal for Jeff Memory  
Authority: subordinate to `MEMORY_SPEC.md`, `CONTEXT_SPEC.md`, `CORE_SCHEMAS_SPEC.md`, `ARCHITECTURE.md`, `STATE_MODEL_SPEC.md`, `PLANNING_AND_RESEARCH_SPEC.md`, `RAW_INGEST_AND_SOURCE_STORE_ARCHITECTURE.md`, `KNOWLEDGE_LAYER_ARCHITECTURE.md`, and `TESTS_PLAN.md`  
Purpose: define a concrete, buildable architecture for Jeff's Memory layer after the addition of raw source custody, research history, and compiled knowledge, without changing canonical memory law

---

## 1. Why this document exists

Jeff already has canonical memory law.
That law is the hard boundary:

- memory is durable non-truth continuity
- memory is selective, structured, and support-oriented
- only Memory creates memory candidates
- only committed `memory_id` values may be referenced canonically
- current truth lives in canonical state, not in memory
- context reads truth first and memory second
- project remains the hard isolation boundary
- research history is not memory
- compiled knowledge is not memory

This document does not redefine those rules.

It turns them into a concrete implementation architecture for:
- storage layout
- module boundaries
- write pipeline
- retrieval pipeline
- maintenance jobs
- observability
- tests
- rollout posture

It also freezes one important practical boundary that was previously too loose:

Jeff now has **three distinct durable support layers** upstream of canonical truth:
1. raw source custody
2. research history + research artifacts
3. compiled knowledge

Memory is downstream of those layers, not a replacement for them.

---

## 2. Architectural position inside Jeff

Memory is its own first-class semantic layer in Jeff.

Its place in the larger support stack is:

```text
raw source custody
  -> research history / research artifacts
  -> compiled knowledge
  -> Memory candidate consideration
  -> committed memory
  -> context retrieval support
```

Memory is therefore:
- narrower than research history
- narrower than compiled knowledge
- more durable and distilled than one-off artifacts
- still subordinate to canonical truth

Memory is not:
- a raw source store
- a research archive
- a compiled wiki
- a current-truth layer
- a transition layer

---

## 3. Core design goals

### 3.1 Hard goals
1. Preserve durable continuity without creating a rival truth layer.
2. Keep memory selective enough to avoid sludge.
3. Keep retrieval scoped, bounded, and useful for real Jeff work.
4. Keep provenance inspectable.
5. Keep the research-history / compiled-knowledge / memory boundary hard.
6. Make upgrades possible without changing Jeff semantics.
7. Make memory failure degrade usefulness, not integrity.
8. Keep the system compatible with future richer retrieval backends.

### 3.2 Non-goals
1. Remembering everything.
2. Using memory as hidden state repair.
3. Letting a framework or vector store own Jeff semantics.
4. Making memory the home of all research outputs.
5. Making memory the home of all topic notes.
6. Building giant graph-first memory in v1.
7. Building autonomous self-rewriting memory law.

---

## 4. Relationship to neighboring layers

### 4.1 Raw source custody
Raw source custody owns:
- original files
- source identity
- source lineage
- source metadata
- extraction sidecars
- provenance capture

Memory may later link to source refs.
Memory does not own source custody.

### 4.2 Research history / research artifacts
Research owns:
- `research_brief`
- `research_comparison`
- `evidence_bundle`
- `source_set`
- `brief_history_record`
- `event_history_record`

These are durable source-backed support objects.
Memory may use them as support inputs.
Memory does not own them.

### 4.3 Compiled knowledge
Compiled knowledge owns:
- `source_digest`
- `topic_note`
- `concept_note`
- `comparison_note`
- `contradiction_note`
- `open_questions_note`

These are durable thematic support artifacts.
Memory may link to them or derive candidates from them.
Memory does not own them.

### 4.4 Canonical truth
Canonical truth lives only in state.
Memory never overrides it.
Memory may be retrieved after truth is read.

---

## 5. High-level architecture

```text
Lawful upstream support inputs
(research artifacts, history records, compiled knowledge, evaluation signals, operator cues, run context)
        |
        v
+----------------------------------+
| Memory Candidate Builder         |
+----------------------------------+
        |
        v
+----------------------------------+
| Validation + Dedupe + Scope      |
| Type Assignment + Compression    |
+----------------------------------+
        |
        +------------------> reject / defer
        |
        v
+----------------------------------+
| Committed Memory Store           |
| - memory records                 |
| - memory points / claims         |
| - memory links                   |
| - lineage                        |
| - audits                         |
+----------------------------------+
        |
        +------------------> Indexer
        |                    - PostgreSQL FTS
        |                    - pgvector
        |                    - future optional adapters
        |
        v
+----------------------------------+
| Retrieval Engine                 |
| - explicit refs                  |
| - lexical                        |
| - semantic                       |
| - rerank                         |
| - conflict labeling              |
+----------------------------------+
        |
        v
+----------------------------------+
| Context Assembly Consumer        |
| truth first, memory second       |
+----------------------------------+
```

---

## 6. Persistence placement

Memory should persist as a project-scoped durable store, distinct from:
- Jeff-managed source custody
- project-visible research history
- project-visible compiled knowledge

Recommended placement direction for memory-owned durable storage metadata:
- authoritative relational persistence in PostgreSQL

Project-visible exports or operator-facing summaries may later be surfaced elsewhere, but PostgreSQL remains the authoritative memory store.

This means:

- raw sources remain outside the project tree in Jeff-managed source custody
- research history lives under the research-owned project tree
- compiled knowledge lives under `projects/<project_id>/research/knowledge/`
- memory persists in its own authoritative backend, not as loose markdown or raw files

---

## 7. Recommended stack

### 7.1 v1 stack
- PostgreSQL as the authoritative persistence layer for memory metadata, scope, lineage, support links, audits, and retrieval bookkeeping
- `pgvector` as the primary vector search extension inside PostgreSQL
- PostgreSQL full-text search for exact term and phrase retrieval
- Jeff-owned retrieval orchestration and context assembly
- Jeff-owned write pipeline
- Jeff-owned maintenance jobs

Why:
- one authoritative transactional store
- strong auditability
- strong scope filtering
- easy hybrid retrieval
- no semantic surrender to an external framework

### 7.2 v1.5 or v2 optional additions
- Qdrant as an optional external vector retrieval backend behind a Jeff adapter
- Graphiti or another temporal graph system as an optional specialized relationship layer
- LlamaIndex as an optional helper in Infrastructure only, never as owner of memory semantics

### 7.3 What remains Jeff-owned no matter what backend is used
- memory type law
- candidate creation law
- acceptance/reject/defer law
- scope rules
- truth conflict handling
- research-history boundary
- compiled-knowledge boundary
- context assembly rules
- linking semantics
- supersession semantics
- maintenance policy

---

## 8. Memory layer responsibilities

The Memory layer owns:
- candidate creation
- candidate validation
- deduplication and incremental-value checks
- type assignment
- scope assignment
- compression into committed memory form
- commit and issuance of `memory_id`
- indexing
- retrieval
- linking
- supersession and merge discipline
- maintenance jobs
- memory observability

The Memory layer does not own:
- canonical state truth
- transitions
- governance
- proposal/selection
- research semantics
- research artifact storage semantics
- compiled-knowledge semantics
- raw source custody
- interface semantics
- orchestration routing semantics

---

## 9. Recommended module layout

Recommended package layout:

```text
jeff/memory/
  __init__.py
  types.py
  ids.py
  schemas.py
  candidate_builder.py
  validator.py
  dedupe.py
  type_assigner.py
  scope_assigner.py
  compressor.py
  store.py
  linker.py
  indexer.py
  retrieval.py
  reranker.py
  conflict_labeler.py
  maintenance.py
  telemetry.py
  api.py
```

Suggested roles:
- `candidate_builder.py`: build candidates from lawful support inputs
- `validator.py`: enforce hard write rules
- `dedupe.py`: detect duplicates and low incremental value
- `type_assigner.py`: assign exactly one primary memory type
- `scope_assigner.py`: enforce scope rules
- `compressor.py`: produce concise retrievable committed form
- `store.py`: persistence, commit, read, audit
- `linker.py`: support links, related-memory links, supersession links
- `indexer.py`: maintain FTS/vector indexes
- `retrieval.py`: retrieve bounded support sets
- `reranker.py`: merge lexical, semantic, and explicit-ref candidates
- `conflict_labeler.py`: label stale/conflicting memory against current truth
- `maintenance.py`: audits, refresh, cleanup, repair
- `telemetry.py`: metrics and trace-safe events
- `api.py`: public Memory contract

---

## 10. Support inputs accepted by Memory

Allowed support inputs:
- research findings and recommendation context
- outcome object and evidence refs
- evaluation verdict and rationale
- operator-marked continuity cues
- current-truth refs when needed for continuity framing
- research artifact refs
- evidence bundle refs
- brief-history refs
- event-history refs
- compiled-knowledge artifact refs

Forbidden as direct memory authority:
- raw source files
- raw article or PDF bodies
- full research briefs copied wholesale
- full topic notes copied wholesale
- full chat dumps
- raw prompts
- raw traces
- unfiltered daily history dumps
- model output without provenance linkage

Important rule:
upstream layers may inform Memory.
They do not author memory.

---

## 11. MEMORY_RECORD_SCHEMA

### 11.1 Core committed record fields

```json
{
  "memory_id": "mem_...",
  "memory_type": "episodic | semantic | directional | operational",
  "project_id": "proj_...",
  "work_unit_id": "wu_... | null",
  "run_id": "run_... | null",
  "summary": "short concise summary",
  "remembered_points": [
    "bounded remembered claim or point"
  ],
  "why_it_matters": "why future reuse is expected",
  "support_quality": "weak | moderate | strong",
  "stability": "tentative | stable | reinforced",
  "freshness_sensitivity": "low | medium | high",
  "retrieval_weight": 0.0,
  "status": "active | superseded | deprecated | quarantined",
  "conflict_posture": "none | stale_support | contradiction_support | mismatch_support",
  "created_at": "iso8601",
  "updated_at": "iso8601",
  "created_from_run_id": "run_... | null",
  "extractor_version": "string",
  "embedding_profile_id": "string | null",
  "schema_version": "1.0"
}
```

### 11.2 Required record rules
- `summary` must be concise and one memory-sized unit
- `remembered_points` must be bounded and individually inspectable
- `why_it_matters` is required
- `support_quality` is support strength for reuse, not truth probability
- `status` defaults to `active`
- `conflict_posture` defaults to `none`
- raw logs, prompts, trace dumps, article bodies, full history records, and full compiled notes are forbidden

### 11.3 Claim model
Some memory records need claim-level inspection.

Support this with a separate claim table rather than hiding everything in prose.

Each claim row should include:
- `memory_claim_id`
- `memory_id`
- `claim_text`
- `claim_kind`: `fact | lesson | rationale | caution | pattern`
- `claim_support_quality`
- `claim_conflict_posture`
- `claim_order`

### 11.4 Link model
Every committed memory should have typed links.

Required:
- one primary scope link through `project_id`
- zero or one local `work_unit_id`
- zero or one local `run_id`

Optional:
- research artifact links
- compiled-knowledge artifact links
- source refs
- evidence refs
- related committed memory links
- supersedes / superseded-by links
- history-record refs

### 11.5 Lineage model
Support explicit lineage:
- `supersedes_memory_id`
- `superseded_by_memory_id`
- `merged_into_memory_id`
- `derived_from_candidate_id`
- `derived_from_run_id`
- `derived_from_artifact_id`

---

## 12. Physical storage schema

### 12.1 `memory_records`
Authoritative committed memory rows.

Suggested columns:
- `memory_id text primary key`
- `memory_type text not null`
- `project_id text not null`
- `work_unit_id text null`
- `run_id text null`
- `summary text not null`
- `why_it_matters text not null`
- `support_quality text not null`
- `stability text not null`
- `freshness_sensitivity text not null`
- `retrieval_weight double precision not null default 0`
- `status text not null`
- `conflict_posture text not null default 'none'`
- `created_from_run_id text null`
- `extractor_version text not null`
- `embedding_profile_id text null`
- `schema_version text not null`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`
- `supersedes_memory_id text null`
- `superseded_by_memory_id text null`
- `merged_into_memory_id text null`

### 12.2 `memory_points`
Bounded remembered points or compressed claim-like payload.

### 12.3 `memory_claims`
Optional stricter claim-level rows when needed.

### 12.4 `memory_links`
Typed links from memory to support objects.

Expected `link_type` values:
- `research_artifact_support`
- `knowledge_artifact_support`
- `source_support`
- `evidence_support`
- `history_record_support`
- `related_memory`
- `supersedes`
- `superseded_by`
- `derived_from`

### 12.5 `memory_embeddings`
Embedding storage and versioning.

### 12.6 `memory_candidates`
Pre-commit candidate staging.

### 12.7 `memory_write_events`
Audit trail for write decisions.

### 12.8 `memory_retrieval_events`
Retrieval audit and evaluation surface.

### 12.9 `memory_maintenance_jobs`
Scheduled or manual maintenance job registry.

---

## 13. Write pipeline

The write pipeline must be deterministic enough to audit and conservative enough to reject junk.

```text
support inputs
  -> candidate creation
  -> candidate validation
  -> dedupe / incremental-value check
  -> type assignment
  -> scope assignment
  -> compression
  -> accept / reject / defer
  -> commit
  -> indexing
  -> linking
```

### 13.1 Candidate creation
Input:
- bounded support inputs
- explicit scope
- reason this might matter later

Rules:
- selective, not automatic
- one candidate should express one memory-sized continuity unit
- no `memory_id` is assigned yet

### 13.2 Candidate validation
Checks:
- required fields present
- support linkage exists
- not raw residue
- not current-truth duplication only
- not wrong scope
- concise enough for retrieval
- provenance is inspectable
- not actually a research artifact or knowledge artifact in disguise

### 13.3 Dedupe and incremental-value check
Purpose:
- stop sludge
- stop near duplicates
- stop weak add-ons

Recommended decisions:
- `reject_duplicate`
- `merge_into_existing`
- `supersede_existing`
- `continue_new_record`

### 13.4 Type assignment
Assign exactly one primary type:
- `episodic`
- `semantic`
- `directional`
- `operational`

If the candidate spans more than one primary role, split it.

### 13.5 Scope assignment
Rules:
- project scope required
- narrower locality attached when justified
- do not over-promote local memory into project-wide importance unless it honestly generalizes

### 13.6 Compression
Purpose:
- make the record retrievable
- prevent giant prose blobs

Compression output should preserve:
- summary
- bounded points
- why it matters
- support quality
- stability
- freshness sensitivity
- explicit links

### 13.7 Accept / reject / defer
Possible outcomes:
- `write`
- `reject`
- `defer`
- `merge_into_existing`
- `supersede_existing`

### 13.8 Commit
Commit creates:
- authoritative `memory_record`
- child points / claims
- support links
- lineage links
- write audit row

Rules:
- atomic enough to avoid partial semantic commit
- `memory_id` issued only here

### 13.9 Indexing
Index after commit:
- PostgreSQL FTS document
- pgvector embedding row
- optional future external backend row

### 13.10 Linking
Write selective links to:
- research artifacts
- compiled-knowledge artifacts
- source refs
- evidence refs
- related memory refs
- supersession refs
- project / work_unit / run locality

Do not generate relation spam.

---

## 14. Retrieval pipeline

Retrieval exists to supply bounded support for a concrete purpose.

### 14.1 Retrieval principles
- truth first, memory second
- scope filter before ranking
- exact linkage before semantic search
- stronger provenance over weaker summary
- stale/conflicting memory stays labeled as support

### 14.2 Retrieval order of operations

```text
1. confirm scope and purpose
2. receive truth anchor from context assembly caller
3. explicit linked memory fetch
4. scoped lexical retrieval
5. scoped semantic retrieval
6. dedupe
7. rerank
8. conflict labeling against truth anchor
9. budget trim
10. package output
```

### 14.3 Retrieval stages
- explicit linked memory fetch
- lexical retrieval
- semantic retrieval
- dedupe
- rerank
- conflict labeling
- budget trim
- package output

### 14.4 Retrieval outputs
Return:
- memory summaries
- relevant remembered points / claims
- why the memory matters
- provenance links
- stale / conflict labels when relevant

Do not return:
- giant raw bodies by default
- hidden stitched truth
- unbounded dumps

---

## 15. Retrieval relationship to context

Memory is not context assembly, but retrieval must be designed for it.

Context priority remains:

1. canonical truth
2. governance-relevant current truth where needed
3. committed memory
4. compiled knowledge
5. raw sources when verification or detail is required

Memory therefore outranks compiled knowledge only in the sense of durable continuity reuse, not as current truth.
Memory must remain source-labeled and conflict-labeled.

---

## 16. Relationship to research history and compiled knowledge during retrieval

Memory retrieval should not try to replace those layers.

When the caller needs:
- a dated historical brief
- an evidence-heavy source bundle
- a thematic topic overview
- contradiction analysis across many sources

the correct answer may be:
- retrieve a memory record **plus**
- retrieve the linked research artifact or knowledge artifact separately through the owning layer

Memory should link outward.
It should not absorb those objects wholesale.

---

## 17. Maintenance jobs

Recommended maintenance jobs:
- embedding refresh
- dedupe audit
- supersession audit
- stale memory review
- broken link audit
- retrieval quality evaluation
- index consistency audit
- compression refresh
- quarantine review

Maintenance rules:
- maintenance may improve indexes and labels
- maintenance must not silently rewrite memory meaning
- maintenance must not repair truth
- maintenance must remain scoped and auditable

---

## 18. Observability

Observe memory without letting telemetry become semantics.

Recommended write metrics:
- candidate creation count
- write outcome counts by type and scope
- reject reasons by code
- defer reasons by code
- duplicate rejection rate
- supersession count
- merge count
- indexing backlog count

Recommended retrieval metrics:
- retrieval count by purpose
- latency by purpose and profile
- lexical hit ratio
- semantic hit ratio
- explicit-link hit ratio
- duplicate suppression count
- contradiction-labeled return rate
- average returned memory count

Recommended maintenance metrics:
- stale active memory count
- orphan link count
- missing embedding count
- quarantined memory count

---

## 19. Failure handling

### 19.1 Write failures
- validation failure -> reject candidate
- dedupe ambiguity -> defer or quarantine
- commit failure -> no `memory_id`, no partial semantic record
- index failure after commit -> record committed, mark index backlog state

### 19.2 Retrieval failures
- vector backend down -> degrade to lexical + explicit-link retrieval
- lexical index unavailable -> explicit-link + semantic retrieval if safe
- reranker failure -> fallback to transparent base scoring
- over-budget result set -> trim aggressively, do not dump

### 19.3 Integrity failures
- broken lineage -> quarantine affected rows from default retrieval
- wrong-project leakage -> hard fail
- state conflict surge -> keep retrieval support-only and surface contradictions, never patch truth

---

## 20. Security and isolation

Hard rules:
- all memory reads and writes require explicit `project_id`
- cross-project retrieval is blocked by default
- maintenance jobs may not cross project boundaries unless purely structural
- any user-facing display must keep memory labeled as memory/support
- external retrieval backends receive only the minimum retrieval projection needed

---

## 21. Test strategy

Minimum required test families:

### 21.1 Unit tests
- candidate validation
- type assignment
- scope assignment
- compression output shape
- dedupe rules
- conflict labeling
- reranking
- budget trimming

### 21.2 Integration tests
- write pipeline end to end against PostgreSQL
- retrieval pipeline with lexical + semantic + explicit-ref merging
- supersession and merge behavior
- link integrity to research artifacts and knowledge artifacts
- index consistency behaviors
- maintenance job behaviors

### 21.3 Invariant tests
- only Memory creates candidates
- only committed `memory_id` can be canonically referenced
- memory never overrides state
- wrong-project retrieval blocked
- research artifacts do not become memory automatically
- compiled-knowledge artifacts do not become memory automatically
- superseded memory does not outrank active replacement by default
- raw residue cannot be committed

### 21.4 Failure-path tests
- duplicate memory buildup pressure
- stale memory vs fresh truth
- vector backend unavailable
- missing links
- malformed candidate payload
- index backlog after commit
- quarantine behavior

### 21.5 Evaluation tests
- retrieval quality by purpose profile
- contradiction surfacing
- duplicate suppression
- packaged context size control

---

## 22. Rollout plan

### Phase M1 - Minimal bounded memory core
- committed memory record model
- write pipeline
- simple store
- scope-safe retrieval
- truth-separation tests

### Phase M2 - Better indexing and provenance linkage
- FTS
- pgvector
- memory claims / points
- richer support linking
- research / knowledge artifact thin-link support

### Phase M3 - Research-aware and knowledge-aware handoff
- lawful input from research artifacts and history records
- lawful input from compiled-knowledge artifacts
- rejection rules for archive-dump attempts
- stronger link vocabulary

### Phase M4 - Maintenance and quality improvement
- re-embedding
- conflict refresh
- duplicate cluster cleanup
- retrieval quality audits

### Phase M5 - Future richer retrieval adapters
- Qdrant adapter if needed
- optional relation-aware expansion
- stronger ranking experiments under Jeff-owned semantics

---

## 23. Sharp implementation rules

1. Do not store everything.
2. Do not let arbitrary modules commit memory.
3. Do not let memory answer current-truth questions ahead of state.
4. Do not let memory absorb research history.
5. Do not let memory absorb compiled knowledge.
6. Do not use one giant blob table as fake architecture.
7. Do not dump top-k vectors into context.
8. Do not allow superseded memory to remain silently co-equal in retrieval.
9. Do not let external backends own semantics.
10. Do not broaden scope for convenience.
11. Do not erase provenance.
12. Do not let maintenance jobs rewrite meaning silently.

---

## 24. Final recommendation

The Memory layer should be built as a Jeff-owned, layered system:

```text
PostgreSQL authoritative memory store
+ pgvector lexical/semantic hybrid retrieval
+ Jeff write pipeline
+ Jeff retrieval pipeline
+ Jeff maintenance jobs
+ thin links to research artifacts and compiled knowledge
+ optional future adapters behind strict interfaces
```

That gives Jeff:
- durable continuity without fake truth
- retrieval quality without dump behavior
- clean separation from research history
- clean separation from compiled knowledge
- auditability without heavy bureaucracy
- scale-up options without semantic surrender

If these boundaries stay hard, Memory becomes a force multiplier.
If they soften, it becomes sludge.
