# MEMORY_V1.md

Status: implementation specification for Jeff Memory v1  
Authority: subordinate to `MEMORY_SPEC_NEW.md`, `MEMORY_ARCHITECTURE_NEW.md`, `RESEARCH_HISTORY_AND_ARCHIVE_ARCHITECTURE.md`, `KNOWLEDGE_LAYER_ARCHITECTURE.md`, `CONTEXT_SPEC.md`, `CORE_SCHEMAS_SPEC.md`, `STATE_MODEL_SPEC.md`, `PROJECT_AND_WORK_UNIT_MODEL_SPEC.md`, `TRANSITION_MODEL_SPEC.md`, `ARCHITECTURE.md`, and `TESTS_PLAN.md`  
Purpose: define the concrete implementation target for Jeff Memory v1 so a coding model can build it without reopening core design decisions

---

## 1. Why this document exists

Jeff already has canonical memory law and a broader memory architecture direction.
What still needs to be frozen for implementation is the **v1 executable target**:
- what gets built now
- what is explicitly forbidden now
- which open-source components are used now
- which file/module layout is expected now
- how write, retrieval, linking, and maintenance behave now
- how Memory integrates with Research Archive, Compiled Knowledge, Context, and Core now

This document is not a new semantic owner.
It is the concrete build spec for Memory v1.

---

## 2. Final v1 decisions

The following decisions are frozen for Memory v1.

### 2.1 Scope model
- Memory is **project-scoped only** in v1.
- Every read and write requires explicit `project_id`.
- `work_unit_id` and `run_id` are optional locality refinements, not substitutes for `project_id`.
- Cross-project writes are forbidden.
- Cross-project retrieval is forbidden.

### 2.2 Global/system memory
- Global/system memory is **hard-forbidden** in v1.
- Do not add global/system memory write surfaces.
- Do not add global/system memory retrieval surfaces.
- Do not add schema fields that imply legal global/system memory use.
- Do not add “temporary” fallback paths that behave like global memory.

### 2.3 Research / knowledge boundary
- Research History and Archive is a **Research-owned submodule**, not a Memory submodule.
- Memory may thin-link to research-owned archive objects.
- Memory may thin-link to compiled-knowledge artifacts.
- Memory must not own research artifact persistence.
- Memory must not own compiled-knowledge persistence.

### 2.4 Fixed compiled knowledge path
Compiled knowledge is frozen at:

```text
projects/<project_id>/research/knowledge/
```

Do not support a parallel `artifacts/knowledge/` path.

### 2.5 Retrieval composition
- Memory retrieval and compiled-knowledge retrieval remain **separate** in v1.
- Context Assembly composes them.
- Do not build a new top-level “unified support retrieval orchestrator” layer in v1.
- Internal helper functions inside Context are allowed.
- A new semantic owner layer is not allowed.

### 2.6 Write posture
- Default write posture is **automatic commit when the candidate is strong enough**.
- Review does **not** gate all memory writes.
- `defer` is the canonical outcome when review is required.
- `defer` must carry a machine-readable reason code, including `review_required` when applicable.

---

## 3. What Memory v1 must do

Memory v1 must:
- create Memory-owned candidates from lawful support inputs
- validate candidate quality and shape
- reject low-value or invalid candidates
- deduplicate against existing committed memory
- assign exactly one primary memory type
- assign lawful scope
- compress accepted candidates into concise committed records
- commit memory atomically enough to avoid partial semantic state
- issue committed `memory_id` only at commit
- maintain links to research archive, knowledge artifacts, source refs, evidence refs, and related memory
- support truth-first, bounded, scope-safe retrieval
- label stale/conflicting memory against current truth
- support bounded maintenance and observability

Memory v1 must not:
- define current truth
- mutate truth
- absorb research history
- absorb compiled knowledge
- store raw logs, prompt dumps, or trace dumps
- return giant memory dumps to context
- create cross-project continuity soup

---

## 4. Required open-source stack

### 4.1 Required in v1
1. **PostgreSQL**
   - authoritative persistence layer
   - stores committed records, points/claims, links, lineage, audits, retrieval bookkeeping

