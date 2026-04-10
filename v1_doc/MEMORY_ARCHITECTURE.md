# MEMORY_ARCHITECTURE.md

Status: implementation architecture proposal for Jeff Memory  
Authority: subordinate to `MEMORY_SPEC.md`, `CONTEXT_SPEC.md`, `CORE_SCHEMAS_SPEC.md`, `ARCHITECTURE.md`, `STATE_MODEL_SPEC.md`, and `TESTS_PLAN.md`  
Purpose: define a concrete buildable architecture for Jeff's Memory layer without changing canonical memory law

---

## 1. Why this document exists

Jeff already has canonical memory law. That law is the hard boundary:
- memory is durable non-truth continuity
- memory is selective, structured, and support-oriented
- only Memory creates memory candidates
- only committed `memory_id` values may be referenced canonically
- current truth lives in canonical state, not in memory
- context reads truth first and memory second
- project remains the hard isolation boundary

This document does not redefine those rules. It turns them into a concrete implementation architecture:
- storage layout
- record schema
- write pipeline
- retrieval pipeline
- maintenance jobs
- interfaces
- observability
- tests
- rollout

---

## 2. Design goals

### 2.1 Hard goals
1. Preserve continuity without creating a rival truth layer.
2. Keep memory selective enough to avoid sludge.
3. Keep retrieval scoped, bounded, and useful for concrete Jeff actions.
4. Keep provenance inspectable.
5. Make upgrades possible without changing Jeff semantics.
6. Make memory failure degrade usefulness, not integrity.
7. Keep the system compatible with future richer retrieval backends.

### 2.2 Non-goals
1. Remembering everything.
2. Using memory as hidden state repair.
3. Letting a framework or vector store own Jeff semantics.
4. Building a giant graph-first system in v1.
5. Making memory the default answer to current-truth questions.
6. Building universal autonomous self-rewriting memory logic.

---

## 3. Recommended stack

## 3.1 v1 stack
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
- low operational complexity
- easy hybrid retrieval: SQL filter + full-text + vector similarity

## 3.2 v1.5 or v2 optional additions
- Qdrant as an optional external vector retrieval backend behind a Jeff adapter
- Graphiti or another temporal graph system as an optional specialized relationship and time-aware retrieval layer
- LlamaIndex as an optional retrieval/query/workflow helper in Infrastructure, never as owner of Jeff Memory semantics
- Zep only as an external benchmark or experiment source, never as Jeff's semantic owner

## 3.3 What remains Jeff-owned no matter what backend is used
- memory type law
- candidate creation law
- acceptance/reject/defer law
- scope rules
- truth conflict handling
- context assembly rules
- linking semantics
- supersession semantics
- maintenance policy

---

## 4. Memory layer responsibilities

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
- evaluation semantics
- orchestration routing semantics
- interface semantics

---

## 5. High-level architecture

```text
Upstream support inputs
(research, outcome, evaluation, operator cues, artifact refs)
        |
        v
+-----------------------------+
| Memory Candidate Builder    |
+-----------------------------+
        |
        v
+-----------------------------+
| Validation + Dedupe         |
| Type + Scope Assignment     |
| Compression                 |
+-----------------------------+
        |
        +------------------> reject / defer
        |
        v
+-----------------------------+
| Commit Store (PostgreSQL)   |
| - records                   |
| - claims                    |
| - links                     |
| - lineage                   |
| - audits                    |
+-----------------------------+
        |
        +------------------> Indexer
        |                    - FTS
        |                    - pgvector
        |                    - optional future adapters
        |
        v
+-----------------------------+
| Retrieval Engine            |
| - explicit refs             |
| - lexical                   |
| - semantic                  |
| - optional relation expand  |
| - rerank                    |
| - bounded result packaging  |
+-----------------------------+
        |
        v
+-----------------------------+
| Context Assembly Consumer   |
| (truth first, memory second)|
+-----------------------------+
        |
        v
Jeff context package
```

---

## 6. Core implementation decisions

## 6.1 Scope model
Primary write scope in v1:
- `project_id` is required
- `work_unit_id` is optional but strongly recommended when the memory is materially local to one work unit
- `run_id` is optional but strongly recommended when the memory is materially tied to one run
- every committed memory has exactly one primary scope
- cross-project writes are forbidden in v1
- global/system memory is deferred

