# RESEARCH_HISTORY_AND_ARCHIVE_ARCHITECTURE.md

Status: implementation architecture proposal for Jeff Research History and Archive  
Authority: subordinate to `PLANNING_AND_RESEARCH_SPEC.md`, `ARCHITECTURE.md`, `MEMORY_SPEC.md`, `KNOWLEDGE_LAYER_ARCHITECTURE.md`, `RAW_INGEST_AND_SOURCE_STORE_ARCHITECTURE.md`, `CONTEXT_SPEC.md`, `CORE_SCHEMAS_SPEC.md`, `STATE_MODEL_SPEC.md`, and `TESTS_PLAN.md`  
Purpose: define a concrete, buildable architecture for Jeff's research-owned history and archive layer, including durable research artifacts, evidence bundles, and dated research history records, without changing canonical truth, memory law, or compiled-knowledge law

---

## 1. Why this document exists

Jeff now has three distinct durable support strata that must not collapse into one blob:

1. raw source custody
2. research history / research archive
3. compiled knowledge

And then, narrower than all of them:

4. memory

The ownership boundary is already clear at the semantic level:
- research owns bounded inquiry and direct research outputs
- compiled knowledge owns durable thematic support organization across time
- memory owns distilled durable continuity only
- state owns current truth only

What is still missing is a buildable architecture for the **research-owned history and archive layer**.

Without this document, the system will drift into one or more bad failures:
- research briefs start being treated like memory
- evidence bundles get buried inside random artifact folders
- recurring research history becomes an accidental archive with no schema discipline
- compiled knowledge starts owning dated history just because it is durable
- operator-visible research support becomes hard to inspect, hard to compare, and hard to trace

This document exists to stop that.

---

## 2. Core architectural decision

Jeff will treat **Research History and Archive** as a **Research-owned sublayer**, not as:
- memory
- compiled knowledge
- canonical truth
- a new top-level semantic layer

That means:

- raw source custody remains below it
- research history / archive remains inside Research ownership
- compiled knowledge remains downstream of research/archive when thematic synthesis is needed
- memory remains downstream of both research history and compiled knowledge when durable continuity is worth preserving
- context may retrieve from research history when the purpose actually requires dated research support or evidence-heavy support

Conceptually:

```text
raw source custody
  -> research ingestion / extraction
  -> research artifacts + history records
  -> compiled knowledge (optional)
  -> memory candidate consideration (optional)
```

This is the cleanest ownership model.

---

## 3. What this layer is

Research History and Archive is the durable, source-aware support layer for bounded research outputs and dated research records.

It owns durable research support objects such as:
- `research_brief`
- `research_comparison`
- `evidence_bundle`
- `source_set`
- `brief_history_record`
- `event_history_record`

This layer is meant to preserve:
- what question was asked
- what scope the research belonged to
- which sources were used
- what findings were extracted
- what inference was drawn
- what remained uncertain
- what dated research outputs were produced over time

It is meant to support:
- operator inspection
- source-aware reuse
- recurring brief history
- evidence lookup
- cross-run research continuity
- downstream compiled-knowledge generation
- downstream memory consideration

It is not meant to own:
- current truth
- thematic topic maintenance across time
- memory write semantics
- transition semantics
- policy or approval meaning

---

## 4. What this layer is not

Research History and Archive is not:
- canonical truth
- memory
- compiled knowledge
- raw source custody
- a generic artifact dump
- a session transcript archive
- trace storage
- a hidden knowledge wiki
- a replacement for context assembly
- an excuse to keep every noisy web scrap forever without structure

This layer is still bounded support.

---

## 5. Design principles

### 5.1 Research history is not memory
A dated brief, evidence bundle, or research comparison may be durable and valuable without being a memory entry.
Memory remains selective distilled continuity.

### 5.2 Research history is not compiled knowledge
Research history preserves bounded research outputs and dated support records.
Compiled knowledge organizes themes across time and across related sources into navigable support notes.
These are different roles.

### 5.3 Research history is not truth
Research outputs may be source-backed and well supported, but they do not become current truth by existing.
Truth still lives in canonical state only.