2. **pgvector**
   - vector extension inside PostgreSQL
   - used for semantic retrieval projection only
   - does not own semantics

3. **PostgreSQL full-text search**
   - lexical retrieval over summary, points, claims, and reason fields

### 4.2 Explicitly not required in first implementation slice
- Qdrant
- Graphiti
- LlamaIndex
- Zep
- any graph database
- any external memory SaaS

### 4.3 Allowed later only behind Jeff-owned interfaces
- Qdrant as optional external vector adapter
- Graphiti or similar temporal graph layer for future relation/time-aware retrieval
- LlamaIndex as infrastructure helper only
- Zep only as benchmark/experiment input

### 4.4 Hard rule
External tools may provide storage or retrieval capability.
They must never own:
- memory type law
- candidate creation law
- write / reject / defer semantics
- scope law
- truth-conflict handling
- research-history boundary
- compiled-knowledge boundary
- context assembly rules

---

## 5. V1 architecture shape

```text
Lawful support inputs
(research artifacts, history records, compiled-knowledge refs,
 outcome/evaluation signals, operator cues, current-truth linkage)
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
        +------------------> reject
        |
        +------------------> defer(review_required | ...)
        |
        +------------------> merge_into_existing
        |
        +------------------> supersede_existing
        |
        v
+----------------------------------+
| Commit Store (PostgreSQL)        |
| - memory_records                 |
| - memory_points                  |
| - memory_claims                  |
| - memory_links                   |
| - memory_embeddings              |
| - memory_write_events            |
+----------------------------------+
        |
        +------------------> Index maintenance
        |                    - FTS
        |                    - pgvector
        |
        v
+----------------------------------+
| Retrieval Engine                 |
| - explicit refs                  |
| - lexical                        |
| - semantic                       |
| - rerank                         |
| - conflict labeling              |
| - budget trim                    |
+----------------------------------+
        |
        v
+----------------------------------+
| Context Assembly consumer        |
| truth first, memory second       |
+----------------------------------+
```

---

## 6. Required Python package layout

```text
jeff/memory/
  __init__.py
  api.py
  ids.py
  types.py
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
```

### 6.1 Module responsibilities
- `ids.py`: Memory-owned typed IDs and helpers
- `types.py`: internal typed enums/value objects for memory type, support quality, conflict posture, write outcomes, defer reason codes
- `schemas.py`: pydantic/dataclass schemas for candidates, committed records, links, retrieval requests/results, maintenance job records
- `candidate_builder.py`: builds candidate objects from lawful inputs only
- `validator.py`: enforces hard write rules and shape rules
- `dedupe.py`: duplicate detection and incremental-value checks
- `type_assigner.py`: assigns exactly one primary type
- `scope_assigner.py`: enforces v1 project-only scope law
- `compressor.py`: compresses accepted candidates into concise committed form
- `store.py`: PostgreSQL read/write layer and transaction boundaries
- `linker.py`: support links, supersession links, merge links, related-memory links
- `indexer.py`: FTS and vector indexing hooks
- `retrieval.py`: retrieval pipeline orchestration
- `reranker.py`: merges explicit/lexical/semantic candidates into a final ordered bounded set
- `conflict_labeler.py`: compares memory against current truth anchor and labels support posture
- `maintenance.py`: re-embed, audits, stale/conflict refresh, integrity checks
- `telemetry.py`: observability events and counters
- `api.py`: stable Memory-facing contract for other Jeff modules

### 6.2 Explicitly forbidden package drift
Do not create:
- `jeff/memory/research/`
- `jeff/memory/archive/`
- `jeff/memory/knowledge/`
- any package that makes Memory the owner of research or knowledge persistence

---

## 7. Required data model

### 7.1 Committed record shape
Every committed record must contain at least:
- `memory_id`
- `memory_type`
- `project_id`
- `work_unit_id | null`
- `run_id | null`
- `summary`
- `remembered_points`
- `why_it_matters`
- `support_quality`
- `stability`
- `freshness_sensitivity`
- `status`
- `conflict_posture`
- `created_at`
- `updated_at`
- `created_from_run_id | null`
- `schema_version`