## 6.2 Type model
Each committed memory record has exactly one primary type:
- `episodic`
- `semantic`
- `directional`
- `operational`

Optional secondary tags may exist for retrieval tuning, but they do not replace primary type.

## 6.3 Memory identity
- `memory_id` is a Jeff-issued opaque string
- no external backend ID becomes semantic authority
- external backend identifiers may be stored as implementation linkage only

## 6.4 Truth conflict posture
When state and memory disagree:
- state wins
- memory may still be retrieved, but only as contradiction/stale/mismatch support
- retrieval output must keep conflict labeling explicit
- no automatic truth repair is performed by memory

## 6.5 Storage strategy
Use one normalized authoritative schema in PostgreSQL.
Do not store memory as one giant JSON blob table only.
Use JSON only for bounded flexible fields, not for the entire model.

---

## 7. Canonical implementation modules inside Memory

Recommended Python package layout:

```text
src/jeff/memory/
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

Module purposes:
- `candidate_builder.py`: build candidate objects from lawful support inputs
- `validator.py`: enforce hard write rules
- `dedupe.py`: detect duplicates and low incremental value
- `type_assigner.py`: select one primary memory type
- `scope_assigner.py`: enforce project/work_unit/run scope rules
- `compressor.py`: produce concise, retrievable committed form
- `store.py`: persistence, commit, read, audit
- `linker.py`: support links, related-memory links, supersession links
- `indexer.py`: maintain FTS/vector/optional external indexes
- `retrieval.py`: retrieve bounded support sets
- `reranker.py`: merge lexical, semantic, and explicit-ref candidates
- `conflict_labeler.py`: label stale/conflicting memory against current truth
- `maintenance.py`: scheduled repair, cleanup, reindex, audits
- `telemetry.py`: metrics and trace-safe events
- `api.py`: Memory module public contract

---

## 8. MEMORY_RECORD_SCHEMA

This section defines the buildable committed record shape.

## 8.1 Core committed record fields

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

## 8.2 Required record rules
- `summary` must be concise and one memory-sized unit, not a report
- `remembered_points` must be bounded and individually inspectable
- `why_it_matters` is required
- `support_quality` is not probability of truth; it is support strength for reuse
- `stability` expresses how likely the memory is to remain useful without revision
- `status` defaults to `active`
- `conflict_posture` defaults to `none`
- raw logs, prompts, trace dumps, and article bodies are forbidden

## 8.3 Claim model
Some memory records need claim-level inspection. Support this with a separate claim table rather than hiding everything in prose.

Each claim row should include:
- `memory_claim_id`
- `memory_id`
- `claim_text`
- `claim_kind`: `fact | lesson | rationale | caution | pattern`
- `claim_support_quality`
- `claim_conflict_posture`
- `claim_order`

Reason:
- better provenance
- better contradiction handling
- better future graph projection
- cleaner retrieval snippets

## 8.4 Link model
Every committed memory should have typed links.

Required:
- one primary scope link through `project_id`
- zero or one local `work_unit_id`
- zero or one local `run_id`

Optional:
- artifact links
- source refs
- evidence refs
- related committed memory links
- supersedes/superseded-by links

## 8.5 Lineage model
Support explicit lineage:
- `supersedes_memory_id`
- `superseded_by_memory_id`
- `merged_into_memory_id`
- `derived_from_candidate_id`
- `derived_from_run_id`

---

## 9. Physical storage schema

Recommended PostgreSQL tables.

## 9.1 `memory_records`
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

Indexes:
- `(project_id, status, memory_type)`
- `(project_id, work_unit_id, status)`
- `(project_id, run_id, status)`
- `(project_id, updated_at desc)`
- partial index on active rows

## 9.2 `memory_points`
Bounded remembered points or compressed claim-like payload.

Suggested columns:
- `memory_point_id bigserial primary key`
- `memory_id text not null`
- `point_order integer not null`
- `point_text text not null`
- `point_kind text not null`
- `support_quality text not null`
- `conflict_posture text not null default 'none'`

## 9.3 `memory_claims`
Optional stricter claim-level rows when needed.

Suggested columns:
- `memory_claim_id text primary key`
- `memory_id text not null`
- `claim_order integer not null`
- `claim_text text not null`
- `claim_kind text not null`
- `claim_support_quality text not null`
- `claim_conflict_posture text not null`

## 9.4 `memory_links`
Typed links from memory to support objects.

Suggested columns:
- `memory_link_id bigserial primary key`
- `memory_id text not null`
- `link_type text not null`
- `linked_object_type text not null`
- `linked_object_id text null`
- `locator text null`
- `project_id text null`
- `work_unit_id text null`
- `run_id text null`
- `metadata_json jsonb not null default '{}'::jsonb`

Expected `link_type` values:
- `artifact_support`
- `source_support`
- `evidence_support`
- `related_memory`
- `supersedes`
- `superseded_by`
- `derived_from`

## 9.5 `memory_embeddings`
Embedding storage and versioning.

Suggested columns:
- `memory_embedding_id bigserial primary key`
- `memory_id text not null`
- `embedding_model_id text not null`
- `embedding_profile_id text not null`
- `embedding vector(...) not null`
- `embedding_dim integer not null`
- `is_primary boolean not null default true`
- `created_at timestamptz not null`

Rules:
- one primary active embedding per retrieval profile in v1
- allow additional embeddings for migration
- do not overwrite old embeddings during rollout; dual-write then cut over

## 9.6 `memory_candidates`
Pre-commit candidate staging.

Suggested columns:
- `candidate_id text primary key`
- `project_id text not null`
- `work_unit_id text null`
- `run_id text null`
- `candidate_payload jsonb not null`
- `candidate_source_summary jsonb not null`
- `candidate_status text not null`
- `rejection_reason_code text null`
- `defer_reason_code text null`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`