### 5.4 Provenance must survive
Source linkage and evidence lineage are mandatory.
If provenance disappears, Jeff starts pretending that clean summaries are enough.

### 5.5 Dated history must stay explicit
A brief produced on one date is not a timeless fact.
A historical record must preserve date and freshness posture rather than pretending permanent currentness.

### 5.6 Project scope remains hard
Research archive objects are project-scoped in v1.
Jeff does not get a free global research soup.

### 5.7 Research archive must stay queryable
Durability without retrieval is just hoarding.
This layer must stay inspectable and queryable by type, scope, date, and support links.

### 5.8 Research archive must stay bounded
Do not archive everything just because it passed through the system.
This layer stores durable research support outputs, not every intermediate scratch artifact.

---

## 6. Ownership boundary

### 6.1 Owned by Research History and Archive
The following support-object families belong here:

- `research_brief`
- `research_comparison`
- `evidence_bundle`
- `source_set`
- `brief_history_record`
- `event_history_record`

### 6.2 Not owned here
Not owned here:
- raw source originals and source custody metadata
- `source_digest`
- `topic_note`
- `concept_note`
- `comparison_note` in the compiled-knowledge sense
- `contradiction_note`
- `open_questions_note`
- committed memory records
- memory candidates
- canonical state truth

### 6.3 Downstream relationships
Research History and Archive may feed:
- direct operator inspection
- later research reuse
- compiled knowledge generation
- memory candidate consideration

But those downstream layers do not retroactively take ownership of the original research record.

---

## 7. Artifact families and meanings

## 7.1 `research_brief`
A bounded direct-output research artifact answering a bounded question or objective.

Typical contents:
- question or objective
- scope
- findings
- inference
- uncertainty
- source refs
- recommendation or implication when justified

Use when:
- the research result is itself a useful durable support object
- the operator may want to inspect it again later
- later work may reuse the exact brief

## 7.2 `research_comparison`
A bounded research output focused on comparing alternatives, approaches, tools, claims, or sources.

Typical contents:
- comparison target set
- comparison criteria
- comparative findings
- contradictions
- uncertainty
- recommendation only when justified

## 7.3 `evidence_bundle`
A durable, evidence-bearing support object preserving the extracted support used for a bounded research question.

Typical contents:
- source refs
- extracted evidence items
- evidence groupings
- claim-to-evidence mapping
- contradiction markers
- extraction quality notes

This is not a memory object.
It is an inspectable support bundle.

## 7.4 `source_set`
A durable record of the bounded source set used for a research task.

Typical contents:
- source refs
- source ordering or ranking hints
- selection rationale
- coverage notes
- exclusions or rejected-source reasons when relevant

This is useful for:
- reproducibility
- auditability
- later refresh or rebuild
- comparison of research runs

## 7.5 `brief_history_record`
A dated historical record of one recurring or repeated brief run.

Use when:
- a recurring daily, weekly, or event-driven brief produced a durable historical output
- the date and time of the research result materially matter
- later inspection may need to compare this brief to later briefs

This is history, not memory.

## 7.6 `event_history_record`
A dated, source-backed historical record of a meaningful event or observed development captured through research.

Use when:
- the record is tied to a time-sensitive event
- it should remain available as history
- it may later support compiled knowledge or memory, but is not itself memory by default

This is still not current truth.

---

## 8. High-level architecture

```text
raw source custody
    |
    v
+--------------------------------------+
| Research Request / Plan              |
+--------------------------------------+
    |
    v
+--------------------------------------+
| Discovery / Extraction / Evidence    |
+--------------------------------------+
    |
    v
+--------------------------------------+
| Research Artifact Builder            |
| - research_brief                     |
| - research_comparison                |
| - evidence_bundle                    |
| - source_set                         |
| - brief_history_record               |
| - event_history_record               |
+--------------------------------------+
    |
    v
+--------------------------------------+
| Research Archive Registry            |
| - artifact identity                  |
| - type                               |
| - scope                              |
| - history timestamps                 |
| - provenance                         |
| - lineage                            |
+--------------------------------------+
    |
    +------------------> direct retrieval / inspection
    |
    +------------------> compiled knowledge generation
    |
    +------------------> optional memory handoff signals
```