### 7.2 Fixed v1 enums

#### `memory_type`
- `episodic`
- `semantic`
- `directional`
- `operational`

#### `support_quality`
- `weak`
- `moderate`
- `strong`

#### `stability`
- `tentative`
- `stable`
- `reinforced`

#### `freshness_sensitivity`
- `low`
- `medium`
- `high`

#### `status`
- `active`
- `superseded`
- `deprecated`
- `quarantined`

#### `conflict_posture`
- `none`
- `stale_support`
- `contradiction_support`
- `mismatch_support`

#### `write_outcome`
- `write`
- `reject`
- `defer`
- `merge_into_existing`
- `supersede_existing`

#### `defer_reason_code`
At minimum:
- `review_required`
- `dedupe_ambiguity`
- `insufficient_support`
- `scope_ambiguity`
- `candidate_needs_rewrite`
- `linkage_incomplete`

### 7.3 Required support links
Committed memory may link to:
- research archive artifact refs
- compiled-knowledge artifact refs
- source refs
- evidence refs
- related committed memory refs
- supersession refs
- merge lineage refs

### 7.4 Required hard rules
- no committed record may exist without `project_id`
- no committed record may exist without exactly one primary `memory_type`
- no committed record may store raw source body as memory body
- no committed record may masquerade as current truth

---

## 8. Required PostgreSQL schema

### 8.1 `memory_records`
Authoritative committed memory rows.

Required columns:
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
- `status text not null`
- `conflict_posture text not null default 'none'`
- `created_from_run_id text null`
- `schema_version text not null`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`
- `supersedes_memory_id text null`
- `superseded_by_memory_id text null`
- `merged_into_memory_id text null`

Required indexes:
- `(project_id, status, memory_type)`
- `(project_id, work_unit_id, status)`
- `(project_id, run_id, status)`
- `(project_id, updated_at)`

### 8.2 `memory_points`
Bounded remembered points.

Required columns:
- `memory_point_id text primary key`
- `memory_id text not null`
- `point_order integer not null`
- `point_text text not null`

### 8.3 `memory_claims`
Optional but required in v1 implementation if claim-level provenance is introduced now.
If not implemented in first slice, leave as a reserved next-slice table.

If implemented, required columns:
- `memory_claim_id text primary key`
- `memory_id text not null`
- `claim_text text not null`
- `claim_kind text not null`
- `claim_support_quality text not null`
- `claim_conflict_posture text not null`
- `claim_order integer not null`

### 8.4 `memory_links`
Required thin-link table.

Required columns:
- `memory_link_id text primary key`
- `memory_id text not null`
- `link_type text not null`
- `target_id text not null`
- `target_family text not null`
- `metadata_json jsonb null`

`link_type` must support at least:
- `research_artifact_ref`
- `history_record_ref`
- `knowledge_artifact_ref`
- `source_ref`
- `evidence_ref`
- `related_memory_ref`
- `supersedes_ref`
- `merged_into_ref`

### 8.5 `memory_embeddings`
Required vector table.

Required columns:
- `memory_id text primary key`
- `embedding_profile_id text not null`
- `embedding vector not null`
- `embedded_at timestamptz not null`

### 8.6 `memory_write_events`
Audit table for write decisions.

Required columns:
- `memory_write_event_id text primary key`
- `candidate_id text not null`
- `project_id text not null`
- `write_outcome text not null`
- `defer_reason_code text null`
- `decision_summary text not null`
- `related_memory_id text null`
- `created_at timestamptz not null`

### 8.7 `memory_retrieval_events`
Retrieval audit/evaluation table.

Required columns:
- `memory_retrieval_event_id text primary key`
- `project_id text not null`
- `purpose text not null`
- `returned_count integer not null`
- `explicit_hit_count integer not null`
- `lexical_hit_count integer not null`
- `semantic_hit_count integer not null`
- `contradiction_count integer not null`
- `created_at timestamptz not null`

### 8.8 `memory_maintenance_jobs`
Maintenance registry.

Required columns:
- `memory_maintenance_job_id text primary key`
- `job_type text not null`
- `project_id text not null`
- `job_status text not null`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`
- `details_json jsonb null`