Candidate statuses:
- `proposed`
- `validated`
- `rejected`
- `deferred`
- `committed`
- `superseded`

## 9.7 `memory_write_events`
Audit trail for write decisions.

Suggested columns:
- `memory_write_event_id bigserial primary key`
- `candidate_id text null`
- `memory_id text null`
- `event_type text not null`
- `event_payload jsonb not null`
- `created_at timestamptz not null`

Expected event types:
- `candidate_created`
- `candidate_validated`
- `candidate_rejected`
- `candidate_deferred`
- `candidate_committed`
- `memory_superseded`
- `memory_merged`
- `indexing_completed`

## 9.8 `memory_retrieval_events`
Retrieval audit and evaluation surface.

Suggested columns:
- `memory_retrieval_event_id bigserial primary key`
- `project_id text not null`
- `work_unit_id text null`
- `run_id text null`
- `purpose text not null`
- `query_text text null`
- `profile_id text not null`
- `budget_profile_id text not null`
- `candidate_count integer not null`
- `returned_count integer not null`
- `latency_ms integer not null`
- `result_payload jsonb not null`
- `created_at timestamptz not null`

## 9.9 `memory_maintenance_jobs`
Scheduled or manual maintenance job registry.

Suggested columns:
- `job_id text primary key`
- `job_type text not null`
- `target_scope_json jsonb not null`
- `job_status text not null`
- `job_payload jsonb not null`
- `started_at timestamptz null`
- `finished_at timestamptz null`

---

## 10. Write-time source inputs

Upstream stages may inform memory, but they do not author memory.

Allowed support inputs:
- research findings and recommendation context
- execution residue
- outcome object and evidence refs
- evaluation verdict and rationale
- operator-marked importance cues
- current-truth refs that explain continuity relevance
- artifacts and source refs with provenance

Forbidden as direct memory commits:
- raw chat transcript dumps
- full trace dumps
- full log dumps
- prompt bodies
- arbitrary interface text
- direct writes from non-Memory modules
- state snapshots copied into memory without continuity value

---

## 11. MEMORY_WRITE_PIPELINE

The write pipeline must be deterministic enough to audit and conservative enough to reject junk.

## 11.1 Pipeline overview

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

## 11.2 Step 1: candidate creation
Input:
- bounded support inputs
- explicit scope
- current truth refs when relevant
- reason this might matter later

Output:
- `memory_candidate`

Rules:
- selective, not automatic
- one candidate should express one memory-sized continuity unit
- split muddled multi-role candidates into multiple candidates
- no `memory_id` is assigned yet