---

## 9. Persistence placement

This is now frozen.

Research History and Archive lives under the project tree in the Research-owned area.

Recommended layout:

```text
projects/
  <project_id>/
    research/
      artifacts/
      history/
      knowledge/
```

With these meanings:

- `research/artifacts/`  
  durable bounded direct research outputs and support artifacts such as:
  - `research_brief`
  - `research_comparison`
  - `evidence_bundle`
  - `source_set`

- `research/history/`  
  dated recurring or event-oriented historical research records such as:
  - `brief_history_record`
  - `event_history_record`

- `research/knowledge/`  
  compiled knowledge only, not owned by this layer

This separation is intentional.

### 9.1 Why not put this in memory
Because research history is not memory.

### 9.2 Why not put this outside the project tree
Because unlike raw source custody, these are operator-meaningful project support objects.

### 9.3 Why not mix it with compiled knowledge
Because direct research outputs and dated history are not the same thing as thematic notes.

---

## 10. Recommended archive layout examples

### 10.1 Artifact storage
```text
projects/
  <project_id>/
    research/
      artifacts/
        <artifact_id>.json
```

### 10.2 History storage
```text
projects/
  <project_id>/
    research/
      history/
        <history_record_id>.json
```

Optional future structured directories are allowed, for example by date or family, but the family split above should remain visible.

---

## 11. Identity and scope model

Each research archive object should have a Jeff-issued opaque ID.

Suggested families:
- `research_artifact_id`
- `history_record_id`

Or one shared `artifact_id` plus explicit `artifact_family`, if the project wants to stay closer to existing artifact identity discipline.

Required scope:
- `project_id`
- optional `work_unit_id`
- optional `run_id`

Rules:
- every archived research object belongs to one project in v1
- work-unit and run locality may narrow retrieval and lineage
- cross-project archive objects are forbidden in v1

---

## 12. Recommended schema shape

A shared high-level shape should include:

```json
{
  "artifact_id": "art_...",
  "artifact_family": "research_brief",
  "project_id": "proj_...",
  "work_unit_id": null,
  "run_id": null,
  "title": "Daily market brief",
  "summary": "Short bounded summary.",
  "question_or_objective": "What changed today in X?",
  "findings": [],
  "inference": [],
  "uncertainty": [],
  "source_refs": [],
  "evidence_refs": [],
  "generated_at": "2026-04-18T08:00:00Z",
  "effective_date": "2026-04-18",
  "staleness_sensitivity": "high",
  "derived_from_artifact_ids": [],
  "schema_version": "1.0"
}
```

This is implementation guidance, not final shared-schema law.

---

## 13. Required fields by family

### 13.1 `research_brief`
Must carry:
- question or objective
- findings
- inference
- uncertainty
- source refs
- generation timestamp

### 13.2 `research_comparison`
Must carry:
- comparison target set
- criteria
- findings
- contradictions or uncertainty
- source refs

### 13.3 `evidence_bundle`
Must carry:
- evidence items
- source refs
- claim/evidence relationships where possible
- extraction quality or caution markers

### 13.4 `source_set`
Must carry:
- source refs
- source selection scope
- source ordering or grouping if relevant

### 13.5 `brief_history_record`
Must carry:
- date or period
- source refs
- brief summary
- freshness posture
- optional links to preceding / following records

### 13.6 `event_history_record`
Must carry:
- event date or observed date
- event summary
- source refs
- uncertainty if event framing is incomplete

---

## 14. Provenance rules

Provenance is mandatory for this layer.

Every meaningful research archive object should preserve:
- source refs
- extraction or evidence refs when relevant
- generation timestamp
- run linkage when applicable
- question or objective linkage
- derived-from linkage when applicable

Allowed support linkage includes:
- raw source refs from source custody
- evidence bundle refs
- source set refs
- upstream research artifact refs
- downstream compiled knowledge refs or memory refs later, but only as thin links

This layer must never turn into “summary with nowhere it came from.”