---

## 9. Public API contract

The following public Memory API surface is required.
These are Python service-level contracts, not CLI commands.

### 9.1 Write-side API
- `build_candidate(input_bundle) -> MemoryCandidate`
- `evaluate_candidate(candidate) -> MemoryWriteDecision`
- `commit_candidate(candidate, decision) -> CommittedMemoryRecord`
- `process_candidate(input_bundle) -> MemoryWriteResult`

### 9.2 Retrieval API
- `retrieve(request: MemoryRetrievalRequest) -> MemoryRetrievalResult`
- `get_by_id(project_id, memory_id) -> CommittedMemoryRecord | None`
- `get_linked(project_id, linked_target_ids, purpose) -> list[CommittedMemoryRecord]`

### 9.3 Maintenance API
- `run_maintenance(job_request) -> MaintenanceJobResult`
- `refresh_conflict_labels(project_id) -> RefreshResult`
- `rebuild_indexes(project_id) -> RebuildResult`

### 9.4 API rules
- all public methods require explicit `project_id`
- no public method may expose global/system memory behavior
- no public method may return unbounded result sets by default
- retrieval methods must accept a `purpose`

---

## 10. Lawful support inputs

Memory may accept support from:
- research findings and bounded inferences
- research artifact refs
- history record refs
- compiled-knowledge artifact refs
- execution residue that passed through outcome/evaluation discipline
- outcome evidence refs
- evaluation verdict and rationale
- operator continuity cues
- bounded current-truth refs for linkage only

Memory may not accept as direct authority:
- raw article bodies
- full PDF text bodies as memory bodies
- full chat dumps
- raw prompts
- raw trace dumps
- generic daily news dumps
- model prose with no provenance linkage

---

## 11. Candidate creation rules

### 11.1 Only Memory creates candidates
No upstream module may create a canonical candidate object.
Upstream modules may only provide structured support inputs.

### 11.2 Candidate builder responsibilities
The builder must:
- collect lawful support inputs
- identify candidate-worthy durable continuity
- reject obvious archive-dump attempts early
- produce one candidate-sized unit per candidate
- avoid hybrid sludge candidates

### 11.3 Candidate splitting rule
If one input bundle contains multiple materially different continuity items, split them.
Do not build one vague “important things we learned” blob.

### 11.4 Candidate anti-patterns
Reject or rewrite candidates that are:
- raw summaries of whole briefs
- whole topic notes copied into memory
- current truth statements disguised as lessons
- one-off noise with no expected reuse value
- direction-shaping statements with weak support and no review path

---

## 12. Validation rules

Validation must fail closed.
At minimum it must check:
- required fields present
- project scope explicit
- no global/system scope
- no cross-project refs
- candidate expresses continuity, not current truth
- candidate body is bounded and concise enough
- support linkage exists
- raw residue is not embedded
- primary type can be assigned honestly
- candidate is not obviously a research artifact or knowledge artifact masquerading as memory

Validation failure outcome:
- `reject`

Ambiguous but salvageable outcome:
- `defer`

---

## 13. Dedupe and incremental-value rules

The dedupe stage must compare candidates against active committed memory in the same project.

At minimum it must detect:
- exact duplicates
- near duplicates
- low incremental value paraphrases
- replacement candidates that should supersede
- candidates that should merge into existing memory

### 13.1 Outcome rules
- exact duplicate with no meaningful new value -> `reject`
- low-value paraphrase -> `reject`
- clearly stronger replacement -> `supersede_existing`
- additive refinement of same memory unit -> `merge_into_existing`
- ambiguous relation -> `defer` with `dedupe_ambiguity`

---

## 14. Type assignment rules

Each committed memory must have exactly one primary type.

### 14.1 `episodic`
Use for:
- bounded remembered cases
- dated precedents
- major events with precedent value