Recommended candidate fields:
- `candidate_id`
- `project_id`
- `work_unit_id`
- `run_id`
- `proposed_summary`
- `proposed_points`
- `proposed_why_it_matters`
- `candidate_sources`
- `candidate_origin_kind`
- `candidate_priority_hint`

## 11.3 Step 2: candidate validation
Checks:
- required fields present
- source linkage exists
- not raw residue
- not current-truth duplication only
- not wrong scope
- concise enough for retrieval
- provenance is inspectable

Hard reject examples:
- vague generic statements
- duplicated report prose
- unsupported "important insight"
- missing source links
- current truth copied into memory with no continuity value

## 11.4 Step 3: dedupe and incremental-value check
Purpose:
- stop sludge
- stop near duplicates
- stop weak add-ons

Dedupe should use:
- exact signature match
- lexical overlap
- semantic similarity
- same scope + same type + same source cluster
- same core claim set

Recommended decisions:
- `reject_duplicate`
- `merge_into_existing`
- `supersede_existing`
- `continue_new_record`

Rules:
- merge only if inspectability is preserved
- supersede when new memory is materially better or newer
- prefer false negatives over polluted memory

## 11.5 Step 4: type assignment
Assign exactly one primary type.

Heuristics:
- `episodic`: bounded event/case/episode
- `semantic`: durable general conclusion or pattern
- `directional`: strategic boundary, anti-drift lesson, non-goal, direction anchor
- `operational`: practical repeatable working lesson or procedure

Failure mode:
- if the candidate spans more than one primary role, split it

## 11.6 Step 5: scope assignment
Rules:
- project scope required
- narrower locality attached when justified
- do not over-promote run-local memory into project-wide importance unless it clearly generalizes
- do not broaden scope for retrieval convenience

Recommended outcomes:
- `project_only`
- `project_with_work_unit_locality`
- `project_with_run_locality`
- `project_with_work_unit_and_run_locality`

## 11.7 Step 6: compression
Purpose:
- make the record retrievable
- prevent giant prose blobs

Compression output should include:
- concise summary
- bounded points
- why it matters
- support quality
- stability
- freshness sensitivity
- explicit links

Compression rules:
- do not erase nuance needed for later inspection
- do not turn contradiction into certainty
- do not strip provenance
- do not paraphrase away decisive caution

## 11.8 Step 7: accept / reject / defer
Possible outcomes:
- `write`
- `reject`
- `defer`
- `merge_into_existing`
- `supersede_existing`

Recommended decision criteria:
- write: durable, grounded, concise, useful again
- reject: weak, vague, duplicative, wrong scope, wrong shape
- defer: maybe useful, not strong enough yet
- merge: clear additive enrichment to an existing memory
- supersede: new record should replace previous active record

## 11.9 Step 8: commit and storage
Commit creates:
- authoritative `memory_record`
- child points/claims
- support links
- lineage links
- write audit row

Commit rules:
- atomic per memory write
- no partial commit
- `memory_id` issued only here
- committed rows must be readable before indexing completes
- failed indexing must not roll back committed semantics, but must set index backlog state

## 11.10 Step 9: indexing
Index after commit:
- PostgreSQL FTS document
- pgvector embedding row
- optional future external backend row
- optional future graph projection queue

Indexing rules:
- index build is part of successful write flow, but may complete asynchronously if explicitly tracked
- retrieval must suppress non-indexed rows for search modes that depend on indexing, unless explicit direct ID fetch is used
- direct ID fetch may still read committed memory before full index completion

## 11.11 Step 10: linking
Write/selective links:
- source refs
- artifact refs
- related memory refs
- supersession refs
- project/work_unit/run locality

Do not generate relation spam.

---

## 12. Candidate scoring and acceptance policy

Use an explicit scoring sheet inside the write pipeline.

Recommended dimensions:
- continuity value
- support strength
- specificity
- reusability
- scope correctness
- novelty
- compactness
- provenance completeness

Recommended acceptance posture:
- score high and clean: write
- medium with gaps: defer
- low or dirty: reject

Do not treat the numeric score as law.
Use it as structured support for bounded write decisions.

---

## 13. LLM role in write pipeline

LLM can help with:
- candidate extraction
- memory compression
- type suggestions
- dedupe explanations
- supersession suggestion text