---

## 15. Dated history rules

History records must stay explicitly historical.

Rules:
- dated records must preserve the date or period they represent
- history records must not masquerade as timeless facts
- retrieval must preserve their dated nature
- repeated daily or weekly outputs should remain individually identifiable
- history records may later be compared, clustered, or compiled into thematic knowledge
- history records do not become memory automatically just because they recur

This is the difference between:
- “we observed this on that date”
and
- “this is a durable conclusion Jeff should remember”

Those are not the same thing.

---

## 16. Relationship to compiled knowledge

Compiled knowledge is downstream of research/archive when thematic organization across time is useful.

Examples:
- multiple `research_brief` items may contribute to one `topic_note`
- multiple `event_history_record` items may contribute to one `contradiction_note`
- multiple `evidence_bundle` items may contribute to one `comparison_note`

Research/archive owns the direct outputs and dated history.
Compiled knowledge owns the later thematic compression and navigation layer.

That boundary must remain hard.

---

## 17. Relationship to memory

Memory is downstream and narrower.

Research/archive objects may support memory when they reveal:
- durable pattern
- repeated lesson
- important rationale
- useful precedent
- enduring strategic boundary

But:
- a `research_brief` is not memory
- an `event_history_record` is not memory
- an `evidence_bundle` is not memory
- a `source_set` is not memory

The correct flow is:

```text
research archive object
  -> optional memory candidate consideration
  -> write / reject / defer by Memory
```

Only Memory creates memory candidates.

---

## 18. Relationship to context assembly

Research/archive artifacts are eligible support for context assembly when the current purpose actually needs them.

Examples:
- direct research reuse
- evaluation support that needs dated evidence
- operator explanation that needs the original brief
- contradiction follow-up across previous history records

They should not be dumped by default.

The retrieval order remains subordinate to truth-first context law:
- current truth first
- governance-relevant truth when relevant
- memory
- compiled knowledge
- research/archive objects or raw sources when the purpose needs more direct support or dated support

This layer should be available, not overused.

---

## 19. Retrieval model

The archive layer should support at least:

- exact fetch by artifact/history id
- fetch by family
- fetch by project / work_unit / run scope
- fetch by date or period
- fetch by question/objective text
- source-aware lookup
- related-record lookup
- freshness-sensitive lookup where relevant

Retrieval should prefer:
- exact scope
- explicit date filters for history
- stronger provenance
- bounded result packaging

Retrieval should avoid:
- dumping large numbers of near-duplicate briefs
- mixing history and thematic knowledge invisibly
- using archive history as fake current truth

---

## 20. Recommended module layout

Recommended Research-owned package structure:

```text
jeff/cognitive/research/
  __init__.py
  archive/
    __init__.py
    ids.py
    models.py
    artifact_builder.py
    history_builder.py
    registry.py
    store.py
    retrieval.py
    lineage.py
    telemetry.py
    api.py
```

Suggested roles:
- `ids.py`: typed identifiers
- `models.py`: shared archive object models
- `artifact_builder.py`: research artifact family creation
- `history_builder.py`: dated history record creation
- `registry.py`: persistence registry and indexing
- `store.py`: filesystem storage and read/write helpers
- `retrieval.py`: bounded retrieval
- `lineage.py`: derived-from and temporal linkage
- `telemetry.py`: observability
- `api.py`: public contract for research archive access

This should remain inside Research ownership, not in Memory and not in Knowledge.

---

## 21. Build pipeline

The archive build pipeline should look like:

```text
research request
  -> evidence prep
  -> findings / inference separation
  -> artifact family decision
  -> archive object construction
  -> provenance binding
  -> registry write
  -> optional downstream signals
```

### 21.1 Artifact family decision
Choose whether the output is:
- direct research artifact
- comparison artifact
- evidence bundle
- source set
- dated brief-history record
- dated event-history record

### 21.2 Registry write
Write the object with:
- identity
- family
- scope
- provenance
- timestamps
- lineage

### 21.3 Optional downstream signals
Emit support signals for:
- compiled knowledge generation
- memory candidate consideration
- operator surfacing