Do not use for:
- raw history logs
- full recurring briefs

### 14.2 `semantic`
Use for:
- durable conclusions
- reusable patterns
- stable lessons grounded in support

### 14.3 `directional`
Use for:
- strategic anchors
- non-goals
- anti-drift boundaries
- direction-shaping rationale likely to affect later judgment

### 14.4 `operational`
Use for:
- practical know-how
- repeated working procedures
- recovery lessons
- execution habits that materially improve later work

### 14.5 Anti-blur rule
If the candidate needs two materially different roles, split it.
Do not invent fuzzy mixed types.

---

## 15. Scope assignment rules

### 15.1 Required v1 law
- `project_id` is mandatory
- `work_unit_id` optional
- `run_id` optional
- every committed memory has exactly one primary project scope

### 15.2 Scope narrowing
Use `work_unit_id` or `run_id` when the memory is materially local.
Do not over-promote local lessons into broad project memory.

### 15.3 Forbidden scope behavior
- no global/system memory assignment
- no cross-project linkage for convenience
- no missing `project_id`

---

## 16. Compression rules

Compression exists to make memory retrievable, inspectable, and prompt-budget-safe.

Compressed output must preserve:
- concise summary
- bounded remembered points
- why it matters
- support quality
- stability
- freshness sensitivity
- explicit links

Compression must not produce:
- report-sized prose
- stitched current-truth narratives
- hidden source dumps

---

## 17. Write decision policy

### 17.1 Decision outcomes
The write stage may return only:
- `write`
- `reject`
- `defer`
- `merge_into_existing`
- `supersede_existing`

### 17.2 Default auto-commit cases
Default `write` is allowed when all are true:
- support is `strong` or clearly sufficient for the candidate class
- scope is clear and narrow enough
- the candidate is not direction-shaping in a broad way
- the candidate is not behavior-shaping across the project in a risky way
- dedupe relation is clear
- provenance is intact

Typical examples:
- narrowly scoped `episodic` precedent with strong evidence
- strongly supported `semantic` lesson with clear reuse value
- localized `operational` lesson with strong support and low governance risk

### 17.3 Required `defer(review_required)` cases
Use `defer` with `defer_reason_code = review_required` when any of the following is true:
- candidate primary type is `directional`, except clearly trivial low-impact cases
- candidate is a project-wide or strongly behavior-shaping `operational` memory
- candidate has only `moderate` support but could materially steer future reasoning
- candidate would likely alter project direction interpretation
- candidate has unusually high downstream impact relative to its support quality

### 17.4 Required `reject` cases
Reject when:
- support is too weak
- continuity value is low
- candidate is archive dump behavior
- candidate tries to encode current truth
- candidate breaks scope law
- candidate embeds raw residue

### 17.5 Review surface rule
Do not add a new memory status for review.
Review-required stays represented as:
- `write_outcome = defer`
- `defer_reason_code = review_required`

---

## 18. Commit rules

Commit must:
- create the authoritative committed record
- create remembered points rows
- create link rows
- create write audit row
- create `memory_id` only here
- run inside a transaction strong enough to avoid partial semantic commit

If indexing fails after record commit:
- committed record remains authoritative
- backlog state must be recorded
- retrieval may degrade safely

---

## 19. Retrieval pipeline

### 19.1 Retrieval principles
- truth first, memory second
- scope filter before ranking
- explicit linkage before semantic search
- provenance-aware support outranks clean unsupported summary
- stale/conflicting memory remains labeled support
- bounded result packaging always

### 19.2 Required request fields
A retrieval request must include:
- `project_id`
- `purpose`
- `truth_anchor`
- optional `work_unit_id`
- optional `run_id`
- optional explicit linked target ids
- optional result budget/profile

### 19.3 Required stages
1. confirm scope and purpose
2. receive truth anchor from Context caller
3. explicit linked memory fetch
4. scoped lexical retrieval
5. scoped semantic retrieval
6. dedupe and merge candidates
7. rerank by scope fit, purpose fit, support quality, and recency
8. conflict labeling against truth anchor
9. budget trim
10. package output