LLM does not get to:
- commit directly
- override hard validation
- broaden scope silently
- bypass reject/defer outcomes
- define truth
- author canonical links to state

Recommended model usage:
- smaller fast model for candidate extraction and compression
- stronger model only for ambiguous dedupe/supersession decisions or complex contradiction framing

---

## 14. MEMORY_RETRIEVAL_PIPELINE

Retrieval exists to supply bounded support for a concrete purpose.

## 14.1 Retrieval input contract
Every retrieval request must include:
- `purpose`
- `project_id`
- optional `work_unit_id`
- optional `run_id`
- `query_text` or `query_embedding_basis`
- `budget_profile_id`
- optional `required_memory_types`
- optional `freshness_sensitivity`
- optional `explicit_memory_ids`

Suggested purposes:
- `context_for_research`
- `context_for_proposal`
- `context_for_selection`
- `context_for_planning`
- `context_for_evaluation_review`
- `context_for_operator_explanation`
- `memory_inspection`
- `maintenance_audit`

## 14.2 Retrieval order of operations

```text
1. confirm scope and purpose
2. receive truth anchor from context assembly caller
3. explicit linked memory fetch
4. scoped lexical retrieval
5. scoped semantic retrieval
6. optional relation expansion
7. dedupe
8. rerank
9. conflict labeling against truth anchor
10. budget trim
11. package output
```

Important:
- memory retrieval does not read truth in place of Context
- Context reads truth first and passes relevant truth anchor/constraints into retrieval
- retrieval remains support-only

## 14.3 Retrieval stages

### Stage A: explicit linked memory fetch
First retrieve memory explicitly linked from:
- project truth
- work-unit truth
- run truth
- directly requested memory IDs

These explicit refs get priority because their linkage itself is current operational truth.

### Stage B: lexical retrieval
Use PostgreSQL full-text search over:
- summary
- points
- claims
- why_it_matters

Use lexical retrieval for:
- exact names
- error codes
- terminology
- decisions
- design terms
- identifiers

### Stage C: semantic retrieval
Use pgvector similarity over embedding-bearing text representation of:
- summary + points + why_it_matters

Use semantic retrieval for:
- concept similarity
- lesson reuse
- analogous episodes
- similar operational patterns

### Stage D: optional relation expansion
Future optional step:
- expand one hop through `related_memory`, `supersedes`, or explicit dependency-style links
- only after a strong seed set exists
- hard cap expansion size

### Stage E: dedupe
Collapse:
- near duplicates
- active + superseded pairs where active should dominate
- multiple hits from same memory through different retrieval modes

### Stage F: rerank
Recommended reranking factors:
- exact scope fit
- purpose relevance
- support quality
- stability
- freshness fit
- contradiction salience
- explicit linkage bonus
- type fit
- novelty vs redundancy

### Stage G: conflict labeling
Compare candidates with current truth anchor.
Label each included memory as:
- `aligned_support`
- `stale_support`
- `contradiction_support`
- `mismatch_support`

### Stage H: budget trim
Use hard caps:
- max returned memories
- max returned points
- max returned claims
- max total tokens/characters for context use

### Stage I: package output
Return a bounded, source-labeled support set.

## 14.4 Retrieval scoring formula

Use a transparent weighted score, for example:

```text
final_score =
  scope_score
+ explicit_link_bonus
+ lexical_score
+ semantic_score
+ support_quality_score
+ stability_score
+ freshness_fit_score
+ purpose_fit_score
+ contradiction_salience_bonus
- redundancy_penalty
- superseded_penalty
```

This does not need to be frozen as one exact formula, but it must remain inspectable and tunable.

## 14.5 Retrieval budgets
Define named budget profiles.

Suggested profiles:
- `tiny`: 2 to 4 memories, operator quick answer
- `small`: 4 to 8 memories, normal context build
- `medium`: 8 to 12 memories, research/evaluation review
- `inspection`: up to 20 memories, human review only, not default model context
- `audit`: bounded maintenance/debug use only

Default model-facing profile in v1 should be `small`.

## 14.6 Retrieval output schema