Do not create downstream objects automatically by semantic shortcut.

---

## 22. Lineage model

Archive objects should preserve lineage explicitly.

Useful lineage fields:
- `derived_from_source_ids`
- `derived_from_artifact_ids`
- `previous_history_record_id`
- `next_history_record_id`
- `supersedes_artifact_id`
- `superseded_by_artifact_id`

Rules:
- lineage must remain inspectable
- rebuild or refresh must not erase historical traceability
- recurring brief series should keep date-aware continuity when useful

---

## 23. Maintenance jobs

This layer should support bounded maintenance jobs such as:

- archive integrity audit
- missing-provenance scan
- stale-history tagging for freshness-sensitive domains
- orphan evidence-bundle detection
- duplicate-brief detection
- link integrity audit
- recurring-series continuity audit

Maintenance may improve archive health.
It must not silently rewrite the meaning of archived research outputs.

---

## 24. Failure modes

This layer must explicitly guard against:

### 24.1 Archive-memory blur
A history record starts being treated like memory by convenience.

### 24.2 Archive-knowledge blur
A research brief starts being treated like a topic note by convenience.

### 24.3 Provenance loss
The record becomes readable but no longer inspectable.

### 24.4 Date loss
A historical record starts sounding timeless.

### 24.5 Raw-sludge archive
The archive becomes a dump of noisy extracts and scraps.

### 24.6 Weak-source confidence
A clean brief overstates support from weak sources.

### 24.7 Family drift
The same object type appears under multiple incompatible meanings.

### 24.8 Cross-project leakage
Archive retrieval crosses projects casually.

---

## 25. Security and safety posture

This is not a full security spec, but the archive layer should assume:
- extracted content may be noisy
- web-derived material may be messy
- metadata may be incomplete
- time-sensitive support may go stale quickly

Therefore:
- provenance must be mandatory
- dated history must stay dated
- scope must stay explicit
- archive objects must stay bounded
- direct source links should remain inspectable

---

## 26. Test strategy

Minimum required test coverage should include:

- `research_brief` preserves source refs
- `research_comparison` preserves compared alternatives clearly
- `evidence_bundle` preserves source/evidence linkage
- `source_set` preserves bounded source selection
- `brief_history_record` preserves date / period correctly
- `event_history_record` preserves dated event framing correctly
- wrong-project retrieval is rejected
- archive objects do not become memory automatically
- archive objects do not become compiled knowledge automatically
- lineage survives rebuild or refresh where applicable
- stale/freshness-sensitive historical retrieval stays labeled when relevant

This layer needs anti-drift tests because archive/knowledge/memory blur is one of the easiest ways to rot the system.

---

## 27. Recommended first implementation slice

The first useful slice should stay narrow:

1. `research_brief`
2. `research_comparison`
3. `evidence_bundle`
4. `source_set`
5. `brief_history_record`
6. archive registry and persistence
7. exact retrieval by id + family + scope
8. provenance integrity tests
9. anti-blur tests versus Memory and Compiled Knowledge

Do not try to build the full recurring-brief intelligence system in one shot.
Get ownership and archival discipline right first.

---

## 28. Deferred work

Deferred beyond the initial slice:
- richer recurring-series analysis
- temporal diffing across brief history
- visual timelines over history records
- stronger freshness-aware archive retrieval
- automatic suggestions for compiled-knowledge generation
- richer event clustering
- connector-aware archive ingestion from future research modes

Deferred expansion does not weaken the ownership boundary.

---

## 29. Final architecture summary

Jeff should treat Research History and Archive as a Research-owned durable support sublayer.

That means:

- raw source custody stays below it
- research direct outputs and dated history live here
- compiled knowledge stays separate and downstream
- memory stays narrower and downstream
- truth stays elsewhere
- provenance survives
- date-sensitive history stays explicitly historical
- direct research outputs stay inspectable
- archive does not collapse into memory
- archive does not collapse into compiled knowledge

If this boundary stays hard, Jeff gets durable research continuity without archive sludge or semantic blur.
If it softens, research, knowledge, and memory will collapse back into one garbage pile.