### 19.4 Output shape
Return:
- memory summaries
- relevant remembered points / claims
- why the memory matters
- provenance links
- stale/conflict labels

Do not return by default:
- giant raw bodies
- full source text
- hidden stitched truth
- unbounded dump sets

### 19.5 Required ranking factors
At minimum reranking must consider:
- exact scope fit
- explicit link match
- purpose fit
- support quality
- status (`active` before `superseded`)
- freshness sensitivity when relevant
- recency as a secondary factor only

---

## 20. Retrieval relationship to Context

Context Assembly owns full context composition.
Memory owns only memory-side retrieval discipline.

Required context priority remains:
1. canonical truth
2. governance-relevant truth when needed
3. committed memory
4. compiled knowledge
5. research archive or raw sources when the purpose needs them

### 20.1 Hard rule
Memory retrieval and compiled-knowledge retrieval stay separate in v1.
Context may compose them.
Memory must not quietly call knowledge retrieval and present the result as memory.

### 20.2 Hard rule
When the caller needs:
- a dated brief
- an evidence-heavy bundle
- a thematic topic overview
- contradiction analysis across many sources

the correct behavior may be:
- return memory support **plus**
- return linked research archive or knowledge artifacts through the owning layer

Do not absorb them into memory bodies.

---

## 21. Research archive and knowledge interplay

### 21.1 Research Archive ownership
Research Archive owns:
- `research_brief`
- `research_comparison`
- `evidence_bundle`
- `source_set`
- `brief_history_record`
- `event_history_record`

Its fixed project-tree placement is:

```text
projects/<project_id>/research/artifacts/
projects/<project_id>/research/history/
projects/<project_id>/research/knowledge/
```

### 21.2 Memory relationship to Research Archive
Memory may:
- link to archive objects
- derive candidate-worthy continuity from them
- retrieve them separately through Context when needed

Memory may not:
- own their persistence
- embed them wholesale
- promote them automatically into memory

### 21.3 Memory relationship to Compiled Knowledge
Memory may:
- link to `source_digest`, `topic_note`, `concept_note`, `comparison_note`, `contradiction_note`, `open_questions_note`
- derive selective durable continuity from them

Memory may not:
- own compiled-knowledge persistence
- treat compiled knowledge as memory by default
- collapse thematic notes into semantic memory automatically

---

## 22. Maintenance jobs

Required maintenance jobs:
- `embedding_refresh`
- `dedupe_audit`
- `supersession_audit`
- `stale_memory_review`
- `broken_link_audit`
- `retrieval_quality_evaluation`
- `index_consistency_audit`
- `compression_refresh`
- `quarantine_review`

### 22.1 Maintenance rules
- maintenance may improve indexes and labels
- maintenance must not silently rewrite meaning
- maintenance must not repair truth
- maintenance must remain project-scoped and auditable

---

## 23. Observability

Required observability metrics/counters:
- candidate created count
- candidate rejected count
- candidate deferred count
- committed count
- duplicate rejection rate
- merge count
- supersession count
- retrieval latency by purpose
- explicit-link hit ratio
- lexical hit ratio
- semantic hit ratio
- contradiction-labeled return rate
- stale active memory count
- orphan link count
- missing embedding count
- quarantined record count

Observability is support only.
It must not become hidden semantics.

---

## 24. Failure handling

### 24.1 Write failures
- validation failure -> reject
- dedupe ambiguity -> defer
- commit failure -> no `memory_id`, no partial semantic record
- index failure after commit -> commit stands, backlog recorded

### 24.2 Retrieval failures
- vector backend unavailable -> degrade to explicit-link + lexical retrieval
- lexical index unavailable -> explicit-link + semantic retrieval if safe
- reranker failure -> transparent base scoring fallback
- over-budget result set -> trim aggressively

### 24.3 Integrity failures
- broken lineage -> quarantine from default retrieval
- wrong-project leakage -> hard fail
- state conflict surge -> return contradiction/stale labels, never patch truth

---

## 25. Required tests