```json
{
  "purpose": "context_for_selection",
  "scope": {
    "project_id": "proj_...",
    "work_unit_id": "wu_... | null",
    "run_id": "run_... | null"
  },
  "returned_memories": [
    {
      "memory_id": "mem_...",
      "memory_type": "operational",
      "summary": "....",
      "remembered_points": ["..."],
      "why_it_matters": "...",
      "support_quality": "strong",
      "stability": "stable",
      "conflict_posture": "none",
      "retrieval_reason": "same work unit + lexical + semantic",
      "support_links": [
        {"linked_object_type": "artifact", "linked_object_id": "artifact_..."}
      ]
    }
  ],
  "excluded_due_to_budget": 3,
  "warnings": [],
  "telemetry": {}
}
```

## 14.7 Cross-project retrieval
Default:
- forbidden in v1

Future:
- only through explicit canonical promotion or tightly governed global memory policy
- never as casual fallback because local project memory was weak

---

## 15. Context assembly interaction

Memory is not context assembly, but retrieval must be designed for it.

The Context layer should:
1. determine purpose
2. determine scope
3. read truth first
4. determine governance-relevant current truth if needed
5. ask Memory for bounded support
6. receive source-labeled memory results
7. combine truth + memory + evidence without collapsing their classes

Memory must therefore expose retrieval results that are:
- bounded
- source-labeled
- conflict-labeled
- scope-explicit
- concise enough for direct inclusion in context packages

---

## 16. MEMORY_MAINTENANCE_JOBS

Memory without maintenance rots into sludge.

## 16.1 Job family overview
Recommended recurring jobs:
1. embedding refresh
2. dedupe audit
3. supersession audit
4. stale memory review
5. broken link audit
6. retrieval quality evaluation
7. index consistency audit
8. compression refresh
9. quarantine review
10. archival/reporting jobs

## 16.2 `embedding_refresh`
Purpose:
- migrate to new embedding model/profile
- preserve retrieval quality

Steps:
1. select target scope
2. compute new embeddings
3. dual-write old + new
4. run retrieval eval set
5. cut over primary embedding profile only after passing eval thresholds
6. keep old embeddings temporarily for rollback
7. prune old profile later

## 16.3 `dedupe_audit`
Purpose:
- detect duplicate buildup missed at write time

Checks:
- lexical near duplicates
- semantic near duplicates
- same-support-cluster duplicates
- multiple active records that look equivalent

Outcomes:
- no-op
- suggest merge
- suggest supersession
- quarantine for human review

## 16.4 `supersession_audit`
Purpose:
- detect older active memories that should no longer be primary

Candidates:
- old operational lesson replaced by better current procedure
- semantic lesson updated by stronger evidence
- directional lesson clarified by later operator decision
- episodic memory compressed into stronger generalized semantic memory

## 16.5 `stale_memory_review`
Purpose:
- downgrade or relabel stale memory when reuse quality has decayed

Checks:
- freshness-sensitive memories that have aged out
- memory repeatedly retrieved but repeatedly discarded after rerank
- memory conflicting with new truth often enough to stop default active use

Possible outcomes:
- keep active
- relabel as `stale_support`
- deprecate
- supersede
- quarantine

## 16.6 `broken_link_audit`
Purpose:
- maintain inspectability and provenance

Checks:
- missing artifact refs
- missing source refs
- broken related-memory refs
- invalid lineage chains

## 16.7 `retrieval_quality_evaluation`
Purpose:
- measure whether retrieval is getting better or worse

Requires:
- curated eval prompts
- expected relevant memory IDs or relevance judgments
- metrics by purpose profile

Track:
- precision@k
- recall@k where labels exist
- contradiction surfacing quality
- duplicate suppression quality
- latency
- token cost of packaged results

## 16.8 `index_consistency_audit`
Purpose:
- ensure store and indexes agree

Checks:
- committed memories missing embeddings
- embeddings for nonexistent memories
- FTS doc missing
- primary embedding profile mismatch
- Qdrant shadow index drift if future adapter exists

## 16.9 `compression_refresh`
Purpose:
- improve concise committed form without changing semantics

Use only when:
- extractor/compressor improved materially
- summaries are too verbose or too weak

Rules:
- preserve lineage
- preserve links
- create new version or audit event
- do not silently overwrite meaning

## 16.10 `quarantine_review`
Purpose:
- hold dirty or suspicious memories out of normal retrieval

Reasons to quarantine:
- severe contradiction
- broken provenance
- malformed record
- unsafe merge state
- unresolved migration anomaly

Quarantined memories:
- remain inspectable
- are excluded from default retrieval
- do not become canonically linked by new writes

---

## 17. Optional future graph projection

This is explicitly future-facing and not required for v1.

Graph projection should be generated from committed memory, not from raw chat or traces.

Possible graph projection sources:
- memory claims
- memory-to-memory relations
- memory-to-artifact/source links
- temporal validity or supersession lineage

Use cases:
- relation-aware retrieval
- time-aware fact lookup
- contradiction/supersession visualization
- dependency and rationale tracing

Rules:
- graph remains downstream of committed memory
- graph never becomes canonical truth by itself
- graph results remain support, not truth

---

## 18. Optional future external backend adapters

## 18.1 Qdrant adapter
Use when:
- retrieval scale or latency requires a dedicated vector store
- multiple embedding profiles or large corpora make PostgreSQL-only retrieval painful

Adapter law:
- PostgreSQL remains authoritative for memory semantics and metadata
- Qdrant stores retrieval projection only
- adapter IDs never replace `memory_id`
- retrieval merges Qdrant results back into Jeff-scoped candidate sets

## 18.2 LlamaIndex adapter
Use when:
- Jeff wants faster experimentation for retrieval pipelines, reranking, or research-specific query flows

Adapter law:
- LlamaIndex may orchestrate retrieval helpers
- LlamaIndex may not own Jeff's memory law
- committed memory records stay in Jeff-owned schema
- retrieval output must still satisfy Jeff retrieval contracts

## 18.3 Zep/Graph memory experiments
Use only as:
- benchmark
- experiment
- optional sidecar for specialized graph/context problems

Do not use as:
- canonical store
- canonical write pipeline
- owner of scope, type, or truth semantics

---

## 19. Public module API

Expose two main public contracts.

## 19.1 Write contract

### Request
```json
{
  "module": "memory",
  "scope": {
    "project_id": "proj_...",
    "work_unit_id": "wu_... | null",
    "run_id": "run_... | null"
  },
  "payload": {
    "purpose": "memory_write_from_evaluation",
    "support_inputs": [],
    "write_policy_profile_id": "default"
  },
  "metadata": {}
}
```

### Result
```json
{
  "module": "memory",
  "scope": {
    "project_id": "proj_...",
    "work_unit_id": "wu_... | null",
    "run_id": "run_... | null"
  },
  "module_call_status": "succeeded",
  "result": {
    "write_outcome": "write | reject | defer | merge_into_existing | supersede_existing",
    "memory_id": "mem_... | null",
    "candidate_id": "cand_...",
    "reasons": [],
    "warnings": []
  },
  "validation_errors": [],
  "warnings": [],
  "telemetry": {},
  "metadata": {}
}
```

## 19.2 Retrieval contract

### Request
```json
{
  "module": "memory",
  "scope": {
    "project_id": "proj_...",
    "work_unit_id": "wu_... | null",
    "run_id": "run_... | null"
  },
  "payload": {
    "purpose": "context_for_proposal",
    "query_text": "string",
    "budget_profile_id": "small",
    "required_memory_types": [],
    "explicit_memory_ids": []
  },
  "metadata": {}
}
```

### Result
```json
{
  "module": "memory",
  "scope": {
    "project_id": "proj_...",
    "work_unit_id": "wu_... | null",
    "run_id": "run_... | null"
  },
  "module_call_status": "succeeded",
  "result": {
    "returned_memories": [],
    "excluded_due_to_budget": 0,
    "warnings": [],
    "telemetry": {}
  },
  "validation_errors": [],
  "warnings": [],
  "telemetry": {},
  "metadata": {}
}
```

---

## 20. Observability

Observe memory without letting telemetry become semantics.

Recommended write metrics:
- candidate creation count
- write outcome counts by type and scope
- reject reasons by code
- defer reasons by code
- duplicate rejection rate
- supersession count
- merge count
- average summary length
- average points per record
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
- average packaged token count

Recommended maintenance metrics:
- stale active memory count
- orphan link count
- missing embedding count
- quarantined memory count
- eval precision/recall trends

Trace-safe observability events:
- write pipeline stage transitions
- retrieval stage transitions
- maintenance job start/finish
- cutover events for embeddings/index profiles