### 25.1 Unit tests
- candidate validation
- type assignment
- scope assignment
- compression shape
- dedupe rules
- conflict labeling
- reranking
- budget trimming
- defer policy for `review_required`
- hard rejection of global/system scope

### 25.2 Integration tests
- write pipeline end to end against PostgreSQL
- retrieval pipeline with explicit + lexical + semantic merge
- supersession behavior
- merge behavior
- link integrity to research artifacts and knowledge artifacts
- index consistency behavior
- maintenance jobs behavior

### 25.3 Invariant tests
- only Memory creates candidates
- only committed `memory_id` values are canonically referenceable
- memory never overrides state
- wrong-project retrieval blocked
- research artifacts do not become memory automatically
- compiled-knowledge artifacts do not become memory automatically
- superseded memory does not outrank active replacement by default
- raw residue cannot be committed
- no global/system memory write or retrieval path exists in v1

### 25.4 Failure-path tests
- duplicate buildup pressure
- stale memory vs fresh truth
- vector backend unavailable
- malformed candidate payload
- index backlog after commit
- quarantine behavior
- review-required defer path

### 25.5 Acceptance tests
- strong narrow semantic candidate auto-commits
- broad directional candidate defers for review
- project-wide operational behavior-shaping candidate defers for review
- archive-dump candidate is rejected
- context receives memory and knowledge via separate retrieval paths

---

## 26. Implementation phases

### Phase M1 - Minimal bounded memory core
Build:
- core schemas
- candidate builder
- validator
- basic dedupe
- type assignment
- scope assignment
- compressor
- PostgreSQL store
- committed record model
- write audit table
- hard project-only scope enforcement
- no-global-memory tests

### Phase M2 - Hybrid retrieval core
Build:
- explicit linked fetch
- PostgreSQL FTS retrieval
- pgvector retrieval
- reranker
- conflict labeling
- bounded output packaging
- retrieval audit table

### Phase M3 - Research/archive and knowledge linkage
Build:
- thin links to research archive artifacts/history records
- thin links to compiled-knowledge artifacts
- archive-dump rejection rules
- retrieval contract compatibility with Context

### Phase M4 - Maintenance and hardening
Build:
- maintenance jobs
- quarantine handling
- index rebuild tools
- conflict refresh
- retrieval quality evaluation

### Phase M5 - Deferred only if needed later
Possible later work:
- external vector backend adapters
- richer claim graphs
- stronger relation-aware expansion

Do not start Phase M5 in the first implementation pass.

---

## 27. Explicit out-of-scope items for Memory v1

Do not implement now:
- global/system memory
- cross-project memory
- graph-native memory backend
- full manual review for all writes
- external semantic owner services
- unified support retrieval owner layer
- archive persistence inside Memory
- compiled-knowledge persistence inside Memory
- giant autonomous memory governance

---

## 28. Sharp implementation rules

1. Do not store everything.
2. Do not let arbitrary modules commit memory.
3. Do not let memory answer current-truth questions ahead of state.
4. Do not let memory absorb research history.
5. Do not let memory absorb compiled knowledge.
6. Do not introduce global/system memory in v1 “just for convenience.”
7. Do not use one giant blob table as fake architecture.
8. Do not dump top-k vectors into context.
9. Do not let superseded memory remain silently co-equal in retrieval.
10. Do not let external backends own semantics.
11. Do not weaken project isolation.
12. Do not erase provenance.
13. Do not silently rewrite memory meaning in maintenance jobs.

---

## 29. Final implementation target

Memory v1 is the following concrete system:

```text
PostgreSQL authoritative memory store
+ pgvector semantic retrieval projection
+ PostgreSQL full-text lexical retrieval
+ Jeff-owned candidate builder
+ Jeff-owned write pipeline
+ Jeff-owned retrieval pipeline
+ Jeff-owned maintenance jobs
+ hard project-only scope
+ no global/system memory
+ thin links to research archive and compiled knowledge
+ Context-owned final support composition
```

If implemented this way, Memory v1 will be useful without becoming sludge.
If the boundaries soften, it will rot fast and poison later reasoning.