---

## 21. Failure handling

## 21.1 Write failures
- validation failure -> reject candidate
- dedupe ambiguity -> defer or quarantine
- commit failure -> no `memory_id`, no partial record
- index failure after commit -> record committed, mark index backlog state, suppress from search modes until indexing repaired

## 21.2 Retrieval failures
- vector backend down -> degrade to lexical + explicit-link retrieval
- lexical index unavailable -> explicit-link + semantic retrieval if safe
- reranker failure -> fallback to transparent base scoring
- over-budget result set -> trim aggressively, log it, do not dump

## 21.3 Integrity failures
- broken lineage -> quarantine affected rows from default retrieval
- wrong-project leakage -> hard fail and alert
- state conflict surge -> keep retrieval support-only and surface contradictions, never patch truth

---

## 22. Security and isolation

Hard rules:
- all memory reads and writes require explicit `project_id`
- cross-project retrieval is blocked by default
- maintenance jobs may not cross project boundaries unless they are purely structural and do not surface cross-project content together
- external vector stores receive only the minimum retrieval projection needed
- any user-facing display must keep memory labeled as memory/support

---

## 23. Test strategy for Memory implementation

Minimum required test families:

## 23.1 Unit tests
- candidate validation
- type assignment
- scope assignment
- compression output shape
- dedupe rules
- conflict labeling
- reranking
- budget trimming

## 23.2 Integration tests
- write pipeline end to end against PostgreSQL
- retrieval pipeline with lexical + semantic + explicit ref merging
- supersession and merge behavior
- index consistency behaviors
- maintenance job behaviors

## 23.3 Invariant tests
- only Memory creates candidates
- only committed `memory_id` can be canonically referenced
- memory never overrides state
- wrong-project retrieval blocked
- superseded memory does not outrank active replacement by default
- raw residue cannot be committed

## 23.4 Failure-path tests
- duplicate memory buildup pressure
- stale memory vs fresh truth
- vector backend unavailable
- missing links
- malformed candidate payload
- index backlog after commit
- quarantine behavior

## 23.5 Evaluation tests
- retrieval quality by purpose profile
- contradiction surfacing
- duplicate suppression
- packaged context size control

---

## 24. Rollout plan

## Phase A: v1 minimum
Build:
- PostgreSQL committed store
- pgvector
- memory_records / points / links / embeddings / candidates / write_events / retrieval_events
- write pipeline
- retrieval pipeline
- maintenance jobs: embedding refresh, dedupe audit, broken link audit, index consistency audit
- test suite
- operator inspection surface later through CLI

## Phase B: v1 hardening
Add:
- claim table
- supersession audit
- stale memory review
- retrieval eval harness
- quarantine path
- explicit budget profiles
- better conflict labeling

## Phase C: v1.5
Optional:
- Qdrant adapter
- LlamaIndex retrieval experiment adapter
- stronger reranking
- memory quality scoring improvements

## Phase D: v2
Optional:
- graph projection
- richer temporal retrieval
- multi-profile retrieval tuning
- stronger memory review workflows
- richer operator memory inspection surfaces

---

## 25. Sharp implementation rules

1. Do not store everything.
2. Do not let memory commit itself from arbitrary modules.
3. Do not let memory answer current-truth questions ahead of state.
4. Do not use one giant blob table as a fake architecture.
5. Do not dump top-k vectors into context.
6. Do not allow superseded memory to remain silently co-equal in retrieval.
7. Do not let external backends own semantics.
8. Do not broaden scope for convenience.
9. Do not erase provenance.
10. Do not let maintenance jobs rewrite meaning silently.

---

## 26. Final recommendation

The Memory layer should be built as a Jeff-owned, layered system:

```text
PostgreSQL authoritative memory store
+ pgvector lexical/semantic hybrid retrieval
+ Jeff write pipeline
+ Jeff retrieval pipeline
+ Jeff maintenance jobs
+ optional future adapters behind strict interfaces
```

That gives Jeff:
- durable continuity without fake truth
- retrieval quality without dump behavior
- auditability without heavy bureaucracy
- scale-up options without semantic surrender

If we keep these boundaries hard, Memory becomes a force multiplier.
If we soften them, it becomes sludge.
